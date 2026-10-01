"""Account endpoints: CSRF on anonymous transitions, no token/account enumeration in replies."""

from django.contrib.auth import logout
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import Throttled
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from backend.core import accounts
from backend.core.api import handled
from backend.core.consents import POLICIES, POLICY_VERSION, record_consent
from backend.core.match_ingestion import active_owner
from backend.core.models import (
    AccountEmail,
    AccountSession,
    ConsentReceipt,
    MatchSuppression,
    Profile,
)
from backend.core.ownership import lock_owner
from backend.core.security import consume_budget

ACCEPTED = {
    "status": "ACCEPTED",
    "message": "If the details are eligible, a link will be prepared in the local test mailbox. No live email is sent.",
}


def public_budget(request):
    delay = consume_budget("account-public", request.META.get("REMOTE_ADDR", "unknown"), 10, 60)
    if delay:
        raise Throttled(wait=delay)


class Registration(serializers.Serializer):
    username = serializers.CharField(max_length=30)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=256, trim_whitespace=False)
    policy_version = serializers.CharField(max_length=60)
    accepted_terms = serializers.BooleanField()


@api_view(["GET"])
@permission_classes([AllowAny])
def policy(request):
    return Response(
        {
            "version": POLICY_VERSION,
            "policies": POLICIES,
            "registration_enabled": accounts.local_accounts_enabled(),
            "delivery": "LOCAL_TEST_MAILBOX",
            "minimum_password_length": 12,
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
@handled
def registration(request):
    public_budget(request)
    data = Registration(data=request.data)
    data.is_valid(raise_exception=True)
    values = data.validated_data
    if not values.pop("accepted_terms"):
        raise ValidationError("Accept the local account policy to register")
    try:
        accounts.register(
            values["username"], values["email"], values["password"], values["policy_version"]
        )
    except IntegrityError:
        pass  # Concurrent duplicate gets the same non-enumerating result.
    return Response(ACCEPTED, status=202)


class LinkRequest(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    purpose = serializers.ChoiceField(choices=["VERIFY", "RESET"])


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
@handled
def request_link(request):
    public_budget(request)
    if not accounts.local_accounts_enabled():
        return Response({"error": "Local account delivery is disabled"}, status=503)
    data = LinkRequest(data=request.data)
    data.is_valid(raise_exception=True)
    accounts.request_link(**data.validated_data)
    return Response(ACCEPTED, status=202)


class Confirmation(serializers.Serializer):
    token = serializers.CharField(max_length=100, trim_whitespace=False)
    purpose = serializers.ChoiceField(choices=["VERIFY", "RESET"])
    password = serializers.CharField(max_length=256, trim_whitespace=False, required=False)


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
@handled
def confirm(request):
    public_budget(request)
    data = Confirmation(data=request.data)
    data.is_valid(raise_exception=True)
    if data.validated_data["purpose"] == "RESET" and "password" not in data.validated_data:
        raise ValidationError("A new password is required")
    accounts.consume_challenge(**data.validated_data)
    if data.validated_data["purpose"] == "RESET" and request.user.is_authenticated:
        logout(request)
    return Response({"status": "CONFIRMED", "message": "You can now sign in."})


@api_view(["GET"])
@handled
def account_details(request):
    address = AccountEmail.objects.filter(owner=request.user).first()
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return Response(
        {
            "username": request.user.username,
            "email": address.normalized if address else None,
            "email_verified": bool(address and address.verified_at),
            "processing_withdrawn": bool(profile.processing_withdrawn_at),
            "processing_consent": bool(profile.processing_consent_at),
            "training_consent": bool(profile.training_consent_at),
            "policy_version": POLICY_VERSION,
            "suppressed_matches": MatchSuppression.objects.filter(owner=request.user).count(),
            "sessions": [
                {
                    "id": item.pk,
                    "created_at": item.created_at,
                    "expires_at": item.expires_at,
                    "current": str(item.pk) == request.session.get("account_session"),
                }
                for item in AccountSession.objects.filter(
                    owner=request.user, revoked_at=None, expires_at__gt=timezone.now()
                ).order_by("-created_at")[:100]
            ],
            "consent_history": list(
                ConsentReceipt.objects.filter(owner=request.user)
                .order_by("-created_at")
                .values("id", "scope", "action", "policy_version", "created_at")[:100]
            ),
        }
    )


class PasswordChange(serializers.Serializer):
    current_password = serializers.CharField(max_length=256, trim_whitespace=False)
    new_password = serializers.CharField(max_length=256, trim_whitespace=False)


@api_view(["POST"])
@handled
def password_change(request):
    data = PasswordChange(data=request.data)
    data.is_valid(raise_exception=True)
    accounts.change_password(
        request.user, data.validated_data["current_password"], data.validated_data["new_password"]
    )
    logout(request)
    return Response({"status": "PASSWORD_CHANGED", "signed_out": True})


class EmailChange(serializers.Serializer):
    password = serializers.CharField(max_length=256, trim_whitespace=False)
    email = serializers.EmailField(max_length=254)


@api_view(["POST"])
@handled
def email_change(request):
    data = EmailChange(data=request.data)
    data.is_valid(raise_exception=True)
    accounts.change_email(request.user, **data.validated_data)
    return Response(ACCEPTED, status=202)


@api_view(["DELETE"])
@handled
@transaction.atomic
def revoke_session(request, session_id):
    active_owner(request.user)
    entry = AccountSession.objects.get(pk=session_id, owner=request.user)
    entry.revoked_at = timezone.now()
    entry.save(update_fields=["revoked_at"])
    current = str(entry.pk) == request.session.get("account_session")
    if current:
        logout(request)
    return Response({"revoked": True, "signed_out": current})


@api_view(["POST"])
@handled
@transaction.atomic
def logout_all(request):
    owner = lock_owner(request.user.pk)
    accounts.revoke_sessions(owner)
    logout(request)
    return Response({"signed_out": True})


class ConsentInput(serializers.Serializer):
    scope = serializers.ChoiceField(choices=["PROCESSING", "TRAINING"])
    action = serializers.ChoiceField(choices=["GRANT", "WITHDRAW"])
    policy_version = serializers.CharField(max_length=60)
    request_id = serializers.UUIDField()
    confirmed = serializers.BooleanField()


@api_view(["POST"])
@handled
def consent(request):
    data = ConsentInput(data=request.data)
    data.is_valid(raise_exception=True)
    values = data.validated_data
    if not values.pop("confirmed"):
        raise ValidationError("Confirm the consent change")
    values["version"] = values.pop("policy_version")
    receipt = record_consent(request.user, **values)
    return Response({"receipt_id": receipt.pk, "scope": receipt.scope, "action": receipt.action})

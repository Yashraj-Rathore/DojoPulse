"""Local account lifecycle. Never sends email to an external transport."""

import hashlib
import json
import re
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from backend.core.consents import POLICY_VERSION, policy_digest
from backend.core.models import (
    AccountChallenge,
    AccountEmail,
    AccountSession,
    ConsentReceipt,
    Profile,
)
from backend.core.ownership import lock_owner
from backend.core.security import consume_budget
from backend.core.storage import private_path


def local_accounts_enabled():
    return settings.DEBUG and settings.LOCAL_ACCOUNT_SIGNUP


def email_value(value):
    normalized = value.strip().lower()
    if len(normalized) > 254:
        raise ValidationError("Email address is too long")
    validate_email(normalized)
    return normalized


def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def mail_path(challenge):
    return private_path(f"account-mail/{challenge.owner_id}/{challenge.pk}.json")


def issue_challenge(owner, email, purpose, *, activates_account=False):
    """Caller holds the owner lock. Only hashes are stored in the database.

    Development delivery is a private local mailbox. Its secrets never appear in HTTP
    responses, application logs or an external message. Expired files are purged by maintenance.
    """
    if not local_accounts_enabled():
        raise ValidationError("Local account delivery is disabled")
    if consume_budget("account-mail", owner.pk, 3, 3600):
        return
    token = secrets.token_urlsafe(32)
    AccountChallenge.objects.filter(owner=owner, purpose=purpose, consumed_at=None).update(
        consumed_at=timezone.now()
    )
    challenge = AccountChallenge.objects.create(
        owner=owner,
        purpose=purpose,
        activates_account=activates_account,
        email=email,
        token_digest=token_digest(token),
        auth_state=owner.get_session_auth_hash(),
        expires_at=timezone.now() + timedelta(minutes=30),
    )
    # Trusted configured origin, never request Host. URL fragment is not sent as a request URL.
    envelope = {
        "to": email,
        "purpose": purpose,
        "expires_at": challenge.expires_at.isoformat(),
        "url": settings.ACCOUNT_PUBLIC_ORIGIN + "/#account=" + purpose.lower() + ":" + token,
    }
    path = mail_path(challenge)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("x", encoding="utf-8") as stream:
        path.chmod(0o600)
        json.dump(envelope, stream)
    return challenge


@transaction.atomic
def register(username, email, password, version):
    if not local_accounts_enabled():
        raise ValidationError("Local registration is disabled")
    name = username.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{2,29}", name) or version != POLICY_VERSION:
        raise ValidationError("Use a 3–30 character username and review the current policy")
    email = email_value(email)
    User = get_user_model()
    candidate = User(username=name, email=email, is_active=False)
    validate_password(password, candidate)
    # Perform hashing on both paths; do not reveal which address/username already exists.
    candidate.set_password(password)
    if (
        User.objects.filter(username__iexact=name).exists()
        or AccountEmail.objects.filter(normalized=email).exists()
        or User.objects.filter(email__iexact=email).exists()
    ):
        return
    candidate.save()
    AccountEmail.objects.create(owner=candidate, normalized=email)
    Profile.objects.create(user=candidate)
    ConsentReceipt.objects.create(
        owner=candidate,
        scope="TERMS",
        action="GRANT",
        policy_version=version,
        policy_digest=policy_digest("TERMS"),
        source="REGISTRATION",
    )
    issue_challenge(candidate, email, "VERIFY", activates_account=True)


@transaction.atomic
def request_link(email, purpose):
    normalized = email_value(email)
    address = AccountEmail.objects.select_related("owner").filter(normalized=normalized).first()
    if not address:
        return
    owner = lock_owner(address.owner_id)
    if Profile.objects.filter(user=owner, deleted_at__isnull=False).exists():
        return
    if purpose == "RESET" and (not owner.is_active or not address.verified_at):
        return
    if purpose == "VERIFY" and address.verified_at:
        return
    issue_challenge(owner, normalized, purpose, activates_account=not address.verified_at)


@transaction.atomic
def consume_challenge(token, purpose, password=None):
    if not local_accounts_enabled() or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise ValidationError("Link is invalid, expired or already used")
    initial = AccountChallenge.objects.filter(
        token_digest=token_digest(token), purpose=purpose
    ).first()
    if not initial:
        raise ValidationError("Link is invalid, expired or already used")
    owner = lock_owner(initial.owner_id)
    challenge = AccountChallenge.objects.select_for_update().get(pk=initial.pk)
    if (
        challenge.consumed_at
        or challenge.expires_at <= timezone.now()
        or not secrets.compare_digest(challenge.auth_state, owner.get_session_auth_hash())
        or Profile.objects.filter(user=owner, deleted_at__isnull=False).exists()
    ):
        raise ValidationError("Link is invalid, expired or already used")
    if purpose == "RESET":
        address = AccountEmail.objects.get(owner=owner)
        if not owner.is_active or not address.verified_at or address.normalized != challenge.email:
            raise ValidationError("Link is invalid, expired or already used")
        validate_password(password, owner)
        owner.set_password(password)
        owner.save(update_fields=["password"])
        revoke_sessions(owner)
        AccountChallenge.objects.filter(owner=owner, consumed_at=None).update(
            consumed_at=timezone.now()
        )
    else:
        if not owner.is_active and not challenge.activates_account:
            raise ValidationError("Link is invalid, expired or already used")
        if (
            challenge.activates_account
            and AccountEmail.objects.filter(owner=owner, verified_at__isnull=False).exists()
        ):
            raise ValidationError("Link is invalid, expired or already used")
        if AccountEmail.objects.filter(normalized=challenge.email).exclude(owner=owner).exists():
            raise ValidationError("Address is unavailable; request another verification")
        AccountEmail.objects.update_or_create(
            owner=owner, defaults={"normalized": challenge.email, "verified_at": timezone.now()}
        )
        owner.email = challenge.email
        owner.is_active = True
        owner.save(update_fields=["email", "is_active"])
    challenge.consumed_at = timezone.now()
    challenge.save(update_fields=["consumed_at"])
    return owner


def revoke_sessions(owner):
    from backend.core.companion import revoke_all

    revoke_all(owner)
    profile, _ = Profile.objects.get_or_create(user=owner)
    profile.session_epoch += 1
    profile.save(update_fields=["session_epoch"])
    AccountSession.objects.filter(owner=owner, revoked_at=None).update(revoked_at=timezone.now())


@transaction.atomic
def track_session(request, *, authenticating=False):
    current = lock_owner(request.user.pk)
    profile, _ = Profile.objects.get_or_create(user=current)
    if (
        not current.is_active
        or profile.deleted_at
        or current.password != request.user.password
        or (not authenticating and profile.session_epoch != request.session.get("account_epoch", 0))
    ):
        logout(request)
        return
    request.session["account_epoch"] = profile.session_epoch
    entry, _ = AccountSession.objects.get_or_create(
        owner=request.user,
        key_digest=token_digest(request.session.session_key),
        defaults={"expires_at": request.session.get_expiry_date()},
    )
    request.session["account_session"] = str(entry.pk)


def forget_session(sender, request, user, **kwargs):
    if request is not None and user is not None:
        AccountSession.objects.filter(
            pk=request.session.get("account_session"), owner=user, revoked_at=None
        ).update(revoked_at=timezone.now())


class AccountSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile, _ = Profile.objects.get_or_create(user=request.user)
            session_id = request.session.get("account_session")
            if (
                profile.session_epoch != request.session.get("account_epoch", 0)
                or profile.deleted_at
            ):
                logout(request)
            elif (
                session_id
                and not AccountSession.objects.filter(
                    pk=session_id,
                    owner=request.user,
                    key_digest=token_digest(request.session.session_key),
                    revoked_at=None,
                    expires_at__gt=timezone.now(),
                ).exists()
            ):
                logout(request)
            elif not session_id:
                track_session(request)
        return self.get_response(request)


@transaction.atomic
def change_password(owner, current, replacement):
    owner = lock_owner(owner.pk)
    if not owner.is_active or not owner.check_password(current):
        raise ValidationError("Current password is incorrect")
    validate_password(replacement, owner)
    owner.set_password(replacement)
    owner.save(update_fields=["password"])
    revoke_sessions(owner)
    AccountChallenge.objects.filter(owner=owner, consumed_at=None).update(
        consumed_at=timezone.now()
    )


@transaction.atomic
def change_email(owner, password, email):
    owner = lock_owner(owner.pk)
    if not owner.is_active or not owner.check_password(password):
        raise ValidationError("Current password is incorrect")
    normalized = email_value(email)
    if (
        AccountEmail.objects.filter(normalized=normalized).exclude(owner=owner).exists()
        or get_user_model().objects.filter(email__iexact=normalized).exclude(pk=owner.pk).exists()
    ):
        return
    issue_challenge(owner, normalized, "VERIFY")


def cleanup_account_mail(owner_id=None):
    root = private_path("account-mail")
    if not root.exists():
        return 0
    removed = 0
    paths = (
        (root / str(int(owner_id))).glob("*.json")
        if owner_id is not None
        else root.glob("*/*.json")
    )
    for path in paths:
        resolved = path.resolve()
        if not resolved.is_relative_to(root.resolve()) or not path.parent.name.isdecimal():
            continue
        try:
            challenge_id = uuid.UUID(path.stem)
        except ValueError:
            continue
        with transaction.atomic():
            # Serialize with issuance/consumption. A new registration may have written
            # its envelope before its owner row is visible to this transaction.
            owner = (
                get_user_model()
                .objects.select_for_update()
                .filter(pk=int(path.parent.name))
                .first()
            )
            if owner is None:
                try:
                    if path.stat().st_mtime > (timezone.now() - timedelta(minutes=30)).timestamp():
                        continue
                except FileNotFoundError:
                    continue
            live = AccountChallenge.objects.filter(
                pk=challenge_id,
                owner_id=int(path.parent.name),
                consumed_at=None,
                expires_at__gt=timezone.now(),
            ).exists()
            if owner_id is not None or not live:
                path.unlink(missing_ok=True)
                removed += 1
    return removed

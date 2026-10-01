from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "backend.core"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from django.contrib.auth.signals import user_logged_out

        from backend.core.accounts import forget_session

        user_logged_out.connect(forget_session, dispatch_uid="dojopulse.account.logout")

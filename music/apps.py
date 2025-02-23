from django.apps import AppConfig
from django.core.mail import mail_admins
from django.dispatch import receiver
from invitations.signals import invite_accepted


class MusicConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "music"


@receiver(invite_accepted)
def handle_invite_accepted(sender, email, **kwargs):
    mail_admins(
        "Invitation accepted",
        f"Invitation accepted by {email}",
        fail_silently=True,
    )

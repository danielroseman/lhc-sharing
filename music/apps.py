from allauth.account.signals import user_signed_up
from django.apps import AppConfig
from django.conf import settings
from django.core.mail import mail_admins
from django.dispatch import receiver
from invitations.signals import invite_accepted
from mailchimp_marketing import Client


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


@receiver(user_signed_up)
def user_signup_callback(request, user, **kwargs):
    mailchimp = Client()
    mailchimp.set_config({
        "api_key": settings.MAILCHIMP_API_KEY,
        "server": settings.MAILCHIMP_SERVER_PREFIX,
    })
    mailchimp.lists.add_list_member(
        settings.MAILCHIMP_LIST_ID,
        {
            "email_address": user.email,
            "status": "subscribed",
            "merge_fields": {"FNAME": user.first_name, "LNAME": user.last_name},
        },
    )

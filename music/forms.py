import logging

import mailchimp_marketing
from django import forms
from django.conf import settings

logger = logging.getLogger(__name__)

GDPR_MESSAGE = (
    "I consent to my email address being added to the London Humanist Choir "
    "mailing list for the purposes of choir information only. I understand "
    "that I can unsubscribe at any time using the link in the footer of "
    "any email I receive from the choir."
)


class SignupForm(forms.Form):
    first_name = forms.CharField()
    last_name = forms.CharField()
    email_permission = forms.BooleanField(
        help_text=GDPR_MESSAGE,
        required=True,
    )

    def signup(self, request, user):
        mailchimp = mailchimp_marketing.Client()
        mailchimp.set_config({
            "api_key": settings.MAILCHIMP_API_KEY,
            "server": settings.MAILCHIMP_SERVER_PREFIX,
        })
        try:
            mailchimp.lists.add_list_member(
                settings.MAILCHIMP_LIST_ID,
                {
                    "email_address": user.email,
                    "status": "subscribed",
                    "merge_fields": {"FNAME": user.first_name, "LNAME": user.last_name},
                },
            )
        except mailchimp_marketing.api_client.ApiClientError as e:
            logger.exception("Mailchimp API error in signup")

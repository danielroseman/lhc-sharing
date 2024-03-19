from django import forms

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
        pass

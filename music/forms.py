from django import forms


class SignupForm(forms.Form):
    first_name = forms.CharField()
    last_name = forms.CharField()

    def signup(self, request, user):
        pass

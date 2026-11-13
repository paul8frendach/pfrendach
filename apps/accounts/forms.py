"""Forms for accounts: signup, player profile, ratings, offers, messages."""

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Message, Offer, PlayerProfile, Thread


# ---------------------------------------------------------------- auth

class SignupForm(forms.Form):
    first_name = forms.CharField(max_length=40, label="First name")
    last_name  = forms.CharField(max_length=40, label="Last name")
    email      = forms.EmailField(label="Email")
    password1  = forms.CharField(widget=forms.PasswordInput, label="Password", min_length=8)
    password2  = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with that email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        return cleaned

    def save(self) -> User:
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data["email"].lower(),
            email=data["email"].lower(),
            password=data["password1"],
            first_name=data["first_name"],
            last_name=data["last_name"],
        )
        PlayerProfile.objects.create(user=user)
        return user


# ---------------------------------------------------------------- coach tools

class PlayerRatingForm(forms.ModelForm):
    class Meta:
        model  = PlayerProfile
        fields = ("rating", "notes", "club", "position", "grad_year")
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class OfferForm(forms.ModelForm):
    class Meta:
        model  = Offer
        fields = (
            "title", "body", "cta_label", "cta_url",
            "min_rating", "max_rating", "requires_auth",
            "tier_label", "is_live", "sort",
        )
        widgets = {
            "body": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "min_rating": "0 = all players",
            "max_rating": "5 = all players",
        }


# ---------------------------------------------------------------- messaging

class ComposeForm(forms.Form):
    """Player composes a new thread."""
    subject = forms.CharField(max_length=200, label="Subject")
    body    = forms.CharField(widget=forms.Textarea(attrs={"rows": 5}), label="Message")
    service = forms.CharField(max_length=80, required=False, widget=forms.HiddenInput)


class ReplyForm(forms.Form):
    """Reply inside an existing thread."""
    body = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), label="Reply")

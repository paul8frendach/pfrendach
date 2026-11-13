"""The commission request form — how a film actually gets booked."""

from __future__ import annotations

from django import forms

from .models import Commission, Package


class CommissionForm(forms.ModelForm):
    # Bots fill everything. People leave this alone.
    company = forms.CharField(required=False, widget=forms.HiddenInput)

    # A client account, offered inside the quote — never a wall in front of it.
    create_account = forms.BooleanField(
        required=False,
        initial=True,
        label="Create an account so you can track your project and pay online",
    )
    password = forms.CharField(
        required=False,
        min_length=8,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        label="Choose a password",
        help_text="At least 8 characters. Skip it to just send the request.",
    )

    class Meta:
        model = Commission
        fields = [
            "name",
            "email",
            "phone",
            "service",
            "event_date",
            "location",
            "budget",
            "details",
            "how_heard",
        ]
        widgets = {
            "event_date": forms.DateInput(attrs={"type": "date"}),
            "details": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, service: str | None = None, package: Package | None = None,
                 authenticated: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected_package = package
        self.authenticated = authenticated
        # A signed-in client is already an account — don't re-offer one.
        if authenticated:
            self.fields.pop("create_account", None)
            self.fields.pop("password", None)
        self.fields["phone"].required = False
        self.fields["event_date"].required = False
        self.fields["location"].required = False
        self.fields["budget"].required = False
        self.fields["how_heard"].required = False
        if service in dict(Commission.Service.choices):
            self.fields["service"].initial = service
        placeholders = {
            "name": "Your name",
            "email": "you@email.com",
            "phone": "Best number to reach you",
            "location": "Venue or town",
            "budget": "Optional, in dollars",
            "details": "The date, the place, what you want to remember. The more you tell me, the better the quote.",
            "how_heard": "Instagram, a friend, a venue…",
        }
        for name, field in self.fields.items():
            if name in placeholders:
                field.widget.attrs.setdefault("placeholder", placeholders[name])

    def clean_company(self):
        if self.cleaned_data.get("company"):
            raise forms.ValidationError("Rejected.")
        return ""

    def clean(self):
        cleaned = super().clean()
        if not self.authenticated and cleaned.get("create_account") and not cleaned.get("password"):
            self.add_error(
                "password",
                "Choose a password to create your account — or untick the box to just send the request.",
            )
        return cleaned

    def save(self, commit: bool = True) -> Commission:
        obj = super().save(commit=False)
        if self.selected_package is not None:
            obj.package = self.selected_package
        if commit:
            obj.save()
        return obj

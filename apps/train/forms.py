from django import forms
from django.utils import timezone

from .models import Booking, Slot


class BookingForm(forms.ModelForm):
    consent = forms.BooleanField(
        label="I understand this is a request, not a confirmed session.",
        required=True,
    )
    company = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Booking
        fields = [
            "player_name",
            "player_age",
            "club_or_school",
            "position",
            "contact_name",
            "email",
            "phone",
            "goal",
        ]
        widgets = {"goal": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, slot: Slot, **kwargs):
        super().__init__(*args, **kwargs)
        self.slot = slot
        placeholders = {
            "player_name": "Player name",
            "player_age": "Age",
            "club_or_school": "Club or school",
            "position": "Position",
            "contact_name": "Parent or guardian",
            "email": "you@email.com",
            "phone": "Optional",
            "goal": "What do you want to get better at?",
        }
        for name, field in self.fields.items():
            if name in placeholders:
                field.widget.attrs.setdefault("placeholder", placeholders[name])
            if name in {"player_age", "club_or_school", "position", "contact_name", "phone"}:
                field.required = False

    def clean_company(self):
        if self.cleaned_data.get("company"):
            raise forms.ValidationError("Rejected.")
        return ""

    def clean(self):
        cleaned = super().clean()
        # Re-check the slot at submit time: someone else may have taken the last seat
        # while this form sat open in a tab.
        slot = Slot.objects.filter(pk=self.slot.pk).first()
        if slot is None or not slot.is_bookable:
            raise forms.ValidationError(
                "That slot has just gone. Pick another time and it will hold."
            )
        if slot.starts_at < timezone.now():
            raise forms.ValidationError("That slot is in the past.")
        return cleaned

    def save(self, commit: bool = True) -> Booking:
        booking = super().save(commit=False)
        booking.slot = self.slot
        if commit:
            booking.save()
        return booking

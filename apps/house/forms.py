from django import forms

from .models import Inquiry, World


class InquiryForm(forms.ModelForm):
    # Bots fill everything. People leave this alone.
    company = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Inquiry
        fields = ["name", "email", "phone", "subject", "message", "budget", "world"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 5}),
            "world": forms.Select(),
        }

    def __init__(self, *args, world: World | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["world"].queryset = World.objects.filter(is_live=True)
        self.fields["world"].required = False
        self.fields["world"].empty_label = "The house"
        self.fields["phone"].required = False
        self.fields["subject"].required = False
        if world is not None:
            self.fields["world"].initial = world.pk
        placeholders = {
            "name": "Your name",
            "email": "you@email.com",
            "phone": "Optional",
            "subject": "What is this about",
            "message": "Tell me what you are trying to make.",
            "budget": "Optional, in dollars",
        }
        for name, field in self.fields.items():
            if name in placeholders:
                field.widget.attrs.setdefault("placeholder", placeholders[name])

    def clean_company(self):
        if self.cleaned_data.get("company"):
            raise forms.ValidationError("Rejected.")
        return ""

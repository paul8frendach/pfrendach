"""The coach's intake form, rendered here and posted back to The LAB.

The form on this site is not written here. `GET /api/v1/intake-form` returns
what the coach has configured — which of the standard details to collect, and
whatever custom questions they have added — and this module turns that into
fields and then turns the answers back into a `POST /api/v1/leads` body.

The consequence worth stating: a question Paul adds in The LAB appears on
paulfrendach.com on the next page load, with no deploy and no edit here. A
hand-copied form goes stale the first time the coach edits one.
"""
from __future__ import annotations

from django import forms

# The three ways The LAB will accept an age, and the only ones it will accept.
# `page/leads.py` stores exactly one of them, chosen by `age_type`.
AGE_RANGES = ("2-6", "7-10", "11-14", "15-18", "18+")
AGE_CHOICES = [("range", "Age range"), ("year", "Birth year"), ("birthday", "Date of birth")]

# The LAB caps a lead at 12 athletes (api/views.py MAX_ATHLETES). Matching it
# here means an over-long submission is refused with an explanation rather than
# silently truncated upstream.
MAX_ATHLETES = 12


def _field_for(spec: dict, *, required: bool | None = None) -> forms.Field:
    """One custom question, as a Django field.

    Unknown types fall back to a text box on purpose. A coach who adds a field
    type The LAB grows later should get a usable box here, not a broken page.
    """
    kind = spec.get("type", "short_text")
    label = spec.get("label", "")
    is_required = spec.get("required", False) if required is None else required
    options = [(o, o) for o in (spec.get("options") or [])]
    common = {"label": label, "required": is_required}

    if kind == "long_text":
        return forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), **common)
    if kind == "dropdown":
        return forms.ChoiceField(choices=[("", "Choose…")] + options, **common)
    if kind == "multiple_choice":
        return forms.ChoiceField(choices=options, widget=forms.RadioSelect, **common)
    if kind == "checkboxes":
        return forms.MultipleChoiceField(
            choices=options, widget=forms.CheckboxSelectMultiple, **common)
    if kind == "date":
        return forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), **common)
    if kind == "number":
        return forms.IntegerField(**common)
    return forms.CharField(max_length=200, **common)


def build_form_class(definition: dict, *, athletes: int = 1) -> type[forms.Form]:
    """A form class for this coach's configuration, with `athletes` player blocks.

    Athlete fields are indexed (`athlete_0_first_name`) rather than put in a
    formset because the blocks are cloned client-side and a formset's
    management form is one more thing that can arrive inconsistent from a page
    that has been open a while.
    """
    collect = definition.get("collect") or {}
    custom = definition.get("fields") or []
    count = max(1, min(int(athletes or 1), MAX_ATHLETES))

    attrs: dict = {}

    # -- the payer: who the coach replies to ------------------------------
    if collect.get("parent_name", True):
        attrs["payer_first_name"] = forms.CharField(label="Your first name", max_length=50)
        attrs["payer_last_name"] = forms.CharField(label="Your last name", max_length=50)
    # Email is not conditional. The LAB refuses a lead without one, because it
    # is what links the enquiry to a person the coach can actually answer.
    attrs["payer_email"] = forms.EmailField(label="Email")
    if collect.get("phone", False):
        attrs["payer_phone"] = forms.CharField(label="Phone", max_length=20, required=False)

    # -- the athletes -----------------------------------------------------
    for i in range(count):
        first_required = i == 0 and collect.get("athlete_name", True)
        attrs[f"athlete_{i}_first_name"] = forms.CharField(
            label="Player first name", max_length=50, required=first_required)
        attrs[f"athlete_{i}_last_name"] = forms.CharField(
            label="Player last name", max_length=50, required=False)

        if collect.get("age", False):
            attrs[f"athlete_{i}_age_type"] = forms.ChoiceField(
                label="How would you like to give their age?", choices=AGE_CHOICES,
                initial="range", required=False)
            attrs[f"athlete_{i}_age_range"] = forms.ChoiceField(
                label="Age range", required=False,
                choices=[("", "Choose…")] + [(r, r) for r in AGE_RANGES])
            attrs[f"athlete_{i}_birth_year"] = forms.IntegerField(
                label="Birth year", required=False, min_value=1990, max_value=2035)
            attrs[f"athlete_{i}_birthday"] = forms.DateField(
                label="Date of birth", required=False,
                widget=forms.DateInput(attrs={"type": "date"}))

        if collect.get("experience", False):
            # NOTE: The LAB accepts this per athlete and currently stores it
            # nowhere — `Athlete` has no experience field and it does not reach
            # the lead card either. It is sent anyway (so it starts working the
            # day that lands) AND mirrored into the answers blob below, which
            # is what actually reaches the coach today.
            attrs[f"athlete_{i}_experience"] = forms.CharField(
                label="Experience so far", max_length=100, required=False)

        for spec in custom:
            if spec.get("per_athlete"):
                # Only the first player's copy may be required: a coach asking
                # a required question should not make every optional extra
                # player mandatory too.
                attrs[f"athlete_{i}_custom_{spec['id']}"] = _field_for(
                    spec, required=spec.get("required", False) and i == 0)

    # -- questions asked once ---------------------------------------------
    for spec in custom:
        if not spec.get("per_athlete"):
            attrs[f"custom_{spec['id']}"] = _field_for(spec)

    if collect.get("notes", True):
        attrs["notes"] = forms.CharField(
            label="Anything else the coach should know?", required=False,
            widget=forms.Textarea(attrs={"rows": 4}))

    attrs["athlete_count"] = forms.IntegerField(
        widget=forms.HiddenInput, initial=count, required=False,
        min_value=1, max_value=MAX_ATHLETES)

    # The template cannot look a field up by a name it computes, so the form
    # hands back its own groups. Keeping this here means the rendered order is
    # decided next to the field definitions rather than duplicated in markup.
    attrs["_athlete_count"] = count
    attrs["_custom"] = list(custom)
    attrs["_collect"] = dict(collect)
    attrs["payer_fields"] = _payer_fields
    attrs["athlete_blocks"] = _athlete_blocks
    attrs["general_fields"] = _general_fields

    return type("LabIntakeForm", (forms.Form,), attrs)


def _bound(form, name):
    return form[name] if name in form.fields else None


def _payer_fields(self):
    names = ["payer_first_name", "payer_last_name", "payer_email", "payer_phone"]
    return [f for f in (_bound(self, n) for n in names) if f is not None]


def _athlete_blocks(self):
    """One dict per player.

    Age is handed back separately from the rest because all three
    representations are rendered — The LAB takes exactly one, and a visitor
    with JavaScript off has to be able to reach whichever they prefer. The
    template wraps each so the page can show only the chosen one.
    """
    blocks = []
    for i in range(self._athlete_count):
        names = [f"athlete_{i}_first_name", f"athlete_{i}_last_name"]
        rest = []
        if self._collect.get("experience"):
            rest.append(f"athlete_{i}_experience")
        rest += [f"athlete_{i}_custom_{spec['id']}"
                 for spec in self._custom if spec.get("per_athlete")]

        age = None
        if self._collect.get("age"):
            age = {
                "type": _bound(self, f"athlete_{i}_age_type"),
                "range": _bound(self, f"athlete_{i}_age_range"),
                "year": _bound(self, f"athlete_{i}_birth_year"),
                "birthday": _bound(self, f"athlete_{i}_birthday"),
            }

        blocks.append({
            "index": i,
            "heading": "Player" if i == 0 else f"Player {i + 1}",
            "name_fields": [f for f in (_bound(self, n) for n in names) if f is not None],
            "age": age,
            "fields": [f for f in (_bound(self, n) for n in rest) if f is not None],
        })
    return blocks


def _general_fields(self):
    names = [f"custom_{spec['id']}" for spec in self._custom
             if not spec.get("per_athlete")]
    names.append("notes")
    return [f for f in (_bound(self, n) for n in names) if f is not None]


def payload_from(cleaned: dict, definition: dict, *, athletes: int = 1) -> dict:
    """Turn cleaned form data into a `POST /api/v1/leads` body.

    Everything the coach asked for goes up. Answers are keyed by the question's
    *label* rather than its id, because the coach reads them in a chat thread
    and "What position do you play?: Midfield" is legible where "3: Midfield"
    is not.
    """
    custom = definition.get("fields") or []
    by_id = {spec["id"]: spec for spec in custom}
    count = max(1, min(int(athletes or 1), MAX_ATHLETES))

    def answer(value):
        """Checkbox answers arrive as lists; join so the coach reads a sentence."""
        if isinstance(value, (list, tuple)):
            return ", ".join(str(v) for v in value)
        return value

    rows = []
    for i in range(count):
        first = (cleaned.get(f"athlete_{i}_first_name") or "").strip()
        last = (cleaned.get(f"athlete_{i}_last_name") or "").strip()
        if not first and not last:
            continue  # an empty extra block the visitor never filled in

        row: dict = {"first_name": first, "last_name": last}

        experience = (cleaned.get(f"athlete_{i}_experience") or "").strip()
        if experience:
            row["experience"] = experience

        # Exactly one age representation, the same rule create_athletes applies.
        age_type = cleaned.get(f"athlete_{i}_age_type") or "range"
        if age_type == "birthday" and cleaned.get(f"athlete_{i}_birthday"):
            row["birthday"] = cleaned[f"athlete_{i}_birthday"].isoformat()
        elif age_type == "year" and cleaned.get(f"athlete_{i}_birth_year"):
            row["birth_year"] = str(cleaned[f"athlete_{i}_birth_year"])
        elif cleaned.get(f"athlete_{i}_age_range"):
            row["age_range"] = cleaned[f"athlete_{i}_age_range"]

        answers: dict = {}
        for spec in custom:
            if not spec.get("per_athlete"):
                continue
            value = cleaned.get(f"athlete_{i}_custom_{spec['id']}")
            if value not in (None, "", [], ()):
                answers[spec["label"]] = answer(value)
        # Until The LAB stores `experience`, this is what actually reaches the
        # coach. Keyed in the athlete's own answers so it stays attached to the
        # right player on a multi-athlete enquiry.
        if experience:
            answers.setdefault("Experience so far", experience)
        if answers:
            row["answers"] = answers
        rows.append(row)

    global_answers = {}
    for spec in custom:
        if spec.get("per_athlete"):
            continue
        value = cleaned.get(f"custom_{spec['id']}")
        if value not in (None, "", [], ()):
            global_answers[spec["label"]] = answer(value)

    payload = {
        "payer": {
            "first_name": (cleaned.get("payer_first_name") or "").strip(),
            "last_name": (cleaned.get("payer_last_name") or "").strip(),
            "email": (cleaned.get("payer_email") or "").strip(),
            "phone": (cleaned.get("payer_phone") or "").strip(),
        },
        "notes": (cleaned.get("notes") or "").strip(),
    }
    if rows:
        payload["athletes"] = rows
    if global_answers:
        payload["answers"] = global_answers
    return payload

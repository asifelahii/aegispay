from decimal import Decimal

from django import forms

from core.contracts import ScamContext


SCENARIO_CHOICES = (
    ("normal", "Normal payment"),
    ("guided", "Guided / impersonation risk"),
    ("strong", "Strong risk evidence"),
)


class PaymentDemoForm(forms.Form):
    scenario = forms.ChoiceField(
        choices=SCENARIO_CHOICES,
        label="Demo scenario",
    )
    recipient = forms.CharField(max_length=64, required=True)
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    note = forms.CharField(max_length=140, required=False)


class ContextAnswerForm(forms.Form):
    scenario = forms.ChoiceField(choices=SCENARIO_CHOICES, widget=forms.HiddenInput)
    recipient = forms.CharField(max_length=64, widget=forms.HiddenInput)
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"), widget=forms.HiddenInput)
    note = forms.CharField(max_length=140, required=False, widget=forms.HiddenInput)
    answer_key = forms.CharField(widget=forms.HiddenInput)
    answer = forms.ChoiceField(
        choices=(("yes", "Yes"), ("no", "No")),
        widget=forms.RadioSelect,
    )

    def clean_answer_key(self):
        answer_key = self.cleaned_data["answer_key"]
        if answer_key not in ScamContext.__dataclass_fields__:
            raise forms.ValidationError("That security question is not valid.")
        return answer_key

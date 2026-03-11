from django import forms

from cursos.models import Cursos
from .models import AIDraft


class MentorStartForm(forms.Form):
    title = forms.CharField(max_length=120, required=False)
    course = forms.ModelChoiceField(queryset=Cursos.objects.all(), required=False)
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 5}))


class MentorMessageForm(forms.Form):
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 5}))


class StudioForm(forms.Form):
    course = forms.ModelChoiceField(queryset=Cursos.objects.all(), required=False)
    draft_type = forms.ChoiceField(choices=AIDraft.DRAFT_TYPES)
    title = forms.CharField(max_length=160, required=False)
    audience = forms.CharField(max_length=120, required=False)
    goals = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), required=False)
    constraints = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
    tone = forms.CharField(max_length=120, required=False)
    source_material = forms.CharField(widget=forms.Textarea(attrs={"rows": 6}), required=False)

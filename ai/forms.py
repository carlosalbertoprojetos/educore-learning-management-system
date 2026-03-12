from django import forms
from django.utils.translation import gettext_lazy as _

from cursos.models import Cursos
from .models import AIDraft


class MentorStartForm(forms.Form):
    title = forms.CharField(label=_("Título"), max_length=120, required=False)
    course = forms.ModelChoiceField(label=_("Curso"), queryset=Cursos.objects.all(), required=False)
    message = forms.CharField(label=_("Mensagem"), widget=forms.Textarea(attrs={"rows": 5}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].widget.attrs.update({"placeholder": _("Nova sessão")})
        self.fields["course"].empty_label = _("Todos os cursos")
        self.fields["message"].widget.attrs.update({"placeholder": _("Descreva sua dúvida")})


class MentorMessageForm(forms.Form):
    message = forms.CharField(label=_("Mensagem"), widget=forms.Textarea(attrs={"rows": 5}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["message"].widget.attrs.update({"placeholder": _("Escreva sua mensagem")})


class StudioForm(forms.Form):
    course = forms.ModelChoiceField(label=_("Curso"), queryset=Cursos.objects.all(), required=False)
    draft_type = forms.ChoiceField(label=_("Tipo de rascunho"), choices=AIDraft.DRAFT_TYPES)
    title = forms.CharField(label=_("Título"), max_length=160, required=False)
    audience = forms.CharField(label=_("Público"), max_length=120, required=False)
    goals = forms.CharField(label=_("Objetivos"), widget=forms.Textarea(attrs={"rows": 4}), required=False)
    constraints = forms.CharField(label=_("Restrições"), widget=forms.Textarea(attrs={"rows": 3}), required=False)
    tone = forms.CharField(label=_("Tom"), max_length=120, required=False)
    source_material = forms.CharField(label=_("Material base"), widget=forms.Textarea(attrs={"rows": 6}), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course"].empty_label = _("Todos os cursos")
        self.fields["title"].widget.attrs.update({"placeholder": _("Título do rascunho")})
        self.fields["audience"].widget.attrs.update({"placeholder": _("Ex: iniciantes")})
        self.fields["goals"].widget.attrs.update({"placeholder": _("Objetivos principais")})
        self.fields["constraints"].widget.attrs.update({"placeholder": _("Limites e formato")})
        self.fields["tone"].widget.attrs.update({"placeholder": _("Tom desejado")})
        self.fields["source_material"].widget.attrs.update({"placeholder": _("Cole o material base")})

from django import forms
from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import gettext_lazy as _

from .models import Comentarios



class FormContatoCurso(forms.Form):
    nome = forms.CharField(label=_("Nome"), widget=forms.TextInput())
    email = forms.EmailField(label=_("E-mail"), widget=forms.TextInput())
    mensagem = forms.CharField(
        label=_("Mensagem/Dúvida"), widget=forms.Textarea())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].widget.attrs.update({'placeholder': _('Seu nome')})
        self.fields['email'].widget.attrs.update({'placeholder': _('Seu email')})
        self.fields['mensagem'].widget.attrs.update({'placeholder': _('Escreva sua mensagem')})

    def send_email(self, curso):
        subject = "[%s] %s" % (curso, _("Contato"))
        mensagem = _("Nome: %(nome)s; E-mail: %(email)s; %(mensagem)s")
        context = {
            'nome': self.cleaned_data['nome'],
            'email': self.cleaned_data['email'],
            'mensagem': self.cleaned_data['mensagem'],
        }
        mensagem = mensagem % context
        send_mail(
            subject, mensagem, settings.DEFAULT_FROM_EMAIL,
            [settings.CONTACT_EMAIL]
        )


class ComentariosForm(forms.ModelForm):

    class Meta:
        model = Comentarios
        fields = ('comentario',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comentario'].widget.attrs.update({'placeholder': _('Escreva um coment\u00e1rio')})

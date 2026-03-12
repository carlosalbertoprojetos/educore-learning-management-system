from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Reply


class ReplyForm(forms.ModelForm):

    class Meta:
        model = Reply
        fields = ['reply']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reply'].widget.attrs.update({'placeholder': _('Escreva sua resposta')})

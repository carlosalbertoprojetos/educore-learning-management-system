from django import forms
from django.contrib.auth import get_user_model
# from django.contrib.auth.forms import UserCreationForm

from .models import ResetarSenha
from .utils import generate_hash_key
from .mail import send_email_template


User = get_user_model()

class CadastrarUsuarioForm(forms.ModelForm):
    password1 = forms.CharField(label='Senha', widget=forms.PasswordInput)
    password2 = forms.CharField(
        label='Confirmação de Senha', widget=forms.PasswordInput
    )
    
    class Meta:
        model = User
        fields = ['email', 'username']
    
    def clean_password2(self):
        password1 = self.cleaned_data['password1']
        password2 = self.cleaned_data['password2']
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                'As senhas não são iguais',
            )
        return password2
    
    def save(self, commit=True):
        user = super(CadastrarUsuarioForm, self).save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user
    

class ResetarSenhaForm(forms.Form):
    email = forms.EmailField(label='email')    

    def clean_email(self):
        """ 
        validação - verificar se o email informado para cadastrado já existe
        """
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            return email
        raise forms.ValidationError(
            'Nenhum usuário encontrado com este email.'
        )
        
    def save(self, commit=True):
        user = User.objects.get(email=self.cleaned_data['email'])
        key = generate_hash_key(user.username)
        reset = ResetarSenha(key=key, user=user)
        reset.save()
        template_name = 'accounts/resetar_senha_email.html'
        subject = 'Criar nova senha.'
        context = {
            'reset': reset,
        }
        send_email_template(subject, template_name, context, ['user.email'])


# class CriarUsuariocomEmailForm(UserCreationForm):
#     email = forms.EmailField(required=True, help_text='Campo obrigatório! Insira um email válido!')

#     class Meta:
#         model = User
#         fields = ['email', 'username']

#     def clean_email(self):
#         """ 
#         validação - verificar se o email informado para cadastrado já existe
#         """
#         email = self.cleaned_data.get('email')
#         if User.objects.filter(email=email).exists():
#             raise forms.ValidationError('Este email já está cadastrado, por favor insira outro.')
#         return email

  
class EditarUsuarioForm(forms.ModelForm):        
 
    class Meta:
        model = User
        fields = ['username', 'email', 'name'] 


# class EditarUsuarioForm(forms.ModelForm):
    
#     def clean_email(self):
#         email = self.cleaned_data['email']
#         queryset = User.objects.filter(
#             email=email).exclude(pk=self.instance.pk)
#         if queryset.exists():
#             raise forms.ValidationError('Este email já está cadastrado, por favor insira outro.')
#         return email
    
#     class Meta:
#         model = User
#         fields = ['username', 'email', 'first_name', 'last_name']
        
        
        
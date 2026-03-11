from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import (
    PasswordChangeForm, SetPasswordForm
    )
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import generic

from .forms import CadastrarUsuarioForm, EditarUsuarioForm, ResetarSenhaForm
from .models import ResetarSenha
User = get_user_model()


class CadastrarUsuarioView(generic.CreateView):
    form_class = CadastrarUsuarioForm
    template_name = 'accounts/cadastrar_usuario.html'
    success_url = reverse_lazy('accounts:login')


def resetar_senha(request):
    template_name = 'accounts/resetar_senha.html'
    context = {}
    form = ResetarSenhaForm(request.POST or None)
    if form.is_valid():
        form.save()
        context['success'] = True
    context['form'] = form
    return render(request, template_name, context)


def confirmar_resetar_senha(request, key):
    template_name = 'accounts/resetar_senha_confirmar.html'
    context = {}
    reset = get_object_or_404(ResetarSenha, key=key)
    form = SetPasswordForm(user=reset.user, data=request.POST or None)
    if form.is_valid():
        form.save()
        context['success'] = True
    context['form'] = form
    return render(request, template_name, context)


# def register(request):
#     template_name = 'accounts/cadastro.html'
#     form_class = CriarUsuariocomEmailForm
#     if request.method == 'POST':
#         form = UserCreationForm(request.POST)
#         if form.is_valid():
#             form.save()
#             return redirect(settings.LOGIN_URL)
#     else:
#         form = UserCreationForm()
#     context = {
#         'form':form
#     }
#     return render(request, template_name, context)


@login_required
def painel(request):
    # template_name = 'accounts/painel.html'
    template_name = 'accounts/dashboard.html'
    context = {}
    # context['enrollments'] = Enrollment.objects.filter(usuario=request.user)
    return render(request, template_name, context)


@login_required
def editar_usuario(request):
    template_name = 'accounts/editar_usuario.html'
    context = {}
    if request.method == 'POST':
        form = EditarUsuarioForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request,
                             'Dados alterados com sucesso!!!'
                             )
            return redirect('accounts:painel')
    else:
        form = EditarUsuarioForm(instance=request.user)
    context['form'] = form
    return render(request, template_name, context)


@login_required
def editar_senha(request):
    template_name = 'accounts/editar_senha.html'
    context = {}
    if request.method == 'POST':
        form = PasswordChangeForm(data=request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request,
                             'Senha alterada com sucesso!!!'
                             )
            return redirect('accounts:painel')
    else:
        form = PasswordChangeForm(user=request.user)
    context['form'] = form
    return render(request, template_name, context)
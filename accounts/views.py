from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import (
    PasswordChangeForm, SetPasswordForm
    )
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.decorators.http import require_http_methods
from urllib.parse import unquote

from .forms import CadastrarUsuarioForm, EditarUsuarioForm, ResetarSenhaForm
from .models import ResetarSenha
User = get_user_model()


RESET_TOKEN_TTL_HOURS = 24


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


def _get_reset_by_key_or_legacy_prefix(raw_key):
    key = unquote(raw_key or "").strip()
    if not key:
        raise Http404

    reset = ResetarSenha.objects.filter(key=key).select_related("user").first()
    if reset:
        return reset

    # Legacy links sometimes carried only a short prefix plus "=".
    legacy_prefix = key.rstrip("=")
    if legacy_prefix and len(legacy_prefix) < 56:
        qs = ResetarSenha.objects.filter(key__startswith=legacy_prefix).select_related("user")
        if qs.count() == 1:
            return qs.first()

    raise Http404


def _is_reset_expired(reset):
    age = timezone.now() - reset.created_at
    return age.total_seconds() > RESET_TOKEN_TTL_HOURS * 3600


def confirmar_resetar_senha(request, key):
    template_name = 'accounts/resetar_senha_confirmar.html'
    context = {"invalid_reset": False}
    try:
        reset = _get_reset_by_key_or_legacy_prefix(key)
    except Http404:
        context["invalid_reset"] = True
        context["invalid_reset_message"] = _(
            "Este link de redefinição é inválido, antigo ou já não está mais disponível."
        )
        return render(request, template_name, context, status=404)

    if reset.confirmed or _is_reset_expired(reset):
        context["invalid_reset"] = True
        context["invalid_reset_message"] = _(
            "Este link de redefinição expirou ou já foi utilizado."
        )
        return render(request, template_name, context, status=410)

    form = SetPasswordForm(user=reset.user, data=request.POST or None)
    if form.is_valid():
        form.save()
        reset.confirmed = True
        reset.save(update_fields=["confirmed"])
        ResetarSenha.objects.filter(user=reset.user, confirmed=False).exclude(pk=reset.pk).delete()
        login(request, reset.user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect(settings.LOGIN_REDIRECT_URL)
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

@require_http_methods(["GET", "POST"])
def logout_view(request):
    """Logout endpoint that works for both link GETs and form POSTs.

    Django 6+ defaults LogoutView to POST-only; this keeps UX simple while redirecting home.
    """
    logout(request)
    return redirect('home')


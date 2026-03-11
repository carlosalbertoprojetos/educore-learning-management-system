import re
from django.db import models
from django.core import validators
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(
        _("Usuário"),
        max_length=30,
        unique=True,
        validators=[
            validators.RegexValidator(
                re.compile(r"^[\w.@+-]+$"),
                _("O nome de usuário só pode conter letras, dígitos ou os seguintes caracteres: @/./+/-/_"),
                _("Usuário inválido ou já existente!"),
            )
        ],
    )
    email = models.EmailField(_("E-mail"), unique=True)
    name = models.CharField(_("Nome"), max_length=100, blank=True)
    is_active = models.BooleanField(_("Está ativo?"), blank=True, default=True)
    is_staff = models.BooleanField(_("É da equipe?"), blank=True, default=False)
    date_joined = models.DateTimeField(_("Data de Entrada"), auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = _("Usuário")
        verbose_name_plural = _("Usuários")

    def __str__(self):
        return self.name or self.username

    def get_short_name(self):
        return self.username

    def get_full_name(self):
        return str(self)


class ResetarSenha(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Usuário"),
        on_delete=models.CASCADE,
        related_name="resets",
    )
    key = models.CharField(_("Chave"), max_length=100, unique=True)
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    confirmed = models.BooleanField(_("Confirmado?"), default=False, blank=True)

    class Meta:
        verbose_name = _("Nova Senha")
        verbose_name_plural = _("Novas Senhas")
        ordering = ["-created_at"]

    def __str__(self):
        return "{0} em {1}".format(self.user, self.created_at)

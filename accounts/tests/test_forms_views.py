from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from accounts.forms import CadastrarUsuarioForm, ResetarSenhaForm
from accounts.models import ResetarSenha


User = get_user_model()


class AccountsFormTests(TestCase):
    def test_cadastrar_usuario_form_cria_usuario(self):
        form = CadastrarUsuarioForm(data={
            "email": "novo@example.com",
            "username": "novo",
            "password1": "Senha@123",
            "password2": "Senha@123",
        })
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.username, "novo")
        self.assertTrue(user.check_password("Senha@123"))

    def test_cadastrar_usuario_form_senha_invalida(self):
        form = CadastrarUsuarioForm(data={
            "email": "novo@example.com",
            "username": "novo",
            "password1": "Senha@123",
            "password2": "Senha@124",
        })
        self.assertFalse(form.is_valid())

    def test_resetar_senha_form_cria_registro(self):
        User.objects.create_user(
            username="user",
            email="user@example.com",
            password="Senha@123",
        )
        form = ResetarSenhaForm(data={"email": "user@example.com"})
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(ResetarSenha.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_resetar_senha_form_email_inexistente(self):
        form = ResetarSenhaForm(data={"email": "invalido@example.com"})
        self.assertFalse(form.is_valid())


class AccountsViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="Senha@123",
        )

    def test_login_view(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")

    def test_painel_requer_login(self):
        response = self.client.get(reverse("accounts:painel"))
        self.assertEqual(response.status_code, 302)


    def test_logout_redireciona_para_home(self):
        self.client.login(username="user", password="Senha@123")
        response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("home"))
        # session should be cleared
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_editar_usuario_get(self):
        self.client.login(username="user", password="Senha@123")
        url = reverse("accounts:editar_usuario")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_editar_usuario_post(self):
        self.client.login(username="user", password="Senha@123")
        url = reverse("accounts:editar_usuario")
        response = self.client.post(url, {"username": "user", "email": "novo@example.com", "name": "Novo"})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "novo@example.com")

    def test_editar_senha_get(self):
        self.client.login(username="user", password="Senha@123")
        url = reverse("accounts:editar_senha")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_editar_senha_post(self):
        self.client.login(username="user", password="Senha@123")
        url = reverse("accounts:editar_senha")
        response = self.client.post(url, {
            "old_password": "Senha@123",
            "new_password1": "NovaSenha@123",
            "new_password2": "NovaSenha@123",
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NovaSenha@123"))

    def test_resetar_senha_view(self):
        url = reverse("accounts:resetar_senha")
        response = self.client.post(url, {"email": "user@example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context.get("success"))
        self.assertEqual(ResetarSenha.objects.count(), 1)

    def test_confirmar_resetar_senha_view(self):
        reset = ResetarSenha.objects.create(user=self.user, key="chave-teste")
        url = reverse("accounts:confirmar_resetar_senha", args=[reset.key])
        response = self.client.post(url, {
            "new_password1": "SenhaNova@123",
            "new_password2": "SenhaNova@123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context.get("success"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("SenhaNova@123"))

    def test_painel_view_logado(self):
        self.client.login(username="user", password="Senha@123")
        response = self.client.get(reverse("accounts:painel"))
        self.assertEqual(response.status_code, 200)

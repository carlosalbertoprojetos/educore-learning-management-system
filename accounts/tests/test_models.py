from django.test import TestCase

from ..models import ResetarSenha, User


class CreateNewUser(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username="Username",
            email="usuario@us.com",
            name="Name",
        )

    def test_filtra_username_e_retorna_dados(self):
        user = User.objects.get(username="Username")
        self.assertEqual(str(user), "Name")
        self.assertEqual(user.username, "Username")
        self.assertEqual(user.email, "usuario@us.com")

    def test_user_helpers(self):
        self.assertEqual(self.user.get_short_name(), "Username")
        self.assertEqual(self.user.get_full_name(), "Name")

    def test_resetar_senha_str(self):
        reset = ResetarSenha.objects.create(user=self.user, key="chave")
        self.assertIn("chave", reset.key)
        self.assertIn("Name", str(reset))


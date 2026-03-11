from django.contrib.auth import get_user_model
from django.test import TestCase

from cursos.models import Cursos, Enrollment
from cursos.templatetags import cursos_tags


User = get_user_model()


class CursosTemplateTagsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="aluno",
            email="aluno@example.com",
            password="Senha@123",
        )
        self.curso = Cursos.objects.create(
            nome="Curso 1",
            slug="curso-1",
            descricao="Descricao",
        )

    def test_listar_meus_cursos(self):
        Enrollment.objects.create(usuario=self.user, curso=self.curso)
        queryset = cursos_tags.listar_meus_cursos(self.user)
        self.assertEqual(queryset.count(), 1)

    def test_meus_cursos_inclusion_tag(self):
        Enrollment.objects.create(usuario=self.user, curso=self.curso)
        context = cursos_tags.meus_cursos(self.user)
        self.assertIn("enrollments", context)
        self.assertEqual(context["enrollments"].count(), 1)

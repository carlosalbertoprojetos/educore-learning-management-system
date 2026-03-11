from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.utils import timezone

from cursos.models import Aulas, Anuncios, Comentarios, Cursos, Enrollment, Materiais


User = get_user_model()


class CursosModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="aluno",
            email="aluno@example.com",
            password="Senha@123",
        )
        self.curso = Cursos.objects.create(
            nome="Django Essencial",
            slug="django-essencial",
            descricao="Curso base de Django",
            sobre="Conteudo completo",
            data_inicial=timezone.now().date(),
        )

    def test_curso_str_and_url(self):
        self.assertEqual(str(self.curso), "Django Essencial")
        self.assertIn(self.curso.slug, self.curso.get_absolute_url())

    def test_aulas_disponiveis_filtra_por_data(self):
        ontem = timezone.now().date() - timedelta(days=1)
        amanha = timezone.now().date() + timedelta(days=1)
        Aulas.objects.create(curso=self.curso, nome="Aula 1", inicio=ontem)
        Aulas.objects.create(curso=self.curso, nome="Aula 2", inicio=amanha)
        disponiveis = self.curso.aulas_disponiveis()
        self.assertEqual(disponiveis.count(), 1)
        self.assertEqual(disponiveis.first().nome, "Aula 1")

    def test_aula_is_disponivel_respeita_regra_atual(self):
        amanha = timezone.now().date() + timedelta(days=1)
        aula = Aulas.objects.create(curso=self.curso, nome="Aula futura", inicio=amanha)
        self.assertTrue(aula.is_disponivel())

    def test_material_is_embutido(self):
        aula = Aulas.objects.create(curso=self.curso, nome="Aula 3")
        material = Materiais.objects.create(aula=aula, nome="Video", embutido="<iframe></iframe>")
        self.assertTrue(material.is_embutido())

    def test_enrollment_ativo_aprovado(self):
        enrollment = Enrollment.objects.create(usuario=self.user, curso=self.curso)
        enrollment.ativo()
        enrollment.refresh_from_db()
        self.assertTrue(enrollment.aprovado())

    def test_anuncio_str(self):
        anuncio = Anuncios.objects.create(curso=self.curso, titulo="Aviso", conteudo="Conteudo")
        self.assertEqual(str(anuncio), "Aviso")

    def test_comentario_str(self):
        anuncio = Anuncios.objects.create(curso=self.curso, titulo="Aviso", conteudo="Conteudo")
        comentario = Comentarios.objects.create(anuncio=anuncio, usuario=self.user, comentario="Bom")
        self.assertEqual(str(comentario), str(self.curso))

    def test_anuncio_dispara_email_para_inscritos_aprovados(self):
        Enrollment.objects.create(usuario=self.user, curso=self.curso, status="1")
        Anuncios.objects.create(curso=self.curso, titulo="Novo aviso", conteudo="Conteudo")
        self.assertEqual(len(mail.outbox), 1)

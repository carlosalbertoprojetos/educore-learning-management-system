from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cursos.models import Aulas, Anuncios, Comentarios, Cursos, Enrollment, Materiais


User = get_user_model()


class CursosViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="aluno",
            email="aluno@example.com",
            password="Senha@123",
        )
        self.staff = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="Senha@123",
            is_staff=True,
        )
        self.curso = Cursos.objects.create(
            nome="Django Essencial",
            slug="django-essencial",
            descricao="Curso base de Django",
            sobre="Conteudo completo",
            data_inicial=timezone.now().date(),
        )

    def test_lista_cursos_view(self):
        response = self.client.get(reverse("cursos:lista_cursos"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.curso.nome)

    def test_detalhes_curso_get_and_post(self):
        url = reverse("cursos:detalhes_curso", args=[self.curso.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["curso"], self.curso)

        payload = {
            "nome": "Teste",
            "email": "teste@example.com",
            "mensagem": "Tenho uma duvida",
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context.get("is_valid"))
        self.assertEqual(len(mail.outbox), 1)

    def test_contato_curso_success(self):
        url = reverse("cursos:contato")
        payload = {
            "nome": "Aluno",
            "email": "aluno@example.com",
            "mensagem": "Ajuda",
        }
        with patch("django.core.mail.EmailMessage.send", return_value=1):
            response = self.client.post(url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context.get("success"))

    def test_contato_curso_fail(self):
        url = reverse("cursos:contato")
        payload = {
            "nome": "Aluno",
            "email": "aluno@example.com",
            "mensagem": "Ajuda",
        }
        with patch("django.core.mail.EmailMessage.send", side_effect=Exception("falha")):
            response = self.client.post(url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context.get("success"))

    def test_enrollment_cria_inscricao(self):
        self.client.login(username="aluno", password="Senha@123")
        url = reverse("cursos:enrollment", args=[self.curso.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Enrollment.objects.filter(usuario=self.user, curso=self.curso).exists()
        )

    def test_cancelar_enrollment(self):
        enrollment = Enrollment.objects.create(usuario=self.user, curso=self.curso)
        self.client.login(username="aluno", password="Senha@123")
        url = reverse("cursos:cancelar_enrollment", args=[self.curso.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Enrollment.objects.filter(pk=enrollment.pk).exists())

    def test_anuncios_view(self):
        Anuncios.objects.create(curso=self.curso, titulo="Aviso", conteudo="Conteudo")
        self.client.login(username="admin", password="Senha@123")
        url = reverse("cursos:anuncios", args=[self.curso.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aviso")

    def test_anuncios_requer_inscricao_para_usuario(self):
        self.client.login(username="aluno", password="Senha@123")
        url = reverse("cursos:anuncios", args=[self.curso.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_anuncios_permite_usuario_inscrito(self):
        Enrollment.objects.create(usuario=self.user, curso=self.curso, status="1")
        self.client.login(username="aluno", password="Senha@123")
        url = reverse("cursos:anuncios", args=[self.curso.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_painel_anuncio_cria_comentario(self):
        anuncio = Anuncios.objects.create(curso=self.curso, titulo="Aviso", conteudo="Conteudo")
        self.client.login(username="admin", password="Senha@123")
        url = reverse("cursos:anuncio", args=[self.curso.slug, anuncio.pk])
        response = self.client.post(url, {"comentario": "Excelente"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Comentarios.objects.filter(anuncio=anuncio).exists())

    def test_aulas_view_mostra_disponiveis_para_staff(self):
        ontem = timezone.now().date() - timedelta(days=1)
        amanha = timezone.now().date() + timedelta(days=1)
        Aulas.objects.create(curso=self.curso, nome="Aula 1", inicio=ontem)
        Aulas.objects.create(curso=self.curso, nome="Aula 2", inicio=amanha)
        self.client.login(username="admin", password="Senha@123")
        url = reverse("cursos:aulas", args=[self.curso.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["aulas"]), 1)

    def test_aulas_view_para_usuario_nao_staff(self):
        ontem = timezone.now().date() - timedelta(days=1)
        amanha = timezone.now().date() + timedelta(days=1)
        Aulas.objects.create(curso=self.curso, nome="Aula 1", inicio=ontem)
        Aulas.objects.create(curso=self.curso, nome="Aula 2", inicio=amanha)
        Enrollment.objects.create(usuario=self.user, curso=self.curso, status="1")
        self.client.login(username="aluno", password="Senha@123")
        url = reverse("cursos:aulas", args=[self.curso.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["aulas"]), 2)

    def test_aula_view_para_staff(self):
        amanha = timezone.now().date() + timedelta(days=1)
        aula = Aulas.objects.create(curso=self.curso, nome="Aula 1", inicio=amanha)
        self.client.login(username="admin", password="Senha@123")
        url = reverse("cursos:aula", args=[self.curso.slug, aula.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, aula.nome)

    def test_aula_view_redireciona_para_usuario_nao_staff(self):
        amanha = timezone.now().date() + timedelta(days=1)
        aula = Aulas.objects.create(curso=self.curso, nome="Aula 1", inicio=amanha)
        Enrollment.objects.create(usuario=self.user, curso=self.curso, status="1")
        self.client.login(username="aluno", password="Senha@123")
        url = reverse("cursos:aula", args=[self.curso.slug, aula.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_material_view_embutido(self):
        amanha = timezone.now().date() + timedelta(days=1)
        aula = Aulas.objects.create(curso=self.curso, nome="Aula 1", inicio=amanha)
        material = Materiais.objects.create(
            aula=aula,
            nome="Video",
            embutido="<iframe></iframe>",
        )
        self.client.login(username="admin", password="Senha@123")
        url = reverse("cursos:material", args=[self.curso.slug, material.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, material.nome)

    def test_material_view_redireciona_download(self):
        amanha = timezone.now().date() + timedelta(days=1)
        aula = Aulas.objects.create(curso=self.curso, nome="Aula 1", inicio=amanha)
        arquivo = SimpleUploadedFile("arquivo.txt", b"conteudo")
        material = Materiais.objects.create(
            aula=aula,
            nome="Arquivo",
            arquivo=arquivo,
        )
        self.client.login(username="admin", password="Senha@123")
        url = reverse("cursos:material", args=[self.curso.slug, material.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/media/aulas/materiais/", response["Location"])


    def test_enrollment_ja_inscrito(self):
        Enrollment.objects.create(usuario=self.user, curso=self.curso)
        self.client.login(username="aluno", password="Senha@123")
        url = reverse("cursos:enrollment", args=[self.curso.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Enrollment.objects.filter(usuario=self.user, curso=self.curso).count(), 1)

    def test_material_view_indisponivel_redireciona_para_aula(self):
        ontem = timezone.now().date() - timedelta(days=1)
        aula = Aulas.objects.create(curso=self.curso, nome="Aula 1", inicio=ontem)
        material = Materiais.objects.create(aula=aula, nome="Arquivo", embutido="")
        self.client.login(username="admin", password="Senha@123")
        url = reverse("cursos:material", args=[self.curso.slug, material.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("cursos:aula", args=[self.curso.slug, aula.pk]), response["Location"])

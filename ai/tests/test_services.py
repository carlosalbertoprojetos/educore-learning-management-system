from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from unittest.mock import patch

from cursos.models import Aulas, Anuncios, Cursos, Materiais
from forum.models import Reply, Thread

from ai.models import AtlasDocument
from ai.services import atlas as atlas_service
from ai.services import studio as studio_service


User = get_user_model()


class StudioServiceTests(SimpleTestCase):
    def test_build_prompt_includes_briefing_fields(self):
        payload = {
            "draft_type": "quiz",
            "title": "Quiz 1",
            "audience": "Iniciantes",
            "goals": "Fixar conceitos",
            "constraints": "5 perguntas",
            "tone": "direto",
            "source_material": "Intro",
        }
        prompt = studio_service.build_prompt(payload)
        self.assertIn("Briefing:", prompt)
        self.assertIn("Tipo: quiz", prompt)
        self.assertIn("Titulo: Quiz 1", prompt)
        self.assertIn("Publico: Iniciantes", prompt)

    def test_generate_draft_returns_fallback_when_not_configured(self):
        output, response = studio_service.generate_draft({"draft_type": "quiz"})
        self.assertIsNone(response)
        self.assertIn("OPENAI_API_KEY", output)

    @patch("ai.services.studio.is_configured", return_value=True)
    @patch("ai.services.studio.create_response", return_value={"output_text": "Rascunho"})
    def test_generate_draft_uses_openai_when_configured(self, _create_response, _configured):
        output, response = studio_service.generate_draft({"draft_type": "quiz", "title": "X"})
        self.assertEqual(output, "Rascunho")
        self.assertIsNotNone(response)


class AtlasServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", email="u@example.com", password="pass")
        self.course = Cursos.objects.create(
            nome="Curso",
            slug="curso",
            descricao="Descricao",
            sobre="Sobre",
        )
        self.aula = Aulas.objects.create(curso=self.course, nome="Aula", descricao="Desc aula")
        self.material = Materiais.objects.create(aula=self.aula, nome="Mat", embutido="Video")
        self.anuncio = Anuncios.objects.create(curso=self.course, titulo="T", conteudo="C")
        self.thread = Thread.objects.create(
            title="Topico",
            slug="topico",
            body="Body",
            author=self.user,
        )
        self.reply = Reply.objects.create(thread=self.thread, reply="Resp", author=self.user)

    def test_build_atlas_creates_documents(self):
        atlas_service.build_atlas(embed=False)
        self.assertEqual(AtlasDocument.objects.count(), 6)
        self.assertTrue(AtlasDocument.objects.filter(source_type="curso").exists())
        self.assertTrue(AtlasDocument.objects.filter(source_type="aula").exists())
        self.assertTrue(AtlasDocument.objects.filter(source_type="material").exists())
        self.assertTrue(AtlasDocument.objects.filter(source_type="anuncio").exists())
        self.assertTrue(AtlasDocument.objects.filter(source_type="forum_thread").exists())
        self.assertTrue(AtlasDocument.objects.filter(source_type="forum_reply").exists())

    @patch("ai.services.atlas.is_configured", return_value=True)
    @patch("ai.services.atlas.create_embedding", return_value={"data": [{"embedding": [0.0, 1.0]}], "model": "test"})
    def test_build_atlas_sets_embeddings_when_enabled(self, _create_embedding, _configured):
        atlas_service.build_atlas(embed=True)
        doc = AtlasDocument.objects.filter(source_type="curso").first()
        self.assertIsNotNone(doc.embedding)
        self.assertEqual(doc.embedding_model, "test")

    def test_search_atlas_falls_back_to_simple_score(self):
        AtlasDocument.objects.create(
            source_type="curso",
            source_id=999,
            course=self.course,
            title="Doc",
            content="alpha beta",
            source_url="/",
            source_hash="x",
            active=True,
        )
        results = atlas_service.search_atlas("alpha", course=self.course, limit=6)
        self.assertTrue(results)
        self.assertEqual(results[0].title, "Doc")

    @patch("ai.services.atlas.is_configured", return_value=True)
    @patch("ai.services.atlas.create_embedding")
    def test_search_atlas_uses_cosine_similarity(self, create_embedding, _configured):
        doc_a = AtlasDocument.objects.create(
            source_type="curso",
            source_id=1000,
            course=self.course,
            title="A",
            content="x",
            source_url="/a",
            source_hash="a",
            active=True,
            embedding=[1.0, 0.0],
        )
        doc_b = AtlasDocument.objects.create(
            source_type="curso",
            source_id=1001,
            course=self.course,
            title="B",
            content="y",
            source_url="/b",
            source_hash="b",
            active=True,
            embedding=[0.0, 1.0],
        )
        create_embedding.return_value = {"data": [{"embedding": [0.0, 1.0]}]}
        results = atlas_service.search_atlas("query", course=self.course, limit=6)
        self.assertTrue(results)
        self.assertEqual(results[0].title, "B")


class RebuildAtlasCommandTests(TestCase):
    @patch("ai.management.commands.rebuild_atlas.build_atlas")
    def test_rebuild_atlas_command_calls_service(self, build_atlas):
        call_command("rebuild_atlas", no_embed=True)
        build_atlas.assert_called_once_with(embed=False)

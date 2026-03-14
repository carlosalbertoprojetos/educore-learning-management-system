from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from cursos.models import Cursos

from ai.models import AIDraft, AtlasDocument, MentorMessage, MentorThread, RiskSignal


User = get_user_model()


class MentorThreadViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u3", email="u3@example.com", password="pass")
        self.course = Cursos.objects.create(nome="Curso", slug="curso")
        self.thread = MentorThread.objects.create(user=self.user, course=self.course, title="T")

    def test_mentor_thread_get(self):
        self.client.login(username="u3", password="pass")
        response = self.client.get(reverse("ai:mentor_thread", args=[self.thread.pk]))
        self.assertEqual(response.status_code, 200)

    def test_mentor_thread_post_creates_messages(self):
        self.client.login(username="u3", password="pass")
        response = self.client.post(
            reverse("ai:mentor_thread", args=[self.thread.pk]),
            {"message": "Como melhorar?"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MentorMessage.objects.filter(thread=self.thread).count(), 2)

    @patch("ai.views.is_configured", return_value=True)
    @patch("ai.views.create_response", return_value={"output_text": "Resposta"})
    @patch("ai.views.atlas_service.search_atlas")
    def test_mentor_reply_configured_path(self, search_atlas, _create_response, _configured):
        doc = AtlasDocument.objects.create(
            source_type="curso",
            source_id=1,
            course=self.course,
            title="Doc",
            content="Conteudo",
            source_url="/cursos/curso/",
            source_hash="x",
            active=True,
        )
        search_atlas.return_value = [doc]

        from ai import views as ai_views

        text, citations = ai_views._mentor_reply(self.thread, "Pergunta")
        self.assertEqual(text, "Resposta")
        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]["title"], "Doc")


class RadarAndStudioActionTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff2", email="s2@example.com", password="pass", is_staff=True
        )
        self.user = User.objects.create_user(username="u4", email="u4@example.com", password="pass")
        self.course = Cursos.objects.create(nome="Curso2", slug="curso2")

    def test_radar_dashboard_requires_staff(self):
        self.client.login(username="u4", password="pass")
        response = self.client.get(reverse("ai:radar_dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_radar_review_marks_signal_reviewed(self):
        signal = RiskSignal.objects.create(
            user=self.user,
            course=self.course,
            label="engagement_drop",
            status="open",
            score=0.9,
        )
        self.client.login(username="staff2", password="pass")
        response = self.client.post(
            reverse("ai:radar_dashboard"),
            {"action": "review", "signal_id": signal.pk},
        )
        self.assertEqual(response.status_code, 302)
        signal.refresh_from_db()
        self.assertEqual(signal.status, "reviewed")
        self.assertEqual(signal.reviewed_by, self.staff)

    def test_studio_approve_and_archive(self):
        draft = AIDraft.objects.create(
            course=self.course,
            created_by=self.staff,
            draft_type="quiz",
            title="D",
            output="x",
        )
        self.client.login(username="staff2", password="pass")

        response = self.client.post(reverse("ai:studio"), {"action": "approve", "draft_id": draft.pk})
        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertEqual(draft.status, "approved")

        response = self.client.post(reverse("ai:studio"), {"action": "archive", "draft_id": draft.pk})
        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertEqual(draft.status, "archived")

    def test_atlas_rebuild_post(self):
        self.client.login(username="staff2", password="pass")
        response = self.client.post(reverse("ai:atlas_rebuild"))
        self.assertEqual(response.status_code, 302)

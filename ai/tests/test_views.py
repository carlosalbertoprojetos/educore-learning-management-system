from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cursos.models import Cursos, Enrollment

from ai.models import AIDraft, LearningEvent, MentorMessage, MentorThread, RiskSignal


User = get_user_model()


class MentorViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user1", email="u1@example.com", password="pass")
        self.course = Cursos.objects.create(nome="Curso X", slug="curso-x")

    def test_mentor_home_requires_login(self):
        response = self.client.get(reverse("ai:mentor_home"))
        self.assertEqual(response.status_code, 302)

    def test_mentor_home_creates_thread(self):
        self.client.login(username="user1", password="pass")
        response = self.client.post(
            reverse("ai:mentor_home"),
            {"title": "Sessao", "course": self.course.id, "message": "Como estudar?"},
        )
        self.assertEqual(response.status_code, 302)
        thread = MentorThread.objects.get(title="Sessao")
        messages = MentorMessage.objects.filter(thread=thread)
        self.assertEqual(messages.count(), 2)


class RadarViewsTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff", email="s@example.com", password="pass", is_staff=True
        )
        self.user = User.objects.create_user(username="user2", email="u2@example.com", password="pass")
        self.course = Cursos.objects.create(nome="Curso Y", slug="curso-y")
        Enrollment.objects.create(usuario=self.user, curso=self.course, status='1')

    def test_radar_analyze_creates_signal(self):
        events = []
        for _ in range(3):
            events.append(
                LearningEvent.objects.create(
                    user=self.user,
                    course=self.course,
                    event_type="view_course",
                    metadata={},
                )
            )
        past = timezone.now() - timedelta(days=20)
        LearningEvent.objects.filter(pk__in=[event.pk for event in events]).update(created_at=past)

        self.client.login(username="staff", password="pass")
        response = self.client.post(reverse("ai:radar_dashboard"), {"action": "analyze"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(RiskSignal.objects.exists())


class StudioViewsTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="studio", email="st@example.com", password="pass", is_staff=True
        )
        self.course = Cursos.objects.create(nome="Curso Z", slug="curso-z")

    def test_studio_creates_draft(self):
        self.client.login(username="studio", password="pass")
        response = self.client.post(
            reverse("ai:studio"),
            {
                "action": "generate",
                "course": self.course.id,
                "draft_type": "quiz",
                "title": "Quiz 1",
                "audience": "Iniciantes",
                "goals": "Fixar conceitos",
                "constraints": "5 perguntas",
                "tone": "direto",
                "source_material": "Introducao",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(AIDraft.objects.filter(title="Quiz 1").exists())

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from django.utils import timezone

from cursos.models import Cursos, Enrollment

from ai.models import LearningEvent
from ai.services import radar as radar_service


User = get_user_model()


class RadarServiceTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="u5", email="u5@example.com", password="pass")
        self.course = Cursos.objects.create(nome="Curso3", slug="curso3")
        Enrollment.objects.create(usuario=self.user, curso=self.course, status=1)

    def test_log_event_ignores_anonymous(self):
        request = self.factory.get("/")
        request.user = AnonymousUser()
        event = radar_service.log_event(request, "view_course", course=self.course)
        self.assertIsNone(event)

    def test_log_event_creates_event_for_authenticated_user(self):
        request = self.factory.get("/")
        request.user = self.user
        event = radar_service.log_event(request, "view_course", course=self.course)
        self.assertIsNotNone(event)
        self.assertEqual(LearningEvent.objects.count(), 1)

    def test_compute_risk_signals_decline_branch(self):
        now = timezone.now()
        recent_start = now - timedelta(days=14)
        prev_start = now - timedelta(days=28)

        prev_ids = []
        for _ in range(10):
            event = LearningEvent.objects.create(
                user=self.user,
                course=self.course,
                event_type="view_course",
                metadata={},
            )
            prev_ids.append(event.pk)
        LearningEvent.objects.filter(pk__in=prev_ids).update(created_at=prev_start + timedelta(hours=1))

        recent_ids = []
        for _ in range(2):
            event = LearningEvent.objects.create(
                user=self.user,
                course=self.course,
                event_type="view_course",
                metadata={},
            )
            recent_ids.append(event.pk)
        LearningEvent.objects.filter(pk__in=recent_ids).update(created_at=recent_start + timedelta(hours=1))

        signals = radar_service.compute_risk_signals(window_days=14, min_prev_events=3)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].label, "engagement_decline")
    def test_compute_risk_signals_skips_when_no_label(self):
        signals = radar_service.compute_risk_signals(window_days=14, min_prev_events=3)
        self.assertEqual(signals, [])

    def test_compute_risk_signals_updates_existing_signal(self):
        now = timezone.now()
        prev_start = now - timedelta(days=28)

        prev_ids = []
        for _ in range(3):
            event = LearningEvent.objects.create(
                user=self.user,
                course=self.course,
                event_type="view_course",
                metadata={},
            )
            prev_ids.append(event.pk)
        LearningEvent.objects.filter(pk__in=prev_ids).update(created_at=prev_start + timedelta(hours=1))

        first = radar_service.compute_risk_signals(window_days=14, min_prev_events=3)
        self.assertEqual(len(first), 1)

        second = radar_service.compute_risk_signals(window_days=14, min_prev_events=3)
        self.assertEqual(len(second), 1)


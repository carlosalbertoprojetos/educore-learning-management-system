from datetime import timedelta

from django.utils import timezone

from cursos.models import Enrollment

from ..models import LearningEvent, RiskSignal


DEFAULT_WINDOW_DAYS = 14


def log_event(request, event_type, course=None, metadata=None):
    if not request.user.is_authenticated:
        return None
    return LearningEvent.objects.create(
        user=request.user,
        course=course,
        event_type=event_type,
        metadata=metadata or {},
    )


def compute_risk_signals(window_days=DEFAULT_WINDOW_DAYS, min_prev_events=3):
    now = timezone.now()
    recent_start = now - timedelta(days=window_days)
    prev_start = now - timedelta(days=window_days * 2)
    signals = []

    for enrollment in Enrollment.objects.select_related("usuario", "curso").all():
        user = enrollment.usuario
        course = enrollment.curso
        recent = LearningEvent.objects.filter(
            user=user,
            course=course,
            created_at__gte=recent_start,
        ).count()
        previous = LearningEvent.objects.filter(
            user=user,
            course=course,
            created_at__gte=prev_start,
            created_at__lt=recent_start,
        ).count()

        label = None
        score = 0.0
        if previous >= min_prev_events and recent == 0:
            label = "engagement_drop"
            score = 0.9
        elif previous >= min_prev_events and recent < max(1, int(previous * 0.3)):
            label = "engagement_decline"
            score = 0.6

        if not label:
            continue

        evidence = {
            "recent": recent,
            "previous": previous,
            "window_days": window_days,
        }
        signal, created = RiskSignal.objects.get_or_create(
            user=user,
            course=course,
            label=label,
            status="open",
            defaults={"score": score, "evidence": evidence},
        )
        if not created:
            signal.score = score
            signal.evidence = evidence
            signal.save(update_fields=["score", "evidence"])
        signals.append(signal)

    return signals

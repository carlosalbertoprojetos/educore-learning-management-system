from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from cursos.models import Cursos


class AtlasDocument(models.Model):
    SOURCE_CHOICES = (
        ("curso", _("Curso")),
        ("aula", _("Aula")),
        ("material", _("Material")),
        ("anuncio", _("Anúncio")),
        ("forum_thread", _("Tópico do fórum")),
        ("forum_reply", _("Resposta do fórum")),
    )

    source_type = models.CharField(max_length=30, choices=SOURCE_CHOICES)
    source_id = models.PositiveIntegerField()
    course = models.ForeignKey(
        Cursos,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="atlas_documents",
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    source_url = models.CharField(max_length=255, blank=True)
    source_hash = models.CharField(max_length=64)
    embedding_model = models.CharField(max_length=80, blank=True)
    embedding = models.JSONField(null=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("source_type", "source_id")
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.source_type}:{self.title}"


class MentorThread(models.Model):
    MODE_CHOICES = (
        ("study", _("Estudo")),
        ("review", _("Revisão")),
        ("coach", _("Mentoria")),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mentor_threads",
    )
    course = models.ForeignKey(
        Cursos,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mentor_threads",
    )
    title = models.CharField(max_length=120)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default="study")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class MentorMessage(models.Model):
    ROLE_CHOICES = (
        ("system", _("Sistema")),
        ("user", _("Usuário")),
        ("assistant", _("Assistente")),
    )

    thread = models.ForeignKey(
        MentorThread,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=12, choices=ROLE_CHOICES)
    content = models.TextField()
    citations = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role} - {self.thread_id}"


class LearningEvent(models.Model):
    EVENT_CHOICES = (
        ("view_course", _("Ver curso")),
        ("view_lesson", _("Ver aula")),
        ("view_material", _("Ver material")),
        ("view_announcements", _("Ver anúncios")),
        ("view_forum", _("Ver fórum")),
        ("view_thread", _("Ver tópico")),
        ("post_reply", _("Publicar resposta")),
        ("login", _("Login")),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="learning_events",
    )
    course = models.ForeignKey(
        Cursos,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="learning_events",
    )
    event_type = models.CharField(max_length=40, choices=EVENT_CHOICES)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} - {self.user_id}"


class RiskSignal(models.Model):
    STATUS_CHOICES = (
        ("open", _("Aberto")),
        ("reviewed", _("Revisado")),
        ("resolved", _("Resolvido")),
    )

    label = models.CharField(max_length=60)
    score = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="risk_signals",
    )
    course = models.ForeignKey(
        Cursos,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="risk_signals",
    )
    evidence = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="open")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_risk_signals",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.label} - {self.user_id}"


class AIDraft(models.Model):
    DRAFT_TYPES = (
        ("quiz", _("Quiz")),
        ("rubric", _("Rubrica")),
        ("announcement", _("Comunicado")),
        ("lesson_outline", _("Plano de aula")),
    )
    STATUS_CHOICES = (
        ("draft", _("Rascunho")),
        ("approved", _("Aprovado")),
        ("archived", _("Arquivado")),
    )

    course = models.ForeignKey(
        Cursos,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_drafts",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_drafts",
    )
    draft_type = models.CharField(max_length=40, choices=DRAFT_TYPES)
    title = models.CharField(max_length=160, blank=True)
    input_context = models.JSONField(null=True, blank=True)
    output = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_ai_drafts",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.draft_type} - {self.title or self.pk}"

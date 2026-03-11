from django.contrib import admin

from .models import AIDraft, AtlasDocument, LearningEvent, MentorMessage, MentorThread, RiskSignal


@admin.register(AtlasDocument)
class AtlasDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "source_type", "source_id", "course", "active", "updated_at")
    list_filter = ("source_type", "active")
    search_fields = ("title", "content")


@admin.register(MentorThread)
class MentorThreadAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "course", "mode", "updated_at")
    search_fields = ("title", "user__username")


@admin.register(MentorMessage)
class MentorMessageAdmin(admin.ModelAdmin):
    list_display = ("thread", "role", "created_at")
    search_fields = ("content",)


@admin.register(LearningEvent)
class LearningEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "user", "course", "created_at")
    list_filter = ("event_type",)


@admin.register(RiskSignal)
class RiskSignalAdmin(admin.ModelAdmin):
    list_display = ("label", "user", "course", "score", "status", "created_at")
    list_filter = ("label", "status")


@admin.register(AIDraft)
class AIDraftAdmin(admin.ModelAdmin):
    list_display = ("draft_type", "title", "course", "created_by", "status", "created_at")
    list_filter = ("draft_type", "status")

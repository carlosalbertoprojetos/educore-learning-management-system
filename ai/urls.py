from django.urls import path

from . import views

app_name = "ai"

urlpatterns = [
    path("", views.mentor_home, name="mentor_home"),
    path("threads/<int:pk>/", views.mentor_thread, name="mentor_thread"),
    path("atlas/", views.atlas_rebuild, name="atlas_rebuild"),
    path("radar/", views.radar_dashboard, name="radar_dashboard"),
    path("studio/", views.studio, name="studio"),
]

"""cursos_online URL Configuration."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from . import views as core_views


urlpatterns = [
    path("favicon.ico", core_views.favicon_ico),
    path("favicon.svg", core_views.favicon_svg),
    path("favicon-32.png", core_views.favicon_png_32),
    path("apple-touch-icon.png", core_views.apple_touch_icon),
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("contato/", TemplateView.as_view(template_name="contato.html"), name="contato"),

    # apps
    path("cursos/", include("cursos.urls", namespace="cursos")),
    path("conta/", include("accounts.urls", namespace="accounts")),
    path("i18n/", include("django.conf.urls.i18n")),
    path("forum/", include("forum.urls", namespace="forum")),
    path("ai/", include("ai.urls", namespace="ai")),

    # admin
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

import os

from django.contrib.staticfiles import finders
from django.http import FileResponse, Http404
from django.utils.http import http_date
from django.views.decorators.http import require_GET


def _serve_favicon(static_path: str, content_type: str):
    absolute_path = finders.find(static_path)
    if not absolute_path:
        raise Http404

    response = FileResponse(open(absolute_path, "rb"), content_type=content_type)

    try:
        mtime = os.path.getmtime(absolute_path)
        response["Last-Modified"] = http_date(mtime)
    except OSError:
        pass

    # Favicons are notoriously over-cached by browsers. Force revalidation.
    response["Cache-Control"] = "no-store, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


@require_GET
def favicon_ico(request):
    return _serve_favicon("favicon.ico", "image/x-icon")


@require_GET
def favicon_svg(request):
    return _serve_favicon("favicon.svg", "image/svg+xml")

@require_GET
def favicon_png_32(request):
    return _serve_favicon("favicon-32.png", "image/png")


@require_GET
def apple_touch_icon(request):
    return _serve_favicon("favicon-180.png", "image/png")


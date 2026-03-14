import os
from pathlib import Path

from django.conf import settings


def favicon_version(request):
    """Expose a stable cache-busting version for favicon assets.

    In dev this uses the favicon.ico mtime; in prod you can override via
    the FAVICON_VERSION env var.
    """

    env_version = os.environ.get("FAVICON_VERSION")
    if env_version:
        return {"FAVICON_VERSION": env_version}

    try:
        static_dir = Path(settings.BASE_DIR) / "static"
        favicon_path = static_dir / "favicon.ico"
        version = str(int(favicon_path.stat().st_mtime))
    except Exception:
        version = "1"

    return {"FAVICON_VERSION": version}

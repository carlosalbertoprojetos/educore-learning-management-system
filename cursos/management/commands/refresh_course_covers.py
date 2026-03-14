from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from cursos.models import Cursos
from cursos.management.commands.seed_investor_demo import (
    STOCK_COVERS,
    _generate_hd_cover,
    _save_stock_cover,
)


class Command(BaseCommand):
    help = "Refresh course cover images (stock HD when possible; local HD fallback)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--stock-images",
            action="store_true",
            help="Download free HD stock covers (Unsplash) and apply them.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing course image fields (default: only set if empty).",
        )

    def handle(self, *args, **options):
        use_stock = bool(options["stock_images"])
        overwrite = bool(options["overwrite"])

        media_root = Path(settings.MEDIA_ROOT or (Path(settings.BASE_DIR) / "media"))
        media_course_dir = media_root / "cursos" / "imagens"
        media_course_dir.mkdir(parents=True, exist_ok=True)

        updated = 0
        missing = 0
        for key, meta in STOCK_COVERS.items():
            slug = meta.get("slug")
            if not slug:
                continue
            try:
                course = Cursos.objects.get(slug=slug)
            except Cursos.DoesNotExist:
                missing += 1
                continue

            if course.imagem and course.imagem.name and not overwrite:
                continue

            dest_name = None
            if use_stock and meta.get("provider") == "unsplash":
                dest_name = _save_stock_cover(course, unsplash_id=meta["id"], out_dir=media_course_dir)
            if not dest_name:
                dest_name = _generate_hd_cover(course, media_course_dir)
            if dest_name:
                course.imagem.name = str(Path("cursos/imagens") / dest_name)
                course.save(update_fields=["imagem"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Covers updated: {updated}. Courses missing: {missing}."))


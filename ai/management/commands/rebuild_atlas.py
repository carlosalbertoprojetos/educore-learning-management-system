from django.core.management.base import BaseCommand

from ai.services.atlas import build_atlas


class Command(BaseCommand):
    help = "Rebuild the Atlas knowledge index."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-embed",
            action="store_true",
            help="Skip embedding generation.",
        )

    def handle(self, *args, **options):
        build_atlas(embed=not options.get("no_embed"))
        self.stdout.write(self.style.SUCCESS("Atlas rebuilt."))

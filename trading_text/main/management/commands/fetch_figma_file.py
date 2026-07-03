import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from main.services.figma import FigmaAPIError, fetch_figma_document


class Command(BaseCommand):
    help = "Fetch a Figma file document with FIGMA_PERSONAL_ACCESS_TOKEN."

    def add_arguments(self, parser):
        parser.add_argument("file_key", help="Figma file key from the file URL.")
        parser.add_argument(
            "--output",
            "-o",
            help="Optional path to write the fetched document JSON.",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=20,
            help="Request timeout in seconds.",
        )

    def handle(self, *args, **options):
        try:
            document = fetch_figma_document(
                options["file_key"],
                timeout=options["timeout"],
            )
        except FigmaAPIError as error:
            raise CommandError(str(error)) from error

        formatted = json.dumps(document, ensure_ascii=False, indent=2)
        output_path = options.get("output")

        if output_path:
            Path(output_path).write_text(formatted + "\n", encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Wrote Figma document to {output_path}"))
            return

        self.stdout.write(formatted)

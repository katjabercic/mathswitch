from django.core.management.base import BaseCommand
from categorizer.categorizer_service import CategorizerService


class Command(BaseCommand):
    help = "Categorize mathematical concepts using all free LLMs (HuggingFace models)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit the number of items to categorize",
        )

    def handle(self, *args, **options):
        limit = options.get("limit")

        service = CategorizerService()

        self.stdout.write("Using all free LLMs: huggingface_flan_t5, huggingface_gpt2, huggingface_dialogpt")
        if limit:
            self.stdout.write(f"Categorizing up to {limit} items...")
        else:
            self.stdout.write("Categorizing all items...")

        try:
            service.categorize_items(limit=limit)
            self.stdout.write(self.style.SUCCESS("Categorization complete!"))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Categorization failed: {e}")
            )

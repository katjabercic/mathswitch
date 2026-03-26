from categorizer.categorizer_service import JUDGE_POOLS, CategorizerService
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Categorize mathematical concepts using LLM judge pools"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit the number of items to categorize",
        )
        parser.add_argument(
            "--judge-pool",
            type=str,
            default="low",
            choices=JUDGE_POOLS.keys(),
            help="LLM judge pool to use: low/local (HuggingFace),"
            " high (~12GB Ollama models)",
        )

    def handle(self, *args, **options):
        limit = options.get("limit")
        judge_pool = options.get("judge_pool")

        service = CategorizerService()

        pool = JUDGE_POOLS[judge_pool]
        model_names = ", ".join(m.value for m in pool)
        self.stdout.write(f"Using judge pool '{judge_pool}': {model_names}")

        if limit:
            self.stdout.write(f"Categorizing up to {limit} items...")
        else:
            self.stdout.write("Categorizing all items...")

        try:
            service.categorize_items(limit=limit, judge_pool=judge_pool)
            self.stdout.write(self.style.SUCCESS("Categorization complete!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Categorization failed: {e}"))

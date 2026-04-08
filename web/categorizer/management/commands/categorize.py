from categorizer.categorizer_service import JUDGE_POOLS, CategorizerService
from concepts.models import Item
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
            default="high",
            choices=JUDGE_POOLS.keys(),
            help="LLM judge pool to use: low/local (HuggingFace),"
            " high (~12GB Ollama models)",
        )
        parser.add_argument(
            "--domain",
            type=str,
            default=Item.Domain.MATHEMATICS,
            choices=Item.Domain.values,
            help="Domain to categorize: math (default) or phys",
        )
        parser.add_argument(
            "--source",
            type=str,
            default=None,
            choices=Item.Source.values,
            help="Filter by source (e.g. Wd, nL, MW, PW, EoM, WpEN, AUm)",
        )
        parser.add_argument(
            "--fetch",
            action="store_true",
            default=False,
            help="Fetch entity data from the source API if missing in item.meta",
        )
        parser.add_argument(
            "--no-mathworld-id",
            action="store_true",
            default=False,
            help="Only process items that have metadata but no MathWorld ID",
        )
        parser.add_argument(
            "--has-mathworld-id",
            action="store_true",
            default=False,
            help="Only process items that have metadata with a MathWorld ID",
        )
        parser.add_argument(
            "--use-other-ids",
            action="store_true",
            default=False,
            help="Include external IDs from metadata in the LLM prompt",
        )
        parser.add_argument(
            "--session-name",
            type=str,
            default=None,
            help="Optional session name to tag categorization results",
        )

    def handle(self, *args, **options):
        limit = options.get("limit")
        judge_pool = options.get("judge_pool")
        domain = options.get("domain")
        source = options.get("source")
        fetch = options.get("fetch")
        no_mathworld_id = options.get("no_mathworld_id")
        has_mathworld_id = options.get("has_mathworld_id")
        use_other_ids = options.get("use_other_ids")
        session_name = options.get("session_name")

        service = CategorizerService()

        pool = JUDGE_POOLS[judge_pool]
        model_names = ", ".join(m.value for m in pool)
        self.stdout.write(f"Using judge pool '{judge_pool}': {model_names}")
        self.stdout.write(f"Domain: {domain}")
        if source:
            self.stdout.write(f"Source: {source}")

        if limit:
            self.stdout.write(f"Categorizing up to {limit} items...")
        else:
            self.stdout.write("Categorizing all items...")

        try:
            service.categorize_items(
                limit=limit,
                judge_pool=judge_pool,
                domain=domain,
                source=source,
                fetch=fetch,
                no_mathworld_id=no_mathworld_id,
                has_mathworld_id=has_mathworld_id,
                use_other_ids=use_other_ids or fetch,
                session_name=session_name,
            )
            self.stdout.write(self.style.SUCCESS("Categorization complete!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Categorization failed: {e}"))

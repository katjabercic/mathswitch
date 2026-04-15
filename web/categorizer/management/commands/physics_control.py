from concepts.models import CategorizerResult, Item
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Summarize the physics-concepts control experiment: distribution of "
        "'math' votes per item, mean confidence per group, and the full list "
        "of items that received a unanimous 'math' vote."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--session",
            type=str,
            required=True,
            help="Session name of the physics-concepts categorization run.",
        )

    def handle(self, *args, **options):
        session = options["session"]

        by_item = {}
        for item_id, answer, confidence in CategorizerResult.objects.filter(
            session_name=session
        ).values_list("item_id", "result_answer", "result_confidence"):
            by_item.setdefault(item_id, []).append((bool(answer), int(confidence)))

        if not by_item:
            self.stdout.write(
                self.style.ERROR(f"No CategorizerResult rows for session '{session}'")
            )
            return

        # Per-item aggregation
        groups = {0: [], 1: [], 2: [], 3: []}  # yes_votes -> list[(item_id, [conf])]
        for item_id, judgments in by_item.items():
            yes_votes = sum(1 for ans, _ in judgments if ans)
            confidences = [c for _, c in judgments]
            groups.setdefault(yes_votes, []).append((item_id, confidences))

        total_items = sum(len(v) for v in groups.values())

        self.stdout.write(
            f"\nPhysics control — session '{session}' — {total_items} items\n"
        )

        # ----- Distribution + mean confidence per group -----
        rows = []
        for k in sorted(groups):
            items = groups[k]
            n = len(items)
            if n == 0:
                mean_conf = 0.0
            else:
                all_confs = [c for _, confs in items for c in confs]
                mean_conf = sum(all_confs) / len(all_confs)
            rows.append((k, n, mean_conf))

        header = f"{'Judges voting math':>20} {'Items':>8} {'Mean confidence':>18}"
        self.stdout.write(header)
        self.stdout.write("-" * len(header))
        for k, n, mean_conf in rows:
            self.stdout.write(f"{k:>20} {n:>8} {mean_conf:>17.1f}")

        # LaTeX tabular for the augmented distribution table
        self.stdout.write("\nLaTeX tabular (vote distribution + mean confidence):\n")
        self.stdout.write(
            "\\begin{tabular}"
            "{>{\\raggedleft\\arraybackslash}p{0.28\\textwidth}"
            ">{\\raggedleft\\arraybackslash}p{0.20\\textwidth}"
            ">{\\raggedleft\\arraybackslash}p{0.20\\textwidth}}"
        )
        self.stdout.write("    \\toprule")
        self.stdout.write(
            "    Judges voting ``math'' & Number of items & " "Mean confidence \\\\"
        )
        self.stdout.write("    \\midrule")
        for k, n, mean_conf in rows:
            self.stdout.write(f"    {k} & {n:>3} & {mean_conf:5.1f} \\\\")
        self.stdout.write("    \\bottomrule")
        self.stdout.write("\\end{tabular}\n")

        # ----- Exhaustive list of items with unanimous 'math' votes -----
        unanimous = groups.get(3, [])
        if not unanimous:
            self.stdout.write("\nNo items received a unanimous 'math' vote.\n")
            return

        unanimous_ids = [item_id for item_id, _ in unanimous]
        items_by_id = {i.id: i for i in Item.objects.filter(id__in=unanimous_ids)}

        # Attach name + mean confidence per item, ordered by name
        enriched = []
        for item_id, confs in unanimous:
            item = items_by_id.get(item_id)
            name = item.name if item and item.name else f"(item #{item_id})"
            mean_conf = sum(confs) / len(confs) if confs else 0.0
            enriched.append((name, mean_conf))
        enriched.sort(key=lambda x: (x[0] or "").lower())

        self.stdout.write(f"\nItems with unanimous 'math' vote ({len(enriched)}):\n")
        for name, mean_conf in enriched:
            self.stdout.write(f"  - {name}  (mean confidence {mean_conf:.1f})")

        # LaTeX tabular for the unanimous-items list
        self.stdout.write("\nLaTeX tabular (unanimous 'math' items):\n")
        self.stdout.write(
            "\\begin{tabular}"
            "{>{\\raggedright\\arraybackslash}p{0.60\\textwidth}"
            ">{\\raggedleft\\arraybackslash}p{0.20\\textwidth}}"
        )
        self.stdout.write("    \\toprule")
        self.stdout.write("    Concept & Mean confidence \\\\")
        self.stdout.write("    \\midrule")
        for name, mean_conf in enriched:
            safe = (name or "").replace("&", "\\&").replace("_", "\\_")
            self.stdout.write(f"    {safe} & {mean_conf:5.1f} \\\\")
        self.stdout.write("    \\bottomrule")
        self.stdout.write("\\end{tabular}\n")

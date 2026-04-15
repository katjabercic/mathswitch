# Requirements: matplotlib, scikit-learn
# Install: pip install matplotlib scikit-learn

import json
import os

import matplotlib.pyplot as plt
import numpy as np
from concepts.models import CategorizerResult, Item
from django.core.management.base import BaseCommand
from sklearn.calibration import calibration_curve
from sklearn.metrics import auc, precision_recall_curve, roc_curve


def aggregate_item_predictions(results):
    """Aggregate multiple LLM judgments for a single item into one prediction.

    results: list of (answer: bool, confidence: int) tuples (typically 3 per item).
    Returns: (aggregated_answer: bool, aggregated_score: float in [0, 100])

    Current strategy: majority vote on answer, mean of math-probability scores.
    The math_score for one judgment is `confidence` if YES else `100 - confidence`.

    This is the ONLY place to change when switching to weighted average.
    """
    if not results:
        return False, 0.0
    yes_votes = sum(1 for ans, _ in results if ans)
    aggregated_answer = yes_votes > len(results) / 2
    math_scores = [c if ans else 100 - c for ans, c in results]
    aggregated_score = sum(math_scores) / len(math_scores)
    return aggregated_answer, aggregated_score


class Command(BaseCommand):
    help = "Generate classifier evaluation charts and confusion matrices"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            type=str,
            default="./classifier_reports/",
            help="Directory to save generated PNG charts"
            " (default: ./classifier_reports/)",
        )
        parser.add_argument(
            "--threshold",
            type=int,
            default=50,
            choices=range(0, 101),
            metavar="0-100",
            help="Classification threshold (0–100, default: 50)",
        )
        parser.add_argument(
            "--tp-session",
            type=str,
            required=True,
            help="Session name for items WITH MathWorld ID, classified WITH it",
        )
        parser.add_argument(
            "--obs-session",
            type=str,
            required=True,
            help="Session name for the same items, classified WITHOUT MathWorld ID",
        )
        parser.add_argument(
            "--results-session",
            type=str,
            required=True,
            help="Session name for items WITHOUT MathWorld ID",
        )
        parser.add_argument(
            "--results-limit",
            type=int,
            default=1500,
            help="How many items to take from the results session (top N by item_id)",
        )

    def handle(self, *args, **options):
        output_dir = options["output_dir"]
        threshold = options["threshold"]
        tp_session = options["tp_session"]
        obs_session = options["obs_session"]
        results_session = options["results_session"]
        results_limit = options["results_limit"]

        # ----- Load and aggregate per-item predictions -----
        tp_preds = self._load_session_predictions(tp_session)
        obs_preds = self._load_session_predictions(obs_session)
        results_preds = self._load_session_predictions(
            results_session, limit=results_limit
        )

        self.stdout.write(
            f"Loaded items — tp: {len(tp_preds)}, obs: {len(obs_preds)}, "
            f"results: {len(results_preds)} (limit {results_limit})"
        )

        # ----- Build ground truth from Item.meta (MW ID presence) -----
        all_item_ids = set(tp_preds) | set(obs_preds) | set(results_preds)
        ground_truth = self._build_ground_truth(all_item_ids)

        n_pos = sum(1 for v in ground_truth.values() if v == 1)
        n_neg = sum(1 for v in ground_truth.values() if v == 0)
        self.stdout.write(
            f"Ground truth (MW ID presence) — positives: {n_pos}, negatives: {n_neg}"
        )

        # ----- Build the 4 datasets and their confusion matrices -----
        tp_results = {**tp_preds, **results_preds}
        obs_results = {**obs_preds, **results_preds}

        cm_a = self._confusion_matrix(tp_preds, ground_truth, threshold)
        cm_b = self._confusion_matrix(obs_preds, ground_truth, threshold)
        cm_c = self._confusion_matrix(tp_results, ground_truth, threshold)
        cm_d = self._confusion_matrix(obs_results, ground_truth, threshold)

        self.stdout.write(f"\nConfusion matrices at threshold = {threshold}")
        self._print_confusion_matrix(
            "Table A: tp_session alone (1000, all positive)", *cm_a
        )
        self._print_confusion_matrix(
            "Table B: obs_session alone (1000, all positive)", *cm_b
        )
        self._print_confusion_matrix(
            "Table C: tp_session + results (with MW ID signal)", *cm_c
        )
        self._print_confusion_matrix(
            "Table D: obs_session + results (without MW ID signal)", *cm_d
        )

        # ----- Generate charts (all derived from confusion matrices / scores) -----
        os.makedirs(output_dir, exist_ok=True)
        plt.style.use("seaborn-v0_8-whitegrid")

        self._plot_confidence_distributions(
            output_dir, tp_preds, obs_preds, results_preds
        )
        auc_c, auc_d = self._plot_roc_curve(
            output_dir, tp_results, obs_results, ground_truth
        )
        self._plot_roc_curve_labeled(output_dir, tp_preds, obs_preds, results_limit)
        self._plot_precision_recall_curve(
            output_dir, tp_results, obs_results, ground_truth
        )
        self._plot_calibration(output_dir, tp_results, obs_results, ground_truth)
        self._plot_threshold_analysis(output_dir, obs_results, ground_truth, threshold)

        self._print_summary(
            tp_preds, obs_preds, results_preds, cm_d, auc_c, auc_d, threshold
        )

        self.stdout.write(self.style.SUCCESS(f"Charts saved to {output_dir}"))

    # ===== Data loading =====

    def _load_session_predictions(self, session_name, limit=None):
        """Load all results for a session, group by item_id, and aggregate per item.

        Returns: {item_id: (aggregated_answer, aggregated_score)}
        """
        qs = CategorizerResult.objects.filter(session_name=session_name)

        if limit is not None:
            top_ids = sorted(set(qs.values_list("item_id", flat=True)))[:limit]
            qs = qs.filter(item_id__in=top_ids)

        by_item = {}
        for item_id, confidence, answer in qs.values_list(
            "item_id", "result_confidence", "result_answer"
        ):
            by_item.setdefault(item_id, []).append((bool(answer), int(confidence)))

        return {
            item_id: aggregate_item_predictions(results)
            for item_id, results in by_item.items()
        }

    def _build_ground_truth(self, item_ids):
        """Return {item_id: 1 if Item.meta contains a mathworld_id, else 0}."""
        gt = {}
        for item_id, meta in Item.objects.filter(id__in=item_ids).values_list(
            "id", "meta"
        ):
            has_mw = False
            if meta:
                try:
                    has_mw = bool(json.loads(meta).get("mathworld_id"))
                except (json.JSONDecodeError, TypeError, AttributeError):
                    pass
            gt[item_id] = 1 if has_mw else 0
        return gt

    # ===== Core primitive: confusion matrix =====

    @staticmethod
    def _confusion_matrix(item_preds, ground_truth, threshold):
        """Return (tp, fp, tn, fn). Predicted positive iff
        aggregated_score >= threshold."""
        tp = fp = tn = fn = 0
        for item_id, (_, score) in item_preds.items():
            if item_id not in ground_truth:
                continue
            actual = ground_truth[item_id]
            predicted = 1 if score >= threshold else 0
            if predicted == 1 and actual == 1:
                tp += 1
            elif predicted == 1 and actual == 0:
                fp += 1
            elif predicted == 0 and actual == 0:
                tn += 1
            else:
                fn += 1
        return tp, fp, tn, fn

    def _print_confusion_matrix(self, label, tp, fp, tn, fn):
        total = tp + fp + tn + fn
        self.stdout.write("\n" + label)
        self.stdout.write("-" * max(len(label), 60))
        self.stdout.write("                       Predicted YES    Predicted NO")
        self.stdout.write(f"  Actual YES (math)        {tp:>6d}            {fn:>6d}")
        self.stdout.write(f"  Actual NO  (no MW)       {fp:>6d}            {tn:>6d}")
        self.stdout.write(f"  Total: {total}")

    # ===== Helpers =====

    @staticmethod
    def _scores_and_labels(item_preds, ground_truth):
        scores, labels = [], []
        for item_id, (_, score) in item_preds.items():
            if item_id not in ground_truth:
                continue
            scores.append(score / 100.0)
            labels.append(ground_truth[item_id])
        return np.array(scores, dtype=float), np.array(labels, dtype=int)

    @staticmethod
    def _aggregated_scores(item_preds):
        return np.array([score for (_, score) in item_preds.values()], dtype=float)

    # ===== Plotting =====

    def _plot_confidence_distributions(
        self, output_dir, tp_preds, obs_preds, results_preds
    ):
        fig, ax = plt.subplots(figsize=(10, 6))
        bins = np.linspace(0, 100, 21)

        tp_scores = self._aggregated_scores(tp_preds)
        obs_scores = self._aggregated_scores(obs_preds)
        results_scores = self._aggregated_scores(results_preds)

        if len(tp_scores) > 0:
            ax.hist(tp_scores, bins=bins, alpha=0.5, label=f"tp (n={len(tp_scores)})")
        if len(obs_scores) > 0:
            ax.hist(
                obs_scores, bins=bins, alpha=0.5, label=f"obs (n={len(obs_scores)})"
            )
        if len(results_scores) > 0:
            ax.hist(
                results_scores,
                bins=bins,
                alpha=0.5,
                label=f"results (n={len(results_scores)})",
            )

        ax.set_xlabel("Aggregated Math Score (per item)")
        ax.set_ylabel("Count")
        ax.set_title("Confidence Score Distributions (per-item aggregated)")
        ax.legend()
        fig.tight_layout()
        fig.savefig(os.path.join(output_dir, "confidence_distributions.png"), dpi=150)
        plt.close(fig)

    def _plot_roc_curve(self, output_dir, tp_results, obs_results, ground_truth):
        scores_c, labels_c = self._scores_and_labels(tp_results, ground_truth)
        scores_d, labels_d = self._scores_and_labels(obs_results, ground_truth)

        if len(np.unique(labels_c)) < 2 or len(np.unique(labels_d)) < 2:
            self.stdout.write(self.style.WARNING("Skipping ROC: need both classes"))
            return float("nan"), float("nan")

        fpr_c, tpr_c, _ = roc_curve(labels_c, scores_c)
        auc_c = auc(fpr_c, tpr_c)
        fpr_d, tpr_d, _ = roc_curve(labels_d, scores_d)
        auc_d = auc(fpr_d, tpr_d)

        fig, ax = plt.subplots(figsize=(8, 8))
        ax.plot(fpr_c, tpr_c, linewidth=2, label=f"Included (AUC={auc_c:.3f})")
        ax.plot(fpr_d, tpr_d, linewidth=2, label=f"Excluded (AUC={auc_d:.3f})")
        ax.plot([0, 1], [0, 1], "k--", linewidth=1, label="Random")
        ax.set_xlabel("False Positive Rate", fontsize=12)
        ax.set_ylabel("True Positive Rate", fontsize=12)
        ax.set_title(
            "ROC Curve (MathWorld identifier included vs. excluded)", fontsize=14
        )
        ax.tick_params(axis="both", labelsize=12)
        ax.legend(loc="lower right", fontsize=12)
        fig.tight_layout()
        fig.savefig(os.path.join(output_dir, "roc_curve.png"), dpi=150)
        plt.close(fig)

        return auc_c, auc_d

    def _plot_roc_curve_labeled(self, output_dir, tp_preds, obs_preds, limit):
        common_ids = sorted(set(tp_preds) & set(obs_preds))[:limit]
        if not common_ids:
            self.stdout.write(
                self.style.WARNING("Skipping labeled ROC: no common items")
            )
            return

        labels = np.array([1 if tp_preds[i][0] else 0 for i in common_ids], dtype=int)
        scores_with = np.array(
            [tp_preds[i][1] / 100.0 for i in common_ids], dtype=float
        )
        scores_without = np.array(
            [obs_preds[i][1] / 100.0 for i in common_ids], dtype=float
        )

        if len(np.unique(labels)) < 2:
            self.stdout.write(
                self.style.WARNING(
                    "Skipping labeled ROC: include-MW-ID answers are single-class"
                )
            )
            return

        fpr_w, tpr_w, _ = roc_curve(labels, scores_with)
        auc_w = auc(fpr_w, tpr_w)
        fpr_wo, tpr_wo, _ = roc_curve(labels, scores_without)
        auc_wo = auc(fpr_wo, tpr_wo)

        fig, ax = plt.subplots(figsize=(8, 8))
        ax.plot(
            fpr_w,
            tpr_w,
            linewidth=2,
            label=f"With MathWorld ID (AUC={auc_w:.3f})",
        )
        ax.plot(
            fpr_wo,
            tpr_wo,
            linewidth=2,
            label=f"Without MathWorld ID (AUC={auc_wo:.3f})",
        )
        ax.plot([0, 1], [0, 1], "k--", linewidth=1, label="Random")
        ax.set_xlabel("False Positive Rate", fontsize=12)
        ax.set_ylabel("True Positive Rate", fontsize=12)
        ax.set_title(
            f"ROC Curve (n={len(common_ids)}, "
            "labels = include-MW-ID aggregated answer)",
            fontsize=14,
        )
        ax.tick_params(axis="both", labelsize=12)
        ax.legend(loc="lower right", fontsize=12)
        fig.tight_layout()
        fig.savefig(os.path.join(output_dir, "roc_curve_labeled.png"), dpi=150)
        plt.close(fig)

    def _plot_precision_recall_curve(
        self, output_dir, tp_results, obs_results, ground_truth
    ):
        scores_c, labels_c = self._scores_and_labels(tp_results, ground_truth)
        scores_d, labels_d = self._scores_and_labels(obs_results, ground_truth)

        if len(np.unique(labels_c)) < 2 or len(np.unique(labels_d)) < 2:
            self.stdout.write(
                self.style.WARNING("Skipping PR curve: need both classes")
            )
            return

        prec_c, rec_c, _ = precision_recall_curve(labels_c, scores_c)
        prec_d, rec_d, _ = precision_recall_curve(labels_d, scores_d)
        prevalence = float(np.mean(labels_d))

        fig, ax = plt.subplots(figsize=(8, 8))
        ax.plot(rec_c, prec_c, linewidth=2, label="Table C: tp+results")
        ax.plot(rec_d, prec_d, linewidth=2, label="Table D: obs+results")
        ax.axhline(
            y=prevalence,
            color="r",
            linestyle="--",
            linewidth=1,
            label=f"Baseline (prevalence={prevalence:.3f})",
        )
        ax.set_xlabel("Recall")
        ax.set_ylabel("Precision")
        ax.set_title("Precision-Recall Curve")
        ax.legend(loc="lower left")
        fig.tight_layout()
        fig.savefig(os.path.join(output_dir, "precision_recall_curve.png"), dpi=150)
        plt.close(fig)

    def _plot_calibration(self, output_dir, tp_results, obs_results, ground_truth):
        scores_c, labels_c = self._scores_and_labels(tp_results, ground_truth)
        scores_d, labels_d = self._scores_and_labels(obs_results, ground_truth)

        if len(np.unique(labels_c)) < 2 or len(np.unique(labels_d)) < 2:
            self.stdout.write(
                self.style.WARNING("Skipping calibration: need both classes")
            )
            return

        frac_c, mean_c = calibration_curve(labels_c, scores_c, n_bins=10)
        frac_d, mean_d = calibration_curve(labels_d, scores_d, n_bins=10)

        fig, ax = plt.subplots(figsize=(8, 8))
        ax.plot(mean_c, frac_c, "s-", linewidth=2, label="Table C: tp+results")
        ax.plot(mean_d, frac_d, "o-", linewidth=2, label="Table D: obs+results")
        ax.plot([0, 1], [0, 1], "k--", linewidth=1, label="Perfect calibration")
        ax.set_xlabel("Mean Predicted Probability")
        ax.set_ylabel("Fraction of Positives")
        ax.set_title("Calibration Plot")
        ax.legend(loc="lower right")
        fig.tight_layout()
        fig.savefig(os.path.join(output_dir, "calibration_plot.png"), dpi=150)
        plt.close(fig)

    def _plot_threshold_analysis(
        self, output_dir, obs_results, ground_truth, selected_threshold
    ):
        if not obs_results:
            self.stdout.write(
                self.style.WARNING("Skipping threshold analysis: no data")
            )
            return

        thresholds = np.arange(1, 100)
        precisions, recalls, f1s = [], [], []
        for t in thresholds:
            tp, fp, _, fn = self._confusion_matrix(obs_results, ground_truth, int(t))
            p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
            precisions.append(p)
            recalls.append(r)
            f1s.append(f1)

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(thresholds, precisions, label="Precision", linewidth=2)
        ax.plot(thresholds, recalls, label="Recall", linewidth=2)
        ax.plot(thresholds, f1s, label="F1", linewidth=2)
        ax.axvline(
            x=selected_threshold,
            color="gray",
            linestyle="--",
            linewidth=1.5,
            label=f"Threshold = {selected_threshold}",
        )
        ax.set_xlabel("Threshold")
        ax.set_ylabel("Score")
        ax.set_title("Precision, Recall, and F1 vs. Threshold (Table D)")
        ax.legend()
        fig.tight_layout()
        fig.savefig(os.path.join(output_dir, "threshold_analysis.png"), dpi=150)
        plt.close(fig)

    # ===== Summary =====

    def _print_summary(
        self, tp_preds, obs_preds, results_preds, cm_d, auc_c, auc_d, threshold
    ):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("CLASSIFIER EVALUATION SUMMARY")
        self.stdout.write("=" * 60)

        self.stdout.write(f"\nAUC Table C (tp+results):  {auc_c:.4f}")
        self.stdout.write(f"AUC Table D (obs+results): {auc_d:.4f}")

        for name, preds in [
            ("tp", tp_preds),
            ("obs", obs_preds),
            ("results", results_preds),
        ]:
            scores = self._aggregated_scores(preds)
            if len(scores) == 0:
                continue
            n_yes = int(np.sum(scores >= threshold))
            self.stdout.write(
                f"\n{name}: n={len(scores)}, "
                f"mean_score={np.mean(scores):.2f}, "
                f"predicted YES at t={threshold}: {n_yes} "
                f"({100 * n_yes / len(scores):.1f}%)"
            )

        # Most actionable number: items the classifier (without MW ID signal) thinks
        # are math but are not yet in MathWorld → suggestions for inclusion.
        _, fp_d, _, _ = cm_d
        self.stdout.write(
            f"\nMW inclusion suggestions (Table D FP at t={threshold}): {fp_d}"
        )
        self.stdout.write("=" * 60 + "\n")

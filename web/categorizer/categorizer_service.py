import logging
import time
from datetime import datetime

from categorizer.llm_service import LLMService, LLMType
from categorizer.prompts import build_categorization_prompt
from categorizer.result_parsers import (
    parse_categorization_result,
    parse_categorization_result_with_reasoning,
)
from categorizer.wikidata_fetch_service import WikidataFetchService
from concepts.models import CategorizerResult, Item

# Free LLM types to use for categorization
LLM_JUDGE_POOL = [
    LLMType.HUGGINGFACE_FLAN_T5,
    LLMType.HUGGINGFACE_GPT2,
    LLMType.HUGGINGFACE_DIALOGPT,
]

# High-parameter local models (~12GB VRAM, Q4 quantization)
LLM_JUDGE_POOL_HIGH = [
    LLMType.OLLAMA_DEEPSEEK_R1_14B,
    LLMType.OLLAMA_QWEN25_14B,
    LLMType.OLLAMA_GEMMA3_12B,
]

JUDGE_POOLS = {
    "low": LLM_JUDGE_POOL,
    "local": LLM_JUDGE_POOL,
    "high": LLM_JUDGE_POOL_HIGH,
}


class CategorizerService:
    """
    Service for categorizing mathematical concepts.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm_service = LLMService()
        self.wikidata_fetch_service = WikidataFetchService()

    def categorize_items(
        self,
        limit=None,
        judge_pool="low",
        domain=None,
        source=None,
        fetch=False,
        no_mathworld_id=False,
        has_mathworld_id=False,
        use_other_ids=False,
        session_name=None,
    ):
        """
        Categorize items from the database using all free LLM types.

        Args:
            limit: Optional limit on number of items to process
            judge_pool: Which pool of LLMs to use ("low", "local", or "high")
            session_name: Optional session name to tag results
        """
        if session_name is None:
            session_name = f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        pool = JUDGE_POOLS.get(judge_pool, LLM_JUDGE_POOL)
        pool_llm_values = {llm.value for llm in pool}

        self.logger.info(f"Session name: '{session_name}'")

        # Build a map of item_id -> set of llm_types already completed
        existing_results = CategorizerResult.objects.filter(
            session_name=session_name,
            llm_type__in=pool_llm_values,
        ).values_list("item_id", "llm_type")
        completed_llms_by_item = {}
        for item_id, llm_type in existing_results:
            completed_llms_by_item.setdefault(item_id, set()).add(llm_type)

        # Items fully covered by all LLMs in the pool can be skipped entirely
        fully_processed_ids = {
            item_id
            for item_id, llm_types in completed_llms_by_item.items()
            if pool_llm_values <= llm_types
        }

        skipped = len(fully_processed_ids)

        queryset = Item.objects.filter(domain=domain) if domain else Item.objects.all()
        if source:
            queryset = queryset.filter(source=source)
        if no_mathworld_id:
            queryset = (
                queryset.exclude(meta__isnull=True)
                .exclude(meta="")
                .exclude(meta__contains='"mathworld_id"')
            )
        if has_mathworld_id:
            queryset = queryset.filter(meta__contains='"mathworld_id"')
        if fully_processed_ids:
            queryset = queryset.exclude(id__in=fully_processed_ids)
        queryset = queryset.order_by("id")
        if limit:
            remaining = limit - skipped
            if remaining <= 0:
                self.logger.info(
                    f"Limit of {limit} already reached "
                    f"({skipped} previously processed). Nothing to do."
                )
                return
            queryset = queryset[:remaining]

        items_to_process = list(queryset)
        to_process = len(items_to_process)

        # Count partially processed items
        partially_processed = sum(
            1 for item in items_to_process if item.id in completed_llms_by_item
        )

        self.logger.info(
            f"Items: {skipped} fully processed, "
            f"{partially_processed} partially processed, "
            f"{to_process - partially_processed} new "
            f"(pool={judge_pool}, {len(pool)} LLMs)"
        )

        total_start = time.perf_counter()
        for i, item in enumerate(items_to_process):
            # Determine which LLMs still need to run for this item
            done_llms = completed_llms_by_item.get(item.id, set())
            remaining_pool = [llm for llm in pool if llm.value not in done_llms]

            if done_llms:
                self.logger.info(
                    f"Processing item {i + 1}/{to_process}: {item.identifier} "
                    f"({len(remaining_pool)}/{len(pool)} LLMs remaining)"
                )
            else:
                self.logger.info(
                    f"Processing item {i + 1}/{to_process}: {item.identifier}"
                )

            if fetch:
                self.wikidata_fetch_service.fetch_and_store_meta(item)
            self.categorize_item(
                item,
                pool=remaining_pool,
                session_name=session_name,
                judge_pool=judge_pool,
                use_other_ids=use_other_ids,
            )

        total_elapsed = time.perf_counter() - total_start
        self.logger.info(f"Categorization complete in {total_elapsed:.2f}s")

    def categorize_item(
        self,
        item,
        predicate: str = "Is the given concept a mathematical concept,"
        " given the name, description, "
        "keywords, and article text?",
        pool=None,
        session_name=None,
        judge_pool="low",
        use_other_ids=True,
    ):
        """
        Categorize a single item using all free LLM types.

        Args:
            item: Item instance to categorize
            predicate: The question to evaluate (default: checks if it's
            a mathematical concept)
            pool: List of LLMType to use (defaults to LLM_JUDGE_POOL)
            session_name: Optional session name to tag results
            judge_pool: Which pool tier ("low", "local", or "high")
            use_other_ids: Include external IDs from meta in prompt

        Returns:
            List of categorization results from all LLMs
        """
        if pool is None:
            pool = LLM_JUDGE_POOL

        use_reasoning = judge_pool not in ("low", "local")

        self.logger.debug(f"Categorizing: {item.name}")

        prompt = build_categorization_prompt(
            item, predicate, with_reasoning=use_reasoning, use_other_ids=use_other_ids
        )

        results = []

        pool_start = time.perf_counter()
        for llm_type in pool:
            try:
                self.logger.info(f"Calling {llm_type.value} for {item.name}")
                llm_start = time.perf_counter()
                raw_result = self.llm_service.call_llm(llm_type, prompt)
                llm_elapsed = time.perf_counter() - llm_start
                self.logger.info(
                    f"LLM call '{llm_type.value}' for '{item.name}' "
                    f"took {llm_elapsed:.2f}s"
                )
                self.logger.info(
                    f"Categorized {item.name} with {llm_type.value}: "
                    f"{raw_result[:100]}..."
                )

                print(f"{raw_result}")

                if use_reasoning:
                    parsed_result = parse_categorization_result_with_reasoning(
                        raw_result
                    )
                else:
                    parsed_result = parse_categorization_result(raw_result)

                confidence = parsed_result["confidence"]
                if confidence is None:
                    confidence = 50

                categorizer_result = CategorizerResult.objects.create(
                    item=item,
                    llm_type=llm_type.value,
                    raw_result=raw_result,
                    result_answer=parsed_result["answer"],
                    result_confidence=confidence,
                    session_name=session_name,
                    reasoning=parsed_result.get("reasoning"),
                )
                categorizer_result.save()

                self.logger.info(
                    f"Saved categorization result for {item.name} ({llm_type.value}): "
                    f"answer={parsed_result['answer']}, "
                    f"confidence={parsed_result['confidence']}"
                )

                results.append(parsed_result)
            except Exception as e:
                self.logger.error(
                    f"Failed to categorize '{item.name}' with '{llm_type.value}': '{e}'"
                )
                # Continue with other LLMs even if one fails?
                continue

        pool_elapsed = time.perf_counter() - pool_start
        self.logger.info(
            f"Pool execution for '{item.name}' took {pool_elapsed:.2f}s "
            f"({len(pool)} LLMs)"
        )

        return results

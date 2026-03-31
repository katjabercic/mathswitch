import logging
import time
from datetime import datetime

from categorizer.llm_service import LLMService, LLMType
from categorizer.prompts import build_categorization_prompt
from categorizer.result_parsers import (
    parse_categorization_result,
    parse_categorization_result_with_reasoning,
)
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

    def categorize_items(self, limit=None, judge_pool="low", session_name=None):
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

        self.logger.info(f"Session name: '{session_name}'")

        already_processed_ids = set(
            CategorizerResult.objects.filter(session_name=session_name)
            .values_list("item_id", flat=True)
            .distinct()
        )

        skipped = len(already_processed_ids)

        queryset = Item.objects.all()
        if already_processed_ids:
            queryset = queryset.exclude(id__in=already_processed_ids)
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

        self.logger.info(
            f"Items: {skipped} already processed, "
            f"{to_process} to process (pool={judge_pool}, "
            f"{len(pool)} LLMs)"
        )

        total_start = time.perf_counter()
        for i, item in enumerate(items_to_process):
            self.logger.info(f"Processing item {i + 1}/{to_process}: {item.identifier}")
            self.categorize_item(
                item,
                pool=pool,
                session_name=session_name,
                judge_pool=judge_pool,
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

        Returns:
            List of categorization results from all LLMs
        """
        if pool is None:
            pool = LLM_JUDGE_POOL

        use_reasoning = judge_pool not in ("low", "local")

        self.logger.debug(f"Categorizing: {item.name}")

        prompt = build_categorization_prompt(
            item, predicate, with_reasoning=use_reasoning
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

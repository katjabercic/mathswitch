import logging

from categorizer.llm_service import LLMService, LLMType
from concepts.models import CategorizerResult, Item

# Free LLM types to use for categorization
LLM_JUDGE_POOL = [
    LLMType.HUGGINGFACE_FLAN_T5,
    LLMType.HUGGINGFACE_GPT2,
    LLMType.HUGGINGFACE_DIALOGPT,
]


class CategorizerService:
    """
    Service for categorizing mathematical concepts.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm_service = LLMService()

    def categorize_items(self, limit=None):
        """
        Categorize items from the database using all free LLM types.

        Args:
            limit: Optional limit on number of items to process
        """
        queryset = Item.objects.all()
        if limit:
            queryset = queryset[:limit]

        total = queryset.count()
        self.logger.info(
            f"Categorizing {total} items using {len(LLM_JUDGE_POOL)} free LLMs"
        )

        for i, item in enumerate(queryset):
            self.logger.info(f"Processing item {i + 1}/{total}: {item.identifier}")
            self.categorize_item(item)

        self.logger.info("Categorization complete")

    def categorize_item(
        self,
        item,
        predicate: str = "Is the given concept a mathematical concept,"
        " given the name, description, "
        "keywords, and article text?",
    ):
        """
        Categorize a single item using all free LLM types.

        Args:
            item: Item instance to categorize
            predicate: The question to evaluate (default: checks if it's
            a mathematical concept)

        Returns:
            List of categorization results from all LLMs
        """
        self.logger.debug(f"Categorizing: {item.name}")

        prompt = self._build_categorization_prompt(item, predicate)

        results = []

        for llm_type in LLM_JUDGE_POOL:
            try:
                self.logger.info(f"Calling {llm_type.value} for {item.name}")
                raw_result = self.llm_service.call_llm(llm_type, prompt)
                self.logger.info(
                    f"Categorized {item.name} with {llm_type.value}: "
                    f"{raw_result[:100]}..."
                )

                print(f"{raw_result}")
                parsed_result = self._parse_categorization_result(raw_result)

                confidence = parsed_result["confidence"]
                if confidence is None:
                    confidence = 50

                categorizer_result = CategorizerResult.objects.create(
                    item=item,
                    llm_type=llm_type.value,
                    raw_result=raw_result,
                    result_answer=parsed_result["answer"],
                    result_confidence=confidence,
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
                    f"Failed to categorize {item.name} with {llm_type.value}: {e}"
                )
                # Continue with other LLMs even if one fails?
                continue

        return results

    def _build_categorization_prompt(self, item, predicate: str):
        """
        Build a prompt for evaluating a concept against a predicate.

        Args:
            item: Item instance to categorize
            predicate: The question/predicate to evaluate

        Returns:
            Formatted prompt string
        """
        system_prompt = """You are a categorization judge. Your task is to
         evaluate whether a given concept satisfies a specific predicate.

You must respond with a structured answer containing:
1. answer: true or false (boolean)
2. confidence: a number from 0 to 100 (representing your confidence percentage)

IMPORTANT: Format your response as comma-separated string:
yes,85
"""

        item_info_parts = [f"Name: {item.name}"]

        if item.description:
            item_info_parts.append(f"Description: {item.description[:100]}")

        if item.keywords:
            item_info_parts.append(f"Keywords: {item.keywords[:200]}")

        if item.article_text:
            # Truncate article text to 1000 characters
            article_text = item.article_text[:1000]
            item_info_parts.append(f"Article text: {article_text}")

        item_info = "\n".join(item_info_parts)

        prompt = f"""{system_prompt}

---

CONCEPT INFORMATION:
{item_info}

---

PREDICATE TO EVALUATE:
{predicate}

---

Please provide your evaluation in the comma-separated format specified above."""

        return prompt

    def _parse_categorization_result(self, result: str) -> dict:
        """
        Parse the LLM's comma-separated response.

        Args:
            result: The raw response from the LLM (expected format: "yes,85"
            or "no,75", "yes ---")

        Returns:
            Dictionary with 'answer' (bool) and 'confidence' (int) keys

        Raises:
            ValueError: If the response cannot be parsed
        """
        try:
            # Clean the result string
            result = result.strip()

            # Split by comma (with or without space) or just space
            # Try separators in order of specificity: ", ", ",", " "
            if ", " in result:
                parts = result.split(", ", 1)
            elif "," in result:
                parts = result.split(",", 1)
            else:
                parts = result.split(" ", 1)

            if len(parts) == 1:
                # Only answer provided, no confidence
                answer_str = parts[0].strip().lower()
                confidence = None
            elif len(parts) == 2:
                # Both answer and confidence provided
                answer_str = parts[0].strip().lower()
                confidence_str = parts[1].strip()

                # Parse confidence if provided
                if confidence_str:
                    try:
                        confidence = int(confidence_str)
                        if not 0 <= confidence <= 100:
                            self.logger.warning(
                                f"Confidence {confidence} out of range [0-100], "
                                f"setting to None"
                            )
                            confidence = None
                    except ValueError:
                        self.logger.warning(
                            f"Invalid confidence value '{confidence_str}', "
                            f"setting to None"
                        )
                        confidence = None
                else:
                    confidence = None
            else:
                raise ValueError(
                    f"Expected format 'answer' or 'answer,confidence', got: {result}"
                )

            # Parse answer - accept yes/true/1 as True, no/false/0 as False
            if answer_str in ("yes", "true", "1"):
                answer = True
            elif answer_str in ("no", "false", "0"):
                answer = False
            else:
                raise ValueError(
                    f"Invalid answer value: {answer_str}. "
                    f"Expected yes/no, true/false, or 1/0"
                )

            return {"answer": answer, "confidence": confidence}

        except (ValueError, IndexError) as e:
            self.logger.error(f"Failed to parse response: {result}")
            raise ValueError(f"Invalid response format: {e}")

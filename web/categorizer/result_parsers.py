import logging

logger = logging.getLogger(__name__)


def parse_categorization_result(result):
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
                        logger.warning(
                            f"Confidence {confidence!r} out of range [0-100], "
                            f"setting to None"
                        )
                        confidence = None
                except ValueError:
                    logger.warning(
                        f"Invalid confidence value {confidence_str!r}, "
                        f"setting to None"
                    )
                    confidence = None
            else:
                confidence = None
        else:
            raise ValueError(
                f"Expected format 'answer' or 'answer,confidence', got: {result!r}"
            )

        # Parse answer - accept yes/true/1 as True, no/false/0 as False
        if answer_str in ("yes", "true", "1"):
            answer = True
        elif answer_str in ("no", "false", "0"):
            answer = False
        else:
            raise ValueError(
                f"Invalid answer value: {answer_str!r}. "
                f"Expected yes/no, true/false, or 1/0"
            )

        return {"answer": answer, "confidence": confidence}

    except (ValueError, IndexError) as e:
        logger.error(f"Failed to parse response: result={result!r}, " f"error={e!r}")
        raise ValueError(f"Invalid response format: {e}")


def parse_categorization_result_with_reasoning(result):
    """
    Parse the LLM's multi-line response with reasoning.

    Expected format:
        answer: yes
        confidence: 85
        reasoning: The concept is clearly mathematical because...

    Returns:
        Dictionary with 'answer' (bool), 'confidence' (int),
        and 'reasoning' (str) keys

    Raises:
        ValueError: If the response cannot be parsed
    """
    try:
        fields = {}
        for line in result.strip().splitlines():
            line = line.strip()
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            fields[key.strip().lower()] = value.strip()

        if "answer" not in fields:
            raise ValueError(f"Missing 'answer' field in response: {result!r}")

        answer_str = fields["answer"].lower()
        if answer_str in ("yes", "true", "1"):
            answer = True
        elif answer_str in ("no", "false", "0"):
            answer = False
        else:
            raise ValueError(
                f"Invalid answer value: {answer_str!r}. "
                f"Expected yes/no, true/false, or 1/0"
            )

        confidence = None
        if "confidence" in fields:
            try:
                confidence = int(fields["confidence"])
                if not 0 <= confidence <= 100:
                    logger.warning(
                        f"Confidence {confidence!r} out of range "
                        f"[0-100], setting to None"
                    )
                    confidence = None
            except ValueError:
                logger.warning(
                    f"Invalid confidence value "
                    f"{fields['confidence']!r}, setting to None"
                )

        reasoning = fields.get("reasoning")

        return {
            "answer": answer,
            "confidence": confidence,
            "reasoning": reasoning,
        }

    except (ValueError, IndexError) as e:
        logger.error(
            f"Failed to parse reasoning response: " f"result={result!r}, error={e!r}"
        )
        raise ValueError(f"Invalid response format: {e}")

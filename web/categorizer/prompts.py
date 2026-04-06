SYSTEM_PROMPT_SIMPLE = """You are a categorization judge. Your task is to
         evaluate whether a given concept satisfies a specific predicate.

You must respond with a structured answer containing:
1. answer: true or false (boolean)
2. confidence: a number from 0 to 100 (representing your confidence percentage)

IMPORTANT: Format your response as comma-separated string:
yes,85
"""

SYSTEM_PROMPT_WITH_REASONING = """You are a categorization judge. Your task is to
         evaluate whether a given concept satisfies a specific predicate.

Be careful with concepts from adjacent domains such as physics, computer science,
or engineering. A concept should only be classified as mathematical if it is
primarily mathematical in nature. Concepts that merely use mathematics as a tool
(e.g. quantum mechanics, signal processing) should not be considered mathematical
concepts. When in doubt, consider whether the concept originates from or is
primarily studied within mathematics.

You must respond with a structured answer containing:
1. answer: yes or no
2. confidence: a number from 0 to 100 (representing your confidence percentage)
3. reasoning: a brief explanation of why you chose that answer

IMPORTANT: Format your response as three lines, exactly like this:
answer: yes
confidence: 85
reasoning: The concept is clearly mathematical because...
"""


def build_categorization_prompt(
    item, predicate, with_reasoning=False, use_other_ids=True
):
    """
    Build a prompt for evaluating a concept against a predicate.

    Args:
        item: Item instance to categorize
        predicate: The question/predicate to evaluate
        with_reasoning: If True, ask for reasoning in the response
        use_other_ids: If True, include external IDs from item.meta
            (only applies to Wikidata items)

    Returns:
        Formatted prompt string
    """
    if with_reasoning:
        system_prompt = SYSTEM_PROMPT_WITH_REASONING
    else:
        system_prompt = SYSTEM_PROMPT_SIMPLE

    item_info_parts = [f"Name: {item.name}"]

    if item.description:
        item_info_parts.append(f"Description: {item.description[:100]}")

    if item.keywords:
        item_info_parts.append(f"Keywords: {item.keywords[:200]}")

    if item.article_text:
        # Truncate article text to 1000 characters
        article_text = item.article_text[:1000]
        item_info_parts.append(f"Article text: {article_text}")

    if use_other_ids:
        other_ids = _get_other_ids(item)
        if other_ids:
            item_info_parts.append(f"External IDs: {other_ids}")

    item_info = "\n".join(item_info_parts)

    prompt = f"""{system_prompt}

---

CONCEPT INFORMATION:
{item_info}

---

PREDICATE TO EVALUATE:
{predicate}

---

Please provide your evaluation in the format specified above."""

    return prompt


_OTHER_ID_KEYS = {
    "mathworld_id": "MathWorld ID",
    "nlab_id": "nLab ID",
    "proofwiki_id": "ProofWiki ID",
    "eom_id": "Encyclopedia of Mathematics ID",
}


def _get_other_ids(item):
    from concepts.models import Item

    if item.source != Item.Source.WIKIDATA:
        return None
    if not item.meta:
        return None
    try:
        import json

        meta = json.loads(item.meta)
    except (json.JSONDecodeError, TypeError):
        return None

    parts = []
    for meta_key, label in _OTHER_ID_KEYS.items():
        value = meta.get(meta_key)
        if value:
            parts.append(f"{label}: {value}")
    return ", ".join(parts) if parts else None

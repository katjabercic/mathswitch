# TODO SST: Move to readme.md
# Load the scientific English model from scispacy
# Note: You need to install the slurper dependencies and download this model first with:
#  make install-slurper

# Lazy-loaded spaCy model
_nlp = None


def _get_nlp():
    """Lazy-load the spaCy model only when needed."""
    global _nlp
    if _nlp is None:
        try:
            import spacy
        except ImportError:
            raise ImportError(
                "spacy package is required. "
                "Install the slurper dependencies with: make install-slurper"
            )
        _nlp = spacy.load("en_core_sci_lg")
    return _nlp


def extract_keywords(text):
    """
    Extract keywords from text using spaCy's named entity recognition.

    Args:
        text: The text to extract keywords from

    Returns:
        A list of recognized entities (keywords) from the text
    """
    if not text:
        return []

    nlp = _get_nlp()
    doc = nlp(text)
    return doc.ents

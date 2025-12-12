import spacy

# TODO SST: Move to readme.md
# TODO SST: Also it should be lazy-loaded
# Load the scientific English model from scispacy
# Note: You need to download this model first with:
# pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz
nlp = spacy.load("en_core_sci_lg")


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

    doc = nlp(text)
    return doc.ents

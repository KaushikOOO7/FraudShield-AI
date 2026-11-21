import re
import unicodedata

PREPROCESSING_VERSION = "sms-text-v1"


def normalize_text(content: str) -> str:
    text = unicodedata.normalize("NFKC", content).casefold()
    return re.sub(r"\s+", " ", text).strip()


def normalize_messages(messages) -> list[str]:
    return [normalize_text(str(content)) for content in messages]


def template_group(content: str) -> str:
    """Keep exact text templates with differing URL/number values in one split.

    This mitigates template leakage; it cannot prove campaign/time independence.
    It is used for split grouping only, never as a fraud classifier.
    """
    text = normalize_text(content)
    text = re.sub(r"(?:https?://|www\.)\S+", "<url>", text)
    return re.sub(r"\d+", "<number>", text)

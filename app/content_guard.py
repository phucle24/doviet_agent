import hashlib
import json
import re

from app.db import normalize_identity


REQUIRED_TOPIC_FIELDS = (
    "topic_key",
    "series_key",
    "series_label",
    "series_number",
    "format",
    "title",
    "prompt_line",
    "clue",
    "answer",
    "answer_note",
    "image_brief",
    "image_text",
)


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def answer_hash(topic: dict) -> str:
    return stable_hash(normalize_identity(topic.get("answer", "")))


def content_fingerprint(topic: dict) -> str:
    payload = {
        "series_key": topic.get("series_key", ""),
        "answer": normalize_identity(topic.get("answer", "")),
        "clue": normalize_identity(topic.get("clue", "")),
    }
    return stable_hash(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def visual_fingerprint(topic: dict) -> str:
    payload = {
        "series_key": topic.get("series_key", ""),
        "format_family": normalize_identity(topic.get("format_family", "")),
        "answer": normalize_identity(topic.get("answer", "")),
        "image_brief": normalize_identity(topic.get("image_brief", "")),
    }
    return stable_hash(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def caption_fingerprint(caption: str) -> str:
    return stable_hash(normalize_identity(caption))


def _meaningful_tokens(value: str) -> set[str]:
    normalized = normalize_identity(value)
    tokens = re.findall(r"[\wÀ-ỹ]+", normalized, flags=re.UNICODE)
    stopwords = {
        "câu",
        "đáp",
        "án",
        "đoán",
        "hình",
        "chữ",
        "tục",
        "ngữ",
        "thành",
        "ca",
        "dao",
        "là",
        "gì",
        "nào",
        "và",
        "của",
        "có",
        "một",
    }
    return {token for token in tokens if len(token) >= 2 and token not in stopwords}


def _text_reveals_answer(text: str, answer: str) -> bool:
    answer_tokens = _meaningful_tokens(answer)
    text_tokens = _meaningful_tokens(text)
    if not answer_tokens or not text_tokens:
        return False

    overlap = answer_tokens & text_tokens
    if any(len(token) >= 5 for token in overlap):
        return True
    return len(overlap) >= 2


def validate_topic(topic: dict) -> list[str]:
    errors = []
    for field in REQUIRED_TOPIC_FIELDS:
        if not str(topic.get(field, "")).strip():
            errors.append(f"Missing topic field: {field}")

    if topic.get("topic_type") != "vietnamese_riddle":
        errors.append("Unsupported topic_type for Đố Việt content.")

    format_text = normalize_identity(topic.get("format", ""))
    prompt_text = normalize_identity(topic.get("prompt_line", ""))
    title_text = normalize_identity(topic.get("title", ""))
    blocked_easy_patterns = ("điền", "dien", "che chữ", "che chu")
    if any(pattern in format_text or pattern in prompt_text or pattern in title_text for pattern in blocked_easy_patterns):
        errors.append("Topic uses an overly easy fill-in/hidden-word format.")

    answer = normalize_identity(topic.get("answer", ""))
    image_text = normalize_identity(topic.get("image_text", ""))
    if answer and image_text and answer in image_text:
        errors.append("Image text appears to reveal the full answer.")
    if _text_reveals_answer(image_text, answer):
        errors.append("Image text appears to reveal answer fragments.")
    if _text_reveals_answer(topic.get("title", ""), answer):
        errors.append("Title appears to reveal answer fragments.")
    if _text_reveals_answer(topic.get("prompt_line", ""), answer):
        errors.append("Prompt line appears to reveal answer fragments.")
    if str(topic.get("safe_hint_level", "none")).lower() not in {"none", "low", "medium"}:
        errors.append("Unsupported safe_hint_level.")
    try:
        viral_score = int(topic.get("viral_score", 0))
        if not 0 <= viral_score <= 100:
            errors.append("viral_score must be between 0 and 100.")
    except (TypeError, ValueError):
        errors.append("viral_score must be an integer.")

    if len(str(topic.get("title", "")).strip()) > 90:
        errors.append("Title is too long for dashboard and caption preview.")

    if len(str(topic.get("image_text", "")).strip()) > 90:
        errors.append("Image text is too long for a readable 4:5 poster.")

    if len(str(topic.get("answer", "")).strip()) < 2:
        errors.append("Answer is too short or ambiguous.")

    return errors


def assert_topic_quality(topic: dict):
    errors = validate_topic(topic)
    if errors:
        raise ValueError("Content quality gate failed: " + "; ".join(errors))


def quality_status(topic: dict) -> str:
    return "PASSED" if not validate_topic(topic) else "FAILED"

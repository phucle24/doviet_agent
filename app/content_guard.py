import hashlib
import json

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


def validate_topic(topic: dict) -> list[str]:
    errors = []
    for field in REQUIRED_TOPIC_FIELDS:
        if not str(topic.get(field, "")).strip():
            errors.append(f"Missing topic field: {field}")

    if topic.get("topic_type") != "vietnamese_riddle":
        errors.append("Unsupported topic_type for Đố Việt content.")

    answer = normalize_identity(topic.get("answer", ""))
    image_text = normalize_identity(topic.get("image_text", ""))
    if answer and image_text and answer in image_text:
        errors.append("Image text appears to reveal the full answer.")

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

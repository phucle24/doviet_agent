from app.config import GEMINI_API_KEY, GEMINI_TEXT_MODEL
from app.content_guard import answer_hash, content_fingerprint, validate_topic
from app.db import normalize_identity
from app.topic_bank import SERIES_META, annotate_topic
from app.utils import safe_json_loads, slugify


def _ensure_api_key():
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing DOVIET_AGENT_GEMINI_API_KEY")


def _client_and_types():
    from google import genai
    from google.genai import types

    return genai.Client(api_key=GEMINI_API_KEY), types


def _used_answers_text(used_answers: set[str], limit: int = 80) -> str:
    answers = sorted(answer for answer in used_answers if answer)
    if not answers:
        return "(chưa có)"
    return "\n".join(f"- {answer}" for answer in answers[-limit:])


def generate_unique_riddle_topic(
    series_key: str,
    series_number: int,
    used_topic_keys: set[str],
    used_answers: set[str],
    used_content_fingerprints: set[str] | None = None,
) -> dict:
    _ensure_api_key()
    client, types = _client_and_types()
    meta = SERIES_META[series_key]
    used_content_fingerprints = used_content_fingerprints or set()

    prompt = f"""
Bạn là biên tập viên cho fanpage "Đố Việt - Kho Đố Dân Gian".

Hãy tạo MỘT nội dung mới cho series: {meta["label"]}.
Không được trùng đáp án, ý tưởng chính, câu hỏi, hình ảnh gợi ý với danh sách đã dùng.

Đáp án đã dùng:
{_used_answers_text(used_answers)}

Output JSON hợp lệ với đúng các key:
- format
- title
- prompt_line
- clue
- answer
- answer_note
- image_brief
- image_text

Yêu cầu:
1. Nội dung phải phù hợp văn hóa Việt, dễ hiểu, kéo comment.
2. Không dùng đáp án mơ hồ hoặc gây tranh cãi.
3. Không để lộ đáp án trong image_text.
4. image_brief viết bằng tiếng Anh, mô tả cảnh/hình ảnh để Gemini tạo poster 4:5.
5. image_text viết tiếng Việt, rất ngắn, dùng như chữ trên ảnh.
6. answer_note giải thích ngắn 1 câu.
7. Với Đuổi Hình Bắt Chữ, image_text nên có dạng rebus bằng từ/icon/dấu cộng.

Chỉ trả về JSON, không giải thích thêm.
"""

    for attempt in range(3):
        response = client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        topic = safe_json_loads(response.text)
        answer = topic.get("answer", "").strip()
        if not answer:
            continue
        normalized_answer = normalize_identity(answer)
        topic_key = f"generated_{series_key}_{slugify(answer)[:60]}_{attempt + 1}"
        if topic_key in used_topic_keys or normalized_answer in used_answers:
            continue

        topic["topic_key"] = topic_key
        topic = annotate_topic(topic, series_key, series_number)
        if answer_hash(topic) in used_answers:
            continue
        if content_fingerprint(topic) in used_content_fingerprints:
            continue
        if validate_topic(topic):
            continue
        return topic

    raise RuntimeError(f"Could not generate a unique topic for {meta['label']}")

from app.content_guard import answer_hash, content_fingerprint, validate_topic
from app.db import normalize_identity
from app.deepseek_service import generate_json
from app.topic_bank import SERIES_META, annotate_topic
from app.utils import slugify


def _used_answers_text(used_answers: set[str], limit: int = 80) -> str:
    answers = sorted(
        answer
        for answer in used_answers
        if answer and not (len(answer) == 64 and all(char in "0123456789abcdef" for char in answer))
    )
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
    meta = SERIES_META[series_key]
    used_content_fingerprints = used_content_fingerprints or set()

    system_prompt = 'Bạn là biên tập viên cho fanpage "Đố Việt - Kho Đố Dân Gian". Chỉ trả về JSON hợp lệ.'
    user_prompt = f"""

Hãy tạo MỘT nội dung mới cho series: {meta["label"]}.
Không được trùng đáp án, ý tưởng chính, câu hỏi, hình ảnh gợi ý với danh sách đã dùng.
Nếu series là ĐỐ TỤC NGỮ, ưu tiên thành ngữ/tục ngữ dạng "nhìn hình đoán câu".
Không tạo dạng điền từ còn thiếu, điền câu tiếp theo, ca dao bị che chữ, hoặc câu hỏi chỉ cần nhìn chữ là ra đáp án.

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
- difficulty
- viral_score
- format_family
- spoiler_risk

Yêu cầu:
1. Nội dung phải phù hợp văn hóa Việt, dễ hiểu, kéo comment.
2. Không dùng đáp án mơ hồ hoặc gây tranh cãi.
3. Không để lộ đáp án hoặc một phần quá rõ của đáp án trong image_text.
4. image_brief viết bằng tiếng Anh, mô tả cảnh/hình ảnh để Gemini tạo ảnh 4:5 bằng manh mối thị giác, không phụ thuộc vào chữ.
5. image_text để chuỗi rỗng hoặc "Đố Việt"; KHÔNG viết "ĐOÁN TỤC NGỮ", "ĐOÁN CA DAO", "NHÌN HÌNH ĐOÁN CHỮ", chữ ghép đáp án, âm tiết đáp án, từ khóa đáp án hoặc gợi ý trực tiếp.
6. answer_note giải thích ngắn 1 câu.
7. Với Đuổi Hình Bắt Chữ, image_brief được mô tả manh mối bằng hình ảnh, nhưng image_text không dùng rebus text như "mặt trời + chân + lý".
8. Với ca dao/thành ngữ/tục ngữ dễ quen thuộc, clue phải là gợi ý rất chung, không trích nguyên văn câu trả lời.
9. difficulty là "medium" hoặc "hard"; tránh "easy".
10. viral_score là số nguyên 70-100, ưu tiên câu dễ kéo bình luận.
11. format_family là nhóm nội dung ngắn bằng snake_case, ví dụ "proverb_visual", "visual_rebus", "folk_trick_question".
12. spoiler_risk là "low" nếu không lộ đáp án.

Chỉ trả về JSON, không giải thích thêm.
"""

    for attempt in range(3):
        attempt_prompt = (
            f"{user_prompt}\n\n"
            f"Lần thử #{attempt + 1}: nếu ý tưởng trước đó bị trùng hoặc không đạt, hãy chọn đáp án và hình ảnh khác hẳn."
        )
        topic = generate_json(system_prompt, attempt_prompt, temperature=0.85)
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

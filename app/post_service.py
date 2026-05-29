import json
from datetime import datetime, timedelta

from app.config import FINAL_DIR
from app.content_guard import (
    answer_hash,
    assert_topic_quality,
    caption_fingerprint,
    content_fingerprint,
    quality_status,
    visual_fingerprint,
)
from app.db import insert_post
from app.utils import slugify


MODEL_RENDERED_TEXT_MARKER = "FINAL RIDDLE IMAGE MUST USE VISUAL CLUES ONLY."
CAPTION_HASHTAGS = "#dotucngu #DoViet #khodogiandan #dovui #duoihinhbatchu"
AI_DISCLAIMERS = (
    "Ảnh minh họa AI.",
    "Ảnh minh hoạ AI.",
    "Ảnh AI minh họa.",
    "Ảnh AI minh hoạ.",
    "AI illustration.",
)

RIDDLE_IMAGE_TEMPLATE = """
FINAL RIDDLE IMAGE MUST USE VISUAL CLUES ONLY.
Create a finished vertical 4:5 Vietnamese folk riddle image for Facebook feed:
- premium folk puzzle artwork, warm, polished, highly shareable
- one clear illustrated clue scene with expressive characters or objects, cinematic sunset/warm village lighting
- Vietnamese countryside details when suitable: bamboo, thatched houses, banana leaves, rice straw, clay jars, village yard
- rich folk colors with tasteful red/gold accents, clean ornamental border if useful
- the puzzle must be understandable from the illustration, not from written labels
- exactly one tiny corner brand badge is allowed, reading only: Đố Việt
- the corner badge must be small, tasteful, readable, and outside the main clue
- no other text anywhere in the image
- no title banner, no bottom question banner, no format tag, no center clue text
- no answer shown anywhere in the image
- no watermark, QR code, fake UI, random extra words, placeholder labels, or unrelated logos
""".strip()

SERIES_STYLE_NOTES = {
    "do_tuc_ngu": "storybook folk illustration, witty visual metaphor, familiar rural Vietnamese objects, warm red banner",
    "do_ca_dao": "poetic Vietnamese countryside, gentle nostalgic mood, soft gold light, elegant red or plum banner",
    "duoi_hinh_bat_chu": "fun visual rebus puzzle, clear separated clues, playful expressions, polished folk game artwork",
    "do_meo_dan_gian": "simple object-focused folk puzzle, humorous everyday scene, one obvious visual twist, bold question mark if useful",
}

CAPTION_TEMPLATES = {
    "do_tuc_ngu": [
        [
            "{code}",
            "",
            "Câu thành ngữ/tục ngữ này nhìn quen quen mà nghĩ kỹ lại dễ lú lắm nha 😄",
            "{clue_line}",
            "",
            "Bạn đoán ra chưa? Comment đáp án xuống dưới 👇",
            "",
            "⏰ Sau 2 giờ, Đố Việt sẽ mở đáp án ở phần bình luận.",
            "Theo dõi page để quay lại kiểm tra xem mình đúng không nhé!",
        ],
        [
            "{code}",
            "",
            "Một bức hình, một câu thành ngữ/tục ngữ. Nghe đơn giản nhưng đừng chủ quan nha 😆",
            "{clue_line}",
            "",
            "Ai nghĩ ra đáp án thì thả ngay dưới bình luận 👇",
            "",
            "⏰ Đáp án lên sau 2 giờ.",
            "Follow Đố Việt để khỏi lỡ khoảnh khắc “à há!” nha!",
        ],
    ],
    "do_ca_dao": [
        [
            "{code}",
            "",
            "Câu này ai từng học chắc thấy quen lắm nè 😄",
            "{clue_line}",
            "",
            "Bạn còn nhớ câu ca dao này không? Comment thử đáp án 👇",
            "",
            "⏰ Sau 2 giờ, Đố Việt sẽ thả đáp án ở bình luận.",
            "Theo dõi page để lát quay lại chấm điểm trí nhớ tuổi thơ nhé!",
        ],
        [
            "{code}",
            "",
            "Một hình ảnh gợi nhớ cả tuổi thơ, nhưng nhớ đúng câu không mới khó 😆",
            "{clue_line}",
            "",
            "Đoán được thì comment liền nha 👇",
            "",
            "⏰ Đáp án có sau 2 giờ ở phần bình luận.",
            "Follow Đố Việt để không bị trôi mất câu trả lời!",
        ],
    ],
    "duoi_hinh_bat_chu": [
        [
            "{code}",
            "",
            "Nhìn hình tưởng dễ, nhưng đừng để bị đánh lừa nha 😆",
            "{clue_line}",
            "",
            "Ai đoán được trong 5 giây thì comment liền 👇",
            "",
            "⏰ Sau 2 giờ, Đố Việt sẽ mở đáp án ở bình luận.",
            "Follow page để không bỏ lỡ màn “à há!” nha!",
        ],
        [
            "{code}",
            "",
            "Câu này nhìn phát tưởng ra ngay, nhưng càng nhìn càng nghi nghi đó 😄",
            "{clue_line}",
            "",
            "Bạn ghép được cụm từ nào? Comment thử xem 👇",
            "",
            "⏰ Đáp án sẽ xuất hiện sau 2 giờ.",
            "Theo dõi Đố Việt để quay lại xem mình có bị lừa không nha!",
        ],
    ],
    "do_meo_dan_gian": [
        [
            "{code}",
            "",
            "Câu này trẻ con đôi khi đoán nhanh hơn người lớn đó 😄",
            "{clue_line}",
            "",
            "Đừng nghĩ quá xa, cứ comment đáp án bạn nghĩ tới trước tiên 👇",
            "",
            "⏰ Sau 2 giờ, Đố Việt sẽ công bố đáp án ở bình luận.",
            "Theo dõi page để lát quay lại chấm điểm chính mình nha!",
        ],
        [
            "{code}",
            "",
            "Nghe đơn giản nhưng dễ làm người lớn suy nghĩ quá mức lắm nha 😆",
            "{clue_line}",
            "",
            "Bạn chọn đáp án nào? Comment thử xem 👇",
            "",
            "⏰ Đáp án sẽ có sau 2 giờ.",
            "Follow Đố Việt để không bỏ lỡ câu trả lời!",
        ],
    ],
}

ANSWER_OPENERS = [
    "🎯 Mở đáp án sau 2 giờ đây!",
    "🥁 Tới giờ bật mí rồi nè!",
    "📣 Đáp án chính thức lên sóng!",
    "✨ Ai chờ đáp án thì vào nhận kết quả nha!",
]


def template_index(topic: dict, total: int) -> int:
    return sum(ord(char) for char in topic["topic_key"]) % total


def should_show_clue(topic: dict) -> bool:
    return False


def clue_line(topic: dict) -> str:
    return "Nhìn hình rồi đoán thẳng nha 😄"


def append_caption_hashtags(caption: str) -> str:
    caption = caption.strip()
    if CAPTION_HASHTAGS in caption:
        return caption
    return f"{caption}\n\n{CAPTION_HASHTAGS}"


def remove_ai_disclaimer(caption: str) -> str:
    cleaned = caption.strip()
    for disclaimer in AI_DISCLAIMERS:
        cleaned = cleaned.replace(disclaimer, "").strip()
    return "\n".join(line.rstrip() for line in cleaned.splitlines()).strip()


def series_code(topic: dict) -> str:
    return f"[{topic['series_label']} #{topic['series_number']:03d}]"


def build_riddle_caption(topic: dict) -> str:
    templates = CAPTION_TEMPLATES.get(topic["series_key"], CAPTION_TEMPLATES["do_meo_dan_gian"])
    lines = templates[template_index(topic, len(templates))]
    caption = "\n".join(lines).format(
        code=series_code(topic),
        clue_line=clue_line(topic),
    )
    return append_caption_hashtags(remove_ai_disclaimer(caption))


def build_answer_comment(topic: dict) -> str:
    opener = ANSWER_OPENERS[template_index(topic, len(ANSWER_OPENERS))]
    prefix = topic.get("default_answer_prefix", "Đáp án")
    lines = [
        opener,
        "",
        f"{prefix}: {topic['answer']}",
    ]
    if topic.get("answer_note"):
        lines.extend(["", "Giải thích ngắn:", topic["answer_note"]])
    lines.extend(
        [
            "",
            "Bạn đoán trúng chưa? Nếu trúng thì nhận ngay 1 điểm danh dự nha 😄",
            "Theo dõi Đố Việt để chơi tiếp câu mới!",
        ]
    )
    return "\n".join(lines)


def answer_comment_at(scheduled_at: str) -> str:
    scheduled_dt = datetime.strptime(scheduled_at, "%Y-%m-%d %H:%M:%S")
    return (scheduled_dt + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")


def build_model_rendered_riddle_prompt(topic: dict) -> str:
    visual_brief = topic.get("image_brief", "")
    style_note = SERIES_STYLE_NOTES.get(topic.get("series_key"), "premium Vietnamese folk puzzle poster")

    return (
        f"{RIDDLE_IMAGE_TEMPLATE}\n\n"
        "Allowed text policy:\n"
        "- Render only one small corner badge with the exact text: Đố Việt\n"
        "- Do not render any category label, series label, game title, question title, or clue text.\n"
        "- Do not render technical placeholder labels or instruction names.\n"
        "- Do not render top banners, bottom banners, speech bubbles, captions, signs, labels, subtitles, or any decorative text.\n\n"
        "Strict answer rule:\n"
        "- The answer is stored separately for a Facebook comment; DO NOT reveal it in the image.\n"
        "- Do not render any answer words, clue words, split-answer words, rebus labels, or syllables from the answer as text.\n"
        "- Text on the poster must stay generic; the puzzle clue must come from the illustration only.\n"
        "- The image should only give visual clues and invite comments.\n\n"
        "Reference-inspired layout:\n"
        "- Full image area is the illustrated clue scene; no title/header/footer text areas.\n"
        "- Keep a clean focal point, not busy clutter.\n"
        "- Place the small 'Đố Việt' badge in one corner only, preferably bottom-right, readable but secondary.\n"
        "- Use consistent margins; never crop text or characters.\n\n"
        "Enhanced art direction:\n"
        f"{style_note}\n\n"
        "Visual clue direction:\n"
        f"{visual_brief}\n\n"
        "Composition rules:\n"
        "- Render the brand only as 'Đố Việt', once, in a corner.\n"
        "- Make the clue understandable at phone size.\n"
        "- For rebus puzzles, use separate clean visual panels if helpful, but do not use written words or text labels.\n"
        "- For proverb or folk-poetry puzzles, use a poetic Vietnamese countryside or folk scene.\n"
        "- For trick-question puzzles, use a simple object-focused visual clue.\n"
        "- Keep faces, objects, and props charming and expressive, not creepy.\n"
        "- Do not add QR codes, social icons, fake UI, English filler text, Vietnamese filler text, or extra captions."
    )


def image_prompt_renders_final_text(image_prompt: str) -> bool:
    return MODEL_RENDERED_TEXT_MARKER in image_prompt


def build_post_payload(topic: dict, scheduled_at: str, slot: str) -> dict:
    if topic["topic_type"] != "vietnamese_riddle":
        raise ValueError(f"Unsupported topic_type: {topic['topic_type']}")
    assert_topic_quality(topic)

    base_name = slugify(f"{scheduled_at}_{slot}_{topic['topic_key']}")
    final_path = str(FINAL_DIR / f"{base_name}.jpg")
    caption = build_riddle_caption(topic)
    answer_comment = build_answer_comment(topic)

    return {
        "scheduled_at": scheduled_at,
        "slot": slot,
        "topic_type": topic["topic_type"],
        "topic_key": topic["topic_key"],
        "title": topic["title"],
        "overlay_title": series_code(topic),
        "overlay_subtitle": topic.get("format"),
        "overlay_stat": None,
        "overlay_hook": None,
        "caption": caption,
        "image_prompt": build_model_rendered_riddle_prompt(topic),
        "topic_payload": json.dumps(topic, ensure_ascii=False),
        "raw_image_path": final_path,
        "final_image_path": final_path,
        "status": "READY",
        "answer_comment": answer_comment,
        "answer_comment_at": answer_comment_at(scheduled_at),
        "answer_comment_status": "PENDING",
        "content_fingerprint": content_fingerprint(topic),
        "answer_hash": answer_hash(topic),
        "quality_status": quality_status(topic),
        "quality_errors": None,
        "prompt_version": "doviet-riddle-v3-visual-only",
        "difficulty": topic.get("difficulty"),
        "viral_score": topic.get("viral_score"),
        "format_family": topic.get("format_family"),
        "spoiler_risk": topic.get("spoiler_risk"),
        "visual_fingerprint": visual_fingerprint(topic),
        "caption_fingerprint": caption_fingerprint(caption),
        "batch_retry_count": 0,
    }


def overlay_post_image(post_data: dict) -> str:
    raise ValueError(
        "Vietnamese riddle posts use final text rendered directly by the image model; "
        "Python overlay is not supported for this topic type."
    )


def build_post(topic: dict, scheduled_at: str, slot: str, image_fallback_on_error: bool | None = None) -> int:
    from app.image_service import generate_image

    post_data = build_post_payload(topic, scheduled_at, slot)
    generate_image(
        post_data["image_prompt"],
        post_data["final_image_path"],
        fallback_on_error=image_fallback_on_error,
    )
    return insert_post(post_data)


def build_post_for_batch(topic: dict, scheduled_at: str, slot: str) -> int:
    post_data = build_post_payload(topic, scheduled_at, slot)
    post_data["status"] = "WAITING_IMAGE"
    post_data["batch_request_key"] = f"{post_data['scheduled_at']}_{post_data['slot']}_{post_data['topic_key']}"
    return insert_post(post_data)

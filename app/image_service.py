from pathlib import Path
import base64
import json

from PIL import Image, ImageDraw

from app.config import (
    LOG_DIR,
    GEMINI_API_KEY,
    GEMINI_IMAGE_MODEL,
    IMAGE_ASPECT_RATIO,
    IMAGE_FALLBACK_ON_ERROR,
)


def _ensure_api_key():
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing DOVIET_AGENT_GEMINI_API_KEY")


def _client():
    from google import genai

    return genai.Client(api_key=GEMINI_API_KEY)


def _types():
    from google.genai import types

    return types


def _describe_response(response) -> str:
    pieces = []

    prompt_feedback = getattr(response, "prompt_feedback", None)
    if prompt_feedback:
        pieces.append(f"prompt_feedback={prompt_feedback!r}")

    text = getattr(response, "text", None)
    if text:
        pieces.append(f"text={text[:500]!r}")

    candidates = getattr(response, "candidates", None) or []
    for index, candidate in enumerate(candidates):
        finish_reason = getattr(candidate, "finish_reason", None)
        safety_ratings = getattr(candidate, "safety_ratings", None)
        pieces.append(
            f"candidate[{index}].finish_reason={finish_reason!r}, "
            f"safety_ratings={safety_ratings!r}"
        )

    return "; ".join(pieces) or "empty response details"


def _iter_parts(value) -> list:
    if not value:
        return []
    try:
        return list(value)
    except TypeError:
        return []


def _part_debug(part) -> dict:
    inline_data = getattr(part, "inline_data", None)
    text = getattr(part, "text", None)
    file_data = getattr(part, "file_data", None)
    data = getattr(inline_data, "data", None) if inline_data else None
    return {
        "type": type(part).__name__,
        "has_text": bool(text),
        "text_preview": text[:300] if text else None,
        "has_inline_data": inline_data is not None,
        "inline_mime_type": getattr(inline_data, "mime_type", None) if inline_data else None,
        "inline_data_type": type(data).__name__ if data is not None else None,
        "inline_data_len": len(data) if data is not None and hasattr(data, "__len__") else None,
        "has_file_data": file_data is not None,
        "file_uri": getattr(file_data, "file_uri", None) if file_data else None,
    }


def write_response_debug(response):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    debug = {
        "type": type(response).__name__,
        "text_preview": (getattr(response, "text", None) or "")[:1000],
        "prompt_feedback": repr(getattr(response, "prompt_feedback", None)),
        "usage_metadata": repr(getattr(response, "usage_metadata", None)),
        "top_level_parts": [],
        "candidates": [],
    }

    for part in _iter_parts(getattr(response, "parts", None)):
        debug["top_level_parts"].append(_part_debug(part))

    for candidate_index, candidate in enumerate(_iter_parts(getattr(response, "candidates", None))):
        content = getattr(candidate, "content", None)
        candidate_debug = {
            "index": candidate_index,
            "finish_reason": repr(getattr(candidate, "finish_reason", None)),
            "safety_ratings": repr(getattr(candidate, "safety_ratings", None)),
            "parts": [],
        }
        for part in _iter_parts(getattr(content, "parts", None)):
            candidate_debug["parts"].append(_part_debug(part))
        debug["candidates"].append(candidate_debug)

    path = LOG_DIR / "last_gemini_image_response.json"
    path.write_text(json.dumps(debug, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _inline_data_to_bytes(inline_data) -> bytes | None:
    data = getattr(inline_data, "data", None)
    if data is None:
        return None
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        try:
            return base64.b64decode(data)
        except Exception:
            return data.encode("utf-8")
    return None


def create_placeholder_image(output_path: str) -> str:
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    width, height = 1080, 1350
    img = Image.new("RGB", (width, height), (28, 42, 56))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        ratio = y / height
        r = int(24 + ratio * 34)
        g = int(54 + ratio * 74)
        b = int(68 + ratio * 42)
        draw.line((0, y, width, y), fill=(r, g, b))

    for x, y, radius, color in [
        (160, 180, 180, (255, 196, 30)),
        (880, 360, 250, (15, 118, 110)),
        (280, 1040, 320, (36, 64, 98)),
    ]:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)

    img.save(output_path)
    return output_path


def save_image_from_response(response, output_path: str) -> str:
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    for part in _iter_parts(getattr(response, "parts", None)):
        saved = save_part_image(part, output_path)
        if saved:
            return saved

    for candidate in _iter_parts(getattr(response, "candidates", None)):
        content = getattr(candidate, "content", None)
        if not content:
            continue
        for part in _iter_parts(getattr(content, "parts", None)):
            saved = save_part_image(part, output_path)
            if saved:
                return saved

    debug_path = write_response_debug(response)
    raise RuntimeError(f"Model did not return an image part: {_describe_response(response)}. Debug: {debug_path}")


def save_part_image(part, output_path: str) -> str | None:
    inline_data = getattr(part, "inline_data", None)
    if inline_data is None:
        return None

    as_image = getattr(part, "as_image", None)
    if callable(as_image):
        try:
            image = as_image()
            save_pil_image(image, output_path)
            return output_path
        except Exception:
            pass

    data = _inline_data_to_bytes(inline_data)
    mime_type = getattr(inline_data, "mime_type", "") or ""
    if data and mime_type.startswith("image/"):
        Path(output_path).write_bytes(data)
        return output_path

    return None


def save_pil_image(image, output_path: str):
    suffix = Path(output_path).suffix.lower()
    if isinstance(image, Image.Image) and suffix in {".jpg", ".jpeg"} and image.mode != "RGB":
        image = image.convert("RGB")
        image.save(output_path, quality=95)
        return

    if isinstance(image, Image.Image):
        image.save(output_path)
        return

    save = getattr(image, "save", None)
    if callable(save):
        save(output_path)
        return

    raise TypeError(f"Unsupported image object returned by SDK: {type(image)!r}")


def _generate_content(client, types, image_prompt: str):
    return client.models.generate_content(
        model=GEMINI_IMAGE_MODEL,
        contents=[image_prompt],
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=IMAGE_ASPECT_RATIO),
        ),
    )


def generate_image(
    image_prompt: str,
    output_path: str,
    retries: int = 1,
    fallback_on_error: bool | None = None,
) -> str:
    _ensure_api_key()
    client = _client()
    types = _types()
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    last_error = "unknown error"

    try:
        response = _generate_content(client, types, image_prompt)
        return save_image_from_response(response, output_path)
    except Exception as exc:
        last_error = repr(exc)

    should_fallback = IMAGE_FALLBACK_ON_ERROR if fallback_on_error is None else fallback_on_error
    if should_fallback:
        return create_placeholder_image(output_path)

    raise RuntimeError(
        f"Generate image failed with model {GEMINI_IMAGE_MODEL!r}: {last_error}. "
        "For low-cost Gemini image generation, try DOVIET_AGENT_GEMINI_IMAGE_MODEL=gemini-2.5-flash-image."
    )

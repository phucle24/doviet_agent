import requests

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_TEXT_MODEL
from app.utils import safe_json_loads


def _ensure_api_key():
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("Missing DOVIET_AGENT_DEEPSEEK_API_KEY")


def generate_json(system_prompt: str, user_prompt: str, temperature: float = 0.8) -> dict:
    _ensure_api_key()
    url = f"{DEEPSEEK_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_TEXT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    response = requests.post(url, headers=headers, json=payload, timeout=120)
    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError(f"DeepSeek returned non-JSON response: {response.text[:500]}") from exc

    if response.status_code >= 400 or "error" in result:
        raise RuntimeError(f"DeepSeek API error: {result}")

    choices = result.get("choices") or []
    if not choices:
        raise RuntimeError(f"DeepSeek returned no choices: {result}")

    message = choices[0].get("message") or {}
    content = message.get("content") or ""
    if not content.strip():
        raise RuntimeError(f"DeepSeek returned empty content: {result}")

    return safe_json_loads(content)

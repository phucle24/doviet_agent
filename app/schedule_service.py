from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import (
    DB_PATH,
    DIRECT_IMAGE_BOOTSTRAP_DAYS,
    DIRECT_IMAGE_BOOTSTRAP_UNTIL,
    MIN_FUTURE_POSTS,
    TARGET_FUTURE_POSTS,
    TIMEZONE,
)
from app.content_guard import answer_hash, content_fingerprint, visual_fingerprint
from app.db import (
    count_future_posts,
    count_posts,
    count_posts_for_batch_submission,
    exists_schedule,
    list_existing_topic_identities,
    list_posts_for_direct_image_generation,
    mark_image_failed,
    mark_image_ready,
    normalize_identity,
    recent_format_families,
)
from app.topic_bank import get_static_topic, series_for_global_index, static_topic_count_for_series


BOOTSTRAP_STATE_PATH = DB_PATH.parent / "direct_image_bootstrap_until.txt"
POSTING_SLOTS = (
    ("morning", 11, 45),
    ("evening", 20, 15),
)


def remember_topic(topic: dict, used_identities: dict[str, set[str]]):
    used_identities["topic_keys"].add(topic["topic_key"])
    if topic.get("answer"):
        used_identities["answers"].add(normalize_identity(topic["answer"]))
        used_identities["answers"].add(answer_hash(topic))
    used_identities["content_fingerprints"].add(content_fingerprint(topic))
    used_identities["content_fingerprints"].add(visual_fingerprint(topic))
    used_identities.setdefault("format_families", []).append(topic.get("format_family", ""))


def topic_score(topic: dict, recent_formats: list[str]) -> int:
    score = int(topic.get("viral_score") or 0)
    if topic.get("format_family") in recent_formats:
        score -= 35
    if topic.get("difficulty") == "hard":
        score += 4
    return score


def choose_unique_topic(global_index: int, used_identities: dict[str, set[str]]) -> dict:
    from app.text_service import generate_unique_riddle_topic

    series_key, series_number = series_for_global_index(global_index)
    static_count = static_topic_count_for_series(series_key)
    start_index = (series_number - 1) % static_count
    recent_formats = list(used_identities.get("format_families", [])[-3:])

    candidates = []
    for offset in range(static_count):
        topic_index = (start_index + offset) % static_count
        topic = get_static_topic(series_key, topic_index, series_number)
        if topic["topic_key"] in used_identities["topic_keys"]:
            continue
        if normalize_identity(topic["answer"]) in used_identities["answers"]:
            continue
        if answer_hash(topic) in used_identities["answers"]:
            continue
        if content_fingerprint(topic) in used_identities["content_fingerprints"]:
            continue
        candidates.append(topic)

    if candidates:
        return max(candidates, key=lambda topic: topic_score(topic, recent_formats))

    return generate_unique_riddle_topic(
        series_key=series_key,
        series_number=series_number,
        used_topic_keys=used_identities["topic_keys"],
        used_answers=used_identities["answers"],
        used_content_fingerprints=used_identities["content_fingerprints"],
    )


def generate_schedule(days: int = 7):
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    start_date = now.date()

    slots = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        for slot_name, hour, minute in POSTING_SLOTS:
            slots.append((slot_name, datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz)))
    return slots


def generate_future_schedule(target_slots: int, lookahead_days: int = 60):
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    slots = []

    for i in range(lookahead_days):
        day = now.date() + timedelta(days=i)
        for slot_name, hour, minute in POSTING_SLOTS:
            dt = datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz)
            if dt > now:
                slots.append((slot_name, dt))
            if len(slots) >= target_slots:
                return slots

    return slots


def prepare_weekly_posts(days: int = 7) -> list[dict]:
    from app.post_service import build_post

    slots = generate_schedule(days=days)
    base_index = count_posts()
    used_identities = list_existing_topic_identities()
    used_identities["format_families"] = recent_format_families()
    created = []
    offset = 0

    for slot_name, dt in slots:
        scheduled_at = dt.strftime("%Y-%m-%d %H:%M:%S")

        if exists_schedule(scheduled_at, slot_name):
            continue

        topic = choose_unique_topic(base_index + offset, used_identities)
        post_id = build_post(topic, scheduled_at, slot_name)
        remember_topic(topic, used_identities)
        created.append(
            {
                "id": post_id,
                "scheduled_at": scheduled_at,
                "slot": slot_name,
                "topic_key": topic["topic_key"],
            }
        )
        offset += 1

    return created


def prepare_weekly_posts_for_batch(days: int = 7) -> list[dict]:
    from app.post_service import build_post_for_batch

    slots = generate_schedule(days=days)
    base_index = count_posts()
    used_identities = list_existing_topic_identities()
    used_identities["format_families"] = recent_format_families()
    created = []
    offset = 0

    for slot_name, dt in slots:
        scheduled_at = dt.strftime("%Y-%m-%d %H:%M:%S")

        if exists_schedule(scheduled_at, slot_name):
            continue

        topic = choose_unique_topic(base_index + offset, used_identities)
        post_id = build_post_for_batch(topic, scheduled_at, slot_name)
        remember_topic(topic, used_identities)
        created.append(
            {
                "id": post_id,
                "scheduled_at": scheduled_at,
                "slot": slot_name,
                "topic_key": topic["topic_key"],
            }
        )
        offset += 1

    return created


def prepare_future_posts_for_batch(posts_to_create: int, start_after_iso: str | None = None) -> list[dict]:
    from app.post_service import build_post_for_batch

    if posts_to_create <= 0:
        return []

    base_index = count_posts()
    used_identities = list_existing_topic_identities()
    used_identities["format_families"] = recent_format_families()
    created = []
    offset = 0

    # Scan more slots than needed because some future slots may already exist.
    slots = generate_future_schedule(target_slots=posts_to_create + 60)
    for slot_name, dt in slots:
        scheduled_at = dt.strftime("%Y-%m-%d %H:%M:%S")
        if start_after_iso and scheduled_at <= start_after_iso:
            continue
        if exists_schedule(scheduled_at, slot_name):
            continue

        topic = choose_unique_topic(base_index + offset, used_identities)
        post_id = build_post_for_batch(topic, scheduled_at, slot_name)
        remember_topic(topic, used_identities)
        created.append(
            {
                "id": post_id,
                "scheduled_at": scheduled_at,
                "slot": slot_name,
                "topic_key": topic["topic_key"],
                "mode": "batch_new",
            }
        )
        offset += 1

        if len(created) >= posts_to_create:
            break

    return created


def parse_local_datetime(value: str, tz: ZoneInfo) -> datetime:
    value = value.strip()
    if not value:
        raise ValueError("empty datetime")

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=tz)
    return parsed.astimezone(tz)


def direct_image_bootstrap_until(now: datetime) -> datetime | None:
    if DIRECT_IMAGE_BOOTSTRAP_UNTIL:
        return parse_local_datetime(DIRECT_IMAGE_BOOTSTRAP_UNTIL, ZoneInfo(TIMEZONE))

    if BOOTSTRAP_STATE_PATH.exists():
        value = BOOTSTRAP_STATE_PATH.read_text(encoding="utf-8").strip()
        if value:
            return parse_local_datetime(value, ZoneInfo(TIMEZONE))

    if DIRECT_IMAGE_BOOTSTRAP_DAYS <= 0:
        return None

    until = now + timedelta(days=DIRECT_IMAGE_BOOTSTRAP_DAYS)
    BOOTSTRAP_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BOOTSTRAP_STATE_PATH.write_text(until.isoformat(), encoding="utf-8")
    return until


def generate_direct_images_for_near_term_posts(start_after_iso: str, cutoff_iso: str) -> list[dict]:
    from app.image_service import generate_image

    converted = []
    for post in list_posts_for_direct_image_generation(start_after_iso, cutoff_iso):
        try:
            generate_image(post["image_prompt"], post["final_image_path"])
            mark_image_ready(post["id"], post["final_image_path"], post["final_image_path"])
            converted.append(
                {
                    "id": post["id"],
                    "scheduled_at": post["scheduled_at"],
                    "slot": post["slot"],
                    "topic_key": post["topic_key"],
                    "mode": "direct_existing",
                }
            )
        except Exception as exc:
            mark_image_failed(post["id"], str(exc))

    return converted


def prepare_future_posts_direct(posts_to_create: int, cutoff_iso: str) -> list[dict]:
    from app.post_service import build_post

    if posts_to_create <= 0:
        return []

    base_index = count_posts()
    used_identities = list_existing_topic_identities()
    used_identities["format_families"] = recent_format_families()
    created = []
    offset = 0

    slots = generate_future_schedule(target_slots=posts_to_create + 60)
    for slot_name, dt in slots:
        scheduled_at = dt.strftime("%Y-%m-%d %H:%M:%S")
        if scheduled_at > cutoff_iso:
            continue
        if exists_schedule(scheduled_at, slot_name):
            continue

        topic = choose_unique_topic(base_index + offset, used_identities)
        post_id = build_post(topic, scheduled_at, slot_name)
        remember_topic(topic, used_identities)
        created.append(
            {
                "id": post_id,
                "scheduled_at": scheduled_at,
                "slot": slot_name,
                "topic_key": topic["topic_key"],
                "mode": "direct_new",
            }
        )
        offset += 1

        if len(created) >= posts_to_create:
            break

    return created


def ensure_future_posts_for_batch(
    min_future_posts: int = MIN_FUTURE_POSTS,
    target_future_posts: int = TARGET_FUTURE_POSTS,
) -> dict:
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    now_iso = now.strftime("%Y-%m-%d %H:%M:%S")
    direct_until = direct_image_bootstrap_until(now)
    direct_enabled = direct_until is not None and now <= direct_until
    direct_cutoff_iso = direct_until.strftime("%Y-%m-%d %H:%M:%S") if direct_until else None

    direct_existing = (
        generate_direct_images_for_near_term_posts(now_iso, direct_cutoff_iso)
        if direct_enabled and direct_cutoff_iso
        else []
    )
    current_ready = count_future_posts(now_iso, statuses=("READY",))
    current_future = count_future_posts(now_iso, statuses=("READY", "WAITING_IMAGE"))
    pending_batch_submission = count_posts_for_batch_submission()

    if current_ready > min_future_posts:
        if pending_batch_submission:
            from app.batch_service import submit_pending_image_batch

            batch = submit_pending_image_batch(limit=min(pending_batch_submission, target_future_posts))
        else:
            batch = {"submitted": 0, "batch_job_name": None, "batch_state": None}
        return {
            "current_future": current_future,
            "current_ready": current_ready,
            "pending_batch_submission": pending_batch_submission,
            "created": [],
            "direct_existing": direct_existing,
            "direct_cutoff": direct_cutoff_iso,
            "direct_enabled": direct_enabled,
            "batch": batch,
        }

    posts_to_create = max(target_future_posts - current_future, 0)

    if direct_enabled and direct_cutoff_iso and posts_to_create:
        created = prepare_future_posts_direct(
            posts_to_create=posts_to_create,
            cutoff_iso=direct_cutoff_iso,
        )
        remaining_for_batch = max(posts_to_create - len(created), 0)
        batch_created = prepare_future_posts_for_batch(
            posts_to_create=remaining_for_batch,
            start_after_iso=direct_cutoff_iso,
        )
        created.extend(batch_created)
    elif posts_to_create:
        created = prepare_future_posts_for_batch(posts_to_create=posts_to_create)
    else:
        created = []

    batch_created_count = sum(1 for post in created if post.get("mode") == "batch_new")
    pending_batch_submission = count_posts_for_batch_submission()
    batch_limit = min(max(batch_created_count, pending_batch_submission), target_future_posts)
    if batch_limit:
        from app.batch_service import submit_pending_image_batch

        batch = submit_pending_image_batch(limit=batch_limit)
    else:
        batch = {"submitted": 0, "batch_job_name": None, "batch_state": None}

    return {
        "current_future": current_future,
        "current_ready": current_ready,
        "pending_batch_submission": pending_batch_submission,
        "created": created,
        "direct_existing": direct_existing,
        "direct_cutoff": direct_cutoff_iso,
        "direct_enabled": direct_enabled,
        "batch": batch,
    }


def prepare_one_test_post(topic_index: int = 0) -> dict:
    from app.post_service import build_post

    tz = ZoneInfo(TIMEZONE)
    scheduled_at = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    used_identities = list_existing_topic_identities()
    used_identities["format_families"] = recent_format_families()
    topic = choose_unique_topic(topic_index, used_identities)
    post_id = build_post(topic, scheduled_at, "test", image_fallback_on_error=False)
    return {
        "id": post_id,
        "scheduled_at": scheduled_at,
        "slot": "test",
        "topic_key": topic["topic_key"],
    }

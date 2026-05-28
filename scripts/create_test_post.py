from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import list_existing_topic_identities
from app.db import insert_post
from app.image_service import create_placeholder_image
from app.post_service import build_post, build_post_payload
from app.schedule_service import choose_unique_topic, prepare_one_test_post
from app.topic_bank import get_topic_by_index
from app.config import TIMEZONE

from datetime import datetime
from zoneinfo import ZoneInfo


if __name__ == "__main__":
    args = [
        arg
        for arg in sys.argv[1:]
        if arg not in {"--allow-placeholder", "--force-duplicate"}
    ]
    topic_index = int(args[0]) if args else 0
    allow_placeholder = "--allow-placeholder" in sys.argv[1:]
    force_duplicate = "--force-duplicate" in sys.argv[1:]

    if allow_placeholder:
        tz = ZoneInfo(TIMEZONE)
        scheduled_at = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        topic = (
            get_topic_by_index(topic_index)
            if force_duplicate
            else choose_unique_topic(topic_index, list_existing_topic_identities())
        )
        post_data = build_post_payload(topic, scheduled_at, "test")
        create_placeholder_image(post_data["final_image_path"])
        post_id = insert_post(post_data)
        post = {
            "id": post_id,
            "scheduled_at": scheduled_at,
            "slot": "test",
            "topic_key": topic["topic_key"],
        }
    else:
        if force_duplicate:
            tz = ZoneInfo(TIMEZONE)
            scheduled_at = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
            topic = get_topic_by_index(topic_index)
            post_id = build_post(topic, scheduled_at, "test", image_fallback_on_error=False)
            post = {
                "id": post_id,
                "scheduled_at": scheduled_at,
                "slot": "test",
                "topic_key": topic["topic_key"],
            }
        else:
            post = prepare_one_test_post(topic_index=topic_index)
    print(
        "Created test post "
        f"ID={post['id']} | {post['scheduled_at']} | {post['slot']} | {post['topic_key']}"
    )

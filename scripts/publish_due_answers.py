import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import TIMEZONE
from app.db import get_due_answer_comments, mark_answer_comment_failed, mark_answer_commented
from app.facebook_service import publish_comment


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv[1:]
    tz = ZoneInfo(TIMEZONE)
    now_iso = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    posts = get_due_answer_comments(now_iso)

    if not posts:
        print("No due answer comments.")
        sys.exit(0)

    print(f"Found {len(posts)} due answer comments at {now_iso}.")

    for post in posts:
        if dry_run:
            print(
                "Would comment answer "
                f"local_id={post['id']} | fb_post_id={post['fb_post_id']} | "
                f"answer_comment_at={post['answer_comment_at']}"
            )
            continue

        try:
            result = publish_comment(post["fb_post_id"], post["answer_comment"])
            fb_comment_id = result.get("id", "")
            mark_answer_commented(post["id"], fb_comment_id)
            print(f"Commented local_id={post['id']} => fb_comment_id={fb_comment_id}")
        except Exception as exc:
            mark_answer_comment_failed(post["id"], str(exc))
            print(f"Failed answer comment local_id={post['id']} => {exc}")

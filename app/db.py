import json
import hashlib
import sqlite3
from collections import Counter
from pathlib import Path

from app.config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheduled_at TEXT NOT NULL,
            slot TEXT NOT NULL,
            topic_type TEXT NOT NULL,
            topic_key TEXT NOT NULL,
            title TEXT NOT NULL,
            overlay_title TEXT,
            overlay_subtitle TEXT,
            overlay_stat TEXT,
            overlay_hook TEXT,
            caption TEXT NOT NULL,
            image_prompt TEXT NOT NULL,
            topic_payload TEXT,
            raw_image_path TEXT,
            final_image_path TEXT,
            status TEXT NOT NULL DEFAULT 'READY',
            fb_post_id TEXT,
            error_message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    _ensure_columns(
        cur,
        "posts",
        {
            "batch_job_name": "TEXT",
            "batch_request_key": "TEXT",
            "batch_state": "TEXT",
            "batch_error": "TEXT",
            "batch_submitted_at": "TEXT",
            "batch_completed_at": "TEXT",
            "answer_comment": "TEXT",
            "answer_comment_at": "TEXT",
            "answer_comment_status": "TEXT DEFAULT 'PENDING'",
            "fb_answer_comment_id": "TEXT",
            "answer_comment_error": "TEXT",
            "answer_commented_at": "TEXT",
            "content_fingerprint": "TEXT",
            "answer_hash": "TEXT",
            "quality_status": "TEXT",
            "quality_errors": "TEXT",
            "prompt_version": "TEXT",
            "difficulty": "TEXT",
            "viral_score": "INTEGER",
            "format_family": "TEXT",
            "spoiler_risk": "TEXT",
            "visual_fingerprint": "TEXT",
            "caption_fingerprint": "TEXT",
            "batch_retry_count": "INTEGER DEFAULT 0",
        },
    )
    _backfill_content_identities(cur)

    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_posts_schedule_slot
        ON posts (scheduled_at, slot)
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_status ON posts (status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_topic_key ON posts (topic_key)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_batch_job_name ON posts (batch_job_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_answer_hash ON posts (answer_hash)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_format_family ON posts (format_family)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_viral_score ON posts (viral_score)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_batch_retry_count ON posts (batch_retry_count)")
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_posts_content_fingerprint_unique
        ON posts (content_fingerprint)
        WHERE content_fingerprint IS NOT NULL
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_posts_visual_fingerprint_unique
        ON posts (visual_fingerprint)
        WHERE visual_fingerprint IS NOT NULL
        """
    )

    conn.commit()
    conn.close()


def _ensure_columns(cur, table_name: str, columns: dict[str, str]):
    cur.execute(f"PRAGMA table_info({table_name})")
    existing = {row["name"] for row in cur.fetchall()}
    for column, definition in columns.items():
        if column not in existing:
            cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column} {definition}")


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _content_fingerprint_from_topic(topic: dict) -> str | None:
    series_key = topic.get("series_key", "")
    answer = normalize_identity(topic.get("answer", ""))
    clue = normalize_identity(topic.get("clue", ""))
    if not series_key or not answer or not clue:
        return None

    payload = {
        "series_key": series_key,
        "answer": answer,
        "clue": clue,
    }
    return _stable_hash(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _backfill_content_identities(cur):
    cur.execute(
        """
        SELECT id, topic_payload, answer_comment, content_fingerprint, answer_hash, quality_status
        FROM posts
        ORDER BY id ASC
        """
    )
    rows = cur.fetchall()
    seen_fingerprints = {row["content_fingerprint"] for row in rows if row["content_fingerprint"]}

    for row in rows:
        topic = {}
        if row["topic_payload"]:
            try:
                topic = json.loads(row["topic_payload"])
            except (TypeError, json.JSONDecodeError):
                topic = {}

        answer = topic.get("answer", "")
        if not answer and row["answer_comment"]:
            first_line = row["answer_comment"].splitlines()[0]
            if ":" in first_line:
                answer = first_line.split(":", 1)[1]

        next_answer_hash = row["answer_hash"]
        if not next_answer_hash and answer:
            next_answer_hash = _stable_hash(normalize_identity(answer))

        next_fingerprint = row["content_fingerprint"]
        if not next_fingerprint and topic:
            candidate = _content_fingerprint_from_topic(topic)
            if candidate and candidate not in seen_fingerprints:
                next_fingerprint = candidate
                seen_fingerprints.add(candidate)

        next_quality_status = row["quality_status"] or ("LEGACY" if topic else None)
        if (
            next_answer_hash != row["answer_hash"]
            or next_fingerprint != row["content_fingerprint"]
            or next_quality_status != row["quality_status"]
        ):
            cur.execute(
                """
                UPDATE posts
                SET content_fingerprint = ?,
                    answer_hash = ?,
                    quality_status = ?
                WHERE id = ?
                """,
                (next_fingerprint, next_answer_hash, next_quality_status, row["id"]),
            )


def insert_post(data: dict) -> int:
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO posts (
            scheduled_at, slot, topic_type, topic_key, title,
            overlay_title, overlay_subtitle, overlay_stat, overlay_hook,
            caption, image_prompt, topic_payload, raw_image_path,
            final_image_path, status, batch_job_name, batch_request_key,
            batch_state, batch_error, batch_submitted_at, batch_completed_at,
            answer_comment, answer_comment_at, answer_comment_status,
            fb_answer_comment_id, answer_comment_error, answer_commented_at,
            content_fingerprint, answer_hash, quality_status, quality_errors,
            prompt_version, difficulty, viral_score, format_family, spoiler_risk,
            visual_fingerprint, caption_fingerprint, batch_retry_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["scheduled_at"],
                data["slot"],
                data["topic_type"],
                data["topic_key"],
                data["title"],
                data.get("overlay_title"),
                data.get("overlay_subtitle"),
                data.get("overlay_stat"),
                data.get("overlay_hook"),
                data["caption"],
                data["image_prompt"],
                data.get("topic_payload"),
                data.get("raw_image_path"),
                data.get("final_image_path"),
                data.get("status", "READY"),
                data.get("batch_job_name"),
                data.get("batch_request_key"),
                data.get("batch_state"),
                data.get("batch_error"),
                data.get("batch_submitted_at"),
                data.get("batch_completed_at"),
                data.get("answer_comment"),
                data.get("answer_comment_at"),
                data.get("answer_comment_status", "PENDING"),
                data.get("fb_answer_comment_id"),
                data.get("answer_comment_error"),
                data.get("answer_commented_at"),
                data.get("content_fingerprint"),
                data.get("answer_hash"),
                data.get("quality_status"),
                data.get("quality_errors"),
                data.get("prompt_version"),
                data.get("difficulty"),
                data.get("viral_score"),
                data.get("format_family"),
                data.get("spoiler_risk"),
                data.get("visual_fingerprint"),
                data.get("caption_fingerprint"),
                data.get("batch_retry_count", 0),
            ),
        )
    except sqlite3.IntegrityError as exc:
        conn.close()
        if "content_fingerprint" in str(exc):
            raise ValueError("Duplicate content blocked by content_fingerprint.") from exc
        if "visual_fingerprint" in str(exc):
            raise ValueError("Duplicate content blocked by visual_fingerprint.") from exc
        raise

    post_id = cur.lastrowid
    conn.commit()
    conn.close()
    return post_id


def exists_schedule(scheduled_at: str, slot: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 1 FROM posts
        WHERE scheduled_at = ? AND slot = ?
        LIMIT 1
        """,
        (scheduled_at, slot),
    )
    row = cur.fetchone()
    conn.close()
    return row is not None


def count_posts() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS total FROM posts")
    total = cur.fetchone()["total"]
    conn.close()
    return total


def recent_format_families(limit: int = 3) -> list[str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT format_family
        FROM posts
        WHERE format_family IS NOT NULL
        ORDER BY scheduled_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = [row["format_family"] for row in cur.fetchall() if row["format_family"]]
    conn.close()
    return rows


def count_future_posts(now_iso: str, statuses: tuple[str, ...] = ("READY", "WAITING_IMAGE")) -> int:
    conn = get_conn()
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in statuses)
    cur.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM posts
        WHERE scheduled_at > ?
          AND status IN ({placeholders})
        """,
        (now_iso, *statuses),
    )
    total = cur.fetchone()["total"]
    conn.close()
    return total


def list_existing_topic_identities() -> dict[str, set[str]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT topic_key, topic_payload, answer_comment, content_fingerprint, answer_hash, visual_fingerprint
        FROM posts
        ORDER BY id ASC
        """
    )
    rows = cur.fetchall()
    conn.close()

    topic_keys = set()
    answers = set()
    content_fingerprints = set()
    for row in rows:
        if row["topic_key"]:
            topic_keys.add(row["topic_key"])
        if row["content_fingerprint"]:
            content_fingerprints.add(row["content_fingerprint"])
        if row["visual_fingerprint"]:
            content_fingerprints.add(row["visual_fingerprint"])
        if row["answer_hash"]:
            answers.add(row["answer_hash"])

        payload = row["topic_payload"]
        if payload:
            try:
                topic = json.loads(payload)
                answer = topic.get("answer")
                if answer:
                    answers.add(normalize_identity(answer))
                    continue
            except (TypeError, json.JSONDecodeError):
                pass

        if row["answer_comment"]:
            first_line = row["answer_comment"].splitlines()[0]
            if ":" in first_line:
                answers.add(normalize_identity(first_line.split(":", 1)[1]))

    return {
        "topic_keys": topic_keys,
        "answers": answers,
        "content_fingerprints": content_fingerprints,
    }


def normalize_identity(value: str) -> str:
    return " ".join(value.casefold().strip().split())


def get_due_posts(now_iso: str, slot: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM posts
        WHERE status = 'READY'
          AND slot = ?
          AND scheduled_at <= ?
        ORDER BY scheduled_at ASC
        """,
        (slot, now_iso),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_due_posts(now_iso: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM posts
        WHERE status = 'READY'
          AND scheduled_at <= ?
        ORDER BY scheduled_at ASC, id ASC
        """,
        (now_iso,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_post(post_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
    row = cur.fetchone()
    conn.close()
    return row


def mark_posted(post_id: int, fb_post_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE posts
        SET status = 'POSTED',
            fb_post_id = ?,
            error_message = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (fb_post_id, post_id),
    )
    conn.commit()
    conn.close()


def schedule_answer_comment(post_id: int, answer_comment_at: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE posts
        SET answer_comment_at = ?,
            answer_comment_status = CASE
                WHEN answer_comment IS NULL THEN answer_comment_status
                ELSE COALESCE(answer_comment_status, 'PENDING')
            END,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (answer_comment_at, post_id),
    )
    conn.commit()
    conn.close()


def get_due_answer_comments(now_iso: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM posts
        WHERE status = 'POSTED'
          AND fb_post_id IS NOT NULL
          AND answer_comment IS NOT NULL
          AND answer_comment_at IS NOT NULL
          AND answer_comment_at <= ?
          AND COALESCE(answer_comment_status, 'PENDING') IN ('PENDING', 'FAILED')
        ORDER BY answer_comment_at ASC, id ASC
        """,
        (now_iso,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def mark_answer_commented(post_id: int, fb_comment_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE posts
        SET answer_comment_status = 'POSTED',
            fb_answer_comment_id = ?,
            answer_comment_error = NULL,
            answer_commented_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (fb_comment_id, post_id),
    )
    conn.commit()
    conn.close()


def mark_answer_comment_failed(post_id: int, error_message: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE posts
        SET answer_comment_status = 'FAILED',
            answer_comment_error = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (error_message[:1000], post_id),
    )
    conn.commit()
    conn.close()


def mark_failed(post_id: int, error_message: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE posts
        SET status = 'FAILED',
            error_message = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (error_message[:1000], post_id),
    )
    conn.commit()
    conn.close()


def mark_image_ready(post_id: int, raw_image_path: str, final_image_path: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE posts
        SET status = 'READY',
            raw_image_path = ?,
            final_image_path = ?,
            error_message = NULL,
            batch_error = NULL,
            batch_state = 'JOB_STATE_SUCCEEDED',
            batch_completed_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (raw_image_path, final_image_path, post_id),
    )
    conn.commit()
    conn.close()


def mark_image_failed(post_id: int, error_message: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE posts
        SET status = 'IMAGE_FAILED',
            error_message = ?,
            batch_error = ?,
            batch_state = COALESCE(batch_state, 'JOB_STATE_FAILED'),
            batch_completed_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (error_message[:1000], error_message[:1000], post_id),
    )
    conn.commit()
    conn.close()


def reset_post_image_for_retry(post_id: int, error_message: str | None = None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE posts
        SET status = 'WAITING_IMAGE',
            error_message = ?,
            batch_job_name = NULL,
            batch_state = NULL,
            batch_error = ?,
            batch_submitted_at = NULL,
            batch_completed_at = NULL,
            batch_retry_count = COALESCE(batch_retry_count, 0) + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            error_message[:1000] if error_message else None,
            error_message[:1000] if error_message else None,
            post_id,
        ),
    )
    conn.commit()
    conn.close()


def update_status(post_id: int, status: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE posts
        SET status = ?,
            error_message = CASE WHEN ? = 'READY' THEN NULL ELSE error_message END,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (status, status, post_id),
    )
    conn.commit()
    conn.close()


def update_post_caption(post_id: int, caption: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE posts
        SET caption = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (caption, post_id),
    )
    conn.commit()
    conn.close()


def update_post_image_prompt(post_id: int, image_prompt: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE posts
        SET image_prompt = ?,
            status = 'WAITING_IMAGE',
            batch_job_name = NULL,
            batch_state = NULL,
            batch_error = NULL,
            batch_submitted_at = NULL,
            batch_completed_at = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (image_prompt, post_id),
    )
    conn.commit()
    conn.close()


def list_unposted_posts():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM posts
        WHERE status != 'POSTED'
        ORDER BY id ASC
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_posts(post_ids: list[int]) -> int:
    if not post_ids:
        return 0
    conn = get_conn()
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in post_ids)
    cur.execute(f"DELETE FROM posts WHERE id IN ({placeholders})", post_ids)
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


def set_batch_for_posts(post_ids: list[int], batch_job_name: str, batch_state: str | None = None):
    if not post_ids:
        return
    conn = get_conn()
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in post_ids)
    params = [batch_job_name, batch_state, *post_ids]
    cur.execute(
        f"""
        UPDATE posts
        SET batch_job_name = ?,
            batch_state = ?,
            batch_submitted_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id IN ({placeholders})
        """,
        params,
    )
    conn.commit()
    conn.close()


def update_batch_state(batch_job_name: str, batch_state: str, batch_error: str | None = None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE posts
        SET batch_state = ?,
            batch_error = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE batch_job_name = ?
          AND status = 'WAITING_IMAGE'
        """,
        (batch_state, batch_error[:1000] if batch_error else None, batch_job_name),
    )
    conn.commit()
    conn.close()


def list_posts_for_batch_submission(limit: int = 100):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM posts
        WHERE status = 'WAITING_IMAGE'
          AND batch_job_name IS NULL
        ORDER BY scheduled_at ASC, id ASC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def count_posts_for_batch_submission() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS total
        FROM posts
        WHERE status = 'WAITING_IMAGE'
          AND batch_job_name IS NULL
        """
    )
    total = cur.fetchone()["total"]
    conn.close()
    return total


def list_posts_for_direct_image_generation(start_after_iso: str, cutoff_iso: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM posts
        WHERE status IN ('WAITING_IMAGE', 'IMAGE_FAILED')
          AND scheduled_at > ?
          AND scheduled_at <= ?
        ORDER BY scheduled_at ASC, id ASC
        """,
        (start_after_iso, cutoff_iso),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def list_batch_jobs_to_poll():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT batch_job_name
        FROM posts
        WHERE status = 'WAITING_IMAGE'
          AND batch_job_name IS NOT NULL
        GROUP BY batch_job_name
        ORDER BY MIN(batch_submitted_at) ASC
        """
    )
    rows = [row["batch_job_name"] for row in cur.fetchall()]
    conn.close()
    return rows


def batch_publish_overview(now_iso: str) -> dict:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT COUNT(*) AS total
        FROM posts
        WHERE status = 'WAITING_IMAGE'
          AND batch_job_name IS NULL
        """
    )
    waiting_unsubmitted = cur.fetchone()["total"]

    cur.execute(
        """
        SELECT COUNT(*) AS total
        FROM posts
        WHERE status = 'WAITING_IMAGE'
          AND batch_job_name IS NOT NULL
        """
    )
    waiting_submitted = cur.fetchone()["total"]

    cur.execute(
        """
        SELECT COUNT(DISTINCT batch_job_name) AS total
        FROM posts
        WHERE status = 'WAITING_IMAGE'
          AND batch_job_name IS NOT NULL
        """
    )
    batch_jobs_to_poll = cur.fetchone()["total"]

    cur.execute(
        """
        SELECT COUNT(*) AS total
        FROM posts
        WHERE status = 'READY'
          AND scheduled_at <= ?
        """,
        (now_iso,),
    )
    due_ready = cur.fetchone()["total"]

    cur.execute(
        """
        SELECT COUNT(*) AS total
        FROM posts
        WHERE status = 'READY'
          AND scheduled_at > ?
        """,
        (now_iso,),
    )
    future_ready = cur.fetchone()["total"]

    conn.close()
    return {
        "waiting_unsubmitted": waiting_unsubmitted,
        "waiting_submitted": waiting_submitted,
        "batch_jobs_to_poll": batch_jobs_to_poll,
        "due_ready": due_ready,
        "future_ready": future_ready,
    }


def list_posts_by_batch_job(batch_job_name: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM posts
        WHERE batch_job_name = ?
          AND status = 'WAITING_IMAGE'
        ORDER BY id ASC
        """,
        (batch_job_name,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def list_recent_posts(limit: int = 10):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM posts
        ORDER BY scheduled_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def list_posts(status: str | None = None, limit: int = 100):
    conn = get_conn()
    cur = conn.cursor()
    if status:
        cur.execute(
            """
            SELECT * FROM posts
            WHERE status = ?
            ORDER BY scheduled_at ASC, id ASC
            LIMIT ?
            """,
            (status, limit),
        )
    else:
        cur.execute(
            """
            SELECT * FROM posts
            ORDER BY scheduled_at ASC, id ASC
            LIMIT ?
            """,
            (limit,),
        )
    rows = cur.fetchall()
    conn.close()
    return rows


def dashboard_stats() -> dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT status, COUNT(*) AS total FROM posts GROUP BY status")
    status_counts = {row["status"]: row["total"] for row in cur.fetchall()}
    cur.execute("SELECT topic_type, COUNT(*) AS total FROM posts GROUP BY topic_type")
    type_counts = {row["topic_type"]: row["total"] for row in cur.fetchall()}
    cur.execute("SELECT COUNT(*) AS total FROM posts")
    total = cur.fetchone()["total"]
    conn.close()

    return {
        "total": total,
        "status_counts": Counter(status_counts),
        "type_counts": Counter(type_counts),
        "db_path": str(Path(DB_PATH)),
    }

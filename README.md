# Đố Việt Agent

Agent tạo và đăng bài Facebook tự động cho fanpage **Đố Việt - Kho Đố Dân Gian**.

Nội dung xoay quanh 4 series:

- `Đố Tục Ngữ`: nhìn hình đoán tục ngữ, điền từ thiếu, giải nghĩa, chọn đáp án, câu bị che chữ.
- `Đố Ca Dao`: nhìn hình đoán ca dao, điền câu tiếp theo, emoji/hình ảnh gợi nhớ quê hương, cha mẹ, tình yêu.
- `Đuổi Hình Bắt Chữ`: 2-4 hình ghép thành cụm từ, đoán qua icon, bắt chữ theo âm hoặc nghĩa.
- `Đố Mẹo Dân Gian`: câu hỏi mẹo, câu đố vui dân gian, logic nhẹ, câu nghe vậy mà không phải vậy.

Pipeline hiện có:

- tạo caption theo format series, ví dụ `[ĐỐ TỤC NGỮ #001]`
- tạo prompt ảnh 4:5 để Gemini render ảnh final có chữ
- style ảnh dùng prompt poster dân gian/game-show: thanh tiêu đề trên, cảnh gợi ý ở giữa, câu hỏi dưới, brand badge ở góc
- lưu lịch bài vào SQLite
- tạo ảnh qua Gemini Batch API
- đăng ảnh lên Facebook Page
- tự comment đáp án sau 2 giờ kể từ lúc bài được đăng
- tự bù batch mới khi số bài `READY` tương lai còn tối đa 6
- kiểm tra DB để không tạo trùng `topic_key` hoặc đáp án đã từng lên lịch
- lưu `content_fingerprint` và `answer_hash` để chặn trùng ở tầng database
- chạy quality gate nội bộ trước khi lưu bài mới
- nếu kho seed đã dùng hết, Gemini text sẽ sinh câu đố/prompt mới không trùng đáp án cũ
- dashboard Flask để preview, tạo lịch batch, poll batch, đăng thủ công

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Điền `.env`:

```env
DOVIET_AGENT_GEMINI_API_KEY=...
DOVIET_AGENT_GEMINI_TEXT_MODEL=gemini-2.5-flash
DOVIET_AGENT_GEMINI_IMAGE_MODEL=gemini-2.5-flash-image
DOVIET_AGENT_IMAGE_ASPECT_RATIO=4:5

DOVIET_AGENT_FB_PAGE_ID=...
DOVIET_AGENT_FB_PAGE_TOKEN=...
DOVIET_AGENT_FB_GRAPH_VERSION=v21.0

DOVIET_AGENT_TIMEZONE=Asia/Ho_Chi_Minh
DOVIET_AGENT_DB_PATH=data/agent.db
DOVIET_AGENT_OUTPUT_DIR=assets
DOVIET_AGENT_MIN_FUTURE_POSTS=6
DOVIET_AGENT_TARGET_FUTURE_POSTS=14
DOVIET_AGENT_DIRECT_IMAGE_BOOTSTRAP_DAYS=0
```

Các biến `ANIMAL_AGENT_*` cũ vẫn được fallback để không làm hỏng deploy cũ, nhưng cấu hình mới nên dùng `DOVIET_AGENT_*`.

## Khởi tạo DB

```bash
python scripts/init_db.py
```

## Chạy dashboard

```bash
python scripts/run_web.py
```

Mặc định:

```text
http://127.0.0.1:8000
```

## Tạo bài test

```bash
python scripts/create_test_post.py --allow-placeholder
```

Muốn đổi topic index:

```bash
python scripts/create_test_post.py 3 --allow-placeholder
```

## Tạo lịch tuần

Tạo qua Batch API:

```bash
python scripts/prepare_weekly_posts_batch.py
python scripts/poll_batch_images.py
```

## Tự bù batch mới

Script ensure sẽ tự kiểm tra DB:

- nếu số bài tương lai `READY` còn lớn hơn `DOVIET_AGENT_MIN_FUTURE_POSTS` thì không tạo thêm
- nếu `READY` còn tối đa 6, hệ thống bù thêm cho đủ `DOVIET_AGENT_TARGET_FUTURE_POSTS`
- bài mới luôn tránh trùng `topic_key` và đáp án đã có trong DB
- bài mới phải qua quality gate: đủ field, đáp án hợp lệ, chữ trên ảnh không lộ nguyên đáp án
- DB có unique index trên `content_fingerprint`, nên nội dung trùng sẽ bị chặn khi insert
- nếu còn bài `WAITING_IMAGE` chưa gửi Gemini Batch, script sẽ submit batch ảnh
- nếu seed có sẵn đã dùng hết, Gemini text sẽ sinh câu đố mới cùng series

```bash
python scripts/ensure_future_posts_batch.py
```

## Đăng bài và comment đáp án

Đăng mọi bài `READY` đã đến giờ:

```bash
python scripts/publish_due_posts.py all
```

Đăng theo slot:

```bash
python scripts/publish_due_posts.py morning
python scripts/publish_due_posts.py afternoon
```

Comment đáp án cho các bài đã đăng và đã qua mốc 2 giờ:

```bash
python scripts/publish_due_answers.py
```

Dry-run:

```bash
python scripts/publish_due_posts.py all --dry-run
python scripts/publish_due_answers.py --dry-run
```

Cron gợi ý:

```cron
0 2 * * * cd /root/fb_animal_agent && /root/fb_animal_agent/venv/bin/python scripts/ensure_future_posts_batch.py >> logs/agent.log 2>&1
15 */6 * * * cd /root/fb_animal_agent && /root/fb_animal_agent/venv/bin/python scripts/poll_batch_images.py >> logs/agent.log 2>&1
*/15 * * * * cd /root/fb_animal_agent && /root/fb_animal_agent/venv/bin/python scripts/publish_due_posts.py all >> logs/agent.log 2>&1
*/15 * * * * cd /root/fb_animal_agent && /root/fb_animal_agent/venv/bin/python scripts/publish_due_answers.py >> logs/agent.log 2>&1
```

## Deploy systemd

```bash
sudo bash deploy/install_systemd.sh
```

Timer chính:

- `fb-animal-agent-ensure.timer`: tự bù bài tương lai bằng Batch API.
- `fb-animal-agent-poll-batch.timer`: poll ảnh batch.
- `fb-animal-agent-publish-due.timer`: đăng bài đến giờ.
- `fb-animal-agent-publish-answers.timer`: comment đáp án đến giờ.
- `fb-animal-agent-web.service`: dashboard local.

## Preview bài

```bash
python scripts/preview_posts.py
```

Hoặc mở dashboard và vào từng bài để xem ảnh final, caption, bình luận đáp án, prompt ảnh, trạng thái batch/Facebook.

Prompt mẫu để copy/chỉnh tay nằm ở [docs/prompt_templates.md](docs/prompt_templates.md).

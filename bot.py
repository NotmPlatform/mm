import logging
import os
import re
import sqlite3
from datetime import datetime
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =========================================
# НАСТРОЙКИ
# =========================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_BOT_TOKEN_HERE")

# Webhook. Если не указан, бот запустится на polling.
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "webhook")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
PORT = int(os.getenv("PORT", "8080"))

# ID админов для /stats
# Пример: ADMIN_USER_IDS=12345,67890
ADMIN_USER_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_USER_IDS", "").split(",")
    if x.strip().isdigit()
}

# Ключ доступа к боту — участие в закрытой платной группе.
# ВАЖНО: сюда нужен именно numeric chat_id группы, а не invite-link.
# Пример: PAID_GROUP_CHAT=-1001234567890
PAID_GROUP_CHAT = os.getenv("PAID_GROUP_CHAT", "")

# Канал-источник, где лежат видеоуроки mm1, mm2, mm3...
# ВАЖНО: numeric chat_id закрытого канала.
# Бот должен быть админом этого канала, чтобы получать channel_post/edited_channel_post.
VIDEO_SOURCE_CHAT = os.getenv("VIDEO_SOURCE_CHAT", "")

# Ссылка на менеджера, если доступа нет
MANAGER_URL = os.getenv("MANAGER_URL", "https://t.me/+Sr03OD8ZRxwxMDEy")

# Ссылка на бота / тест для получения сертификата
CERT_TEST_BOT_URL = os.getenv("CERT_TEST_BOT_URL", "https://t.me/your_test_bot")

DB_PATH = os.getenv("DB_PATH", "web3_marketer_paid_course.db")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

COURSE_TITLE = "Курс: Маркетолог в Web3"

WELCOME_TEXT = f"""Добро пожаловать в <b>{COURSE_TITLE}</b>.

Ты внутри практического курса, который поможет освоить профессию <b>Web3 Marketer</b> и собрать сильную базу для входа в индустрию.

Что ты получишь внутри:

📘 <b>12 текстовых уроков</b> — структура роли, логика роста, каналы, позиционирование и ключевые задачи маркетолога в Web3
🎬 <b>12 видеоуроков</b> — быстрый и удобный формат для прохождения материала
🧰 <b>Практические материалы</b> — шаблоны, инструменты и готовые заготовки для работы

После прохождения курса тебе также будут доступны:

🛡 <b>Proof of Competency</b> — подтверждение в базе курса для HR
✅ <b>Verified Certificate of Completion</b> — именной PDF-сертификат о прохождении курса

Проходи уроки шаг за шагом. В конце тебя ждут практические материалы и финальный тест для получения сертификата."""

HELP_TEXT = (
    "Команды:\n"
    "/start — открыть курс\n"
    "/help — помощь\n"
    "/stats — статистика (для администратора)"
)

VIDEO_LABEL_RE = re.compile(r"\bmm(\d{1,2})\b", re.IGNORECASE)

# =========================================
# УРОКИ
# =========================================

LESSONS = [
    {
        "number": 1,
        "title": "Урок 1",
        "text_url": "https://telegra.ph/Bolshinstvo-dumayut-chto-marketing-v-Web3--ehto-posty-memy-i-aktivnost-03-19",
    },
    {
        "number": 2,
        "title": "Урок 2",
        "text_url": "https://telegra.ph/Urok-2--Auditoriya-v-Web3--pochemu-nelzya-govorit-so-vsemi-odinakovo-03-19",
    },
    {
        "number": 3,
        "title": "Урок 3",
        "text_url": "https://telegra.ph/Urok-3--Offer-i-pozicionirovanie--kak-obyasnit-cennost-za-10-sekund-03-19",
    },
    {
        "number": 4,
        "title": "Урок 4",
        "text_url": "https://telegra.ph/UROK-4--Kanaly-rosta-v-Web3--gde-proekt-realno-nabiraet-silu-03-19",
    },
    {
        "number": 5,
        "title": "Урок 5",
        "text_url": "https://telegra.ph/Urok-5--Kontent-kotoryj-rastit-proekt-a-ne-prosto-zapolnyaet-lentu-03-19",
    },
    {
        "number": 6,
        "title": "Урок 6",
        "text_url": "https://telegra.ph/Urok-6--Gde-zakanchivayutsya-ohvaty-i-nachinaetsya-realnyj-growth-03-19",
    },
    {
        "number": 7,
        "title": "Урок 7",
        "text_url": "https://telegra.ph/Urok-7--Kampanii-v-Web3--kak-zapuskat-to-chto-dayot-rezultat-03-19",
    },
    {
        "number": 8,
        "title": "Урок 8",
        "text_url": "https://telegra.ph/Urok-8--KOL-i-affiliate--gde-rost-a-gde-sliv-byudzheta-03-19",
    },
    {
        "number": 9,
        "title": "Урок 9",
        "text_url": "https://telegra.ph/Urok-9--Retention-v-Web3--kak-sdelat-tak-chtoby-polzovatel-ne-ischez-03-19",
    },
    {
        "number": 10,
        "title": "Урок 10",
        "text_url": "https://telegra.ph/Urok-10--Metriki-Web3-Marketing--na-chto-smotryat-silnye-komandy-03-19",
    },
    {
        "number": 11,
        "title": "Урок 11",
        "text_url": "https://telegra.ph/Urok-11--Web3-Marketing-v-SNG--kak-adaptirovat-globalnye-mehaniki-pod-lokalnyj-rynok-03-19",
    },
    {
        "number": 12,
        "title": "Урок 12",
        "text_url": "https://telegra.ph/Urok-12--Kak-vojti-v-professiyu-Web3-Marketing-i-pokazat-sebya-rynku-03-19",
    },
]

# =========================================
# МАТЕРИАЛЫ КУРСА
# =========================================

BONUS_ITEMS = [
    {
        "key": "cv",
        "title": "WEB3 MARKETING CV TEMPLATE",
        "url": "https://telegra.ph/WEB3-MARKETING-CV-TEMPLATE-03-19",
    },
    {
        "key": "mock_test_task",
        "title": "MOCK TEST TASK: WEB3 MARKETING",
        "url": "https://telegra.ph/MOCK-TEST-TASK-WEB3-MARKETING-03-19",
    },
    {
        "key": "project_breakdown",
        "title": "WEB3 PROJECT BREAKDOWN TEMPLATE",
        "url": "https://telegra.ph/WEB3-PROJECT-BREAKDOWN-TEMPLATE-03-19",
    },
    {
        "key": "cert_test",
        "title": "Тест для получения сертификата",
        "url": CERT_TEST_BOT_URL,
    },
]

LESSONS_COUNT = len(LESSONS)

# =========================================
# БАЗА ДАННЫХ
# =========================================

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                current_lesson INTEGER NOT NULL DEFAULT 1,
                completed_lessons INTEGER NOT NULL DEFAULT 0,
                materials_unlocked INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lesson_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                lesson_number INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lesson_videos (
                lesson_number INTEGER PRIMARY KEY,
                label TEXT NOT NULL,
                source_message_id INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()

        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        if "last_video_message_id" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN last_video_message_id INTEGER")
            conn.commit()


def upsert_user(user_id: int, username: Optional[str], first_name: Optional[str]) -> None:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        row = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            conn.execute(
                """
                UPDATE users
                SET username = ?, first_name = ?, last_seen_at = ?
                WHERE user_id = ?
                """,
                (username, first_name, now, user_id),
            )
        else:
            conn.execute(
                """
                INSERT INTO users (user_id, username, first_name, created_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, username, first_name, now, now),
            )
        conn.commit()


def get_user_state(user_id: int) -> sqlite3.Row:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()


def set_current_lesson(user_id: int, lesson_number: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET current_lesson = ?, last_seen_at = ? WHERE user_id = ?",
            (lesson_number, datetime.utcnow().isoformat(), user_id),
        )
        conn.commit()


def complete_lesson(user_id: int, lesson_number: int) -> None:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT completed_lessons FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        completed_lessons = row["completed_lessons"] if row else 0

        if lesson_number > completed_lessons:
            conn.execute(
                """
                UPDATE users
                SET completed_lessons = ?, current_lesson = ?, last_seen_at = ?
                WHERE user_id = ?
                """,
                (lesson_number, min(lesson_number + 1, LESSONS_COUNT), now, user_id),
            )
        else:
            conn.execute(
                "UPDATE users SET last_seen_at = ? WHERE user_id = ?",
                (now, user_id),
            )

        conn.execute(
            """
            INSERT INTO lesson_events (user_id, lesson_number, event_type, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, lesson_number, "complete", now),
        )
        conn.commit()


def unlock_materials(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET materials_unlocked = 1, last_seen_at = ? WHERE user_id = ?",
            (datetime.utcnow().isoformat(), user_id),
        )
        conn.commit()


def save_lesson_video_mapping(lesson_number: int, label: str, source_message_id: int) -> None:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO lesson_videos (lesson_number, label, source_message_id, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(lesson_number) DO UPDATE SET
                label = excluded.label,
                source_message_id = excluded.source_message_id,
                updated_at = excluded.updated_at
            """,
            (lesson_number, label, source_message_id, now),
        )
        conn.commit()


def get_lesson_video_message_id(lesson_number: int) -> Optional[int]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT source_message_id FROM lesson_videos WHERE lesson_number = ?",
            (lesson_number,),
        ).fetchone()
        return row["source_message_id"] if row else None


def get_last_video_message_id(user_id: int) -> Optional[int]:
    state = get_user_state(user_id)
    if not state:
        return None
    try:
        return state["last_video_message_id"]
    except Exception:
        return None


def set_last_video_message_id(user_id: int, message_id: Optional[int]) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE users
            SET last_video_message_id = ?, last_seen_at = ?
            WHERE user_id = ?
            """,
            (message_id, datetime.utcnow().isoformat(), user_id),
        )
        conn.commit()


def get_stats() -> dict:
    with get_conn() as conn:
        users_total = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        finished_total = conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE completed_lessons >= ?",
            (LESSONS_COUNT,),
        ).fetchone()["c"]
        materials_total = conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE materials_unlocked = 1"
        ).fetchone()["c"]
        indexed_videos = conn.execute(
            "SELECT COUNT(*) AS c FROM lesson_videos"
        ).fetchone()["c"]

    return {
        "users_total": users_total,
        "finished_total": finished_total,
        "materials_total": materials_total,
        "indexed_videos": indexed_videos,
    }


# =========================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================================

def lesson_by_number(lesson_number: int) -> Optional[dict]:
    for lesson in LESSONS:
        if lesson["number"] == lesson_number:
            return lesson
    return None


def extract_lesson_number_from_mm_label(raw_value: str) -> Optional[int]:
    if not raw_value:
        return None
    match = VIDEO_LABEL_RE.search(raw_value.strip())
    if not match:
        return None
    lesson_number = int(match.group(1))
    if 1 <= lesson_number <= LESSONS_COUNT:
        return lesson_number
    return None


def extract_video_lesson_number(message) -> Optional[int]:
    candidates = []

    if getattr(message, "caption", None):
        candidates.append(message.caption.strip())

    if getattr(message, "text", None):
        candidates.append(message.text.strip())

    video = getattr(message, "video", None)
    if video and getattr(video, "file_name", None):
        file_name = os.path.splitext(video.file_name)[0]
        candidates.append(file_name.strip())

    document = getattr(message, "document", None)
    if document and getattr(document, "file_name", None):
        file_name = os.path.splitext(document.file_name)[0]
        candidates.append(file_name.strip())

    for candidate in candidates:
        lesson_number = extract_lesson_number_from_mm_label(candidate)
        if lesson_number:
            return lesson_number

    return None


def has_copyable_video_content(message) -> bool:
    return bool(
        getattr(message, "video", None)
        or getattr(message, "document", None)
        or getattr(message, "animation", None)
    )


def access_gate_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔐 Проверить доступ", callback_data="check_paid_access")],
        ]
    )


def denied_access_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("👤 Обратиться к менеджеру", url=MANAGER_URL)],
            [InlineKeyboardButton("🔄 Проверить доступ ещё раз", callback_data="check_paid_access")],
        ]
    )


def main_menu_keyboard(current_lesson: int, completed_lessons: int) -> InlineKeyboardMarkup:
    rows = []

    if current_lesson <= LESSONS_COUNT:
        rows.append(
            [InlineKeyboardButton(f"▶️ Продолжить с урока {current_lesson}", callback_data=f"lesson:{current_lesson}")]
        )

    rows.append([InlineKeyboardButton("📚 Все уроки", callback_data="all_lessons")])

    if completed_lessons >= LESSONS_COUNT:
        rows.append([InlineKeyboardButton("📂 Открыть материалы курса", callback_data="check_materials_access")])

    return InlineKeyboardMarkup(rows)


def lessons_keyboard(unlocked_to: int) -> InlineKeyboardMarkup:
    rows = []
    for lesson in LESSONS:
        num = lesson["number"]
        title = lesson["title"]
        if num <= unlocked_to:
            rows.append([InlineKeyboardButton(f"{num}. {title}", callback_data=f"lesson:{num}")])
        else:
            rows.append([InlineKeyboardButton(f"🔒 {num}. {title}", callback_data="locked")])

    rows.append([InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


def lesson_keyboard(lesson_number: int, is_last: bool) -> InlineKeyboardMarkup:
    lesson = lesson_by_number(lesson_number)
    rows = []

    if lesson and lesson.get("text_url"):
        rows.append([InlineKeyboardButton("📖 Открыть текст", url=lesson["text_url"])])

    if VIDEO_SOURCE_CHAT:
        rows.append([InlineKeyboardButton("🎬 Открыть видео", callback_data=f"open_video:{lesson_number}")])

    rows.append([InlineKeyboardButton("✅ Отметить урок пройденным", callback_data=f"complete:{lesson_number}")])

    nav_row = []
    if lesson_number > 1:
        nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"lesson:{lesson_number - 1}"))
    if not is_last:
        nav_row.append(InlineKeyboardButton("➡️ Далее", callback_data=f"lesson:{lesson_number + 1}"))
    if nav_row:
        rows.append(nav_row)

    rows.append([InlineKeyboardButton("📚 Ко всем урокам", callback_data="all_lessons")])
    rows.append([InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


def materials_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for item in BONUS_ITEMS:
        icon = "🎓" if item["key"] == "cert_test" else "🧰"
        rows.append([InlineKeyboardButton(f"{icon} {item['title']}", url=item["url"])])
    rows.append([InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


async def is_member_of_chat(bot, user_id: int, chat_id_raw: str) -> bool:
    if not chat_id_raw:
        return False
    try:
        member = await bot.get_chat_member(chat_id=int(chat_id_raw), user_id=user_id)
        return member.status in {
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        }
    except Exception as exc:
        logger.warning(
            "Membership check failed | chat=%s | user=%s | error=%s",
            chat_id_raw,
            user_id,
            exc,
        )
        return False


async def has_paid_access(bot, user_id: int) -> bool:
    return await is_member_of_chat(bot, user_id, PAID_GROUP_CHAT)


async def show_denied_access(query) -> None:
    text = (
        "🔒 <b>Доступ к курсу закрыт</b>\n\n"
        "Вы не оплатили урок.\n"
        "Обратитесь к менеджеру канала."
    )
    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        reply_markup=denied_access_keyboard(),
        disable_web_page_preview=True,
    )


async def ensure_paid_access(query, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if await has_paid_access(context.bot, user_id):
        return True
    await show_denied_access(query)
    return False


async def delete_previous_video(bot, user_id: int) -> None:
    last_video_message_id = get_last_video_message_id(user_id)
    if not last_video_message_id:
        return

    try:
        await bot.delete_message(chat_id=user_id, message_id=last_video_message_id)
    except Exception as exc:
        logger.info(
            "Previous video delete skipped | user=%s | message_id=%s | error=%s",
            user_id,
            last_video_message_id,
            exc,
        )
    finally:
        set_last_video_message_id(user_id, None)


async def send_lesson_video(
    user_id: int,
    lesson_number: int,
    context: ContextTypes.DEFAULT_TYPE,
) -> str:
    if not VIDEO_SOURCE_CHAT:
        return "source_chat_missing"

    source_message_id = get_lesson_video_message_id(lesson_number)
    if not source_message_id:
        return "not_indexed"

    try:
        await delete_previous_video(context.bot, user_id)

        copied = await context.bot.copy_message(
            chat_id=user_id,
            from_chat_id=int(VIDEO_SOURCE_CHAT),
            message_id=int(source_message_id),
        )

        set_last_video_message_id(user_id, copied.message_id)
        return "ok"
    except Exception as exc:
        logger.exception(
            "Failed to send lesson video | user=%s | lesson=%s | source_chat=%s | source_message_id=%s | error=%s",
            user_id,
            lesson_number,
            VIDEO_SOURCE_CHAT,
            source_message_id,
            exc,
        )
        return "copy_failed"


def build_video_not_indexed_text(lesson_number: int) -> str:
    return (
        f"Видео для урока {lesson_number} ещё не найдено.\n\n"
        f"В закрытом канале должен быть пост с видео и меткой mm{lesson_number} "
        "(в caption, тексте поста или имени файла).\n\n"
        "Если этот пост был опубликован раньше, чем бота добавили в канал, "
        "просто отредактируй пост в канале — бот увидит обновление и сам сохранит нужный ID."
    )


# =========================================
# ХЕНДЛЕРЫ
# =========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    upsert_user(user.id, user.username, user.first_name)

    text = (
        f"<b>{COURSE_TITLE}</b>\n\n"
        "Перед открытием уроков бот должен проверить, есть ли у вас доступ к курсу.\n\n"
        "Нажмите кнопку ниже."
    )

    if update.message:
        await update.message.reply_html(
            text,
            reply_markup=access_gate_keyboard(),
            disable_web_page_preview=True,
        )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(HELP_TEXT)


async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id not in ADMIN_USER_IDS:
        if update.message:
            await update.message.reply_text("У тебя нет доступа к этой команде.")
        return

    stats = get_stats()
    text = (
        "📊 Статистика бота\n\n"
        f"Пользователей: {stats['users_total']}\n"
        f"Завершили все уроки: {stats['finished_total']}\n"
        f"Открыли материалы курса: {stats['materials_total']}\n"
        f"Видео привязано: {stats['indexed_videos']} из {LESSONS_COUNT}"
    )
    if update.message:
        await update.message.reply_text(text)


async def show_main_menu(query, user_id: int) -> None:
    state = get_user_state(user_id)
    text = (
        f"{WELCOME_TEXT}\n\n"
        f"Твой прогресс: <b>{state['completed_lessons']}</b> из <b>{LESSONS_COUNT}</b> уроков."
    )
    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(
            current_lesson=state["current_lesson"],
            completed_lessons=state["completed_lessons"],
        ),
        disable_web_page_preview=True,
    )


async def show_all_lessons(query, user_id: int) -> None:
    state = get_user_state(user_id)
    unlocked_to = min(max(state["completed_lessons"] + 1, 1), LESSONS_COUNT)
    text = (
        "📚 <b>Все уроки курса</b>\n\n"
        f"Открывай уроки по порядку. После завершения {LESSONS_COUNT} уроков откроются материалы курса."
    )
    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        reply_markup=lessons_keyboard(unlocked_to),
        disable_web_page_preview=True,
    )


async def show_lesson(
    query,
    user_id: int,
    lesson_number: int,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    lesson = lesson_by_number(lesson_number)
    if not lesson:
        await query.answer("Урок не найден.", show_alert=True)
        return

    state = get_user_state(user_id)
    unlocked_to = min(max(state["completed_lessons"] + 1, 1), LESSONS_COUNT)
    if lesson_number > unlocked_to:
        await query.answer("Сначала пройди предыдущий урок.", show_alert=True)
        return

    await delete_previous_video(context.bot, user_id)
    set_current_lesson(user_id, lesson_number)

    text = (
        f"📘 <b>{lesson['title']}</b>\n"
        f"Урок {lesson_number} из {LESSONS_COUNT}\n\n"
        "Открой текст и видео, а затем отметь урок как пройденный."
    )
    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        reply_markup=lesson_keyboard(lesson_number, is_last=(lesson_number == LESSONS_COUNT)),
        disable_web_page_preview=True,
    )


async def show_materials_gate(query, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = get_user_state(user_id)
    if state["completed_lessons"] < LESSONS_COUNT:
        await query.answer(f"Сначала пройди все {LESSONS_COUNT} уроков.", show_alert=True)
        return

    if not await has_paid_access(context.bot, user_id):
        await show_denied_access(query)
        return

    unlock_materials(user_id)
    text = (
        "📂 <b>Материалы курса открыты</b>\n\n"
        "Ты завершил обучение и открыл практический блок курса.\n\n"
        "Ниже тебя ждут:\n"
        "🧰 рабочие шаблоны и материалы\n"
        "📑 готовые заготовки для практики\n"
        "🎓 тест для получения сертификата\n\n"
        "После успешного прохождения теста тебе будут доступны:\n"
        "🛡 <b>Proof of Competency</b> — подтверждение в базе курса для HR\n"
        "✅ <b>Verified Certificate of Completion</b> — именной PDF-сертификат"
    )
    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        reply_markup=materials_keyboard(),
        disable_web_page_preview=True,
    )


async def index_video_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return

    if not VIDEO_SOURCE_CHAT:
        return

    try:
        source_chat_id = int(VIDEO_SOURCE_CHAT)
    except ValueError:
        logger.warning("VIDEO_SOURCE_CHAT is not numeric: %s", VIDEO_SOURCE_CHAT)
        return

    if not message.chat or message.chat.id != source_chat_id:
        return

    if not has_copyable_video_content(message):
        return

    lesson_number = extract_video_lesson_number(message)
    if not lesson_number:
        return

    label = f"mm{lesson_number}"
    save_lesson_video_mapping(
        lesson_number=lesson_number,
        label=label,
        source_message_id=message.message_id,
    )
    logger.info(
        "Indexed lesson video | lesson=%s | label=%s | message_id=%s",
        lesson_number,
        label,
        message.message_id,
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    upsert_user(user.id, user.username, user.first_name)

    await query.answer()
    data = query.data

    if data == "check_paid_access":
        if not await ensure_paid_access(query, user.id, context):
            return

        state = get_user_state(user.id)
        if state["completed_lessons"] == 0:
            await show_lesson(query, user.id, 1, context)
        else:
            await show_main_menu(query, user.id)
        return

    guarded = {"main_menu", "all_lessons", "check_materials_access"}
    if data in guarded or data.startswith(("lesson:", "complete:", "open_video:")):
        if not await ensure_paid_access(query, user.id, context):
            return

    if data == "main_menu":
        await show_main_menu(query, user.id)
        return

    if data == "all_lessons":
        await show_all_lessons(query, user.id)
        return

    if data == "locked":
        await query.answer("Сначала пройди предыдущие уроки.", show_alert=True)
        return

    if data == "check_materials_access":
        await show_materials_gate(query, user.id, context)
        return

    if data.startswith("lesson:"):
        lesson_number = int(data.split(":")[1])
        await show_lesson(query, user.id, lesson_number, context)
        return

    if data.startswith("open_video:"):
        lesson_number = int(data.split(":")[1])

        state = get_user_state(user.id)
        unlocked_to = min(max(state["completed_lessons"] + 1, 1), LESSONS_COUNT)
        if lesson_number > unlocked_to:
            await query.answer("Сначала пройди предыдущий урок.", show_alert=True)
            return

        result = await send_lesson_video(user.id, lesson_number, context)
        if result == "ok":
            await query.answer("Видео отправлено в чат.")
        elif result == "source_chat_missing":
            await query.answer("Не настроен VIDEO_SOURCE_CHAT.", show_alert=True)
        elif result == "not_indexed":
            await query.answer(build_video_not_indexed_text(lesson_number), show_alert=True)
        else:
            await query.answer("Не удалось отправить видео. Проверь права бота в канале.", show_alert=True)
        return

    if data.startswith("complete:"):
        lesson_number = int(data.split(":")[1])
        complete_lesson(user.id, lesson_number)

        if lesson_number >= LESSONS_COUNT:
            text = (
                "🏁 <b>Курс завершён</b>\n\n"
                f"Ты прошёл все {LESSONS_COUNT} уроков и собрал полную базу по роли <b>Web3 Marketer</b>.\n\n"
                "Дальше для тебя открываются:\n"
                "📂 практические материалы для работы\n"
                "🧰 готовые шаблоны и рабочие заготовки\n"
                "🎓 тест для получения сертификата\n\n"
                "Нажми ниже, чтобы открыть материалы и перейти к завершающему этапу курса."
            )
            keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("📂 Открыть материалы курса", callback_data="check_materials_access")],
                    [InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")],
                ]
            )
            await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=keyboard)
            return

        next_lesson = lesson_number + 1
        text = (
            f"✅ <b>Урок {lesson_number} отмечен как пройденный.</b>\n\n"
            f"Готов перейти к уроку {next_lesson}?"
        )
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(f"➡️ Перейти к уроку {next_lesson}", callback_data=f"lesson:{next_lesson}")],
                [InlineKeyboardButton("📚 Ко всем урокам", callback_data="all_lessons")],
            ]
        )
        await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=keyboard)
        return


async def menu_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    upsert_user(user.id, user.username, user.first_name)

    if update.message:
        if await has_paid_access(context.bot, user.id):
            state = get_user_state(user.id)
            await update.message.reply_html(
                (
                    "Используй кнопки ниже для навигации по курсу.\n\n"
                    f"Твой прогресс: <b>{state['completed_lessons']}</b> из <b>{LESSONS_COUNT}</b> уроков."
                ),
                reply_markup=main_menu_keyboard(
                    current_lesson=state["current_lesson"],
                    completed_lessons=state["completed_lessons"],
                ),
            )
        else:
            await update.message.reply_html(
                "🔒 <b>Доступ к курсу закрыт</b>\n\nВы не оплатили урок.\nОбратитесь к менеджеру канала.",
                reply_markup=denied_access_keyboard(),
                disable_web_page_preview=True,
            )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled error: %s", context.error)


# =========================================
# ИНИЦИАЛИЗАЦИЯ
# =========================================

def build_application() -> Application:
    for lesson in LESSONS:
        logger.info(
            "Lesson %s URLs | text=%s",
            lesson["number"],
            "set" if lesson["text_url"] else "empty",
        )

    logger.info("Paid group chat for access | %s", PAID_GROUP_CHAT if PAID_GROUP_CHAT else "empty")
    logger.info("Video source chat | %s", VIDEO_SOURCE_CHAT if VIDEO_SOURCE_CHAT else "empty")
    logger.info("Manager url | %s", "set" if MANAGER_URL else "empty")
    logger.info("Admin stats enabled | %s", "yes" if ADMIN_USER_IDS else "no")

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("stats", stats_handler))
    application.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POSTS, index_video_source_post))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
            menu_text_handler,
        )
    )
    application.add_error_handler(error_handler)
    return application


async def post_init(application: Application) -> None:
    logger.info("Bot initialized")
    logger.info(
        "To auto-index old videos, edit the source posts in the channel so the bot receives edited_channel_post updates."
    )


def main() -> None:
    init_db()
    app = build_application()
    app.post_init = post_init

    allowed_updates = ["message", "callback_query", "channel_post", "edited_channel_post"]

    if WEBHOOK_URL:
        webhook_path = f"/{WEBHOOK_PATH}"
        logger.info("Starting bot with webhook on %s%s", WEBHOOK_URL, webhook_path)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=WEBHOOK_PATH,
            webhook_url=f"{WEBHOOK_URL}{webhook_path}",
            secret_token=WEBHOOK_SECRET or None,
            allowed_updates=allowed_updates,
            drop_pending_updates=True,
        )
    else:
        logger.info("Starting bot with polling")
        app.run_polling(
            allowed_updates=allowed_updates,
            drop_pending_updates=True,
        )


if __name__ == "__main__":
    main()

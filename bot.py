import os
import re
import json
import random
import asyncio
import time
import logging
from types import SimpleNamespace
from urllib.parse import quote
from datetime import datetime, timezone, timedelta
from pathlib import Path
from telegram import Update, Poll, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    PollAnswerHandler,
    ContextTypes
)
from result_card import generate_result_card, generate_topper_card, clean_test_title, resolve_student_name

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATABASE_FILE = BASE_DIR / "questions_db.json"
SCORES_FILE = BASE_DIR / "scores.json"
BOT_TOKEN = os.getenv("BOT_TOKEN", "9293701349:AAGmkCZPDO8Sxs1xDdCyEY7gz-fuV0kK5cI")
DAILY_SCHEDULE_FILE = BASE_DIR / "daily_schedule.json"
FREE_DB_FILE = BASE_DIR / "free_promo_db.json"
FREE_SCHEDULE_FILE = BASE_DIR / "free_schedule.json"
PROMO_POSTER_PATH = BASE_DIR / "assets" / "promo_poster.png"
PAID_GROUP_CHAT_ID = -1001986170095
IST = timezone(timedelta(hours=5, minutes=30))

_FREE_DB_CACHE = None

def load_free_database():
    global _FREE_DB_CACHE
    if _FREE_DB_CACHE is not None:
        return _FREE_DB_CACHE
    if FREE_DB_FILE.exists():
        with open(FREE_DB_FILE, "r", encoding="utf-8") as f:
            _FREE_DB_CACHE = json.load(f)
            return _FREE_DB_CACHE
    return {"free_promo": {}}

def _load_schedule_file(path: Path, cid_env: str, time_env: str, start_env: str, max_sets: int, default_cid: str = "", default_time: str = ""):
    data = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = loaded
        except Exception:
            data = {}
    env_cid = os.getenv(cid_env, default_cid).strip()
    env_time = os.getenv(time_env, default_time).strip()
    if env_cid and env_time and env_cid not in data:
        parsed = parse_hhmm_ist(env_time)
        if parsed:
            anchor = datetime(2026, 11, 11, tzinfo=IST).date()
            days_elapsed = max(0, (datetime.now(IST).date() - anchor).days)
            default_set = (days_elapsed % max_sets) + 1
            s_val = os.getenv(start_env, "").strip()
            if s_val.isdigit() and 1 <= int(s_val) <= max_sets:
                default_set = int(s_val)
            data[env_cid] = {
                "chat_id": int(env_cid),
                "time": parsed[2],
                "next_set": default_set,
                "enabled": True,
                "last_run_date": "",
                "reminder_sent_date": "",
            }
    return data

def _save_schedule_file(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_daily_schedules():
    return _load_schedule_file(DAILY_SCHEDULE_FILE, "DAILY_AUTO_CHAT_ID", "DAILY_AUTO_TIME", "DAILY_AUTO_START_SET", 50, "-1001986170095", "17:30")

def save_daily_schedules(data):
    _save_schedule_file(DAILY_SCHEDULE_FILE, data)

def load_free_schedules():
    return _load_schedule_file(FREE_SCHEDULE_FILE, "FREE_AUTO_CHAT_ID", "FREE_AUTO_TIME", "FREE_AUTO_START_SET", 30, "-1001567537194", "19:00")

def save_free_schedules(data):
    _save_schedule_file(FREE_SCHEDULE_FILE, data)

def parse_hhmm_ist(raw: str):
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", (raw or "").strip())
    if not m:
        return None
    hh, mm = int(m.group(1)), int(m.group(2))
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    return hh, mm, f"{hh:02d}:{mm:02d}"

def build_5min_reminder_text():
    return (
        "🏛️ SAGAR COACHING CENTRE, BHAGWANPUR\n"
        "🎓 NMMS छात्रवृत्ति स्पेशल क्लास • ठीक 5 मिनट में!\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👋 प्यारे छात्रों!\n\n"
        "📖 आज के सभी 30 बेहद महत्वपूर्ण प्रश्न मेरे द्वारा लिखी गई किताब — \"NMMS स्पेशल गाइड बुक\" (जो पुस्तक आप सभी के पास है) से ही लिए गए हैं!\n\n"
        "⏱️ हर सवाल के लिए 60 सेकंड का समय मिलेगा\n"
        "🏆 टेस्ट पूरा होते ही Top 20 Merit List और Top 3 विजेताओं को Gold, Silver व Bronze Certificate जारी होंगे!\n\n"
        "✍️ कॉपी-पेन लेकर तैयार हो जाइए — ठीक 5 मिनट में टेस्ट शुरू हो रहा है... देखते हैं आज कौन टॉप करता है! 🔥🏆"
    )

def build_free_5min_reminder_text():
    return (
        "🏛️ SAGAR COACHING CENTRE, BHAGWANPUR\n"
        "🎓 NMMS फ्री डेमो अभ्यास • ठीक 5 मिनट में!\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👋 प्यारे छात्रों!\n\n"
        "📖 ठीक 5 मिनट बाद मेरे द्वारा लिखी गई \"NMMS स्पेशल गाइड बुक\" से चुने गए 10 महत्वपूर्ण प्रश्नों का लाइव डेमो टेस्ट शुरू होगा!\n\n"
        "⏱️ हर सवाल: 45 सेकंड | ⚡ अंत में Top 5 नाम + पूरा कोर्स व गाइड बुक पाने की जानकारी!\n"
        "✍️ कॉपी-पेन लेकर तैयार हो जाइए — देखते हैं आज कौन टॉप करता है! 🔥🏆"
    )

BOT_USERNAME = "sudhir_quiz_bot"

def parse_compound(text: str, prefix: str):
    """Safely extracts key and set even when key contains underscores like Social_Science or Mental_Ability."""
    if text.startswith(prefix + '__'):
        parts = text[len(prefix + '__'):].split('__')
        if len(parts) >= 2:
            return parts[0], parts[1]
    elif text.startswith(prefix + '_'):
        raw = text[len(prefix + '_'):]
        for pattern in ['_set_', '_mat_', '_sat_']:
            if pattern in raw:
                idx = raw.rfind(pattern)
                return raw[:idx], raw[idx+1:]
        parts = raw.split('_', 1)
        if len(parts) == 2:
            return parts[0], parts[1]
    return None, None

_DB_CACHE = None

def load_database():
    global _DB_CACHE
    if _DB_CACHE is not None:
        return _DB_CACHE
    if DATABASE_FILE.exists():
        with open(DATABASE_FILE, "r", encoding="utf-8") as f:
            _DB_CACHE = json.load(f)
            return _DB_CACHE
    return {"daily_mix": {}, "full_mocks": {}, "subjects": {}}

def get_category_group(db, category: str, group_key: str):
    if category == "free":
        return load_free_database().get("free_promo", {}).get(group_key, {})
    if category == "mix":
        return db.get("daily_mix", {}).get(group_key, {})
    if category == "mock":
        return db.get("full_mocks", {}).get(group_key, {})
    return db.get("subjects", {}).get(group_key, {})

def natural_set_items(sets_dict: dict):
    def _key(kv):
        m = re.search(r"(\d+)", kv[0])
        return (int(m.group(1)) if m else 9999, kv[0])
    return sorted(sets_dict.items(), key=_key)

def load_scores():
    if SCORES_FILE.exists():
        try:
            with open(SCORES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_scores(scores):
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)

def update_user_score(user, is_correct):
    scores = load_scores()
    uid = str(user.id)
    name = user.first_name or "Student"
    if user.last_name:
        name += f" {user.last_name}"
    
    if uid not in scores:
        scores[uid] = {
            "name": name,
            "username": user.username or "",
            "quizzes_played": 0,
            "total_questions": 0,
            "correct_answers": 0
        }

    scores[uid]["name"] = name
    if user.username:
        scores[uid]["username"] = user.username

    scores[uid]["total_questions"] += 1
    if is_correct:
        scores[uid]["correct_answers"] += 1

    save_scores(scores)

def shuffle_question_options(q):
    original_options = list(q["options"])
    if q.get("shuffle_options", True) is False:
        return {
            "id": q.get("id", ""),
            "question": q["question"],
            "options": original_options,
            "correct_option_id": q["correct_option_id"],
            "explanation": q.get("explanation", ""),
            "subject": q.get("subject", ""),
            "image": q.get("image"),
            "shuffle_options": False,
        }
    correct_text = original_options[q["correct_option_id"]]
    indexed = list(enumerate(original_options))
    random.shuffle(indexed)
    new_options = [opt for _, opt in indexed]
    new_correct_id = new_options.index(correct_text)
    return {
        "id": q.get("id", ""),
        "question": q["question"],
        "options": new_options,
        "correct_option_id": new_correct_id,
        "explanation": q.get("explanation", ""),
        "subject": q.get("subject", ""),
        "image": q.get("image"),
        "shuffle_options": True,
    }

async def is_group_admin(chat, user_id: int) -> bool:
    """Verifies if the user is a group administrator or creator."""
    if chat.type not in ["group", "supergroup"]:
        return True
    try:
        member = await chat.get_member(user_id)
        return member.status in ["creator", "administrator"]
    except Exception:
        return False

# Start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    is_group = chat.type in ["group", "supergroup"]

    # Security: If in group, only group admins are allowed to launch or see start menus!
    if is_group:
        if not await is_group_admin(chat, user.id):
            if context.args and len(context.args) > 0:
                await update.message.reply_text("⚠️ केवल ग्रुप एडमिन ही टेस्ट शुरू कर सकते हैं!")
            return

    # When launched via "Start in Group" button by an admin:
    if is_group and context.args and len(context.args) > 0:
        arg = context.args[0]
        if arg.startswith("q__"):
            parts = arg.split("__")
            if len(parts) >= 4:
                cat, grp_key, s_key = parts[1], parts[2], "__".join(parts[3:])
                await start_group_quiz(chat.id, user, cat, grp_key, s_key, context)
                return
        elif arg.startswith("mock"):
            mock_type, set_key = parse_compound(arg, "mock")
            if mock_type and set_key:
                await start_group_quiz(chat.id, user, "mock", mock_type, set_key, context)
                return
        elif arg.startswith("subj"):
            subject_key, set_key = parse_compound(arg, "subj")
            if subject_key and set_key:
                await start_group_quiz(chat.id, user, "subj", subject_key, set_key, context)
                return

    db = load_database()
    mix_cnt = len(db.get("daily_mix", {}).get("Daily_Mix", {}).get("sets", {}))
    mat_m_cnt = len(db.get("full_mocks", {}).get("MAT", {}).get("sets", {}))
    sat_m_cnt = len(db.get("full_mocks", {}).get("SAT", {}).get("sets", {}))
    sci_cnt = len(db.get("subjects", {}).get("Science", {}).get("sets", {}))
    sst_cnt = len(db.get("subjects", {}).get("Social_Science", {}).get("sets", {}))
    mat_s_cnt = len(db.get("subjects", {}).get("Mental_Ability", {}).get("sets", {}))
    mth_cnt = len(db.get("subjects", {}).get("Mathematics", {}).get("sets", {}))

    if is_group:
        welcome_text = (
            "🏛️ SAGAR COACHING CENTRE\n"
            "🎓 NMMS लाइव टेस्ट पोर्टल (UP + बिहार PYQ बैंक)\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✍️ पुस्तक लेखक: सागर सर (NMMS एक्सपर्ट)\n"
            "⏱️ प्रत्येक प्रश्न: 60 सेकंड | 🖼️ चित्र-आधारित प्रश्न शामिल\n"
            "🏆 टेस्ट समाप्ति पर टॉप 20 छात्रों की मेरिट लिस्ट जारी होगी।\n\n"
            "👇 नीचे से टेस्ट श्रेणी चुनें:"
        )
    else:
        welcome_text = (
            "🏛️ SAGAR COACHING CENTRE\n"
            "🎓 NMMS टेस्ट कंट्रोल पैनल (2,741 PYQ प्रश्न)\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✍️ पुस्तक लेखक: सागर सर (NMMS एक्सपर्ट)\n"
            "📞 संपर्क / WhatsApp: +91 91101 13671\n\n"
            "यहाँ से सेट चुनें और सीधे कोचिंग ग्रुप में शुरू करें:\n"
            f"• 🎯 डेली मिक्स (30 प्रश्न): {mix_cnt} सेट (10 MAT+8 वि.+7 सा.वि.+5 गणित)\n"
            f"• 🧠 MAT फुल मॉक (90 प्रश्न): {mat_m_cnt} सेट\n"
            f"• 📚 SAT फुल मॉक (90 प्रश्न): {sat_m_cnt} सेट (35 वि.+35 सा.वि.+20 गणित)\n"
            "• 🔬 विषयवार अभ्यास (50 प्रश्न प्रति सेट) • ⏱️ 60s / प्रश्न\n\n"
            "👇 नीचे से टेस्ट श्रेणी चुनें:"
        )

    keyboard = [
        [InlineKeyboardButton(f"🎯 डेली मिक्स टेस्ट (30 Q • {mix_cnt} सेट | 60s)", callback_data="pg__mix__Daily_Mix__0")],
        [
            InlineKeyboardButton(f"🧠 MAT मॉक (90 Q • {mat_m_cnt} सेट)", callback_data="pg__mock__MAT__0"),
            InlineKeyboardButton(f"📚 SAT मॉक (90 Q • {sat_m_cnt} सेट)", callback_data="pg__mock__SAT__0"),
        ],
        [
            InlineKeyboardButton(f"🔬 विज्ञान (50 Q • {sci_cnt} सेट)", callback_data="pg__subj__Science__0"),
            InlineKeyboardButton(f"🌍 सा. विज्ञान (50 Q • {sst_cnt} सेट)", callback_data="pg__subj__Social_Science__0"),
        ],
        [
            InlineKeyboardButton(f"🧠 तर्कशक्ति (50 Q • {mat_s_cnt} सेट)", callback_data="pg__subj__Mental_Ability__0"),
            InlineKeyboardButton(f"📐 गणित (50 Q • {mth_cnt} सेट)", callback_data="pg__subj__Mathematics__0"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)
        except Exception:
            await update.callback_query.message.reply_text(welcome_text, reply_markup=reply_markup)

PAGE_SIZE = 10

async def show_paginated_sets(query, category: str, group_key: str, page: int = 0, edit_in_place: bool = False):
    """Displays 10 sets per page in a clean 2-column grid for Daily Mix, 90Q Mocks, and 50Q Subjects."""
    db = load_database()
    group_data = get_category_group(db, category, group_key)
    if not group_data:
        await query.message.reply_text("⚠️ टेस्ट श्रेणी नहीं मिली!")
        return

    name = group_data.get("name", group_key)
    t_sec = group_data.get("timer_seconds", 60)
    ordered_sets = natural_set_items(group_data.get("sets", {}))
    total_sets = len(ordered_sets)
    total_pages = max(1, (total_sets + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))

    start_i = page * PAGE_SIZE
    page_items = ordered_sets[start_i:start_i + PAGE_SIZE]
    chat = query.message.chat
    is_group = chat.type in ["group", "supergroup"]

    text = (
        "🏛️ SAGAR COACHING CENTRE\n"
        f"📝 {name}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ समय: {t_sec}s / प्रश्न | 📚 कुल सेट: {total_sets} (पेज {page + 1}/{total_pages})\n\n"
        "👇 जो सेट शुरू करना है, उसे चुनें:"
    )

    keyboard = []
    set_buttons = []
    for set_key, set_info in page_items:
        short_label = re.sub(r"\s*\(\d+\s*प्रश्न\)\s*$", "", set_info["name"]).strip()
        prefix = "go" if is_group else "sel"
        cb = f"{prefix}__{category}__{group_key}__{set_key}"
        set_buttons.append(InlineKeyboardButton(f"📝 {short_label}", callback_data=cb))

    for i in range(0, len(set_buttons), 2):
        keyboard.append(set_buttons[i:i + 2])

    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ पिछला", callback_data=f"pg__{category}__{group_key}__{page - 1}"))
        nav_row.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("अगला ➡️", callback_data=f"pg__{category}__{group_key}__{page + 1}"))
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton("🔙 मुख्य मेनू", callback_data="btn_back_subjects")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if edit_in_place:
        try:
            await query.edit_message_text(text, reply_markup=reply_markup)
            return
        except Exception:
            pass
    await query.message.reply_text(text, reply_markup=reply_markup)

# Final Selection in DM: ONLY shows "Start in Group"
async def show_group_starter_card(query, category: str, group_key: str, set_key: str):
    db = load_database()
    group_data = get_category_group(db, category, group_key)
    set_info = group_data.get("sets", {}).get(set_key)
    if not set_info:
        await query.message.reply_text("⚠️ सेट नहीं मिला!")
        return

    q_count = len(set_info.get("questions", []))
    img_count = sum(1 for q in set_info.get("questions", []) if q.get("image"))
    t_sec = group_data.get("timer_seconds", 60)
    text = (
        "🏛️ SAGAR COACHING CENTRE\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 {set_info['name']}\n"
        f"❓ कुल प्रश्न: {q_count} | 🖼️ चित्र प्रश्न: {img_count} | ⏱️ {t_sec}s / प्रश्न\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👉 नीचे बटन दबाकर कोचिंग ग्रुप चुनें और टेस्ट शुरू करें:"
    )

    deep_param = f"q__{category}__{group_key}__{set_key}"
    group_url = f"https://t.me/{BOT_USERNAME}?startgroup={deep_param}"
    m = re.search(r"(\d+)", set_key)
    back_page = (int(m.group(1)) - 1) // PAGE_SIZE if m else 0

    keyboard = [
        [InlineKeyboardButton("👥 Start in Group (ग्रुप चुनें और शुरू करें)", url=group_url)],
        [InlineKeyboardButton("🔙 दूसरा सेट चुनें", callback_data=f"pg__{category}__{group_key}__{back_page}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(text, reply_markup=reply_markup)

# Start Group Quiz immediately
async def start_group_quiz(chat_id: int, user, session_type: str, group_key: str, set_key: str, context: ContextTypes.DEFAULT_TYPE):
    db = load_database()
    group_data = get_category_group(db, session_type, group_key)

    if not group_data:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ टेस्ट समूह नहीं मिला!")
        return

    sets = group_data.get("sets", {})
    set_info = sets.get(set_key)
    if not set_info or not set_info.get("questions"):
        await context.bot.send_message(chat_id=chat_id, text="⚠️ इस सेट में कोई सवाल नहीं मिला!")
        return

    questions = list(set_info["questions"])
    random.shuffle(questions)
    shuffled_questions = [shuffle_question_options(q) for q in questions]

    timer_seconds = group_data.get("timer_seconds", 60)

    session = {
        "chat_id": chat_id,
        "is_group": True,
        "is_free_promo": (session_type == "free"),
        "started_by": getattr(user, "first_name", "Admin"),
        "test_name": set_info["name"],
        "timer_seconds": timer_seconds,
        "questions": shuffled_questions,
        "current_index": 0,
        "total": len(shuffled_questions),
        "group_scores": {},
        "active_poll_id": None
    }

    context.bot_data.setdefault("group_sessions", {})[chat_id] = session

    display_title = clean_test_title(set_info['name'])
    if session_type == "free":
        banner_text = (
            "🏛️ SAGAR COACHING CENTRE, BHAGWANPUR\n"
            "🎓 NMMS छात्रवृत्ति स्पेशल डेमो टेस्ट (10 प्रश्न)\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📖 स्रोत: मेरे द्वारा लिखी गई NMMS स्पेशल गाइड बुक\n"
            f"❓ कुल प्रश्न: {len(shuffled_questions)} | ⏱️ समय: {timer_seconds}s प्रति प्रश्न\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ पहला प्रश्न 5 सेकंड में आ रहा है — देखते हैं आज बाज़ी कौन मारता है! 🥇🔥"
        )
    elif session_type == "mix":
        banner_text = (
            "🏛️ SAGAR COACHING CENTRE, BHAGWANPUR\n"
            "🎓 NMMS स्पेशल गाइड बुक लाइव टेस्ट\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 टेस्ट: {display_title}\n"
            "📖 स्रोत: मेरे द्वारा लिखी गई NMMS स्पेशल गाइड बुक\n"
            f"❓ कुल प्रश्न: {len(shuffled_questions)} | ⏱️ समय: {timer_seconds}s प्रति प्रश्न\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ पहला प्रश्न आ रहा है — देखते हैं आज बाज़ी कौन मारता है! 🥇🔥"
        )
    else:
        banner_text = (
            "🏛️ SAGAR COACHING CENTRE\n"
            "🎓 NMMS छात्रवृत्ति महा-अभ्यास\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 टेस्ट: {display_title}\n"
            f"❓ कुल प्रश्न: {len(shuffled_questions)} | ⏱️ समय: {timer_seconds}s प्रति प्रश्न\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ पहला प्रश्न आ रहा है, सभी छात्र तैयार रहें!"
        )
    await context.bot.send_message(chat_id=chat_id, text=banner_text)

    await asyncio.sleep(5.0)
    await send_next_group_question(chat_id, context)

# Send next question in group
async def send_next_group_question(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    session = context.bot_data.get("group_sessions", {}).get(chat_id)
    if not session:
        return

    idx = session["current_index"]
    questions = session["questions"]
    total = session["total"]

    if idx >= total:
        await finish_group_quiz(chat_id, context)
        return

    q = questions[idx]
    timer = session.get("timer_seconds", 60)

    full_q_text = f"Q{idx + 1}/{total}: {q['question']}"
    q_overflow = len(full_q_text) > 300
    if q_overflow:
        q_title = full_q_text[:297] + "..."
    else:
        q_title = full_q_text

    clean_options = [opt[:100] if len(opt) > 100 else opt for opt in q["options"]]

    img_rel = q.get("image")
    img_path = (BASE_DIR / img_rel) if img_rel else None
    if img_path and img_path.exists():
        caption_parts = [f"🖼️ Q{idx + 1}/{total} के लिए चित्र / आकृति:"]
        if q.get("shuffle_options") is False:
            caption_parts.append("(विकल्प चित्र के (1)–(4) क्रम में हैं)")
        if q_overflow:
            caption_parts.append(f"\n\n{q['question']}")
        caption = " ".join(caption_parts)[:1024]
        for attempt in range(2):
            try:
                with open(img_path, "rb") as img_file:
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=img_file,
                        caption=caption,
                    )
                await asyncio.sleep(0.3)
                break
            except Exception as img_err:
                logger.warning(f"Image send attempt {attempt + 1} failed for {img_rel}: {img_err}")
                if attempt == 0:
                    await asyncio.sleep(1.5)
    elif q_overflow:
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"📝 {full_q_text}")
            await asyncio.sleep(0.2)
        except Exception as msg_err:
            logger.warning(f"Overflow header send warning: {msg_err}")

    try:
        message = await context.bot.send_poll(
            chat_id=chat_id,
            question=q_title,
            options=clean_options,
            type=Poll.QUIZ,
            correct_option_id=q["correct_option_id"],
            explanation=q.get("explanation", "")[:200],
            is_anonymous=False,
            open_period=timer
        )

        poll_id = message.poll.id
        session["active_poll_id"] = poll_id

        context.bot_data.setdefault("active_polls", {})[poll_id] = {
            "chat_id": chat_id,
            "correct_option_id": q["correct_option_id"],
            "question_index": idx,
            "sent_at": time.time()
        }

        # Start 60s round timer for group
        asyncio.create_task(group_question_timer(chat_id, poll_id, idx, timer, context))

    except Exception as e:
        logger.error(f"Error sending poll in group: {e}")
        session["current_index"] += 1
        await send_next_group_question(chat_id, context)

# Background timer for group
async def group_question_timer(chat_id: int, poll_id: str, round_idx: int, wait_seconds: int, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(wait_seconds + 0.5)

    session = context.bot_data.get("group_sessions", {}).get(chat_id)
    if not session:
        return

    if session.get("active_poll_id") == poll_id and session.get("current_index") == round_idx:
        session["current_index"] += 1
        await send_next_group_question(chat_id, context)

# Finish Group Quiz
async def finish_group_quiz(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    session = context.bot_data.get("group_sessions", {}).pop(chat_id, None)
    if not session:
        return

    current_idx = session.get("current_index", 0)
    total_q = session.get("total", len(session.get("questions", [])))

    # If quiz ran to completion naturally, attempted is exactly total_q
    if current_idx >= total_q:
        attempted = total_q
    else:
        # If stopped early mid-quiz, include active poll if one was in flight
        attempted = current_idx + 1 if session.get("active_poll_id") else current_idx
        attempted = min(attempted, total_q)
    
    attempted = max(attempted, 1)

    scores = session.get("group_scores", {})

    if not scores:
        result_msg = (
            "🏛️ SAGAR COACHING CENTRE\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🏁 टेस्ट समाप्त: {session['test_name']}\n\n"
            "⚠️ किसी भी छात्र का स्कोर दर्ज नहीं हुआ।"
        )
    else:
        # Calculate accurate speed and accuracy per student
        for p in scores.values():
            c = p.get("correct_count", p.get("score", 0))
            ans = p.get("answered_count", c)
            if ans < c:
                ans = c
            p["answered_count"] = ans
            # Accuracy is percentage of answered questions that were correct
            p["accuracy"] = round((c / ans) * 100, 1) if ans > 0 else 0.0
            # Speed is average time per question answered
            t = p.get("total_time", 0.0)
            p["avg_time"] = round(t / ans, 1) if ans > 0 else 60.0

        # Sort: Score descending, tie-breaker: Total response time ascending (Fastest Finger First)
        sorted_players = sorted(
            scores.values(),
            key=lambda x: (-x["score"], x.get("total_time", 999999))
        )
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

        total_participants = len(sorted_players)
        list_label = f"टॉप 20 (कुल {total_participants} छात्रों में से)" if total_participants > 10 else f"मेरिट लिस्ट ({total_participants} छात्र)"

        result_msg = (
            "🏛️ SAGAR COACHING CENTRE\n"
            f"🏆 NMMS महा-अभ्यास: {list_label}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 टेस्ट: {clean_test_title(session['test_name'])} | कुल प्रश्न: {attempted} | कुल प्रतिभागी: {total_participants}\n\n"
        )
        for i, p in enumerate(sorted_players[:10]):
            m = medals[i] if i < len(medals) else f"#{i+1}"
            pct = p.get("accuracy", 0.0)
            avg_t = p.get("avg_time", 0.0)
            clean_name = str(p.get("name", "Student")).replace('*', '').replace('_', '').replace('`', '').strip()
            result_msg += f"{m} {clean_name} — {p['score']}/{attempted} ({pct:.1f}% | ⏱️ {avg_t}s avg)\n"
        
        result_msg += (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📖 सभी प्रश्न 'सागर सर' (7+ वर्ष अनुभव) द्वारा रचित NMMS पुस्तक से लिए गए हैं।\n"
            "🏛️ सागर कोचिंग सेन्टर, भगवानपुर | 📞 +91 91101 13671\n"
            "👏 शानदार प्रदर्शन करने वाले सभी छात्रों को बधाई!"
        )

    # Send text leaderboard (plain text - clean without raw markdown stars)
    await context.bot.send_message(chat_id=chat_id, text=result_msg)

    # Free Demo Group flow: keep Top 20 Merit Cards & Certificates exclusive to Paid batch; send HD Course + Book Promo Card!
    if session.get("is_free_promo"):
        wa_course = "https://wa.me/919110113671?text=" + quote("नमस्ते सर, मुझे NMMS 2027-28 पूरा कोर्स जॉइन करना है। कृपया बैच और फीस की जानकारी दें।")
        wa_book = "https://wa.me/919110113671?text=" + quote("नमस्ते सर, मुझे आपके द्वारा लिखी NMMS स्पेशल गाइड बुक खरीदनी है। कृपया जानकारी दें।")
        app_url = "https://play.google.com/store/apps/details?id=com.lct.pbxwdta"
        web_url = "https://www.sagarcoaching.tech/"
        wa_chan_url = "https://www.whatsapp.com/channel/0029Va5PJaVGE56lMwsSzs0g"
        insta_url = "https://www.instagram.com/sagarcoachingcentrebhagwanpur/"
        fb_url = "https://www.facebook.com/SagarCoachingCentreBhagwanpur59"
        promo_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎓 NMMS पूरा कोर्स जॉइन करें (WhatsApp)", url=wa_course)],
            [InlineKeyboardButton("📖 NMMS गाइड बुक मँगवाएँ (WhatsApp)", url=wa_book)],
            [
                InlineKeyboardButton("📱 हमारा App डाउनलोड करें", url=app_url),
                InlineKeyboardButton("🌐 Website देखें", url=web_url),
            ],
            [
                InlineKeyboardButton("📢 WA Channel", url=wa_chan_url),
                InlineKeyboardButton("📸 Instagram", url=insta_url),
                InlineKeyboardButton("📘 Facebook", url=fb_url),
            ],
        ])
        promo_caption = (
            "🏛️ *SAGAR COACHING CENTRE, BHAGWANPUR*\n"
            "🎯 *NMMS 2027-28 संपूर्ण तैयारी + स्पेशल गाइड बुक*\n\n"
            "आज आपने केवल 10 प्रश्नों का डेमो देखा — *Paid Batch* में आपको मिलता है:\n"
            "✅ पूरा MAT + SAT सिलेबस (ट्रिक्स व क्लास नोट्स)\n"
            "✅ रोज़ाना *30Q स्पेशल + 90Q फुल मॉक टेस्ट* (2,741+ PYQs)\n"
            "✅ रोज़ *Top 20 Merit Card* व विजेताओं को *Gold/Silver/Bronze Certificate* 🏆\n"
            "✅ *2021–2026 हल पेपर सहित मेरी अपनी लिखी गाइड बुक*\n\n"
            "🌐 *www.sagarcoaching.tech* | 📱 App Google Play पर उपलब्ध\n"
            "👇 *कोर्स, किताब और हमारे ऑफिशियल चैनल से जुड़ने के लिए बटन दबाएँ:*\n"
            "📞 WhatsApp / कॉल: +91 91101 13671"
        )
        try:
            if PROMO_POSTER_PATH.exists():
                with open(PROMO_POSTER_PATH, "rb") as pf:
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=pf,
                        caption=promo_caption,
                        reply_markup=promo_markup,
                        parse_mode="Markdown",
                    )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=promo_caption,
                    reply_markup=promo_markup,
                    parse_mode="Markdown",
                )
        except Exception as promo_err:
            logger.error(f"Free promo send error: {promo_err}")
        return

    # Send Image Result Card if there were scores
    if scores:
        try:
            total_questions = session.get("total", attempted)

            # Suspense & calculation announcement
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "🏁 *टेस्ट समाप्त हुआ!*\n"
                        "⏳ सभी छात्रों के अंकों की गणना और ऑफिशियल मेरिट लिस्ट तैयार की जा रही है... (कृपया 4-5 सेकंड प्रतीक्षा करें)"
                    ),
                    parse_mode="Markdown"
                )
            except Exception as e_announce:
                logger.warning(f"Could not send suspense announcement: {e_announce}")

            await asyncio.sleep(4.0)

            # Ensure user_id is populated for each player
            for uid_k, p in scores.items():
                if not p.get("user_id"):
                    try: p["user_id"] = int(uid_k)
                    except: pass

            # Concurrently fetch Telegram profile photos for top 20 rankers
            async def fetch_avatar(player):
                uid = player.get("user_id")
                if not uid:
                    return
                try:
                    photos = await asyncio.wait_for(
                        context.bot.get_user_profile_photos(user_id=int(uid), limit=1),
                        timeout=2.0
                    )
                    if photos and photos.total_count > 0:
                        photo_size = photos.photos[0][0]
                        f = await asyncio.wait_for(
                            context.bot.get_file(photo_size.file_id),
                            timeout=2.0
                        )
                        buf = await f.download_as_bytearray()
                        player["avatar_bytes"] = bytes(buf)
                except Exception:
                    player["avatar_bytes"] = None

            avatar_tasks = [fetch_avatar(p) for p in sorted_players[:20]]
            if avatar_tasks:
                await asyncio.gather(*avatar_tasks, return_exceptions=True)

            image_buf = generate_result_card(
                test_name=session["test_name"],
                total_q=total_questions,
                top_students=sorted_players,
                attempted_q=attempted,
                total_participants=len(sorted_players)
            )
            caption = (
                "🏆 *NMMS Official Merit Card (Top 20)*\n"
                "🏛️ Sagar Coaching Centre, Bhagwanpur (Supaul)\n"
                "📖 NMMS Special Guide Book by Sagar Sir (7+ Years Exp.)\n"
                "📞 +91 91101 13671\n\n"
                "✨ आप चाहें तो इस परिणाम को अपने WhatsApp Status पर शेयर कर सकते हैं! 👏"
            )
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=image_buf,
                caption=caption,
                parse_mode="Markdown"
            )

            # Send Personal Topper Certificate Cards for Top 3 with 1.5s cadence
            topper_limit = min(3, len(sorted_players))
            for rank_idx in range(topper_limit):
                topper = sorted_players[rank_idx]
                r_num = rank_idx + 1
                try:
                    await asyncio.sleep(1.5)
                    topper_buf = generate_topper_card(
                        student=topper,
                        rank=r_num,
                        test_name=session["test_name"],
                        total_q=total_questions,
                        attempted_q=attempted,
                        total_participants=len(sorted_players)
                    )
                    medals_label = ["1st Rank Topper", "2nd Rank Topper", "3rd Rank Topper"][rank_idx]
                    topper_name = resolve_student_name(topper)
                    topper_caption = (
                        f"🌟 *{medals_label}:* {topper_name}\n"
                        f"🎯 Score: {topper['score']}/{attempted} | Accuracy: {topper.get('accuracy', 0):.1f}%\n"
                        "🏛️ Sagar Coaching Centre, Bhagwanpur\n\n"
                        "✨ आप चाहें तो इस Topper Certificate को अपने WhatsApp Status पर शेयर कर सकते हैं! 👏"
                    )
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=topper_buf,
                        caption=topper_caption,
                        parse_mode="Markdown"
                    )
                except Exception as ex_topper:
                    logger.error(f"Error sending topper card for rank {r_num}: {ex_topper}")
        except Exception as e:
            logger.error(f"Error generating or sending result card image: {e}")

# Handle Poll Answer in group
async def receive_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer
    poll_id = answer.poll_id
    user = answer.user

    active_polls = context.bot_data.get("active_polls", {})
    poll_info = active_polls.get(poll_id)

    if not poll_info:
        return

    chat_id = poll_info["chat_id"]
    correct_id = poll_info["correct_option_id"]
    sent_at = poll_info.get("sent_at", time.time())
    elapsed = max(0.5, round(time.time() - sent_at, 1))

    is_correct = bool(answer.option_ids and answer.option_ids[0] == correct_id)

    session = context.bot_data.get("group_sessions", {}).get(chat_id)
    if not (session and session.get("is_free_promo")):
        update_user_score(user=user, is_correct=is_correct)
    if session:
        g_scores = session["group_scores"]
        uid = str(user.id)
        if uid not in g_scores:
            full_name = user.first_name or "Student"
            if user.last_name:
                full_name += f" {user.last_name}"
            g_scores[uid] = {
                "user_id": user.id,
                "name": full_name,
                "score": 0,
                "total_time": 0.0,
                "correct_count": 0,
                "answered_count": 0
            }

        # Track every attempted answer and elapsed time
        g_scores[uid]["answered_count"] = g_scores[uid].get("answered_count", 0) + 1
        g_scores[uid]["total_time"] = g_scores[uid].get("total_time", 0.0) + elapsed

        if is_correct:
            g_scores[uid]["score"] += 1
            g_scores[uid]["correct_count"] = g_scores[uid].get("correct_count", 0) + 1

# Command /stop in group
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    # Security check: only group admin can stop
    if chat.type in ["group", "supergroup"]:
        if not await is_group_admin(chat, user.id):
            await update.message.reply_text("⚠️ केवल ग्रुप एडमिन ही टेस्ट रोक सकते हैं!")
            return

    session = context.bot_data.get("group_sessions", {}).get(chat.id)
    if not session:
        await update.message.reply_text("ℹ️ इस ग्रुप में कोई एक्टिव क्विज़ नहीं चल रहा है। नया शुरू करने के लिए `/quiz` लिखें।")
        return

    await update.message.reply_text("🛑 टेस्ट बीच में रोक दिया गया है। परिणाम:")
    await finish_group_quiz(chat.id, context)

# Command /quiz
async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_command(update, context)

# Stats command
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    scores = load_scores()
    uid = str(user.id)
    u_data = scores.get(uid)

    if not u_data:
        text = "📊 आपने अभी तक किसी टेस्ट में भाग नहीं लिया है। क्विज़ शुरू करने के लिए `/quiz` लिखें!"
    else:
        total_q = u_data.get("total_questions", 0)
        correct_q = u_data.get("correct_answers", 0)
        acc = (correct_q / total_q * 100) if total_q > 0 else 0
        text = (
            f"📊 {user.first_name} के NMMS Stats:\n\n"
            f"❓ कुल प्रश्न हल किए: {total_q}\n"
            f"✅ सही उत्तर: {correct_q}\n"
            f"🎯 एक्यूरेसी (Accuracy): {acc:.1f}%"
        )

    if update.message:
        await update.message.reply_text(text)
    elif update.callback_query:
        try: await update.callback_query.answer()
        except: pass
        await update.callback_query.message.reply_text(text)

# Leaderboard command
async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scores = load_scores()
    if not scores:
        text = "🏆 अभी तक कोई स्कोर रिकॉर्ड नहीं हुआ है।"
    else:
        sorted_users = sorted(scores.values(), key=lambda x: x.get("correct_answers", 0), reverse=True)[:10]
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

        text = "🏆 NMMS All-Time Top Rankers:\n\n"
        for i, u in enumerate(sorted_users):
            medal = medals[i] if i < len(medals) else f"#{i+1}"
            name = str(u.get("name", "Unknown")).replace('*', '').replace('_', '')
            correct = u.get("correct_answers", 0)
            text += f"{medal} {name} — {correct} सही उत्तर\n"

    keyboard = [[InlineKeyboardButton("🔙 मुख्य मेनू", callback_data="btn_back_subjects")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        try: await update.callback_query.answer()
        except: pass
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "ℹ️ SAGAR COACHING CENTRE - NMMS Quiz Portal सहायता:\n\n"
        "1. प्राइवेट चैट में:\n"
        "   • /quiz दबाएँ और अपना सेट चुनें।\n"
        "   • फिर '👥 Start in Group' दबाकर कोचिंग ग्रुप चुनें। क्विज़ सीधे उस ग्रुप में शुरू हो जाएगा!\n\n"
        "2. ग्रुप में:\n"
        "   • ग्रुप एडमिन सीधे /quiz लिखकर टेस्ट शुरू कर सकते हैं।\n"
        "   • हर प्रश्न पर 60 सेकंड का समय मिलेगा।\n"
        "   • टेस्ट रोकने के लिए एडमिन /stop भेज सकते हैं।\n\n"
        "📖 NMMS स्पेशल गाइड बुक (लेखक: सागर सर - 7+ वर्ष अनुभव)\n"
        "🏛️ सागर कोचिंग सेन्टर, भगवानपुर | 📞 संपर्क: +91 91101 13671"
    )
    if update.message:
        await update.message.reply_text(help_text)
    elif update.callback_query:
        try: await update.callback_query.answer()
        except: pass
        await update.callback_query.message.reply_text(help_text)

# Button callback router
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    data = query.data
    chat = query.message.chat
    user = query.from_user

    # Security: In groups, only admins can click control buttons!
    if chat.type in ["group", "supergroup"]:
        if not await is_group_admin(chat, user.id):
            await query.answer("⚠️ केवल ग्रुप एडमिन ही टेस्ट शुरू या बदल सकते हैं!", show_alert=True)
            return

    if data == "noop":
        return
    elif data.startswith("pg__"):
        parts = data.split("__")
        if len(parts) >= 4:
            cat, grp_key, pg = parts[1], parts[2], int(parts[3])
            # Edit in-place when paging inside category or back from starter card;
            # keep fresh message when coming from main menu? Wait: editing in-place from main menu too is super clean!
            await show_paginated_sets(query, cat, grp_key, pg, edit_in_place=True)
    elif data.startswith("sel__"):
        parts = data.split("__")
        if len(parts) >= 4:
            cat, grp_key, s_key = parts[1], parts[2], "__".join(parts[3:])
            await show_group_starter_card(query, cat, grp_key, s_key)
    elif data.startswith("go__"):
        parts = data.split("__")
        if len(parts) >= 4:
            cat, grp_key, s_key = parts[1], parts[2], "__".join(parts[3:])
            await start_group_quiz(chat.id, user, cat, grp_key, s_key, context)
    elif data.startswith("menu_mock_"):
        mock_type = data.replace("menu_mock_", "")
        await show_paginated_sets(query, "mock", mock_type, 0)
    elif data.startswith("subj_"):
        subject_key = data.replace("subj_", "")
        await show_paginated_sets(query, "subj", subject_key, 0)
    elif data.startswith("setselect_mock"):
        mock_type, set_key = parse_compound(data, "setselect_mock")
        if mock_type and set_key:
            await show_group_starter_card(query, "mock", mock_type, set_key)
    elif data.startswith("setselect_subj"):
        subject_key, set_key = parse_compound(data, "setselect_subj")
        if subject_key and set_key:
            await show_group_starter_card(query, "subj", subject_key, set_key)
    elif data.startswith("startmock"):
        mock_type, set_key = parse_compound(data, "startmock")
        if mock_type and set_key:
            await start_group_quiz(chat.id, user, "mock", mock_type, set_key, context)
    elif data.startswith("startsubj"):
        subject_key, set_key = parse_compound(data, "startsubj")
        if subject_key and set_key:
            await start_group_quiz(chat.id, user, "subj", subject_key, set_key, context)
    elif data == "btn_back_subjects":
        await start_command(update, context)
    elif data == "btn_stats":
        await stats_command(update, context)
    elif data == "btn_leaderboard":
        await leaderboard_command(update, context)
    elif data == "btn_help":
        await help_command(update, context)

async def send_admin_private_msg(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Keeps daily-scheduler confirmations invisible to group students by replying in admin's private DM."""
    chat = update.effective_chat
    user = update.effective_user
    is_group = chat.type in ["group", "supergroup"]
    if is_group:
        try:
            if update.message:
                await update.message.delete()
        except Exception:
            pass
        try:
            await context.bot.send_message(chat_id=user.id, text=text)
            return
        except Exception:
            pass
    if update.message:
        await update.message.reply_text(text)

async def setdaily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type in ["group", "supergroup"] and not await is_group_admin(chat, user.id):
        try:
            await update.message.delete()
        except Exception:
            pass
        return

    args = context.args or []
    parsed = parse_hhmm_ist(args[0]) if args else None
    if not parsed:
        await send_admin_private_msg(
            update,
            context,
            "⚠️ सही फॉर्मेट भेजें:\n/setdaily HH:MM (उदाहरण: /setdaily 20:00 या /setdaily 20:00 1)",
        )
        return

    db = load_database()
    total_sets = max(1, len(db.get("daily_mix", {}).get("Daily_Mix", {}).get("sets", {})))
    schedules = load_daily_schedules()
    cid_str = str(chat.id)
    prev = schedules.get(cid_str, {})

    set_num = int(prev.get("next_set", 1))
    if len(args) >= 2 and args[1].isdigit():
        requested = int(args[1])
        if 1 <= requested <= total_sets:
            set_num = requested

    schedules[cid_str] = {
        "chat_id": chat.id,
        "time": parsed[2],
        "next_set": set_num,
        "enabled": True,
        "last_run_date": "",
        "reminder_sent_date": "",
    }
    save_daily_schedules(schedules)

    await send_admin_private_msg(
        update,
        context,
        "✅ डेली 30Q स्पेशल टेस्ट सेट हो गया!\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ग्रुप/चैट ID: {chat.id}\n"
        f"⏰ समय: {parsed[2]} IST\n"
        f"📅 अगला सेट: सेट {set_num:02d} / {total_sets}\n"
        "🔔 5-मिनट पहले क्लास संदेश: चालू",
    )

async def dailystatus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type in ["group", "supergroup"] and not await is_group_admin(chat, user.id):
        return

    db = load_database()
    total_sets = max(1, len(db.get("daily_mix", {}).get("Daily_Mix", {}).get("sets", {})))
    schedules = load_daily_schedules()
    s = schedules.get(str(chat.id))
    if not s:
        msg = (
            "📅 डेली 30Q स्पेशल टेस्ट स्थिति\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚪ इस चैट के लिए कोई डेली शेड्यूल सेट नहीं है।\n"
            "शुरू करने के लिए /setdaily HH:MM भेजें।"
        )
    else:
        status_lbl = "🟢 चालू (Active)" if s.get("enabled", True) else "🔴 बंद (Stopped)"
        msg = (
            "📅 डेली 30Q स्पेशल टेस्ट स्थिति\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{status_lbl}\n"
            f"🆔 चैट ID: {s['chat_id']}\n"
            f"⏰ समय: {s['time']} IST\n"
            f"📅 अगला सेट: सेट {int(s.get('next_set', 1)):02d} / {total_sets}\n"
            "🔔 5-मिनट पहले क्लास संदेश: चालू"
        )
    await send_admin_private_msg(update, context, msg)

async def stopdaily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type in ["group", "supergroup"] and not await is_group_admin(chat, user.id):
        return

    schedules = load_daily_schedules()
    cid_str = str(chat.id)
    if cid_str in schedules:
        schedules[cid_str]["enabled"] = False
        save_daily_schedules(schedules)
        msg = (
            "🛑 इस ग्रुप/चैट के लिए डेली 30Q टेस्ट शेड्यूल बंद कर दिया गया है।\n"
            "(दुबारा चालू करने के लिए ग्रुप में /setdaily HH:MM लिखें।)"
        )
    else:
        msg = "ℹ️ इस चैट के लिए कोई सक्रिय डेली शेड्यूल नहीं मिला।"
    await send_admin_private_msg(update, context, msg)

async def setfree_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type in ["group", "supergroup"] and not await is_group_admin(chat, user.id):
        try:
            await update.message.delete()
        except Exception:
            pass
        return

    if chat.id == PAID_GROUP_CHAT_ID:
        await send_admin_private_msg(
            update,
            context,
            "⚠️ यह आपका मुख्य Paid ग्रुप (-1001986170095) है!\nFree 10Q डेमो केवल अपने Free ग्रुप में जाकर /setfree 19:00 से सेट करें।",
        )
        return

    args = context.args or []
    time_raw = args[0] if args else "19:00"
    parsed = parse_hhmm_ist(time_raw)
    if not parsed:
        await send_admin_private_msg(
            update,
            context,
            "⚠️ सही फॉर्मेट भेजें:\n/setfree HH:MM (उदाहरण: /setfree 19:00 या /setfree 19:00 1)",
        )
        return

    free_db = load_free_database()
    total_sets = max(1, len(free_db.get("free_promo", {}).get("Free_Demo", {}).get("sets", {})))
    schedules = load_free_schedules()
    cid_str = str(chat.id)
    prev = schedules.get(cid_str, {})

    set_num = int(prev.get("next_set", 1))
    if len(args) >= 2 and args[1].isdigit():
        requested = int(args[1])
        if 1 <= requested <= total_sets:
            set_num = requested

    schedules[cid_str] = {
        "chat_id": chat.id,
        "time": parsed[2],
        "next_set": set_num,
        "enabled": True,
        "last_run_date": "",
        "reminder_sent_date": "",
    }
    save_free_schedules(schedules)

    await send_admin_private_msg(
        update,
        context,
        "✅ Free 10Q प्रोमो टेस्ट सेट हो गया!\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Free ग्रुप ID: {chat.id}\n"
        f"⏰ समय: {parsed[2]} IST (45s / प्रश्न)\n"
        f"📅 अगला सेट: सेट {set_num:02d} / {total_sets}\n"
        "🖼️ समाप्ति पर: Top 5 स्कोर + Course & Book पोस्टर + WhatsApp बटन",
    )

async def freestatus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type in ["group", "supergroup"] and not await is_group_admin(chat, user.id):
        return

    free_db = load_free_database()
    total_sets = max(1, len(free_db.get("free_promo", {}).get("Free_Demo", {}).get("sets", {})))
    schedules = load_free_schedules()
    s = schedules.get(str(chat.id))
    if not s:
        msg = "📅 Free 10Q प्रोमो टेस्ट स्थिति:\n⚪ इस चैट के लिए कोई Free डेमो शेड्यूल नहीं है। (/setfree 19:00 भेजें)"
    else:
        status_lbl = "🟢 चालू (Active)" if s.get("enabled", True) else "🔴 बंद (Stopped)"
        msg = (
            "📅 Free 10Q प्रोमो टेस्ट स्थिति\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{status_lbl}\n"
            f"🆔 Free ग्रुप ID: {s['chat_id']}\n"
            f"⏰ समय: {s['time']} IST\n"
            f"📅 अगला सेट: सेट {int(s.get('next_set', 1)):02d} / {total_sets}"
        )
    await send_admin_private_msg(update, context, msg)

async def stopfree_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type in ["group", "supergroup"] and not await is_group_admin(chat, user.id):
        return

    schedules = load_free_schedules()
    cid_str = str(chat.id)
    if cid_str in schedules:
        schedules[cid_str]["enabled"] = False
        save_free_schedules(schedules)
        msg = "🛑 Free 10Q प्रोमो टेस्ट इस चैट के लिए बंद कर दिया गया है।"
    else:
        msg = "ℹ️ इस चैट के लिए कोई सक्रिय Free 10Q शेड्यूल नहीं मिला।"
    await send_admin_private_msg(update, context, msg)

async def _process_schedule_bucket(app, schedules: dict, save_fn, total_sets: int, session_type: str, group_key: str, reminder_fn, exclude_chat_id=None):
    if not schedules or total_sets == 0:
        return
    now_ist = datetime.now(IST)
    today_str = now_ist.strftime("%Y-%m-%d")
    active_sessions = app.bot_data.get("group_sessions", {})
    dirty = False

    for cid_str, sched in list(schedules.items()):
        if not sched.get("enabled", True):
            continue
        parsed = parse_hhmm_ist(sched.get("time", ""))
        if not parsed:
            continue
        hh, mm, _ = parsed
        target_chat_id = int(sched["chat_id"])
        if exclude_chat_id is not None and target_chat_id == exclude_chat_id:
            continue
        target_dt = now_ist.replace(hour=hh, minute=mm, second=0, microsecond=0)
        diff_sec = (target_dt - now_ist).total_seconds()

        if 240 <= diff_sec <= 305 and sched.get("reminder_sent_date") != today_str:
            sched["reminder_sent_date"] = today_str
            dirty = True
            save_fn(schedules)
            if target_chat_id not in active_sessions:
                try:
                    await app.bot.send_message(chat_id=target_chat_id, text=reminder_fn())
                except Exception as rem_err:
                    logger.error(f"{session_type} 5-min reminder failed for {target_chat_id}: {rem_err}")

        if -60 < diff_sec <= 0 and sched.get("last_run_date") != today_str:
            sched["last_run_date"] = today_str
            cur_set = int(sched.get("next_set", 1))
            if not (1 <= cur_set <= total_sets):
                cur_set = 1
            set_key = f"set_{cur_set}"
            if target_chat_id in active_sessions:
                dirty = True
                save_fn(schedules)
                logger.warning(f"Skipping {session_type} quiz in {target_chat_id}: another quiz is active.")
                continue
            sched["next_set"] = (cur_set % total_sets) + 1
            dirty = True
            save_fn(schedules)
            asyncio.create_task(
                start_group_quiz(
                    target_chat_id,
                    SimpleNamespace(first_name="Sagar Sir"),
                    session_type,
                    group_key,
                    set_key,
                    app,
                )
            )

    if dirty:
        save_fn(schedules)

async def daily_scheduler_tick(app):
    """Runs both Paid 30Q and Free 10Q Promo IST schedulers cleanly without cross-interference."""
    db = load_database()
    daily_sets = len(db.get("daily_mix", {}).get("Daily_Mix", {}).get("sets", {}))
    await _process_schedule_bucket(
        app,
        load_daily_schedules(),
        save_daily_schedules,
        daily_sets,
        "mix",
        "Daily_Mix",
        build_5min_reminder_text,
    )

    free_db = load_free_database()
    free_sets = len(free_db.get("free_promo", {}).get("Free_Demo", {}).get("sets", {}))
    await _process_schedule_bucket(
        app,
        load_free_schedules(),
        save_free_schedules,
        free_sets,
        "free",
        "Free_Demo",
        build_free_5min_reminder_text,
        exclude_chat_id=PAID_GROUP_CHAT_ID,
    )

async def daily_scheduler_loop(app):
    logger.info("Daily 30Q IST scheduler loop started.")
    while True:
        try:
            await daily_scheduler_tick(app)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Daily scheduler error: {e}")
        await asyncio.sleep(10)

async def post_init(app):
    old_task = app.bot_data.get("daily_scheduler_task")
    if old_task and not old_task.done():
        old_task.cancel()
    app.bot_data["daily_scheduler_task"] = asyncio.create_task(daily_scheduler_loop(app))

def start_dummy_health_server():
    """Starts a lightweight HTTP health-check server on $PORT for Render Free Web Services."""
    port_str = os.getenv("PORT")
    if not port_str:
        return
    try:
        import http.server
        import socketserver
        import threading

        port = int(port_str)
        class HealthHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Sagar Coaching Centre NMMS Bot is Running 24/7!\n")
            def log_message(self, format, *args):
                pass

        socketserver.TCPServer.allow_reuse_address = True
        httpd = socketserver.TCPServer(("0.0.0.0", port), HealthHandler)
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        print(f"🌐 Cloud Health-Check Web Server started on port {port}")
    except Exception as e:
        print(f"Health server info: {e}")

def main():
    start_dummy_health_server()
    print("🤖 Starting NMMS Group-Dedicated Quiz Bot...")
    
    while True:
        try:
            app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

            # Handlers
            app.add_handler(CommandHandler(["start", "startquiz"], start_command))
            app.add_handler(CommandHandler(["quiz", "nmms"], quiz_command))
            app.add_handler(CommandHandler("stop", stop_command))
            app.add_handler(CommandHandler("stats", stats_command))
            app.add_handler(CommandHandler("score", stats_command))
            app.add_handler(CommandHandler("leaderboard", leaderboard_command))
            app.add_handler(CommandHandler("help", help_command))
            app.add_handler(CommandHandler("setdaily", setdaily_command))
            app.add_handler(CommandHandler("dailystatus", dailystatus_command))
            app.add_handler(CommandHandler("stopdaily", stopdaily_command))
            app.add_handler(CommandHandler("setfree", setfree_command))
            app.add_handler(CommandHandler("freestatus", freestatus_command))
            app.add_handler(CommandHandler("stopfree", stopfree_command))
            app.add_handler(CallbackQueryHandler(button_callback))
            app.add_handler(PollAnswerHandler(receive_quiz_answer))

            print("✅ NMMS Quiz Bot is online and listening!")
            app.run_polling(bootstrap_retries=-1)
        except KeyboardInterrupt:
            print("🛑 Stopping bot by user request...")
            break
        except Exception as e:
            print(f"⚠️ Bot polling encountered exception: {e}. Auto-restarting polling in 5s...")
            import time
            time.sleep(5)

if __name__ == "__main__":
    main()

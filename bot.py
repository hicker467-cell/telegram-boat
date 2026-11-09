import os
import json
import random
import asyncio
import time
import logging
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
from result_card import generate_result_card, generate_topper_card, clean_test_title

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

def load_database():
    if DATABASE_FILE.exists():
        with open(DATABASE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"full_mocks": {}, "subjects": {}}

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
    original_options = q["options"]
    correct_text = original_options[q["correct_option_id"]]
    indexed = list(enumerate(original_options))
    random.shuffle(indexed)
    new_options = [opt for _, opt in indexed]
    new_correct_id = new_options.index(correct_text)
    return {
        "question": q["question"],
        "options": new_options,
        "correct_option_id": new_correct_id,
        "explanation": q.get("explanation", ""),
        "subject": q.get("subject", "")
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
        if arg.startswith("mock"):
            mock_type, set_key = parse_compound(arg, "mock")
            if mock_type and set_key:
                await start_group_quiz(chat.id, user, "mock", mock_type, set_key, context)
                return
        elif arg.startswith("subj"):
            subject_key, set_key = parse_compound(arg, "subj")
            if subject_key and set_key:
                await start_group_quiz(chat.id, user, "subject", subject_key, set_key, context)
                return

    if is_group:
        welcome_text = (
            "🏛️ SAGAR COACHING CENTRE\n"
            "🎓 NMMS लाइव टेस्ट पोर्टल\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✍️ पुस्तक लेखक: सागर सर (NMMS एक्सपर्ट)\n"
            "⏱️ प्रत्येक प्रश्न: 60 सेकंड\n"
            "🏆 टेस्ट समाप्ति पर टॉप 20 छात्रों की मेरिट लिस्ट जारी होगी।\n\n"
            "👇 नीचे से टेस्ट सेट चुनें:"
        )
    else:
        welcome_text = (
            "🏛️ SAGAR COACHING CENTRE\n"
            "🎓 NMMS टेस्ट कंट्रोल पैनल\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✍️ पुस्तक लेखक: सागर सर (NMMS एक्सपर्ट)\n"
            "📞 संपर्क / WhatsApp: +91 91101 13671\n\n"
            "यहाँ से सेट चुनें और सीधे कोचिंग ग्रुप में शुरू करें:\n"
            "• 🧠 MAT: 90 प्रश्न (60s / प्रश्न)\n"
            "• 📚 SAT: 90 प्रश्न (35 वि. + 35 सा.वि. + 20 गणित) (60s / प्रश्न)\n"
            "• 🔬 विषयवार अभ्यास: 50 प्रश्न प्रति सेट (60s / प्रश्न)\n\n"
            "👇 नीचे से टेस्ट चुनें:"
        )

    keyboard = [
        # Full 90Q Mocks
        [InlineKeyboardButton("🧠 MAT फुल मॉक टेस्ट (90 प्रश्न | 60s)", callback_data="menu_mock_MAT")],
        [InlineKeyboardButton("📚 SAT फुल मॉक टेस्ट (90 प्रश्न | 60s)", callback_data="menu_mock_SAT")],
        # Subject wise practice
        [
            InlineKeyboardButton("🔬 विज्ञान (50 Q)", callback_data="subj_Science"),
            InlineKeyboardButton("🌍 सा. विज्ञान (50 Q)", callback_data="subj_Social_Science")
        ],
        [
            InlineKeyboardButton("🧠 तर्कशक्ति / MAT (50 Q)", callback_data="subj_Mental_Ability"),
            InlineKeyboardButton("📐 गणित (50 Q)", callback_data="subj_Mathematics")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# Show Mock Sets
async def show_mock_sets(query, mock_type: str):
    db = load_database()
    mocks = db.get("full_mocks", {})
    mock_data = mocks.get(mock_type)
    if not mock_data:
        await query.message.reply_text("⚠️ मॉक टेस्ट नहीं मिला!")
        return

    name = mock_data["name"]
    sets = mock_data.get("sets", {})
    chat = query.message.chat
    is_group = chat.type in ["group", "supergroup"]

    pattern_info = "90 प्रश्न (तर्कशक्ति)" if mock_type == "MAT" else "90 प्रश्न (35 वि. + 35 सा.वि. + 20 गणित)"

    text = (
        "🏛️ SAGAR COACHING CENTRE\n"
        f"📝 {name}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ समय: 60s / प्रश्न | 📋 पैटर्न: {pattern_info}\n\n"
        "👇 जो सेट शुरू करना है, उसे चुनें:"
    )

    keyboard = []
    for set_key, set_info in sets.items():
        if is_group:
            # If directly in group, start right away
            keyboard.append([
                InlineKeyboardButton(f"▶️ {set_info['name']} शुरू करें", callback_data=f"startmock__{mock_type}__{set_key}")
            ])
        else:
            # In DM: show set button which leads to "Start in Group"
            keyboard.append([
                InlineKeyboardButton(f"📝 {set_info['name']}", callback_data=f"setselect_mock__{mock_type}__{set_key}")
            ])

    keyboard.append([InlineKeyboardButton("🔙 मुख्य मेनू", callback_data="btn_back_subjects")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# Final Selection in DM: ONLY shows "Start in Group"
async def show_group_starter_card(query, test_type: str, group_key: str, set_key: str):
    db = load_database()
    if test_type == "mock":
        set_info = db.get("full_mocks", {}).get(group_key, {}).get("sets", {}).get(set_key)
        deep_param = f"mock__{group_key}__{set_key}"
    else:
        set_info = db.get("subjects", {}).get(group_key, {}).get("sets", {}).get(set_key)
        deep_param = f"subj__{group_key}__{set_key}"

    if not set_info:
        await query.message.reply_text("⚠️ सेट नहीं मिला!")
        return

    q_count = len(set_info.get("questions", []))
    text = (
        "🏛️ SAGAR COACHING CENTRE\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 {set_info['name']}\n"
        f"❓ कुल प्रश्न: {q_count} | ⏱️ समय: 60s / प्रश्न\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👉 नीचे बटन दबाकर कोचिंग ग्रुप चुनें और टेस्ट शुरू करें:"
    )

    group_url = f"https://t.me/{BOT_USERNAME}?startgroup={deep_param}"

    keyboard = [
        [InlineKeyboardButton("👥 Start in Group (ग्रुप चुनें और शुरू करें)", url=group_url)],
        [InlineKeyboardButton("🔙 दूसरा सेट चुनें", callback_data=f"menu_mock_{group_key}" if test_type == "mock" else f"subj_{group_key}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# Subject practice sets
async def show_subject_sets(query, subject_key: str):
    db = load_database()
    subjects = db.get("subjects", {})
    subj_data = subjects.get(subject_key)
    if not subj_data:
        await query.message.reply_text("⚠️ विषय नहीं मिला!")
        return

    subj_name = subj_data["name"]
    sets = subj_data.get("sets", {})
    chat = query.message.chat
    is_group = chat.type in ["group", "supergroup"]

    text = (
        "🏛️ SAGAR COACHING CENTRE\n"
        f"📝 {subj_name}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⏱️ समय: 60s / प्रश्न (50 प्रश्न प्रति सेट)\n\n"
        "👇 जो सेट शुरू करना है, उसे चुनें:"
    )

    keyboard = []
    set_buttons = []
    for set_key, set_info in sets.items():
        short_label = set_info['name'].split(" - ")[0]
        if is_group:
            cb = f"startsubj__{subject_key}__{set_key}"
        else:
            cb = f"setselect_subj__{subject_key}__{set_key}"
            
        set_buttons.append(
            InlineKeyboardButton(f"📝 {short_label}", callback_data=cb)
        )

    for i in range(0, len(set_buttons), 2):
        keyboard.append(set_buttons[i:i+2])

    keyboard.append([InlineKeyboardButton("🔙 मुख्य मेनू", callback_data="btn_back_subjects")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# Start Group Quiz immediately
async def start_group_quiz(chat_id: int, user, session_type: str, group_key: str, set_key: str, context: ContextTypes.DEFAULT_TYPE):
    db = load_database()
    if session_type == "mock":
        group_data = db.get("full_mocks", {}).get(group_key, {})
    else:
        group_data = db.get("subjects", {}).get(group_key, {})

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

    timer_seconds = 5

    session = {
        "chat_id": chat_id,
        "is_group": True,
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
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🏛️ SAGAR COACHING CENTRE\n"
            "🎓 NMMS छात्रवृत्ति महा-अभ्यास\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 टेस्ट: {display_title}\n"
            f"❓ कुल प्रश्न: {len(shuffled_questions)} | ⏱️ समय: 60s प्रति प्रश्न\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ पहला प्रश्न आ रहा है, सभी छात्र तैयार रहें!"
        )
    )

    await asyncio.sleep(2.0)
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
    # Fast test mode: Telegram API enforces open_period between 5 and 600 seconds
    timer = 5

    q_title = f"Q{idx + 1}/{total}: {q['question']}"
    if len(q_title) > 300:
        q_title = q_title[:297] + "..."

    clean_options = [opt[:100] if len(opt) > 100 else opt for opt in q["options"]]

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

    # Send Image Result Card if there were scores
    if scores:
        try:
            total_questions = session.get("total", attempted)

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
                "🏆 NMMS Official Merit Card (Top 20)\n"
                "🏛️ Sagar Coaching Centre, Bhagwanpur (Supaul)\n"
                "📖 NMMS Special Guide Book by Sagar Sir (7+ Years Exp.)\n"
                "📞 +91 91101 13671\n"
                "📲 WhatsApp Status पर अवश्य शेयर करें!"
            )
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=image_buf,
                caption=caption
            )

            # Send Personal Topper Certificate Cards for Top 3
            topper_limit = min(3, len(sorted_players))
            for rank_idx in range(topper_limit):
                topper = sorted_players[rank_idx]
                r_num = rank_idx + 1
                try:
                    topper_buf = generate_topper_card(
                        student=topper,
                        rank=r_num,
                        test_name=session["test_name"],
                        total_q=total_questions,
                        attempted_q=attempted,
                        total_participants=len(sorted_players)
                    )
                    medals_label = ["🥇 1st Rank Topper", "🥈 2nd Rank Topper", "🥉 3rd Rank Topper"][rank_idx]
                    topper_name = str(topper.get("name", "Student")).replace('*', '').replace('_', '').strip()
                    topper_caption = (
                        f"🌟 {medals_label}: {topper_name}\n"
                        f"🎯 Score: {topper['score']}/{attempted} | Accuracy: {topper.get('accuracy', 0)}%\n"
                        "🏛️ Sagar Coaching Centre, Bhagwanpur\n"
                        "📲 Topper Certificate: WhatsApp Status पर ज़रूर शेयर करें!"
                    )
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=topper_buf,
                        caption=topper_caption
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

    update_user_score(user=user, is_correct=is_correct)

    session = context.bot_data.get("group_sessions", {}).get(chat_id)
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

    if data.startswith("menu_mock_"):
        mock_type = data.replace("menu_mock_", "")
        await show_mock_sets(query, mock_type)
    elif data.startswith("subj_"):
        subject_key = data.replace("subj_", "")
        await show_subject_sets(query, subject_key)
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
            await start_group_quiz(chat.id, user, "subject", subject_key, set_key, context)
    elif data == "btn_back_subjects":
        await start_command(update, context)
    elif data == "btn_stats":
        await stats_command(update, context)
    elif data == "btn_leaderboard":
        await leaderboard_command(update, context)
    elif data == "btn_help":
        await help_command(update, context)

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
            app = ApplicationBuilder().token(BOT_TOKEN).build()

            # Handlers
            app.add_handler(CommandHandler(["start", "startquiz"], start_command))
            app.add_handler(CommandHandler(["quiz", "nmms"], quiz_command))
            app.add_handler(CommandHandler("stop", stop_command))
            app.add_handler(CommandHandler("stats", stats_command))
            app.add_handler(CommandHandler("score", stats_command))
            app.add_handler(CommandHandler("leaderboard", leaderboard_command))
            app.add_handler(CommandHandler("help", help_command))
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

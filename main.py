# c:\Users\Azamat\Documents\telegram bot\main.py
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from datetime import time, datetime
import pytz

from config import BOT_TOKEN, DEFAULT_NOTIFY_MODE
from storage import get_user, save_user, get_all_users
from timetable import get_faculties, get_timetable

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states for setup
FACULTY, COURSE, SPECIALIZATION, GROUP, NOTIFY_TIME, CONFIRMATION = range(6)

# Helper function to create button layouts
def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu

# --- Timetable and Notification Logic ---

def get_day_of_week(day: str) -> str:
    """Gets the English day of the week for 'today' or 'tomorrow'."""
    tz = pytz.timezone('Asia/Tashkent')
    if day == "today":
        return datetime.now(tz).strftime('%A')
    elif day == "tomorrow":
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        today_index = datetime.now(tz).weekday()
        return days[(today_index + 1) % 7]
    return day

async def send_timetable_for_day(chat_id: int, user: dict, day: str, context: ContextTypes.DEFAULT_TYPE):
    """Fetches and sends the timetable for a specific day."""
    if not all(k in user for k in ["faculty_id", "group"]):
        await context.bot.send_message(chat_id=chat_id, text="Fakultet yoki guruh ma'lumotlari topilmadi. /start orqali qayta sozlang.")
        return

    full_timetable = get_timetable(user["faculty_id"], user["group"])
    day_name = get_day_of_week(day)

    if not full_timetable or day_name not in full_timetable:
        await context.bot.send_message(chat_id=chat_id, text=f"*{day_name}* uchun dars jadvali topilmadi yoki bu kunga darslar yo'q.", parse_mode="Markdown")
        return

    lessons = full_timetable[day_name]
    message = f"📅 *{user['group']}* guruhi uchun *{day_name}* dars jadvali:\n\n"
    for lesson in lessons:
        message += f" cặp (para): {lesson['time']}\n"
        message += f"📚 *Fan:* {lesson['subject']}\n"
        message += f"🧑‍🏫 *O'qituvchi:* {lesson['lecturer']}\n"
        message += f"🚪 *Xona:* {lesson['room']}\n"
        message += "--------------------\n"
    
    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")

async def send_weekly_timetable(chat_id: int, user: dict, context: ContextTypes.DEFAULT_TYPE):
    """Fetches and sends the timetable for the whole week."""
    if not all(k in user for k in ["faculty_id", "group"]):
        await context.bot.send_message(chat_id=chat_id, text="Fakultet yoki guruh ma'lumotlari topilmadi. /start orqali qayta sozlang.")
        return

    full_timetable = get_timetable(user["faculty_id"], user["group"])
    if not full_timetable:
        await context.bot.send_message(chat_id=chat_id, text="Haftalik dars jadvali topilmadi.")
        return

    message = f"📅 *{user['group']}* guruhi uchun haftalik dars jadvali:\n\n"
    for day_name, lessons in sorted(full_timetable.items(), key=lambda item: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"].index(item[0])):
        message += f"--- *{day_name.upper()}* ---\n"
        for lesson in lessons:
            message += f" cặp: {lesson['time']}, {lesson['subject']} ({lesson['room']})\n"
        message += "\n"
    
    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")

# --- Main Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation. Checks if user is already registered."""
    user = get_user(update.message.from_user.id)
    if user and all(k in user for k in ["faculty", "group", "notify_time", "faculty_id", "course", "specialization"]):
        await update.message.reply_text(
            f"Assalomu alaykum! 😊 Siz ro'yxatdan o'tgansiz.\n"
            f"Fakultet: {user['faculty']}\n"
            f"Kurs: {user['course']}-kurs\n"
            f"Yo'nalish: {user['specialization']}\n"
            f"Guruh: {user['group']}\n"
            f"Xabar vaqti: {user['notify_time']}\n\n"
            "Jadvalni ko'rish uchun: /today, /tomorrow, /week\n"
            "Sozlamalarni o'zgartirish uchun /start buyrug'ini qayta bosing."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Assalomu alaykum! 👋\nMen GulDU talabalari uchun dars jadvalini yuboradigan botman.\n"
        "Keling, ma'lumotlaringizni birma-bir kiritamiz."
    )
    
    faculties = get_faculties()
    if not faculties:
        await update.message.reply_text("Xatolik: Fakultetlarni olib bo'lmadi. Iltimos, birozdan so'ng qayta urinib ko'ring.")
        return ConversationHandler.END
    
    context.user_data["faculties"] = faculties
    faculty_names = list(faculties.keys())
    
    reply_markup = ReplyKeyboardMarkup(build_menu(faculty_names, n_cols=1), one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Iltimos, fakultetingizni tanlang 👇", reply_markup=reply_markup)
    return FACULTY

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.message.from_user.id)
    if user:
        await send_timetable_for_day(update.message.chat_id, user, "today", context)
    else:
        await update.message.reply_text("Siz ro'yxatdan o'tmagansiz. /start buyrug'ini bosing.")

async def tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.message.from_user.id)
    if user:
        await send_timetable_for_day(update.message.chat_id, user, "tomorrow", context)
    else:
        await update.message.reply_text("Siz ro'yxatdan o'tmagansiz. /start buyrug'ini bosing.")

async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.message.from_user.id)
    if user:
        await send_weekly_timetable(update.message.chat_id, user, context)
    else:
        await update.message.reply_text("Siz ro'yxatdan o'tmagansiz. /start buyrug'ini bosing.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Jarayon bekor qilindi.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

# --- Setup Conversation Handlers ---

async def faculty_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    faculty_name = update.message.text
    faculties = context.user_data.get("faculties")
    
    if not faculties or faculty_name not in faculties:
        await update.message.reply_text("Iltimos, fakultetni quyidagi tugmalardan birini bosib tanlang.")
        return FACULTY

    context.user_data["faculty_name"] = faculty_name
    context.user_data["faculty_id"] = faculties[faculty_name]
    
    course_buttons = ["1-kurs", "2-kurs", "3-kurs", "4-kurs"]
    reply_markup = ReplyKeyboardMarkup(build_menu(course_buttons, n_cols=2), one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Kursingizni tanlang 👇", reply_markup=reply_markup)
    return COURSE

async def course_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    course_text = update.message.text
    if not course_text.endswith("-kurs"):
        await update.message.reply_text("Iltimos, kursni tugmalar yordamida tanlang.")
        return COURSE
        
    context.user_data["course"] = course_text[0]
    await update.message.reply_text("Endi yo'nalishingiz nomini kiriting (masalan, 'Matematika' yoki 'Kompyuter ilmlari'):", reply_markup=ReplyKeyboardRemove())
    return SPECIALIZATION

async def specialization_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["specialization"] = update.message.text
    await update.message.reply_text("Guruhingiz nomini kiriting (masalan, 101-23):")
    return GROUP

async def group_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["group"] = update.message.text
    await update.message.reply_text(
        "Har kuni soat nechida dars jadvalini yuborishimni xohlaysiz? ⏰\n"
        "Format: HH:MM (masalan: 07:00 yoki 21:30)",
        reply_markup=ReplyKeyboardRemove()
    )
    return NOTIFY_TIME

async def notify_time_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    time_text = update.message.text
    try:
        time.fromisoformat(time_text)
        context.user_data["notify_time"] = time_text
        
        ud = context.user_data
        await update.message.reply_text(
            f"Ma'lumotlaringizni tasdiqlang:\n\n"
            f"🎓 Fakultet: {ud['faculty_name']}\n"
            f"👨‍🎓 Kurs: {ud['course']}-kurs\n"
            f" направления (Yo'nalish): {ud['specialization']}\n"
            f"👥 Guruh: {ud['group']}\n"
            f"⏰ Xabar vaqti: {ud['notify_time']}\n\n"
            "Agar hammasi to'g'ri bo'lsa, 'Tasdiqlash' tugmasini bosing.",
            reply_markup=ReplyKeyboardMarkup([["Tasdiqlash ✅", "Qaytadan boshlash 🔁"]], one_time_keyboard=True, resize_keyboard=True),
        )
        return CONFIRMATION
    except ValueError:
        await update.message.reply_text("Vaqtni noto'g'ri formatda kiritdingiz. Iltimos, HH:MM formatida kiriting (masalan: 08:00).")
        return NOTIFY_TIME

async def confirmation_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "Qaytadan boshlash 🔁":
        context.user_data.clear()
        return await start(update, context)

    if update.message.text != "Tasdiqlash ✅":
        await update.message.reply_text("Iltimos, tugmalardan birini tanlang.")
        return CONFIRMATION

    user_id = update.message.from_user.id
    ud = context.user_data
    user_data = {
        "user_id": user_id,
        "faculty": ud["faculty_name"],
        "faculty_id": ud["faculty_id"],
        "course": ud["course"],
        "specialization": ud["specialization"],
        "group": ud["group"],
        "notify_time": ud["notify_time"],
        "notify_mode": DEFAULT_NOTIFY_MODE,
    }
    save_user(user_id, user_data)
    
    user_time = time.fromisoformat(user_data['notify_time'])
    jobs = context.job_queue.get_jobs_by_name(str(user_id))
    for job in jobs:
        job.schedule_removal()
    context.job_queue.run_daily(daily_timetable_job, user_time, user_id=user_id, name=str(user_id))

    await update.message.reply_text(
        "Hammasi sozlandi! 🎉\nJadvalni ko'rish uchun /today, /tomorrow, /week buyruqlaridan foydalaning.",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data.clear()
    return ConversationHandler.END

# --- Daily Job ---

async def daily_timetable_job(context: ContextTypes.DEFAULT_TYPE):
    """Job callback for sending daily timetables."""
    user_id = context.job.user_id
    user = get_user(user_id)
    if user:
        await send_timetable_for_day(user_id, user, user.get("notify_mode", "tomorrow"), context)

# --- Main Application Setup ---

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    setup_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            FACULTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, faculty_step)],
            COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, course_step)],
            SPECIALIZATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, specialization_step)],
            GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, group_step)],
            NOTIFY_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, notify_time_step)],
            CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmation_step)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        # Allow re-entering the conversation via /start
        allow_reentry=True
    )

    application.add_handler(setup_conv_handler)
    application.add_handler(CommandHandler("today", today))
    application.add_handler(CommandHandler("tomorrow", tomorrow))
    application.add_handler(CommandHandler("week", week))

    # Schedule jobs for existing users on startup
    for user in get_all_users():
        if "notify_time" in user and "user_id" in user:
            try:
                user_time = time.fromisoformat(user['notify_time'])
                application.job_queue.run_daily(daily_timetable_job, user_time, user_id=user['user_id'], name=str(user['user_id']))
            except (ValueError, KeyError):
                logger.error(f"Could not schedule job for user {user.get('user_id')}.")

    application.run_polling()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
import json, os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

TOKEN = "8645831243:AAHfOmOi8UHsAfGhWjpJONVzAAt8mPmSUDM"
DATA_FILE = "tasks.json"
USERS_FILE = "users.json"
WEBAPP_URL = "https://app.uniteagency.uz"

(NAME, CLIENT, DESCRIPTION, DEADLINE, MATERIALS, PRIORITY) = range(6)

# ── Data ──────────────────────────────────────────────────────────────────────
def load_tasks():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return []

def save_tasks(tasks):
    with open(DATA_FILE, "w") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def get_task(task_id):
    return next((t for t in load_tasks() if t["id"] == task_id), None)

def next_id():
    tasks = load_tasks()
    return max((t["id"] for t in tasks), default=0) + 1

# ── Users ─────────────────────────────────────────────────────────────────────
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            return json.load(f)
    return []

def save_user(chat_id, username):
    users = load_users()
    ids = [u["chat_id"] for u in users]
    if chat_id not in ids:
        users.append({"chat_id": chat_id, "username": username})
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

async def notify_all(bot, text, exclude_chat_id=None):
    users = load_users()
    for u in users:
        if u["chat_id"] != exclude_chat_id:
            try:
                await bot.send_message(
                    chat_id=u["chat_id"],
                    text=text,
                    parse_mode="Markdown"
                )
            except Exception:
                pass

# ── Keyboards ─────────────────────────────────────────────────────────────────
def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖥  Открыть приложение", web_app=WebAppInfo(url=WEBAPP_URL))],
    ])

def task_detail_kb(task_id, is_done=False):
    rows = []
    if not is_done:
        rows.append([InlineKeyboardButton("✅  Готово", callback_data=f"done_{task_id}")])
    rows.append([InlineKeyboardButton("🗑  Удалить", callback_data=f"delete_{task_id}")])
    rows.append([InlineKeyboardButton("◀️  К списку", callback_data="all_tasks")])
    return InlineKeyboardMarkup(rows)

def priority_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴  Срочно", callback_data="priority_срочно"),
         InlineKeyboardButton("🟡  Обычно", callback_data="priority_обычно")],
    ])

def task_list_kb(tasks):
    buttons = []
    for t in tasks:
        icon = "🔴" if t.get("priority") == "срочно" else "🟡"
        done = "✅ " if t.get("done") else ""
        label = f"{done}{icon} {t['name']} — {t['client']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"task_{t['id']}")])
    buttons.append([InlineKeyboardButton("◀️  Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

# ── Format ────────────────────────────────────────────────────────────────────
def format_task(task):
    icon = "🔴" if task.get("priority") == "срочно" else "🟡"
    status = "✅ Выполнено" if task.get("done") else "🔄 В работе"
    text = (
        f"*{task['name']}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏢 *Клиент:* {task['client']}\n"
        f"📝 *Описание:*\n{task['description']}\n\n"
        f"📅 *Дедлайн:* `{task['deadline']}`\n"
        f"{icon} *Приоритет:* {task.get('priority', 'обычно')}\n"
        f"👤 *От:* @{task.get('from_username', '?')}\n"
        f"📊 *Статус:* {status}\n"
    )
    if task.get("materials"):
        text += f"🔗 *Материалы:* {task['materials']}\n"
    return text

# ── Handlers ──────────────────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    username = user.username or user.first_name
    save_user(chat_id, username)
    await update.message.reply_text(
        f"👋 Привет, *{user.first_name}*!\n\nТы добавлен в список уведомлений.\nНажми кнопку ниже чтобы открыть приложение 👇",
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )

async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "main_menu":
        await q.edit_message_text(
            "👋 *Unite TZ Bot*\n\nНажми кнопку ниже чтобы открыть приложение 👇",
            parse_mode="Markdown",
            reply_markup=main_menu_kb()
        )

    elif data == "new_tz":
        ctx.user_data.clear()
        await q.edit_message_text("📝 *Новое ТЗ*\n\nШаг 1/6 — Введи название задачи:", parse_mode="Markdown")
        return NAME

    elif data in ("all_tasks", "my_tasks"):
        tasks = [t for t in load_tasks() if not t.get("done")]
        if not tasks:
            await q.edit_message_text("📋 Нет активных задач.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]]))
        else:
            await q.edit_message_text("📋 *Все активные задачи:*", parse_mode="Markdown", reply_markup=task_list_kb(tasks))

    elif data.startswith("task_"):
        task_id = int(data.split("_")[1])
        task = get_task(task_id)
        if task:
            await q.edit_message_text(format_task(task), parse_mode="Markdown",
                reply_markup=task_detail_kb(task_id, task.get("done")),
                disable_web_page_preview=True)

    elif data.startswith("done_"):
        task_id = int(data.split("_")[1])
        tasks = load_tasks()
        task_name = ""
        task_client = ""
        for t in tasks:
            if t["id"] == task_id:
                t["done"] = True
                task_name = t["name"]
                task_client = t["client"]
                break
        save_tasks(tasks)

        # Уведомление всем о завершении
        notify_text = (
            f"✅ *ТЗ завершено!*\n\n"
            f"📋 *{task_name}*\n"
            f"🏢 Клиент: {task_client}\n"
            f"👤 Выполнил: @{q.from_user.username or q.from_user.first_name}"
        )
        await notify_all(ctx.bot, notify_text, exclude_chat_id=q.message.chat_id)

        await q.edit_message_text(
            f"✅ *Задача завершена!*\n\n*{task_name}* отмечена как выполненная.\nВсе участники получили уведомление.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ К списку", callback_data="all_tasks")]]))

    elif data.startswith("delete_"):
        task_id = int(data.split("_")[1])
        tasks = [t for t in load_tasks() if t["id"] != task_id]
        save_tasks(tasks)
        await q.edit_message_text("🗑 Удалено.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ К списку", callback_data="all_tasks")]]))

    elif data.startswith("priority_"):
        priority = data.split("_")[1]
        task = {
            "id": next_id(),
            "name": ctx.user_data["name"],
            "client": ctx.user_data["client"],
            "description": ctx.user_data["description"],
            "deadline": ctx.user_data["deadline"],
            "materials": ctx.user_data.get("materials", ""),
            "priority": priority,
            "done": False,
            "from_username": q.from_user.username or q.from_user.first_name,
            "created_at": datetime.now().isoformat(),
        }
        tasks = load_tasks()
        tasks.append(task)
        save_tasks(tasks)

        # Напоминание за 3 часа
        try:
            deadline_dt = datetime.strptime(task["deadline"], "%d.%m.%Y %H:%M")
            delay = (deadline_dt - timedelta(hours=3) - datetime.now()).total_seconds()
            if delay > 0:
                ctx.application.job_queue.run_once(
                    send_reminder, when=delay,
                    data={"task": task},
                    name=f"reminder_{task['id']}"
                )
        except Exception:
            pass

        # Уведомление всем о новом ТЗ
        icon = "🔴" if priority == "срочно" else "🟡"
        notify_text = (
            f"📋 *Новое ТЗ добавлено!*\n\n"
            f"*{task['name']}*\n"
            f"🏢 Клиент: {task['client']}\n"
            f"📅 Дедлайн: {task['deadline']}\n"
            f"{icon} Приоритет: {priority}\n"
            f"👤 От: @{task['from_username']}"
        )
        await notify_all(ctx.bot, notify_text, exclude_chat_id=q.message.chat_id)

        await q.edit_message_text(
            f"✅ *ТЗ добавлено!*\n\n*{task['name']}*\nВсе участники получили уведомление.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🖥 Открыть приложение", web_app=WebAppInfo(url=WEBAPP_URL))]])
        )
        ctx.user_data.clear()
        return ConversationHandler.END

# ── Conversation ──────────────────────────────────────────────────────────────
async def get_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["name"] = update.message.text
    await update.message.reply_text("Шаг 2/6 — 🏢 Название клиента / бренда:")
    return CLIENT

async def get_client(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["client"] = update.message.text
    await update.message.reply_text("Шаг 3/6 — 📝 Описание задачи:")
    return DESCRIPTION

async def get_description(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["description"] = update.message.text
    await update.message.reply_text("Шаг 4/6 — 📅 Дедлайн (формат: 27.04.2026 18:00):")
    return DEADLINE

async def get_deadline(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        datetime.strptime(update.message.text, "%d.%m.%Y %H:%M")
        ctx.user_data["deadline"] = update.message.text
        await update.message.reply_text("Шаг 5/6 — 🔗 Ссылка на материалы (или напиши «нет»):")
        return MATERIALS
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Пример: 27.04.2026 18:00")
        return DEADLINE

async def get_materials(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    ctx.user_data["materials"] = "" if text.lower() == "нет" else text
    await update.message.reply_text("Шаг 6/6 — ⚡ Приоритет:", reply_markup=priority_kb())
    return PRIORITY

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("❌ Отменено.", reply_markup=main_menu_kb())
    return ConversationHandler.END

# ── Reminder ──────────────────────────────────────────────────────────────────
async def send_reminder(ctx: ContextTypes.DEFAULT_TYPE):
    task = ctx.job.data["task"]
    icon = "🔴" if task.get("priority") == "срочно" else "🟡"
    text = (
        f"⏰ *Дедлайн через 3 часа!*\n\n"
        f"*{task['name']}*\n"
        f"🏢 {task['client']}\n"
        f"📅 `{task['deadline']}`\n"
        f"{icon} {task.get('priority')}\n"
        f"👤 @{task.get('from_username', '?')}"
    )
    await notify_all(ctx.bot, text)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button, pattern="^new_tz$")],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            CLIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_client)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
            DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_deadline)],
            MATERIALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_materials)],
            PRIORITY: [CallbackQueryHandler(button, pattern="^priority_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(button))
    print("🤖 Unite TZ Bot запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

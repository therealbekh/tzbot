#!/usr/bin/env python3
import json
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

TOKEN = "8645831243:AAHfOmOi8UHsAfGhWjpJONVzAAt8mPmSUDM"
DATA_FILE = "tasks.json"

# Conversation states
(NAME, CLIENT, DESCRIPTION, DEADLINE, MATERIALS, PRIORITY) = range(6)

# ── Data helpers ──────────────────────────────────────────────────────────────

def load_tasks():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return []

def save_tasks(tasks):
    with open(DATA_FILE, "w") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def get_task(task_id):
    tasks = load_tasks()
    return next((t for t in tasks if t["id"] == task_id), None)

def next_id():
    tasks = load_tasks()
    return max((t["id"] for t in tasks), default=0) + 1

# ── Keyboards ─────────────────────────────────────────────────────────────────

def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕  Новое ТЗ", callback_data="new_tz")],
        [InlineKeyboardButton("📋  Мои задачи", callback_data="my_tasks"),
         InlineKeyboardButton("⚡  Срочные", callback_data="urgent_tasks")],
        [InlineKeyboardButton("✅  Выполненные", callback_data="done_tasks")],
    ])

def task_list_kb(tasks, prefix="task"):
    buttons = []
    for t in tasks:
        icon = "🔴" if t.get("priority") == "срочно" else "🟡"
        label = f"{icon} {t['name']} — {t['client']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"{prefix}_{t['id']}")])
    buttons.append([InlineKeyboardButton("◀️  Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

def task_detail_kb(task_id, is_done=False):
    rows = []
    if not is_done:
        rows.append([InlineKeyboardButton("✅  Готово", callback_data=f"done_{task_id}")])
    rows.append([InlineKeyboardButton("🗑  Удалить", callback_data=f"delete_{task_id}")])
    rows.append([InlineKeyboardButton("◀️  К списку", callback_data="my_tasks")])
    return InlineKeyboardMarkup(rows)

def priority_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴  Срочно", callback_data="priority_срочно"),
         InlineKeyboardButton("🟡  Обычно", callback_data="priority_обычно")],
    ])

# ── Formatters ────────────────────────────────────────────────────────────────

def format_task(task):
    priority_icon = "🔴" if task.get("priority") == "срочно" else "🟡"
    status = "✅ Выполнено" if task.get("done") else "🔄 В работе"
    text = (
        f"*{task['name']}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏢 *Клиент:* {task['client']}\n"
        f"📝 *Описание:*\n{task['description']}\n\n"
        f"📅 *Дедлайн:* `{task['deadline']}`\n"
        f"{priority_icon} *Приоритет:* {task.get('priority', 'обычно')}\n"
        f"👤 *От:* @{task.get('from_username', '?')}\n"
        f"📊 *Статус:* {status}\n"
    )
    if task.get("materials"):
        text += f"🔗 *Материалы:* {task['materials']}\n"
    return text

# ── Handlers ──────────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Unite TZ Bot*\n\nУправляй техзаданиями удобно.",
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )

async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "main_menu":
        await q.edit_message_text(
            "👋 *Unite TZ Bot*\n\nУправляй техзаданиями удобно.",
            parse_mode="Markdown",
            reply_markup=main_menu_kb()
        )

    elif data == "new_tz":
        ctx.user_data.clear()
        ctx.user_data["new_tz"] = True
        await q.edit_message_text("📝 *Новое ТЗ*\n\nШаг 1/6 — Введи название задачи:", parse_mode="Markdown")
        return NAME

    elif data == "my_tasks":
        tasks = [t for t in load_tasks() if not t.get("done")]
        if not tasks:
            await q.edit_message_text("📋 Нет активных задач.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]]))
        else:
            await q.edit_message_text("📋 *Активные задачи:*", parse_mode="Markdown", reply_markup=task_list_kb(tasks))

    elif data == "urgent_tasks":
        tasks = [t for t in load_tasks() if not t.get("done") and t.get("priority") == "срочно"]
        if not tasks:
            await q.edit_message_text("⚡ Срочных задач нет.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]]))
        else:
            await q.edit_message_text("⚡ *Срочные задачи:*", parse_mode="Markdown", reply_markup=task_list_kb(tasks, "task"))

    elif data == "done_tasks":
        tasks = [t for t in load_tasks() if t.get("done")]
        if not tasks:
            await q.edit_message_text("✅ Выполненных задач нет.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]]))
        else:
            await q.edit_message_text("✅ *Выполненные:*", parse_mode="Markdown", reply_markup=task_list_kb(tasks, "task"))

    elif data.startswith("task_"):
        task_id = int(data.split("_")[1])
        task = get_task(task_id)
        if task:
            await q.edit_message_text(format_task(task), parse_mode="Markdown", reply_markup=task_detail_kb(task_id, task.get("done")), disable_web_page_preview=True)

    elif data.startswith("done_"):
        task_id = int(data.split("_")[1])
        tasks = load_tasks()
        for t in tasks:
            if t["id"] == task_id:
                t["done"] = True
        save_tasks(tasks)
        await q.edit_message_text("✅ Задача отмечена выполненной!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ К списку", callback_data="my_tasks")]]))

    elif data.startswith("delete_"):
        task_id = int(data.split("_")[1])
        tasks = [t for t in load_tasks() if t["id"] != task_id]
        save_tasks(tasks)
        await q.edit_message_text("🗑 Задача удалена.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ К списку", callback_data="my_tasks")]]))

    elif data.startswith("priority_"):
        priority = data.split("_")[1]
        ctx.user_data["priority"] = priority
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

        # Schedule reminder
        try:
            deadline_dt = datetime.strptime(task["deadline"], "%d.%m.%Y %H:%M")
            remind_at = deadline_dt - timedelta(hours=3)
            delay = (remind_at - datetime.now()).total_seconds()
            if delay > 0:
                ctx.application.job_queue.run_once(
                    send_reminder,
                    when=delay,
                    data={"task": task, "chat_id": q.message.chat_id},
                    name=f"reminder_{task['id']}"
                )
        except Exception:
            pass

        await q.edit_message_text(
            f"✅ *ТЗ добавлено!*\n\n*{task['name']}*\nКлиент: {task['client']}\nДедлайн: {task['deadline']}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 К задачам", callback_data="my_tasks")]])
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
    await update.message.reply_text("Шаг 3/6 — 📝 Описание задачи (что нужно смонтировать, референсы, пожелания):")
    return DESCRIPTION

async def get_description(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["description"] = update.message.text
    await update.message.reply_text("Шаг 4/6 — 📅 Дедлайн (формат: 27.04.2026 18:00):")
    return DEADLINE

async def get_deadline(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    try:
        datetime.strptime(text, "%d.%m.%Y %H:%M")
        ctx.user_data["deadline"] = text
        await update.message.reply_text("Шаг 5/6 — 🔗 Ссылка на материалы (Google Drive, Dropbox и т.д.).\nЕсли нет — напиши «нет»:")
        return MATERIALS
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Введи дату так: 27.04.2026 18:00")
        return DEADLINE

async def get_materials(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    ctx.user_data["materials"] = "" if text.lower() == "нет" else text
    await update.message.reply_text("Шаг 6/6 — ⚡ Приоритет задачи:", reply_markup=priority_kb())
    return PRIORITY

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("❌ Отменено.", reply_markup=main_menu_kb())
    return ConversationHandler.END

# ── Reminder ──────────────────────────────────────────────────────────────────

async def send_reminder(ctx: ContextTypes.DEFAULT_TYPE):
    data = ctx.job.data
    task = data["task"]
    chat_id = data["chat_id"]
    priority_icon = "🔴" if task.get("priority") == "срочно" else "🟡"
    text = (
        f"⏰ *Дедлайн через 3 часа!*\n\n"
        f"*{task['name']}*\n"
        f"🏢 Клиент: {task['client']}\n"
        f"📅 Сдать до: `{task['deadline']}`\n"
        f"{priority_icon} Приоритет: {task.get('priority', 'обычно')}\n"
        f"👤 От: @{task.get('from_username', '?')}"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Готово", callback_data=f"done_{task['id']}"),
         InlineKeyboardButton("📋 Открыть", callback_data=f"task_{task['id']}")],
    ])
    await ctx.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=kb)

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

import subprocess
import os
import asyncio
import subprocess
from pathlib import Path
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ------------------------------
# НАСТРОЙКИ
# ------------------------------
BOT_TOKEN = "твой токен"
ALLOWED_USERS = {123456789}       # Укажи свой Telegram ID
BASE_DIR = Path("C:/ToolsServer") # Папка проекта
MEDIA_DIR = BASE_DIR / "media"
SCRIPTS_DIR = BASE_DIR / "scripts"
FILES_DIR = BASE_DIR / "files"

for d in (MEDIA_DIR, SCRIPTS_DIR, FILES_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ------------------------------
# ПРОВЕРКА ДОСТУПА
# ------------------------------
async def check_access(update: Update) -> bool:
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("⛔ Доступ запрещён.")
        return False
    return True



# ---------- import filemanager AFTER check function defined ----------
from filemanager import (
    ui_ls, callback_handler,
    cmd_get, cmd_mkdir, cmd_touch, cmd_rm,
    cmd_mv, cmd_rename, cmd_upload_to, handle_upload,
    cmd_find, cmd_open, cmd_zip
)

# ------------------------------
# /start
# ------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):  return
    await update.message.reply_text(
        "Бот запущен.\n"
        "/menu Удобный меню управления\n"
        "Команды:\n"
        "/cmd <команда> — выполнить команду Windows\n"
        "/files — список файлов\n"
        "/get <имя> — скачать файл\n"
        "/convert <файл> <формат> — конвертация через ffmpeg\n"
        "/run <script.py> — запуск Python-скрипта\n"
        "📁 *Файловый менеджер*\n\n"
        "/pwd — показать текущую папку\n"
        "/cd <путь> — перейти\n"
        "/ls — список (интерактивно)\n"
        "/back /forward — история\n"
        "/get <путь> — скачать\n"
        "/mkdir <путь> — создать папку\n"
        "/touch <путь> — создать файл\n"
        "/rm <путь> — удалить\n"
        "/mv <src> <dst> — переместить\n"
        "/rename <old> <new> — переименовать\n"
        "/upload_to <папка> — задать папку для загрузки\n        (а затем отправить файл)\n"
        "/find <маска> — поиск\n"
        "/open <путь> — просмотр текста\n"
        "/zip <путь> — запаковать\n"
    )

# -----------------------------------------------------
# Главное плиточное меню
# -----------------------------------------------------
async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📁 Файлы", callback_data="m_files"),
            InlineKeyboardButton("🧭 Навигация", callback_data="m_nav")
        ],
        [
            InlineKeyboardButton("🖥 Команды", callback_data="m_cmd"),
            InlineKeyboardButton("🔎 Поиск", callback_data="m_search")
        ],
        [
            InlineKeyboardButton("📤 Загрузки", callback_data="m_uploads"),
            InlineKeyboardButton("🧰 Скрипты", callback_data="m_scripts")
        ],
        [
            InlineKeyboardButton("⚙ Настройки", callback_data="m_settings"),
        ]
    ])

    await update.message.reply_text("📋 Главное меню", reply_markup=kb)


# -----------------------------------------------------
# Обработчик меню (кратко)
# -----------------------------------------------------
async def menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "m_files":
        await query.message.edit_text("💾 Используй /ls чтобы открыть файловую панель")
        return

    if data == "m_nav":
        await query.message.edit_text("🧭 Навигация:\n/pwd\n/cd\n/back\n/forward")
        return

    if data == "m_search":
        await query.message.edit_text("🔎 Поиск: /find <маска>")
        return

    if data == "m_cmd":
        await query.message.edit_text("🖥 CMD: /cmd <команда>")
        return

    if data == "m_uploads":
        await query.message.edit_text("📤 Загрузки: /upload_to <папка>")
        return

    if data == "m_scripts":
        await query.message.edit_text("🧰 Скрипты: /run <script.py>")
        return

    if data == "m_settings":
        await query.message.edit_text("⚙ Настройки пока не доступны")
        return
# ------------------------------
# Выполнение команд Windows
# /cmd dir
# ------------------------------
async def cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    
    if not context.args:
        await update.message.reply_text("Используй: /cmd <команда>")
        return

    command = " ".join(context.args)

    try:
        output = subprocess.check_output(
            command,
            shell=True,
            stderr=subprocess.STDOUT,
            text=True
        )
    except subprocess.CalledProcessError as e:
        output = e.output

    if len(output) > 4000:
        out_file = FILES_DIR / "cmd_output.txt"
        out_file.write_text(output, encoding="utf-8")
        await update.message.reply_document(open(out_file, "rb"))
    else:
        await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")

# ------------------------------
# /files — список файлов
# ------------------------------
async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return

    files = list(FILES_DIR.glob("*"))
    if not files:
        await update.message.reply_text("Файлов нет.")
        return
    
    message = "Файлы:\n" + "\n".join(f"- {f.name}" for f in files)
    await update.message.reply_text(message)

# ------------------------------
# /get filename — скачать файл
# ------------------------------
async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    
    if not context.args:
        await update.message.reply_text("Используй: /get <имя файла>")
        return

    name = context.args[0]
    file_path = FILES_DIR / name

    if not file_path.exists():
        await update.message.reply_text("Файл не найден.")
        return

    await update.message.reply_document(open(file_path, "rb"))

# ------------------------------
# /convert input.mp4 mp3
# ------------------------------
async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return

    if len(context.args) != 2:
        await update.message.reply_text("Использование: /convert <файл> <формат>")
        return

    input_name, target_fmt = context.args
    input_path = MEDIA_DIR / input_name

    if not input_path.exists():
        await update.message.reply_text("Файл не найден в /media.")
        return

    output_path = input_path.with_suffix("." + target_fmt)

    cmd = f'ffmpeg -i "{input_path}" "{output_path}" -y'
    subprocess.run(cmd, shell=True)

    await update.message.reply_document(open(output_path, "rb"))

# ------------------------------
# /run script.py — запуск Python-скрипта
# ------------------------------
async def run_script(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return

    if not context.args:
        await update.message.reply_text("Использование: /run <script.py>")
        return

    name = context.args[0]
    script = SCRIPTS_DIR / name

    if not script.exists():
        await update.message.reply_text("Такого скрипта нет.")
        return

    out = subprocess.check_output(
        f'python "{script}"',
        shell=True,
        text=True,
        stderr=subprocess.STDOUT
    )

    await update.message.reply_text(f"```\n{out}\n```", parse_mode="Markdown")

# ------------------------------
# Загрузка файлов в папку /files
# ------------------------------
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update): return
    
    tg_file = await update.message.document.get_file()
    file_path = FILES_DIR / update.message.document.file_name
    await tg_file.download_to_drive(file_path)

    await update.message.reply_text("Файл сохранён в /files.")


# ------------------------------
# MAIN
# ------------------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.bot_data["check_access"] = check_access

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cmd", cmd))
    app.add_handler(CommandHandler("files", list_files))
    app.add_handler(CommandHandler("get", get_file))
    app.add_handler(CommandHandler("convert", convert))
    app.add_handler(CommandHandler("run", run_script))
    app.add_handler(CommandHandler("menu", menu_cmd))
    app.add_handler(CallbackQueryHandler(menu_buttons, pattern="^m_"))

    # filemanager
    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^fm_"))

    app.add_handler(CommandHandler("ls", ui_ls))
    app.add_handler(CommandHandler("get", cmd_get))
    app.add_handler(CommandHandler("mkdir", cmd_mkdir))
    app.add_handler(CommandHandler("touch", cmd_touch))
    app.add_handler(CommandHandler("rm", cmd_rm))
    app.add_handler(CommandHandler("mv", cmd_mv))
    app.add_handler(CommandHandler("rename", cmd_rename))
    app.add_handler(CommandHandler("upload_to", cmd_upload_to))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_upload))
    app.add_handler(CommandHandler("find", cmd_find))
    app.add_handler(CommandHandler("open", cmd_open))
    app.add_handler(CommandHandler("zip", cmd_zip))
    app.add_handler(CommandHandler("cmd", cmd))

    print("Bot started.")
    app.run_polling()

if __name__ == "__main__":
    main()

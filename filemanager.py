import shutil
from pathlib import Path
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from navigator import nav  # обязательно нужен navigator.py


# ---------------------------------------------------------
#     Хранилище путей (ID → Path)
# ---------------------------------------------------------

def fm_store_path(context: ContextTypes.DEFAULT_TYPE, path: Path) -> str:
    """Сохраняем путь и выдаем короткий ID."""
    paths = context.bot_data.setdefault("fm_paths", {})

    for k, v in paths.items():
        if v == path:
            return str(k)

    new_id = str(len(paths) + 1)
    paths[new_id] = path
    return new_id


def fm_get_path(context: ContextTypes.DEFAULT_TYPE, id_str: str) -> Path | None:
    """Получить путь по ID."""
    return context.bot_data.get("fm_paths", {}).get(id_str)


# ---------------------------------------------------------
#     ПЕРВЫЙ ВЫЗОВ /ls
# ---------------------------------------------------------

async def ui_ls(update, context):
    """Создаёт одно сообщение-панель."""
    msg = await update.message.reply_text("⏳ Загружается…")
    context.bot_data["fm_ui_msg_id"] = msg.message_id
    context.bot_data["fm_ui_chat_id"] = msg.chat.id
    await fm_render(update, context)


# ---------------------------------------------------------
#     ОСНОВНАЯ ПАНЕЛЬ — ОТРИСОВКА FILE UI
# ---------------------------------------------------------

async def fm_render(update, context):
    """Главный метод: перерисовать файловую панель."""
    chat_id = context.bot_data["fm_ui_chat_id"]
    msg_id = context.bot_data["fm_ui_msg_id"]

    path = nav.current
    entries = list(path.iterdir())

    buttons = []

    # ========== файлы и папки ==========
    for e in sorted(entries, key=lambda x: (not x.is_dir(), x.name.lower())):
        entry_id = fm_store_path(context, e)
        if e.is_dir():
            buttons.append([
                InlineKeyboardButton(
                    f"📁 {e.name}",
                    callback_data=f"fm_open:{entry_id}"
                )
            ])
        else:
            buttons.append([
                InlineKeyboardButton(
                    f"📄 {e.name}",
                    callback_data=f"fm_file:{entry_id}"
                )
            ])

    # ========== навигационная панель ==========
    buttons.append([
        InlineKeyboardButton("⬆️ Вверх", callback_data="fm_up"),
        InlineKeyboardButton("⬅️ Назад", callback_data="fm_back"),
        InlineKeyboardButton("➡️ Вперёд", callback_data="fm_forward"),
        InlineKeyboardButton("🔄", callback_data="fm_refresh"),
    ])

    kb = InlineKeyboardMarkup(buttons)

    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=msg_id,
        text=f"📂 *{path}*\nВыбери файл или папку:",
        parse_mode="Markdown",
        reply_markup=kb
    )


# ---------------------------------------------------------
#      CALLBACK HANDLER (ВСЕ КНОПКИ fm_*)
# ---------------------------------------------------------

async def callback_handler(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ========== открыть папку ==========
    if data.startswith("fm_open:"):
        entry_id = data.split(":")[1]
        path = fm_get_path(context, entry_id)
        if path:
            nav.cd(path)
            await fm_render(update, context)
        return

    # ========== открыть файл ==========
    if data.startswith("fm_file:"):
        entry_id = data.split(":")[1]
        path = fm_get_path(context, entry_id)

        if not path:
            return

        chat_id = context.bot_data["fm_ui_chat_id"]
        msg_id = context.bot_data["fm_ui_msg_id"]

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Скачать", callback_data=f"fm_dl:{entry_id}")],
            [InlineKeyboardButton("👁 Просмотреть", callback_data=f"fm_view:{entry_id}")],
            [InlineKeyboardButton("❌ Удалить", callback_data=f"fm_del:{entry_id}")],
            [InlineKeyboardButton("↩️ Назад", callback_data="fm_refresh")]
        ])

        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=f"📄 *{path.name}*\nЧто сделать?",
            parse_mode="Markdown",
            reply_markup=kb
        )
        return

    # ========== скачать файл ==========
    if data.startswith("fm_dl:"):
        entry_id = data.split(":")[1]
        path = fm_get_path(context, entry_id)

        if path:
            await query.message.reply_document(open(path, "rb"))
        return

    # ========== просмотреть текст ==========
    if data.startswith("fm_view:"):
        entry_id = data.split(":")[1]
        path = fm_get_path(context, entry_id)

        try:
            text = path.read_text(errors="ignore")
        except:
            text = "Не удалось открыть файл."

        if len(text) > 3500:
            await query.message.reply_document(open(path, "rb"))
        else:
            chat_id = context.bot_data["fm_ui_chat_id"]
            msg_id = context.bot_data["fm_ui_msg_id"]

            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=f"```\n{text}\n```",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("↩️ Назад", callback_data="fm_refresh")]
                ])
            )
        return

    # ========== удалить ==========
    if data.startswith("fm_del:"):
        entry_id = data.split(":")[1]
        path = fm_get_path(context, entry_id)

        if path:
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            except:
                pass

        await fm_render(update, context)
        return

    # ========== навигация ==========

    if data == "fm_up":
        nav.cd(nav.current.parent)
        await fm_render(update, context)
        return

    if data == "fm_back":
        nav.back()
        await fm_render(update, context)
        return

    if data == "fm_forward":
        nav.forward()
        await fm_render(update, context)
        return

    if data == "fm_refresh":
        await fm_render(update, context)
        return


# ---------------------------------------------------------
#  ПРЯМЫЕ КОМАНДЫ (используются твоим bot.py)
# ---------------------------------------------------------

async def cmd_get(update, context):
    if not context.args:
        await update.message.reply_text("Использование: /get <путь>")
        return

    path = Path(" ".join(context.args))
    if not path.is_absolute():
        path = nav.current / path

    if not path.exists() or path.is_dir():
        await update.message.reply_text("Файл не найден.")
        return

    await update.message.reply_document(open(path, "rb"))


async def cmd_mkdir(update, context):
    if not context.args:
        await update.message.reply_text("Использование: /mkdir <путь>")
        return
    path = Path(" ".join(context.args))
    if not path.is_absolute():
        path = nav.current / path
    path.mkdir(parents=True, exist_ok=True)
    await update.message.reply_text("Папка создана.")


async def cmd_touch(update, context):
    if not context.args:
        await update.message.reply_text("Использование: /touch <путь>")
        return
    path = Path(" ".join(context.args))
    if not path.is_absolute():
        path = nav.current / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    await update.message.reply_text("Файл создан.")


async def cmd_rm(update, context):
    if not context.args:
        await update.message.reply_text("Использование: /rm <путь>")
        return
    path = Path(" ".join(context.args))
    if not path.is_absolute():
        path = nav.current / path
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        await update.message.reply_text("Удалено.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")


async def cmd_mv(update, context):
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /mv <src> <dst>")
        return
    src = Path(context.args[0])
    dst = Path(context.args[1])
    if not src.is_absolute():
        src = nav.current / src
    if not dst.is_absolute():
        dst = nav.current / dst
    try:
        shutil.move(str(src), str(dst))
        await update.message.reply_text("Перемещено.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")


async def cmd_rename(update, context):
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /rename <old> <new>")
        return
    src = Path(context.args[0])
    dst = Path(context.args[1])
    if not src.is_absolute():
        src = nav.current / src
    if not dst.is_absolute():
        dst = nav.current / dst
    try:
        src.rename(dst)
        await update.message.reply_text("Переименовано.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")


async def cmd_upload_to(update, context):
    if not context.args:
        await update.message.reply_text("Использование: /upload_to <папка>")
        return
    path = Path(" ".join(context.args))
    if not path.is_absolute():
        path = nav.current / path
    if not path.exists() or not path.is_dir():
        await update.message.reply_text("Папка не найдена.")
        return
    nav.upload_target = path
    await update.message.reply_text(f"Отправляй файл — сохраню в:\n{path}")


async def handle_upload(update, context):
    if not nav.upload_target:
        await update.message.reply_text("Сначала выбери папку: /upload_to <path>")
        return
    doc = update.message.document
    tgfile = await doc.get_file()
    dest = nav.upload_target / doc.file_name
    await tgfile.download_to_drive(dest)
    await update.message.reply_text(f"Сохранено:\n{dest}")


async def cmd_find(update, context):
    if not context.args:
        await update.message.reply_text("Использование: /find <маска>")
        return
    mask = context.args[0]
    results = list(nav.current.glob(mask))
    if not results:
        await update.message.reply_text("Ничего не найдено.")
        return
    msg = "Найдено:\n" + "\n".join(str(r) for r in results[:50])
    await update.message.reply_text(msg)


async def cmd_open(update, context):
    if not context.args:
        await update.message.reply_text("Использование: /open <путь>")
        return
    path = Path(" ".join(context.args))
    if not path.is_absolute():
        path = nav.current / path
    if not path.exists() or path.is_dir():
        await update.message.reply_text("Файл не найден.")
        return
    text = path.read_text(errors="ignore")
    if len(text) > 3500:
        await update.message.reply_document(open(path, "rb"))
    else:
        await update.message.reply_text(f"```\n{text}\n```", parse_mode="Markdown")


async def cmd_zip(update, context):
    if not context.args:
        await update.message.reply_text("Использование: /zip <путь>")
        return
    path = Path(" ".join(context.args))
    if not path.is_absolute():
        path = nav.current / path
    if not path.exists():
        await update.message.reply_text("Нет такого пути.")
        return
    zip_path = path.with_suffix(".zip")
    shutil.make_archive(str(zip_path).replace(".zip", ""), "zip", str(path))
    await update.message.reply_document(open(zip_path, "rb"))

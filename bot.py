import logging
import os
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import classifier
import database
import state

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

WELCOME_MSG = (
    "¡Hola\\! Soy tu asistente de la compra 🛒\n\n"
    "Pégame la lista de lo que necesitáis comprar \\(tal cual la tenéis en el grupo de WhatsApp\\) "
    "y te la ordeno por secciones de Mercadona\\.\n\n"
    "Podrás ir tachando cada producto conforme lo eches al carrito\\."
)

ERROR_OLLAMA = "⚠️ Ha habido un problema al procesar la lista. Inténtalo de nuevo en un momento."
ERROR_NO_PRODUCTS = "🤔 No he encontrado productos en tu mensaje. Pega la lista de la compra y te la ordeno."


def escape_md(text: str) -> str:
    special = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in text)


def render_seccion(nombre_seccion: str, items: dict) -> str:
    todos_comprados = all(i["comprado"] for i in items.values())
    titulo = f"~{escape_md(nombre_seccion)}~" if todos_comprados else escape_md(nombre_seccion)
    lineas = [titulo, ""]
    for item in items.values():
        nombre = escape_md(item["nombre"])
        lineas.append(f"• ~{nombre}~" if item["comprado"] else f"• {nombre}")
    return "\n".join(lineas)


def build_keyboard(items: dict) -> InlineKeyboardMarkup:
    buttons = []
    for item_id, item in items.items():
        label = f"↩ {item['nombre']}" if item["comprado"] else f"✓ {item['nombre']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"toggle:{item_id}")])
    return InlineKeyboardMarkup(buttons)


def parse_classified(result: str) -> dict[str, list[str]]:
    """Convierte el texto clasificado del LLM en {seccion: [item, ...]}."""
    secciones: dict[str, list[str]] = {}
    current = None
    for line in result.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("•"):
            if current is not None:
                secciones[current].append(line.lstrip("•").strip())
        else:
            current = line
            secciones[current] = []
    return {k: v for k, v in secciones.items() if v}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_MSG, parse_mode=ParseMode.MARKDOWN_V2)


async def handle_lista(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if not text:
        return

    user_id = update.effective_user.id
    processing_msg = await update.message.reply_text("⏳ Procesando tu lista...")

    try:
        result = classifier.classify_list(text)
    except Exception as e:
        logger.error("Error calling Ollama: %s", e)
        await processing_msg.edit_text(ERROR_OLLAMA)
        return

    if not result:
        await processing_msg.edit_text(ERROR_NO_PRODUCTS)
        return

    secciones_parsed = parse_classified(result)
    if not secciones_parsed:
        await processing_msg.edit_text(ERROR_NO_PRODUCTS)
        return

    session_id = str(uuid.uuid4())
    fecha = datetime.now(timezone.utc).isoformat()

    await database.create_session(session_id, user_id, fecha, text)

    db_items = []
    session_state: dict = {"session_id": session_id, "secciones": {}}

    for nombre_seccion, nombres_items in secciones_parsed.items():
        seccion_nombre_limpio = nombre_seccion  # con emoji incluido
        items_seccion = {}
        for nombre in nombres_items:
            item_id = str(uuid.uuid4())
            items_seccion[item_id] = {"nombre": nombre, "comprado": False}
            db_items.append({
                "item_id": item_id,
                "session_id": session_id,
                "nombre": nombre,
                "seccion": seccion_nombre_limpio,
            })
        session_state["secciones"][seccion_nombre_limpio] = {
            "message_id": None,
            "items": items_seccion,
        }

    await database.create_items(db_items)

    # Sobreescribir estado en RAM (nueva sesión)
    state.user_sessions[user_id] = session_state

    await processing_msg.delete()

    for nombre_seccion, sec_data in session_state["secciones"].items():
        texto = render_seccion(nombre_seccion, sec_data["items"])
        keyboard = build_keyboard(sec_data["items"])
        msg = await update.message.reply_text(
            texto,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard,
        )
        sec_data["message_id"] = msg.message_id


async def handle_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    _, item_id = query.data.split(":", 1)
    user_id = query.from_user.id

    # Caso edge: estado perdido (bot reiniciado)
    session = state.user_sessions.get(user_id)
    if session is None:
        await query.answer("Esta lista ya no está activa. Manda una nueva.", show_alert=True)
        return

    # Localizar sección a la que pertenece el ítem
    seccion_encontrada = None
    for nombre_seccion, sec_data in session["secciones"].items():
        if item_id in sec_data["items"]:
            seccion_encontrada = nombre_seccion
            break

    if seccion_encontrada is None:
        await query.answer("Esta lista ya no está activa. Manda una nueva.", show_alert=True)
        return

    sec_data = session["secciones"][seccion_encontrada]
    item = sec_data["items"][item_id]

    # Toggle en RAM
    item["comprado"] = not item["comprado"]
    timestamp = datetime.now(timezone.utc).isoformat() if item["comprado"] else None

    # Persistir en SQLite
    await database.mark_item_comprado(item_id, item["comprado"], timestamp)

    # Redibujar mensaje de la sección
    texto = render_seccion(seccion_encontrada, sec_data["items"])
    keyboard = build_keyboard(sec_data["items"])
    await context.bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=sec_data["message_id"],
        text=texto,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=keyboard,
    )


async def post_init(application) -> None:
    await database.init_db()


def main() -> None:
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN no está definido en las variables de entorno.")

    app = ApplicationBuilder().token(token).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_lista))
    app.add_handler(CallbackQueryHandler(handle_toggle, pattern="^toggle:"))

    logger.info("Bot arrancado. Esperando mensajes...")
    app.run_polling()


if __name__ == "__main__":
    main()

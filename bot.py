import logging
import os

from dotenv import load_dotenv

load_dotenv()

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

import classifier

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

WELCOME_MSG = (
    "¡Hola! Soy tu asistente de la compra 🛒\n"
    "Pégame la lista de lo que necesitáis comprar (tal cual la tenéis en el grupo de WhatsApp) "
    "y te la ordeno por secciones de Mercadona."
)

ERROR_OLLAMA = "⚠️ Ha habido un problema al procesar la lista. Inténtalo de nuevo en un momento."
ERROR_NO_PRODUCTS = "🤔 No he encontrado productos en tu mensaje. Pega la lista de la compra y te la ordeno."


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_MSG)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if not text:
        return

    processing_msg = await update.message.reply_text("⏳ Procesando tu lista...")

    try:
        result = classifier.classify_list(text)
    except Exception as e:
        logger.error("Error calling Ollama: %s", e)
        await processing_msg.edit_text(ERROR_OLLAMA)
        return

    if not result or result.strip() == "":
        await processing_msg.edit_text(ERROR_NO_PRODUCTS)
        return

    await processing_msg.edit_text(result)


def main() -> None:
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN no está definido en las variables de entorno.")

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot arrancado. Esperando mensajes...")
    app.run_polling()


if __name__ == "__main__":
    main()

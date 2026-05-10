# Bot Lista de la Compra

Bot de Telegram que recibe una lista de la compra desordenada (copiada de un grupo de WhatsApp familiar) y la devuelve organizada por secciones de Mercadona, con botones interactivos para ir tachando productos en el súper.

## Funcionalidades

- Clasifica automáticamente cualquier texto sucio en secciones de Mercadona usando un LLM (Ollama Cloud)
- Cada sección llega como un mensaje independiente con botones para marcar/desmarcar cada ítem
- Colores por sección para distinguir visualmente los grupos
- Título de sección se tacha al completarla
- Historial de sesiones e ítems guardado en SQLite
- `/reset` para limpiar la lista activa y empezar de cero

## Comandos

| Comando | Descripción |
|---------|-------------|
| `/start` | Mensaje de bienvenida |
| `/reset` | Borra la lista activa y elimina los mensajes del chat |
| _(texto libre)_ | Procesa el texto como lista de la compra |

## Stack

| Capa | Tecnología |
|------|-----------|
| Bot | `python-telegram-bot` v20 (async) |
| LLM | Ollama Cloud (`gpt-oss:120b-cloud`) |
| Base de datos | SQLite vía `aiosqlite` |
| Hosting | Railway |

## Estructura

```
├── bot.py          # Lógica principal del bot
├── classifier.py   # Llamada a Ollama + system prompt
├── sections.py     # Secciones de Mercadona y colores
├── database.py     # SQLite: sesiones e ítems
├── state.py        # Estado en RAM de la sesión activa
├── requirements.txt
└── railway.json
```

## Instalación local

```bash
cp .env.example .env
# Rellenar TELEGRAM_TOKEN y OLLAMA_API_KEY en .env

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python bot.py
```

## Variables de entorno

```
TELEGRAM_TOKEN=tu_token_de_botfather
OLLAMA_API_KEY=tu_api_key_de_ollama
```

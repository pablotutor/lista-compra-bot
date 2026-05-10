# PRD — Bot de Telegram: Lista de la Compra

## Objetivo

Bot de Telegram que recibe una lista de la compra desordenada (copiada de un grupo de WhatsApp familiar) y la devuelve ordenada por secciones de supermercado, usando un LLM para la clasificación.

---

## Stack técnico

| Capa | Tecnología |
|------|-----------|
| Bot | `python-telegram-bot` (v20+, async) |
| LLM | Ollama Cloud (`gpt-oss:120b-cloud`) vía `ollama` Python client |
| Hosting | Railway |
| Config | Variables de entorno (`.env`) |

### Cliente Ollama Cloud
```python
from ollama import Client
import os

client = Client(
    host="https://ollama.com",
    headers={'Authorization': 'Bearer ' + os.environ.get('OLLAMA_API_KEY')}
)
```

---

## Estructura de archivos

```
lista-compra-bot/
├── bot.py              # Lógica principal del bot
├── classifier.py       # Lógica de llamada a Ollama + prompt
├── sections.py         # Secciones hardcodeadas de Mercadona
├── .env                # TELEGRAM_TOKEN, OLLAMA_API_KEY
├── requirements.txt
└── railway.json        # Config de deploy
```

---

## Flujo completo

```
1. Usuario pega texto en Telegram (lista desordenada, puede tener ruido)
        ↓
2. bot.py recibe el mensaje
        ↓
3. classifier.py llama a Ollama Cloud con system prompt
        ↓
4. LLM extrae ítems + clasifica por secciones
        ↓
5. bot.py formatea la respuesta y la envía
```

---

## Secciones de Mercadona (hardcodeadas en el prompt)

```python
SECCIONES = [
    "🥬 Frutas y verduras",
    "🥩 Carnicería y charcutería",
    "🐟 Pescadería",
    "🥛 Lácteos y huevos",
    "🧀 Refrigerados",
    "🥖 Panadería",
    "🥫 Conservas y enlatados",
    "🍝 Pasta, arroz y legumbres",
    "🧴 Limpieza y hogar",
    "🛁 Higiene personal",
    "🍷 Bebidas",
    "🧊 Congelados",
    "🍬 Dulces y snacks",
    "🛒 Otros",
]
```

Si un ítem no encaja claramente en ninguna sección, va a "🛒 Otros".

---

## System prompt (en `classifier.py`)

```
Eres un asistente que organiza listas de la compra para un supermercado Mercadona español.

Tu tarea es:
1. Extraer todos los productos de la compra del texto recibido.
   - Ignora mensajes de conversación, nombres de personas, emojis irrelevantes, y cualquier texto que no sea un producto.
   - El input puede estar sucio: frases mezcladas, faltas de ortografía, abreviaciones. Interpreta con sentido común.
2. Clasificar cada producto en una de estas secciones (en este orden):
   - 🥬 Frutas y verduras
   - 🥩 Carnicería y charcutería
   - 🐟 Pescadería
   - 🥛 Lácteos y huevos
   - 🧀 Refrigerados
   - 🥖 Panadería
   - 🥫 Conservas y enlatados
   - 🍝 Pasta, arroz y legumbres
   - 🧴 Limpieza y hogar
   - 🛁 Higiene personal
   - 🍷 Bebidas
   - 🧊 Congelados
   - 🍬 Dulces y snacks
   - 🛒 Otros

3. Devolver SOLO la lista ordenada, con este formato exacto:

🥬 Frutas y verduras
• tomates
• lechuga

🥛 Lácteos y huevos
• leche
• yogures

(omite las secciones vacías)

No añadas explicaciones, saludos, ni texto adicional. Solo la lista.
```

---

## Comportamiento del bot

### Comando `/start`
Mensaje de bienvenida explicando cómo usar el bot:
```
¡Hola! Soy tu asistente de la compra 🛒
Pégame la lista de lo que necesitáis comprar (tal cual la tenéis en el grupo de WhatsApp) y te la ordeno por secciones de Mercadona.
```

### Mensaje de texto normal
→ Se procesa como lista de la compra.

### Mensajes de error
- Si Ollama no responde: `"⚠️ Ha habido un problema al procesar la lista. Inténtalo de nuevo en un momento."`
- Si el texto no contiene productos reconocibles: `"🤔 No he encontrado productos en tu mensaje. Pega la lista de la compra y te la ordeno."`

---

## Variables de entorno

```env
TELEGRAM_TOKEN=tu_token_de_botfather
OLLAMA_API_KEY=tu_api_key_de_ollama
```

---

## requirements.txt

```
python-telegram-bot==20.7
ollama>=0.1.0
python-dotenv==1.0.0
```

---

## railway.json

```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python bot.py",
    "restartPolicyType": "ON_FAILURE"
  }
}
```

---

## MVP — Lo que NO está en scope (para después)

- Fotos de listas manuscritas (OCR)
- Audios (Whisper)
- Memoria de preferencias del usuario
- Soporte multi-supermercado
- Comando para editar/añadir ítems tras la clasificación

---

## Pasos para arrancar

1. Crear bot en Telegram con @BotFather → obtener `TELEGRAM_TOKEN`
2. Crear API key en https://ollama.com/settings/keys → obtener `OLLAMA_API_KEY`
3. `pip install -r requirements.txt`
4. Crear `.env` con las dos variables
5. `python bot.py` para probar en local
6. Deploy en Railway conectando el repo de GitHub

# PRD v2 — Bot de Telegram: Lista de la Compra Interactiva

## Contexto

El MVP (v1) ya funciona en local. Clasifica una lista de texto desordenada usando Ollama Cloud y devuelve la lista ordenada por secciones de Mercadona como texto plano.

Esta versión (v2) añade:
1. **Experiencia interactiva** — un mensaje por sección con botones inline para tachar ítems
2. **Base de datos SQLite** — logs de sesiones e ítems para uso futuro (sugerencias inteligentes)

No se toca la lógica de clasificación (Ollama + prompt). Solo cambia lo que ocurre después de clasificar.

---

## Estructura de archivos (delta respecto a v1)

```
lista-compra-bot/
├── bot.py              # MODIFICAR — nueva lógica de mensajes interactivos
├── classifier.py       # SIN CAMBIOS
├── sections.py         # SIN CAMBIOS
├── database.py         # NUEVO — SQLite, modelos, helpers
├── state.py            # NUEVO — estado en memoria de la sesión activa
├── .env                # SIN CAMBIOS
├── requirements.txt    # AÑADIR: aiosqlite
└── railway.json        # SIN CAMBIOS
```

---

## Base de datos (SQLite vía aiosqlite)

### Schema

```sql
CREATE TABLE IF NOT EXISTS shopping_sessions (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    fecha TEXT NOT NULL,              -- ISO 8601: "2025-05-11T10:30:00"
    lista_raw TEXT NOT NULL           -- texto original que mandó el usuario
);

CREATE TABLE IF NOT EXISTS shopping_items (
    item_id TEXT PRIMARY KEY,         -- uuid4
    session_id TEXT NOT NULL,
    nombre TEXT NOT NULL,
    seccion TEXT NOT NULL,            -- nombre de la sección sin emoji
    comprado INTEGER DEFAULT 0,       -- 0 = pendiente, 1 = comprado
    timestamp_comprado TEXT,          -- ISO 8601, NULL si no comprado
    FOREIGN KEY (session_id) REFERENCES shopping_sessions(session_id)
);
```

### database.py — funciones requeridas

```python
async def init_db()
# Crea las tablas si no existen. Llamar al arrancar el bot.

async def create_session(session_id, user_id, fecha, lista_raw)
# Inserta una nueva sesión.

async def create_items(items: list[dict])
# Inserta todos los ítems de la sesión de una vez.
# Cada dict: {item_id, session_id, nombre, seccion}

async def mark_item_comprado(item_id, comprado: bool, timestamp=None)
# Actualiza comprado y timestamp_comprado de un ítem.
```

---

## Estado en memoria (state.py)

Durante una sesión activa de compra, el bot necesita saber qué mensaje de Telegram corresponde a qué sección, para poder editarlo cuando el usuario pulsa un botón.

```python
# Estructura en memoria por user_id:
# {
#   user_id: {
#     "session_id": "uuid",
#     "secciones": {
#       "nombre_seccion": {
#         "message_id": int,          # ID del mensaje de Telegram
#         "items": {
#           "item_id": {
#             "nombre": str,
#             "comprado": bool
#           }
#         }
#       }
#     }
#   }
# }

user_sessions = {}  # dict global, en memoria RAM
```

Este estado se pierde si el bot se reinicia — es aceptable para el MVP. La persistencia real está en SQLite.

---

## Flujo detallado

### 1. Usuario manda la lista (texto)

- `bot.py` recibe el mensaje
- Llama a `classifier.py` (sin cambios)
- Crea una nueva sesión en SQLite (`create_session`)
- Crea todos los ítems en SQLite (`create_items`)
- Inicializa el estado en memoria para ese `user_id`
- Por cada sección con ítems: manda un mensaje con inline keyboard (ver formato abajo)
- Guarda el `message_id` de cada mensaje en el estado en memoria

### 2. Formato de cada mensaje de sección

```
🥬 Frutas y verduras

• tomates
• lechuga
• manzanas
```

Inline keyboard: un botón por ítem, en filas de 1:
```
[ ✓ tomates    ]
[ ✓ lechuga    ]
[ ✓ manzanas   ]
```

Callback data del botón: `"toggle:{item_id}"`

### 3. Usuario pulsa un botón [✓ ítem]

- `bot.py` recibe el callback query
- Parsea `item_id` del callback data
- Actualiza estado en memoria: `comprado = not comprado`
- Actualiza SQLite: `mark_item_comprado(item_id, comprado)`
- Regenera el texto e inline keyboard del mensaje:
  - Ítem comprado → `• ~~nombre~~` (texto tachado con `~~` en Markdown)
  - Botón del ítem comprado → `[ ↩ nombre ]` (para poder desmarcar)
  - Si TODOS los ítems de la sección están comprados → título también tachado: `~~🥬 Frutas y verduras~~`
- Llama a `edit_message_text` con el nuevo contenido

### 4. Desmarcar un ítem

- Usuario pulsa `[ ↩ nombre ]`
- Mismo flujo que marcar, pero en sentido inverso
- `comprado = False`, `timestamp_comprado = None`
- Texto vuelve a `• nombre`, botón vuelve a `[ ✓ nombre ]`
- Si la sección estaba toda tachada, el título vuelve a normal

---

## Renderizado de texto (Markdown en Telegram)

Usar `parse_mode=ParseMode.MARKDOWN_V2`. 

Reglas importantes para MarkdownV2:
- Tachado: `~texto~` → `~~texto~~` NO funciona, usar `~texto~`
- Caracteres especiales que hay que escapar: `. ! ( ) - = + { } [ ] | # > ~`
- Escapar con `\` delante: `\.`, `\!`, `\(`, etc.

Función helper requerida en `bot.py`:

```python
def escape_md(text: str) -> str:
    """Escapa caracteres especiales para MarkdownV2."""
    special = r'\_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{c}' if c in special else c for c in text)
```

Formato del mensaje renderizado:

```python
def render_seccion(nombre_seccion: str, items: dict, todos_comprados: bool) -> str:
    titulo = f"~{escape_md(nombre_seccion)}~" if todos_comprados else escape_md(nombre_seccion)
    lineas = [titulo, ""]
    for item_id, item in items.items():
        nombre = escape_md(item["nombre"])
        if item["comprado"]:
            lineas.append(f"• ~{nombre}~")
        else:
            lineas.append(f"• {nombre}")
    return "\n".join(lineas)
```

---

## Inline keyboard

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def build_keyboard(items: dict) -> InlineKeyboardMarkup:
    buttons = []
    for item_id, item in items.items():
        label = f"↩ {item['nombre']}" if item["comprado"] else f"✓ {item['nombre']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"toggle:{item_id}")])
    return InlineKeyboardMarkup(buttons)
```

---

## Handlers en bot.py

```python
# Handler de texto → procesa la lista
async def handle_lista(update, context):
    ...

# Handler de callback → toggle ítem
async def handle_toggle(update, context):
    query = update.callback_query
    await query.answer()  # IMPORTANTE: siempre llamar answer() primero
    
    _, item_id = query.data.split(":")
    user_id = query.from_user.id
    
    # 1. Encontrar el ítem en el estado en memoria
    # 2. Toggle comprado
    # 3. Actualizar SQLite
    # 4. Encontrar la sección a la que pertenece
    # 5. Verificar si todos los ítems de esa sección están comprados
    # 6. Regenerar texto y keyboard
    # 7. edit_message_text
    ...

# Registro de handlers
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_lista))
app.add_handler(CallbackQueryHandler(handle_toggle, pattern="^toggle:"))
```

---

## Comando /start (actualizar mensaje)

```
¡Hola! Soy tu asistente de la compra 🛒

Pégame la lista de lo que necesitáis comprar (tal cual la tenéis en el grupo de WhatsApp) y te la ordeno por secciones de Mercadona.

Podrás ir tachando cada producto conforme lo eches al carrito.
```

---

## requirements.txt (delta)

Añadir:
```
aiosqlite>=0.19.0
```

---

## Casos edge a manejar

- **Usuario manda nueva lista mientras tiene una activa** → crear nueva sesión, mandar nuevos mensajes. Los mensajes anteriores quedan en el chat pero ya no son interactivos (el estado en memoria se sobreescribe).
- **Ítem con caracteres especiales en el nombre** (paréntesis, puntos, etc.) → `escape_md()` los escapa antes de renderizar.
- **Sección con un solo ítem** → funciona igual.
- **Callback de una sesión antigua** (bot reiniciado, estado en RAM perdido) → capturar `KeyError`, responder con `query.answer("Esta lista ya no está activa. Manda una nueva.")` y no editar el mensaje.

---

---

## Cambios implementados sobre el diseño original (rama `feature/checks`)

### UI/UX — Solo botones, sin cuerpo de texto duplicado

El diseño original del PRD mostraba cada ítem dos veces: en el cuerpo del mensaje (con tachado MarkdownV2) y en el botón inline (con el nombre). Se eliminó el cuerpo de texto con los ítems para reducir el ruido visual.

**Resultado:** el título de sección es el único texto del mensaje. Los botones son la lista completa.

### Indicadores de estado en los botones

| Estado | Botón |
|--------|-------|
| Pendiente | `🟩 tomates` (cuadrado de color) |
| Comprado | `✅ tomates` |

Al completar toda la sección, el título se tacha (`~🥬 Frutas y verduras~`) en lugar de añadir un emoji.

### Color por sección (`sections.py` → `SECCION_COLORES`)

Cada sección tiene asignado un cuadrado de color en `SECCION_COLORES`. Se usa como prefijo en los botones pendientes para diferenciar visualmente las secciones entre sí.

```
🟩 Frutas y verduras      🟥 Carnicería    🟦 Pescadería
🟨 Lácteos y huevos       🟧 Refrigerados  🟫 Panadería
🟪 Limpieza y hogar       ⬜ Congelados     ⬛ Otros
```

### Funciones modificadas en `bot.py`

- `render_seccion()` — solo renderiza el título; tachado si todos comprados
- `build_keyboard()` — acepta `color: str`; prefijo de color en pendientes, ✅ en comprados
- `handle_lista` y `handle_toggle` — pasan el color desde `SECCION_COLORES`

---

## Lo que NO está en scope en v2 (para v3)

- Sugerencias basadas en compras anteriores (la DB ya las registra, pero no se usan todavía)
- Añadir ítems a la lista desde el bot
- Compartir sesión entre varios usuarios (ej: madre y padre en la misma lista)
- Notificaciones o recordatorios

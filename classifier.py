import os
from ollama import Client
from sections import SECCIONES

client = Client(
    host="https://ollama.com",
    headers={"Authorization": "Bearer " + os.environ.get("OLLAMA_API_KEY", "")},
)

_SECCIONES_TEXT = "\n".join(f"   - {s}" for s in SECCIONES)

SYSTEM_PROMPT = f"""Eres un asistente que organiza listas de la compra para un supermercado Mercadona español.

Tu tarea es:
1. Extraer todos los productos de la compra del texto recibido.
   - Ignora mensajes de conversación, nombres de personas, emojis irrelevantes, y cualquier texto que no sea un producto.
   - El input puede estar sucio: frases mezcladas, faltas de ortografía, abreviaciones. Interpreta con sentido común.
2. Clasificar cada producto en una de estas secciones (en este orden):
{_SECCIONES_TEXT}

3. Devolver SOLO la lista ordenada, con este formato exacto:

🥬 Frutas y verduras
• tomates
• lechuga

🥛 Lácteos y huevos
• leche
• yogures

(omite las secciones vacías)

No añadas explicaciones, saludos, ni texto adicional. Solo la lista."""


def classify_list(text: str) -> str:
    response = client.chat(
        model="gpt-oss:120b-cloud",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    )
    return response["message"]["content"].strip()

# Estado en RAM de la sesión activa por usuario.
# Estructura:
# {
#   user_id: {
#     "session_id": str,
#     "secciones": {
#       nombre_seccion: {
#         "message_id": int,
#         "items": {
#           item_id: {"nombre": str, "comprado": bool}
#         }
#       }
#     }
#   }
# }

user_sessions: dict = {}

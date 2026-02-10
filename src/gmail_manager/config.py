# Configuración central del proyecto

# Scopes necesarios para:
# - Leer/Buscar/Modificar/Aplicar etiquetas: gmail.modify
# - Crear/editar etiquetas: gmail.labels
# - Crear/eliminar filtros: gmail.settings.basic
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.settings.basic",
    "https://mail.google.com/",  # NECESARIO para eliminación permanente (users.messages.delete)
]

APP_NAME = "Gmail Label Manager"
TOKEN_FILE = "token.json"  # se genera después del flujo OAuth
CREDENTIALS_PATH = "credentials/credentials.json"

from googleapiclient.discovery import build
from .auth import get_credentials


def get_gmail_service():
    """Construye y devuelve el servicio de Gmail API."""
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    return service

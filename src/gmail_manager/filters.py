from typing import Dict, List, Optional
from .service import get_gmail_service

USER_ID = "me"


def list_filters() -> List[Dict]:
    service = get_gmail_service()
    res = service.users().settings().filters().list(userId=USER_ID).execute()
    return res.get("filter", [])


def create_filter(criteria: Dict, action: Dict) -> Dict:
    """Crea un filtro.
    Ejemplo:
    criteria = {
        "from": "facturas@ejemplo.com",
        "to": "",
        "subject": "Factura",
        "query": "has:attachment",
        "negatedQuery": "",
        "hasAttachment": True,
        "size": 0,
        "sizeComparison": "larger",  # o "smaller"
        "excludeChats": True
    }
    action = {
        "addLabelIds": ["Label_1_id"],
        "removeLabelIds": ["INBOX"],  # para archivar
        "forward": ""
    }
    """
    service = get_gmail_service()
    body = {"criteria": criteria, "action": action}
    return (
        service.users().settings().filters().create(userId=USER_ID, body=body).execute()
    )


def delete_filter(filter_id: str) -> None:
    service = get_gmail_service()
    service.users().settings().filters().delete(userId=USER_ID, id=filter_id).execute()

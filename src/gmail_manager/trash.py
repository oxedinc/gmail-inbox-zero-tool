from typing import Dict, List
from .service import get_gmail_service

USER_ID = "me"


def list_trash_ids(max_results: int = 500) -> List[str]:
    service = get_gmail_service()
    ids = []
    next_page_token = None
    while True:
        resp = (
            service.users()
            .messages()
            .list(
                userId=USER_ID,
                labelIds=["TRASH"],
                pageToken=next_page_token,
                maxResults=500,
            )
            .execute()
        )
        msgs = resp.get("messages", [])
        ids.extend([m["id"] for m in msgs])
        next_page_token = resp.get("nextPageToken")
        if not next_page_token or len(ids) >= max_results:
            break
    return ids


def empty_trash(batch_size: int = 1000) -> Dict:
    """Elimina permanentemente todos los mensajes en TRASH usando batchDelete."""
    service = get_gmail_service()
    total_deleted = 0
    while True:
        ids = list_trash_ids(max_results=batch_size)
        if not ids:
            break
        service.users().messages().batchDelete(
            userId=USER_ID, body={"ids": ids}
        ).execute()
        total_deleted += len(ids)
        if len(ids) < batch_size:
            break
    return {"deleted": total_deleted}

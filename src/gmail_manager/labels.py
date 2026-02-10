from typing import List, Dict, Optional
from googleapiclient.errors import HttpError
from .service import get_gmail_service

USER_ID = "me"


def list_labels() -> List[Dict]:
    service = get_gmail_service()
    results = service.users().labels().list(userId=USER_ID).execute()
    return results.get("labels", [])


def list_labels_with_counts() -> List[Dict]:
    """
    Devuelve etiquetas con conteos (messagesTotal, threadsTotal).
    Usa users.labels.get por cada etiqueta.
    """
    service = get_gmail_service()
    base = list_labels()
    detailed = []
    for lbl in base:
        lid = lbl.get("id")
        try:
            got = service.users().labels().get(userId=USER_ID, id=lid).execute()
            # Asegurar campos presentes
            got.setdefault("messagesTotal", 0)
            got.setdefault("threadsTotal", 0)
            detailed.append(got)
        except Exception:
            # Si falla get, devolvemos al menos lo básico
            lbl.setdefault("messagesTotal", 0)
            lbl.setdefault("threadsTotal", 0)
            detailed.append(lbl)
    return detailed


def create_label(
    name: str, text_color: str = "#000000", bg_color: str = "#FFFFFF"
) -> Dict:
    service = get_gmail_service()
    label_body = {
        "name": name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
        "color": {"textColor": text_color, "backgroundColor": bg_color},
    }
    return service.users().labels().create(userId=USER_ID, body=label_body).execute()


def delete_label(label_id: str) -> None:
    service = get_gmail_service()
    service.users().labels().delete(userId=USER_ID, id=label_id).execute()


def rename_label(label_id: str, new_name: str) -> Dict:
    service = get_gmail_service()
    body = {"name": new_name}
    return (
        service.users()
        .labels()
        .update(userId=USER_ID, id=label_id, body=body)
        .execute()
    )


def get_label_id_by_name(name: str) -> Optional[str]:
    for lbl in list_labels():
        if lbl.get("name") == name:
            return lbl.get("id")
    return None


def apply_label_to_query(
    query: str,
    add_label_ids: Optional[List[str]] = None,
    remove_label_ids: Optional[List[str]] = None,
    max_batch: int = 1000,
) -> Dict:
    """
    Aplica o quita etiquetas a los mensajes que coincidan con una consulta.
    """
    service = get_gmail_service()
    add_label_ids = add_label_ids or []
    remove_label_ids = remove_label_ids or []

    modified = 0
    next_page_token = None
    while True:
        resp = (
            service.users()
            .messages()
            .list(userId=USER_ID, q=query, pageToken=next_page_token, maxResults=500)
            .execute()
        )
        msgs = resp.get("messages", [])
        if not msgs:
            break
        for i in range(0, len(msgs), max_batch):
            batch = msgs[i : i + max_batch]
            ids = [m["id"] for m in batch]
            body = {
                "ids": ids,
                "addLabelIds": add_label_ids,
                "removeLabelIds": remove_label_ids,
            }
            service.users().messages().batchModify(userId=USER_ID, body=body).execute()
            modified += len(ids)
        next_page_token = resp.get("nextPageToken")
        if not next_page_token:
            break
    return {"modified": modified}

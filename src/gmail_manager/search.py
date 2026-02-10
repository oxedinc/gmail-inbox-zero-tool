from collections import Counter
from email.utils import parseaddr
from typing import Dict, List, Tuple, Optional

from .service import get_gmail_service

USER_ID = "me"


import re


def top_senders(
    q: str = "", limit: int = 50, regex_pattern: Optional[str] = None
) -> List[Tuple[str, int]]:
    """Devuelve los remitentes más frecuentes (optimizado con BatchHttpRequest) y filtrado opcional por Regex."""
    service = get_gmail_service()
    counts = Counter()

    # 1. Obtener todos los IDs primero (rápido si usamos fields)
    next_page_token = None
    all_ids = []
    # Límite de seguridad para no explotar memoria si q devuelve millones
    # Tomamos 2000 msgs más recientes como muestra significativa para el "Top"
    SAMPLE_LIMIT = 2000

    while True:
        resp = (
            service.users()
            .messages()
            .list(
                userId=USER_ID,
                q=q,
                pageToken=next_page_token,
                maxResults=500,
                fields="nextPageToken,messages(id)",
            )
            .execute()
        )
        messages = resp.get("messages", [])
        if not messages:
            break
        all_ids.extend([m["id"] for m in messages])

        if len(all_ids) >= SAMPLE_LIMIT:
            all_ids = all_ids[:SAMPLE_LIMIT]
            break

        next_page_token = resp.get("nextPageToken")
        if not next_page_token:
            break

    if not all_ids:
        return []

    # 2. Descargar headers en Batch (lotes de 50-100)
    # Callback para procesar cada respuesta del batch
    def callback(request_id, response, exception):
        if exception:
            return  # Ignorar fallos puntuales

        headers = response.get("payload", {}).get("headers", [])
        sender = ""
        for h in headers:
            if h.get("name") == "From":
                sender = h.get("value", "")
                break
        email = parseaddr(sender)[1].lower()
        if email:
            # Regex Filter (Client-side)
            if regex_pattern:
                try:
                    if not re.search(
                        regex_pattern, email, re.IGNORECASE
                    ) and not re.search(regex_pattern, sender, re.IGNORECASE):
                        return  # No match
                except re.error:
                    pass  # Invalid regex, ignore filter or log error? (safest: ignore filter)

            counts[email] += 1

    # Ejecutar batch (la librería maneja la fragmentación interna si es muy grande,
    # pero mejor no excedernos del límite de la API, aunque 2000 suele pasar bien
    # si la librería hace auto-batching. La de Python NO hace auto-split de batches > 1000.
    # Así que lo partimos nosotros manualmente.)

    # Batch manual de 100 en 100 para ser seguros y rápidos
    BATCH_SIZE = 100
    total = len(all_ids)
    for i in range(0, total, BATCH_SIZE):
        chunk = all_ids[i : i + BATCH_SIZE]
        batch = service.new_batch_http_request(callback=callback)
        for mid in chunk:
            batch.add(
                service.users()
                .messages()
                .get(
                    userId=USER_ID, id=mid, format="metadata", metadataHeaders=["From"]
                )
            )
        try:
            batch.execute()
        except Exception:
            pass  # Continuar con siguiente bloque

    return counts.most_common(limit)

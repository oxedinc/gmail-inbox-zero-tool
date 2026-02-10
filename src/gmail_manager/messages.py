from typing import List, Optional, Dict, Set, Callable, Iterable
from googleapiclient.errors import HttpError
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading, time, random

from .service import get_gmail_service

USER_ID = "me"
MAX_RESULTS_PER_PAGE = 500
BATCH_LIMIT = 1000  # Gmail permite hasta 1000 ids por batchModify

# ---------- helpers de servicio por hilo ----------
_thread_local = threading.local()


def _thread_service():
    if not hasattr(_thread_local, "svc"):
        _thread_local.svc = get_gmail_service()
    return _thread_local.svc


# ---------- backoff / reintentos ----------
RETRY_STATUS = {429, 500, 502, 503, 504}


def _with_retries(fn, retries: int = 6, base: float = 0.4):
    """
    Ejecuta fn() con reintentos exponenciales y jitter para 429/5xx.
    """
    last = None
    for attempt in range(retries):
        try:
            return fn()
        except HttpError as e:
            last = e
            code = getattr(e.resp, "status", None)
            if code not in RETRY_STATUS:
                raise
            sleep = base * (2**attempt) + random.uniform(0, base)
            time.sleep(min(8.0, sleep))
    # último intento
    if last:
        raise last


# ---------- queries / listados ----------
def _safe_query(q: str, protect_starred: bool) -> str:
    q = (q or "").strip()
    if protect_starred and "-is:starred" not in q:
        q = (q + " -is:starred").strip()
    return q


def _list_page(
    service, q: Optional[str], label_ids: Optional[List[str]], page_token: Optional[str]
):
    return _with_retries(
        lambda: service.users()
        .messages()
        .list(
            userId=USER_ID,
            q=q or None,
            labelIds=label_ids or None,
            pageToken=page_token or None,
            includeSpamTrash=False,
            maxResults=MAX_RESULTS_PER_PAGE,
            fields="messages/id,nextPageToken,resultSizeEstimate",
        )
        .execute()
    )


def estimate_count(q: str = "", label_ids: Optional[List[str]] = None) -> int:
    """
    Estima cuántos mensajes coinciden SIN traer todos los IDs.
    Usa resultSizeEstimate de la 1ª página.
    """
    svc = get_gmail_service()
    resp = _list_page(svc, q or None, label_ids or None, None)
    return int(resp.get("resultSizeEstimate", 0) or 0)


def iter_message_ids(
    q: Optional[str], label_ids: Optional[List[str]], max_total: Optional[int] = None
) -> Iterable[str]:
    """
    Itera IDs página a página (bajo consumo de memoria).
    """
    svc = get_gmail_service()
    token = None
    yielded = 0
    while True:
        resp = _list_page(svc, q or None, label_ids or None, token)
        for m in resp.get("messages", []) or []:
            yield m["id"]
            yielded += 1
            if max_total and yielded >= max_total:
                return
        token = resp.get("nextPageToken")
        if not token:
            return


# ---------- listados "clásicos" (compat) ----------
def _list_ids_pagewise(
    service, q: Optional[str], label_ids: Optional[List[str]]
) -> List[str]:
    ids: List[str] = []
    next_page_token = None
    while True:
        resp = _list_page(service, q, label_ids, next_page_token)
        msgs = resp.get("messages", [])
        ids.extend([m["id"] for m in msgs])
        next_page_token = resp.get("nextPageToken")
        if not next_page_token:
            break
    return ids


def list_message_ids(
    q: str = "", label_ids: Optional[List[str]] = None, max_fetch: Optional[int] = None
) -> List[str]:
    service = get_gmail_service()
    ids = _list_ids_pagewise(service, q, label_ids)
    if max_fetch:
        ids = ids[:max_fetch]
    return ids


def list_message_ids_any_label(
    label_ids: List[str], q: str = "", max_fetch: Optional[int] = None
) -> List[str]:
    """
    OR lógico entre etiquetas (une IDs sin duplicados).
    """
    service = get_gmail_service()
    seen: Set[str] = set()
    for lid in label_ids:
        ids = _list_ids_pagewise(service, q or None, [lid])
        for _id in ids:
            if _id not in seen:
                seen.add(_id)
                if max_fetch and len(seen) >= max_fetch:
                    break
        if max_fetch and len(seen) >= max_fetch:
            break
    result = list(seen)
    if max_fetch:
        result = result[:max_fetch]
    return result


# ---------- acciones BATCH (Trash vs Delete) ----------
def _batch_modify_add_trash(ids: List[str]) -> None:
    """Mueve en bloque a TRASH con batchModify."""
    svc = _thread_service()
    body = {"ids": ids, "addLabelIds": ["TRASH"]}
    _with_retries(
        lambda: svc.users().messages().batchModify(userId=USER_ID, body=body).execute()
    )


def _batch_delete_permanently(ids: List[str]) -> None:
    """Elimina PERMANENTEMENTE en bloque con batchDelete."""
    svc = _thread_service()
    body = {"ids": ids}
    _with_retries(
        lambda: svc.users().messages().batchDelete(userId=USER_ID, body=body).execute()
    )


def _trash_one(mid: str) -> bool:
    svc = _thread_service()
    _with_retries(
        lambda: svc.users().messages().trash(userId=USER_ID, id=mid).execute()
    )
    return True


def _delete_one(mid: str) -> bool:
    svc = _thread_service()
    _with_retries(
        lambda: svc.users().messages().delete(userId=USER_ID, id=mid).execute()
    )
    return True


def _chunks(seq: List[str], size: int):
    size = max(1, min(size, BATCH_LIMIT))
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


# ---------- WORKERS GENÉRICOS ----------
def _get_worker_func(action_type: str, stop_event: Optional[threading.Event]):
    """
    Retorna la función worker adecuada (Trash o Delete).
    action_type: "TRASH" o "DELETE"
    """
    is_trash = action_type == "TRASH"
    batch_fn = _batch_modify_add_trash if is_trash else _batch_delete_permanently
    single_fn = _trash_one if is_trash else _delete_one

    def worker(chunk: List[str]) -> int:
        nonlocal batch_fn, single_fn
        try:
            batch_fn(chunk)
            return len(chunk)
        except HttpError as e:
            # Si falla el batch, intenta uno por uno o reporta error
            if e.resp is not None and e.resp.status == 403:
                raise PermissionError(
                    f"Permisos insuficientes para {action_type}. "
                    "Reautentica con los scopes requeridos."
                ) from e

            # Fallback unitario
            ok = 0
            for mid in chunk:
                if stop_event and stop_event.is_set():
                    break
                try:
                    single_fn(mid)
                    ok += 1
                except HttpError:
                    pass
            return ok

    return worker


# ---------- STREAMING GENÉRICO ----------
def _stream_action_from_ids(
    id_iter: Iterable[str],
    est_total: int,
    max_fetch: Optional[int],
    batch_size: int,
    batch_concurrency: int,
    progress_cb: Optional[Callable[[int, int], None]],
    stop_event: Optional[threading.Event],
    action_type: str,
) -> int:
    """
    Tubería: itera IDs -> empaqueta -> hilo worker (Trash o Delete).
    """
    if progress_cb:
        progress_cb(0, est_total)

    done = 0
    processed_count = 0
    current: List[str] = []
    futures = []
    workers = max(1, min(int(batch_concurrency or 1), 8))

    worker_func = _get_worker_func(action_type, stop_event)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        emitted = 0
        for mid in id_iter:
            if stop_event and stop_event.is_set():
                break
            current.append(mid)
            emitted += 1
            if max_fetch and emitted >= max_fetch:
                break

            if len(current) >= batch_size:
                futures.append(ex.submit(worker_func, list(current)))
                current.clear()
                # limitar cola
                if len(futures) >= workers * 4:
                    done += _drain_some(futures, progress_cb, done, est_total)

        # último lote
        if current:
            futures.append(ex.submit(worker_func, list(current)))

        # drenar restantes
        for f in as_completed(futures):
            try:
                gained = f.result()
            except Exception:
                gained = 0
            processed_count += gained
            done += gained
            if progress_cb:
                progress_cb(done, est_total)

    if progress_cb and done < est_total:
        progress_cb(done, est_total)

    return processed_count


def _drain_some(futures, progress_cb, done, total):
    gained_total = 0
    n = max(1, len(futures) // 2)
    ready = []
    for f in futures:
        if f.done():
            ready.append(f)
        if len(ready) >= n:
            break
    for f in ready:
        futures.remove(f)
        try:
            gained = f.result()
        except Exception:
            gained = 0
        gained_total += gained
        if progress_cb:
            progress_cb(done + gained_total, total)
    return gained_total


# ---------- PUBLIC: TRASH (Mover a papelera) ----------
def trash_by_query_fast(
    q: str,
    protect_starred: bool = True,
    max_fetch: Optional[int] = None,
    concurrency: int = 4,
    batch_size: int = BATCH_LIMIT,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    stop_event: Optional[threading.Event] = None,
) -> Dict:
    return _action_by_query_fast(
        q,
        protect_starred,
        max_fetch,
        concurrency,
        batch_size,
        progress_cb,
        stop_event,
        "TRASH",
    )


def trash_by_label_ids_fast(
    label_ids: List[str],
    protect_starred: bool = True,
    max_fetch: Optional[int] = None,
    use_or: bool = True,
    concurrency: int = 4,
    batch_size: int = BATCH_LIMIT,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    stop_event: Optional[threading.Event] = None,
) -> Dict:
    return _action_by_label_ids_fast(
        label_ids,
        protect_starred,
        max_fetch,
        use_or,
        concurrency,
        batch_size,
        progress_cb,
        stop_event,
        "TRASH",
    )


# ---------- PUBLIC: DELETE (Eliminar permanentemente) ----------
def delete_permanently_by_query_fast(
    q: str,
    protect_starred: bool = True,
    max_fetch: Optional[int] = None,
    concurrency: int = 4,
    batch_size: int = BATCH_LIMIT,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    stop_event: Optional[threading.Event] = None,
) -> Dict:
    return _action_by_query_fast(
        q,
        protect_starred,
        max_fetch,
        concurrency,
        batch_size,
        progress_cb,
        stop_event,
        "DELETE",
    )


def delete_permanently_by_label_ids_fast(
    label_ids: List[str],
    protect_starred: bool = True,
    max_fetch: Optional[int] = None,
    use_or: bool = True,
    concurrency: int = 4,
    batch_size: int = BATCH_LIMIT,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    stop_event: Optional[threading.Event] = None,
) -> Dict:
    return _action_by_label_ids_fast(
        label_ids,
        protect_starred,
        max_fetch,
        use_or,
        concurrency,
        batch_size,
        progress_cb,
        stop_event,
        "DELETE",
    )


# ---------- IMPLEMENTACIÓN COMÚN (Query / Labels) ----------
def _action_by_query_fast(
    q: str,
    protect_starred: bool,
    max_fetch: Optional[int],
    concurrency: int,
    batch_size: int,
    progress_cb: Optional[Callable[[int, int], None]],
    stop_event: Optional[threading.Event],
    action_type: str,
) -> Dict:
    q2 = _safe_query(q, protect_starred)
    est = estimate_count(q2, None)
    ids_iter = iter_message_ids(q2, None, max_total=max_fetch)
    processed = _stream_action_from_ids(
        ids_iter,
        est,
        max_fetch,
        batch_size,
        concurrency,
        progress_cb,
        stop_event,
        action_type,
    )
    matched = (
        min(est, processed) if max_fetch and est > max_fetch else max(processed, est)
    )
    return {
        "processed": processed,
        "matched": matched,
        "query_used": q2,
        "estimated": est,
        "action": action_type,
    }


def _action_by_label_ids_fast(
    label_ids: List[str],
    protect_starred: bool,
    max_fetch: Optional[int],
    use_or: bool,
    concurrency: int,
    batch_size: int,
    progress_cb: Optional[Callable[[int, int], None]],
    stop_event: Optional[threading.Event],
    action_type: str,
) -> Dict:
    if not label_ids:
        if progress_cb:
            progress_cb(0, 0)
        return {
            "processed": 0,
            "matched": 0,
            "label_ids": [],
            "query_used": "",
            "mode": "OR",
            "skipped_labels": [],
        }

    lids = list(label_ids)
    skipped: List[str] = []
    if protect_starred and "STARRED" in lids:
        lids = [x for x in lids if x != "STARRED"]
        skipped.append("STARRED")

    q2 = _safe_query("", protect_starred)
    est_total = 0

    def _iter_and():
        nonlocal est_total
        est_total = estimate_count(q2, lids)
        yield from iter_message_ids(q2, lids, max_total=max_fetch)

    def _iter_or():
        nonlocal est_total
        svc = get_gmail_service()
        seen: Set[str] = set()
        for lid in lids:
            est_total += estimate_count(q2, [lid])
        yielded = 0
        for lid in lids:
            token = None
            while True:
                resp = _list_page(svc, q2, [lid], token)
                for m in resp.get("messages", []) or []:
                    mid = m["id"]
                    if mid in seen:
                        continue
                    seen.add(mid)
                    yield mid
                    yielded += 1
                    if max_fetch and yielded >= max_fetch:
                        return
                token = resp.get("nextPageToken")
                if not token:
                    break

    iterator = _iter_or() if use_or else _iter_and()
    processed = _stream_action_from_ids(
        iterator,
        est_total,
        max_fetch,
        batch_size,
        concurrency,
        progress_cb,
        stop_event,
        action_type,
    )

    return {
        "processed": processed,
        "matched": max(processed, est_total),
        "label_ids": lids,
        "query_used": q2,
        "mode": "OR" if use_or else "AND",
        "skipped_labels": skipped,
        "estimated": est_total,
        "action": action_type,
    }


# ---------- Compat (Wrappers para mantener firma antigua si fuese necesario) ----------
def trash_by_query(
    q: str,
    protect_starred: bool = True,
    max_fetch: Optional[int] = None,
    concurrency: int = 4,
    batch_size: int = BATCH_LIMIT,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    stop_event: Optional[threading.Event] = None,
) -> Dict:
    # Redirigir siempre al fast/stream
    res = trash_by_query_fast(
        q, protect_starred, max_fetch, concurrency, batch_size, progress_cb, stop_event
    )
    return {
        "trashed": res["processed"],
        "matched": res["matched"],
        "query_used": res["query_used"],
    }


def trash_by_label_ids(
    label_ids: List[str],
    protect_starred: bool = True,
    max_fetch: Optional[int] = None,
    use_or: bool = True,
    concurrency: int = 4,
    batch_size: int = BATCH_LIMIT,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    stop_event: Optional[threading.Event] = None,
) -> Dict:
    res = trash_by_label_ids_fast(
        label_ids,
        protect_starred,
        max_fetch,
        use_or,
        concurrency,
        batch_size,
        progress_cb,
        stop_event,
    )
    return {
        "trashed": res["processed"],
        "matched": res["matched"],
        "label_ids": res["label_ids"],
        "query_used": res["query_used"],
        "mode": res["mode"],
        "skipped_labels": res["skipped_labels"],
    }

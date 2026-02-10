import os
from typing import Optional, List
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from .config import SCOPES, TOKEN_FILE, CREDENTIALS_PATH


def _has_required_scopes(creds: Optional[Credentials]) -> bool:
    if not creds:
        return False
    token_scopes = set(creds.scopes or [])
    return set(SCOPES).issubset(token_scopes)


def get_credentials(force_reauth: bool = False) -> Credentials:
    """
    Devuelve credenciales válidas. Si no existen, están inválidas o carecen de scopes,
    abre el flujo OAuth y guarda token.json.
    """
    creds: Optional[Credentials] = None

    if not force_reauth and os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception:
            creds = None

        # refresca si hace falta
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

    # Si se pide reauth o faltan scopes o no hay credenciales válidas -> flujo OAuth
    if (
        force_reauth
        or (not creds)
        or (not creds.valid)
        or (not _has_required_scopes(creds))
    ):
        if not os.path.exists(CREDENTIALS_PATH):
            raise FileNotFoundError(
                f"No se encontró {CREDENTIALS_PATH}. Coloca tus credenciales OAuth."
            )
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


def delete_token_file() -> None:
    """Elimina token.json para forzar reautenticación en el próximo uso."""
    try:
        os.remove(TOKEN_FILE)
    except FileNotFoundError:
        pass


def current_token_scopes() -> List[str]:
    """Lee los scopes actuales del token, si existe."""
    if not os.path.exists(TOKEN_FILE):
        return []
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        return list(creds.scopes or [])
    except Exception:
        return []

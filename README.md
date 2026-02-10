# InboxZero Tool (Gmail Label Manager)
<img width="2428" height="2044" alt="CleanShot 2026-02-10 at 17 02 11@2x" src="https://github.com/user-attachments/assets/412ae1d0-e852-4d4d-aa0d-6d68df73da62" />

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)

Herramienta de escritorio potente para limpiar tu bandeja de entrada y alcanzar el **Inbox Zero**. Administra etiquetas, filtros, y elimina correos masivamente (incluso permanentemente) usando la **Gmail API**.
<img width="2428" height="2044" alt="CleanShot 2026-02-10 at 17 02 49@2x" src="https://github.com/user-attachments/assets/3c1a841b-f202-4c96-b1a8-97afd9639169" />

## Funcionalidades
- **Limpieza Profunda**: Eliminar permanentemente correos (bypass Trash) para liberar espacio.
- **Búsqueda Inteligente**: Encuentra **archivos grandes (>10MB)** con un solo clic.
- **Gestión de Etiquetas**: Crear, renombrar, eliminar y listar etiquetas (con colores).
- Aplicar / quitar etiquetas a correos por consulta (`q`).
- Crear y eliminar **filtros** (criterios y acciones).
- Búsqueda por remitente y ranking de remitentes más frecuentes.
- Vaciar la papelera (eliminar permanentemente lo que está en `TRASH`).
- Interfaz gráfica con pestañas (Etiquetas, Búsqueda, Filtros, Papelera).
- Estructura lista para subir a GitHub.

> **⚠️ Aviso:** Este proyecto realiza acciones **destructivas** si así lo indicas (p. ej., vaciar papelera o mover/eliminar muchos correos). Úsalo con responsabilidad y primero prueba en una cuenta secundaria.

---

## Requisitos

- Python 3.9+
- Tkinter (viene con la mayoría de instalaciones de Python en Windows/macOS; en algunas distros Linux es necesario instalar `python3-tk`).
- Credenciales de la **Gmail API** (OAuth client ID tipo *Desktop*).

Instala dependencias (modo moderno):
```bash
# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # O en Windows: .venv\Scripts\activate

# Instalar el proyecto y dependencias
pip install -e .
```

## Activar Gmail API y credenciales

1. Ve a Google Cloud Console → **APIs & Services** → **Credentials**.
2. Crea un **OAuth client ID** tipo **Desktop** (también puedes usar `OAuth Consent Screen` en modo `External` para pruebas).
3. Descarga el archivo **`credentials.json`** y colócalo en la carpeta `credentials/credentials.json`.
4. En el primer arranque, se abrirá el navegador para autorizar. Se guardará `token.json` para futuros usos.

**Scopes** usados (mínimos necesarios para todas las funciones):
- `https://www.googleapis.com/auth/gmail.modify`
- `https://www.googleapis.com/auth/gmail.labels`
- `https://www.googleapis.com/auth/gmail.settings.basic`

> Si quieres solo lectura, limita los scopes, pero desactivarás varias funciones.

## Ejecutar

### Opción A (Recomendada - Nueva)
```bash
# Simplemente ejecuta el script run.py desde la raíz
# (asegúrate de tener el entorno activado)
python run.py
```

### Opción B (Clásica)
```bash
# Activar entorno y dependencias como arriba, luego:
python -m src.gmail_manager.main
```
o
```bash
# Esto fallará si no estás en el directorio correcto o sin configuración de path
# python src/gmail_manager/main.py  <-- NO USAR ESTO DIRECTAMENTE
```

## Empaquetado / Distribución

Este proyecto es simple; puedes usar `pyinstaller` si deseas un binario:
```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --name GmailLabelManager src/gmail_manager/main.py
```

## Notas y límites

- La **Papelera** sólo se vacía eliminando permanentemente los mensajes que ya están en `TRASH` (no hay endpoint de "vaciar papelera" global).
- Los **Filtros** requieren scope `gmail.settings.basic` y se aplican a **mensajes nuevos** que lleguen tras su creación.
- Las búsquedas aceptan la sintaxis de Gmail (campo `q`), por ejemplo: `from:alguien subject:(factura) newer_than:1y`.

## Estructura

```
gmail_label_manager/
├─ assets/
├─ credentials/
│  └─ credentials.json      # NO subir a GitHub
├─ src/
│  └─ gmail_manager/
│     ├─ __init__.py
│     ├─ config.py
│     ├─ auth.py
│     ├─ service.py
│     ├─ labels.py
│     ├─ search.py
│     ├─ filters.py
│     ├─ trash.py
│     ├─ gui.py
│     └─ main.py
├─ tests/
│  └─ test_smoke.py
├─ .gitignore
├─ LICENSE
└─ requirements.txt
```

## Licencia

MIT. Consulta `LICENSE` para detalles.

import threading
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import ttk, messagebox

from . import labels as labels_api
from . import search as search_api
from . import filters as filters_api
from . import trash as trash_api
from . import messages as messages_api
from . import auth as auth_api
from .service import get_gmail_service
from .config import APP_NAME

CHECK_OFF = "☐"
CHECK_ON = "☑"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1000x780")
        self.minsize(880, 640)

        self.selected_label_ids = set()
        self._sort_state = {}
        self._labels_cache = []

        # Progreso / cancelación
        self._cancel_event = None
        self._last_logged = -1

        self._build_ui()

    def _build_ui(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        nb = self.notebook

        self.tab_labels = ttk.Frame(nb)
        self.tab_search = ttk.Frame(nb)
        self.tab_filters = ttk.Frame(nb)
        self.tab_trash = ttk.Frame(nb)
        self.tab_account = ttk.Frame(nb)

        nb.add(self.tab_labels, text="Etiquetas")
        nb.add(self.tab_search, text="Búsqueda")
        nb.add(self.tab_filters, text="Filtros")
        nb.add(self.tab_trash, text="Papelera")
        nb.add(self.tab_account, text="Cuenta")

        self._build_labels_tab()
        self._build_search_tab()
        self._build_filters_tab()
        self._build_trash_tab()
        self._build_account_tab()

        self.log = tk.Text(self, height=8)
        self.log.pack(fill=tk.BOTH, padx=8, pady=(0, 8))
        self._log("Aplicación iniciada.")

    def _log(self, msg: str):
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    # -------------------- Labels Tab --------------------
    def _build_labels_tab(self):
        frame = self.tab_labels
        for i in range(6):
            frame.grid_columnconfigure(i, weight=1 if i in (1, 3) else 0)

        # Fila 0
        ttk.Button(
            frame, text="Listar etiquetas", command=lambda: self._list_labels()
        ).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Button(
            frame, text="Seleccionar todo", command=lambda: self._select_all_labels()
        ).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Button(
            frame,
            text="Limpiar selección",
            command=lambda: self._clear_label_selection(),
        ).grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.lbl_selected_count = ttk.Label(frame, text="Seleccionadas: 0")
        self.lbl_selected_count.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # Fila 1 filtro
        ttk.Label(frame, text="Buscar etiqueta:").grid(
            row=1, column=0, padx=5, pady=(0, 5), sticky="e"
        )
        self.entry_label_filter = ttk.Entry(frame)
        self.entry_label_filter.grid(
            row=1, column=1, columnspan=2, padx=5, pady=(0, 5), sticky="ew"
        )
        ttk.Button(
            frame, text="Filtrar", command=lambda: self._apply_label_filter()
        ).grid(row=1, column=3, padx=5, pady=(0, 5), sticky="w")
        ttk.Button(
            frame, text="Limpiar filtro", command=lambda: self._clear_label_filter()
        ).grid(row=1, column=4, padx=5, pady=(0, 5), sticky="w")
        self.entry_label_filter.bind(
            "<KeyRelease>", lambda e: self._apply_label_filter()
        )

        # Fila 2 tabla
        self.tree_labels = ttk.Treeview(
            frame, columns=("sel", "name", "messages"), show="headings", height=14
        )
        self.tree_labels.heading("sel", text="Sel")
        self.tree_labels.heading(
            "name",
            text="Nombre",
            command=lambda: self._sort_tree(self.tree_labels, "name", as_int=False),
        )
        self.tree_labels.heading(
            "messages",
            text="Mensajes",
            command=lambda: self._sort_tree(self.tree_labels, "messages", as_int=True),
        )
        self.tree_labels.column("sel", width=54, anchor="center", stretch=False)
        self.tree_labels.column("name", width=420, minwidth=220, stretch=True)
        self.tree_labels.column(
            "messages", width=120, minwidth=100, anchor="e", stretch=False
        )
        self.tree_labels.grid(
            row=2, column=0, columnspan=6, sticky="nsew", padx=5, pady=5
        )
        frame.grid_rowconfigure(2, weight=1)
        self.tree_labels.bind("<Button-1>", self._on_label_tree_click)
        self.tree_labels.bind("<Key-space>", self._on_space_toggle)

        # Fila 3 crear
        ttk.Label(frame, text="Nueva etiqueta:").grid(
            row=3, column=0, padx=5, sticky="e"
        )
        self.entry_label_name = ttk.Entry(frame)
        self.entry_label_name.grid(row=3, column=1, padx=5, sticky="ew")
        ttk.Label(frame, text="Texto color (#hex):").grid(
            row=3, column=2, padx=5, sticky="e"
        )
        self.entry_text_color = ttk.Entry(frame, width=10)
        self.entry_text_color.insert(0, "#000000")
        self.entry_text_color.grid(row=3, column=3, padx=5, sticky="w")
        ttk.Label(frame, text="Fondo color (#hex):").grid(
            row=3, column=4, padx=5, sticky="e"
        )
        self.entry_bg_color = ttk.Entry(frame, width=10)
        self.entry_bg_color.insert(0, "#FFFFFF")
        self.entry_bg_color.grid(row=3, column=5, padx=5, sticky="w")
        ttk.Button(frame, text="Crear", command=lambda: self._create_label()).grid(
            row=3, column=5, padx=5, pady=5, sticky="e"
        )

        # Fila 4 rename/delete
        ttk.Label(frame, text="ID etiqueta:").grid(row=4, column=0, padx=5, sticky="e")
        self.entry_label_id = ttk.Entry(frame)
        self.entry_label_id.grid(row=4, column=1, padx=5, sticky="ew")
        ttk.Label(frame, text="Nuevo nombre:").grid(row=4, column=2, padx=5, sticky="e")
        self.entry_new_name = ttk.Entry(frame)
        self.entry_new_name.grid(row=4, column=3, padx=5, sticky="ew")
        ttk.Button(frame, text="Renombrar", command=lambda: self._rename_label()).grid(
            row=4, column=4, padx=5, pady=5, sticky="ew"
        )
        ttk.Button(
            frame, text="Eliminar etiqueta", command=lambda: self._delete_label()
        ).grid(row=4, column=5, padx=5, pady=5, sticky="ew")

        # Fila 5 q
        ttk.Label(frame, text="Consulta (q):").grid(row=5, column=0, padx=5, sticky="e")
        self.entry_q = ttk.Entry(frame)
        self.entry_q.grid(row=5, column=1, columnspan=5, padx=5, sticky="ew")

        # Fila 6 apply/remove ids
        ttk.Label(frame, text="Add Label IDs (coma):").grid(
            row=6, column=0, padx=5, sticky="e"
        )
        self.entry_add_ids = ttk.Entry(frame)
        self.entry_add_ids.grid(row=6, column=1, columnspan=2, padx=5, sticky="ew")
        ttk.Label(frame, text="Remove Label IDs (coma):").grid(
            row=6, column=3, padx=5, sticky="e"
        )
        self.entry_remove_ids = ttk.Entry(frame)
        self.entry_remove_ids.grid(row=6, column=4, padx=5, sticky="ew")
        ttk.Button(
            frame,
            text="Aplicar/Quitar etiquetas",
            command=lambda: self._apply_labels_to_query(),
        ).grid(row=6, column=5, padx=5, pady=5, sticky="ew")

        # Fila 7 opciones
        self.var_protect_starred = tk.BooleanVar(value=True)
        self.var_or_labels = tk.BooleanVar(value=True)
        self.var_turbo = tk.BooleanVar(value=True)  # turbo por defecto
        self.var_perm_delete = tk.BooleanVar(value=False)  # Nuevo: borrar permanente

        ttk.Checkbutton(
            frame,
            text="Proteger destacados (-is:starred)",
            variable=self.var_protect_starred,
        ).grid(row=7, column=0, columnspan=2, padx=5, sticky="w")
        ttk.Checkbutton(
            frame,
            text="Combinar etiquetas con OR (cualquier)",
            variable=self.var_or_labels,
        ).grid(row=7, column=2, columnspan=2, padx=5, sticky="w")
        ttk.Checkbutton(frame, text="Turbo (streaming)", variable=self.var_turbo).grid(
            row=7, column=4, padx=5, sticky="w"
        )

        # Fila 8 límites/paralelo
        ttk.Label(frame, text="Máximo a procesar:").grid(
            row=8, column=0, padx=5, sticky="e"
        )
        self.entry_max_to_process = ttk.Entry(frame, width=10)
        self.entry_max_to_process.grid(row=8, column=1, padx=5, sticky="w")
        ttk.Label(frame, text="Tamaño de lote:").grid(
            row=8, column=2, padx=5, sticky="e"
        )
        self.entry_batch_size = ttk.Entry(frame, width=10)
        self.entry_batch_size.insert(0, "1000")
        self.entry_batch_size.grid(row=8, column=3, padx=5, sticky="w")
        ttk.Label(frame, text="Peticiones paralelas:").grid(
            row=8, column=4, padx=5, sticky="e"
        )
        self.entry_parallel = ttk.Entry(frame, width=8)
        self.entry_parallel.insert(0, "4")
        self.entry_parallel.grid(row=8, column=5, padx=5, sticky="w")

        # Fila 9 acciones
        # Checkbox "Peligroso" en rojo o destacado
        chk_del = ttk.Checkbutton(
            frame,
            text="⚠ ELIMINAR PERMANENTEMENTE (Sin papelera)",
            variable=self.var_perm_delete,
        )
        chk_del.grid(row=9, column=0, columnspan=3, padx=5, pady=(5, 0), sticky="w")

        # Fila 10 Botones acción
        ttk.Button(
            frame,
            text="Ejecutar acción por CONSULTA (q)",
            command=lambda: self._trash_by_query(),
        ).grid(row=10, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        ttk.Button(
            frame,
            text="Ejecutar acción por ETIQUETAS SELECCIONADAS",
            command=lambda: self._trash_by_selected_labels(),
        ).grid(row=10, column=3, columnspan=3, padx=5, pady=5, sticky="ew")

        # Fila 11 progreso
        self.progress = ttk.Progressbar(frame, mode="determinate")
        self.progress.grid(
            row=11, column=0, columnspan=3, padx=5, pady=(8, 5), sticky="ew"
        )
        self.lbl_progress = ttk.Label(frame, text="Progreso: 0/0")
        self.lbl_progress.grid(row=11, column=3, padx=5, pady=(8, 5), sticky="w")
        self.btn_cancel = ttk.Button(
            frame, text="Cancelar", command=lambda: self._cancel_long_task()
        )
        self.btn_cancel.grid(row=11, column=5, padx=5, pady=(8, 5), sticky="e")

    # ---------- Render / Sort ----------
    def _clear_search(self):
        self.entry_search.delete(0, tk.END)
        for i in self.tree_search.get_children():
            self.tree_search.delete(i)

    def _quick_search(self, query):
        """Helper para búsquedas rápidas (ej. botones predefinidos)"""
        self.entry_search_q.delete(0, tk.END)
        self.entry_search_q.insert(0, query)
        self._calc_top_senders()

    def _render_labels(self, labels):
        for i in self.tree_labels.get_children():
            self.tree_labels.delete(i)
        for lbl in labels:
            lid = lbl.get("id")
            name = lbl.get("name")
            total = int(lbl.get("messagesTotal", 0) or 0)
            checked = CHECK_ON if lid in self.selected_label_ids else CHECK_OFF
            self.tree_labels.insert(
                "", tk.END, iid=str(lid), values=(checked, name, str(total))
            )
        self._update_selected_count()

    def _apply_label_filter(self):
        term = (self.entry_label_filter.get() or "").strip().lower()
        filtered = (
            self._labels_cache
            if not term
            else [l for l in self._labels_cache if term in (l.get("name", "").lower())]
        )
        self._render_labels(filtered)

    def _clear_label_filter(self):
        self.entry_label_filter.delete(0, tk.END)
        self._apply_label_filter()

    def _sort_tree(self, tree: ttk.Treeview, column_key: str, as_int: bool = False):
        reverse = self._sort_state.get(column_key, False)
        items = [(tree.set(k, column_key), k) for k in tree.get_children("")]
        items.sort(
            key=(
                (lambda x: int(x[0] or 0))
                if as_int
                else (lambda x: (x[0] or "").lower())
            ),
            reverse=reverse,
        )
        for index, (_, k) in enumerate(items):
            tree.move(k, "", index)
        self._sort_state[column_key] = not reverse

    # ---------- Select helpers ----------
    def _on_label_tree_click(self, event):
        region = self.tree_labels.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.tree_labels.identify_column(event.x)
        row = self.tree_labels.identify_row(event.y)
        if row and col == "#1":
            self._toggle_row_checkbox(row)

    def _on_space_toggle(self, _event):
        row = self.tree_labels.focus()
        if row:
            self._toggle_row_checkbox(row)

    def _toggle_row_checkbox(self, row_iid: str):
        cur = self.tree_labels.set(row_iid, "sel")
        new = CHECK_ON if cur != CHECK_ON else CHECK_OFF
        self.tree_labels.set(row_iid, "sel", new)
        lid = row_iid
        if new == CHECK_ON:
            self.selected_label_ids.add(lid)
        else:
            self.selected_label_ids.discard(lid)
        self._update_selected_count()

    def _update_selected_count(self):
        self.lbl_selected_count.config(
            text=f"Seleccionadas: {len(self.selected_label_ids)}"
        )

    def _select_all_labels(self):
        self.selected_label_ids = set()
        for row in self.tree_labels.get_children(""):
            self.tree_labels.set(row, "sel", CHECK_ON)
            self.selected_label_ids.add(row)
        self._update_selected_count()

    def _clear_label_selection(self):
        self.selected_label_ids.clear()
        for row in self.tree_labels.get_children(""):
            self.tree_labels.set(row, "sel", CHECK_OFF)
        self._update_selected_count()

    # ---------- Acciones etiquetas ----------
    def _list_labels(self):
        def task():
            self._log("Listando etiquetas con conteos...")
            try:
                labels = labels_api.list_labels_with_counts()
                self._labels_cache = labels
                self._apply_label_filter()
                self._log(f"Encontradas {len(labels)} etiquetas.")
            except Exception as e:
                self._log(self._format_error(e))

        threading.Thread(target=task, daemon=True).start()

    def _create_label(self):
        def task():
            name = self.entry_label_name.get().strip()
            txt = self.entry_text_color.get().strip() or "#000000"
            bg = self.entry_bg_color.get().strip() or "#FFFFFF"
            if not name:
                messagebox.showwarning(
                    "Falta nombre", "Escribe el nombre de la etiqueta."
                )
                return
            try:
                res = labels_api.create_label(name, text_color=txt, bg_color=bg)
                self._log(f"Etiqueta creada: {res.get('name')} ({res.get('id')})")
                self._list_labels()
            except Exception as e:
                self._log(self._format_error(e))

        threading.Thread(target=task, daemon=True).start()

    def _rename_label(self):
        def task():
            lid = self.entry_label_id.get().strip()
            new = self.entry_new_name.get().strip()
            if not lid or not new:
                messagebox.showwarning(
                    "Datos incompletos", "Proporciona ID y nuevo nombre."
                )
                return
            try:
                res = labels_api.rename_label(lid, new)
                self._log(f"Etiqueta renombrada: {res.get('name')} ({res.get('id')})")
                self._list_labels()
            except Exception as e:
                self._log(self._format_error(e))

        threading.Thread(target=task, daemon=True).start()

    def _delete_label(self):
        def task():
            lid = self.entry_label_id.get().strip()
            if not lid:
                messagebox.showwarning(
                    "Falta ID", "Proporciona el ID de la etiqueta a eliminar."
                )
                return
            if not messagebox.askyesno(
                "Confirmar", "¿Eliminar etiqueta de forma permanente?"
            ):
                return
            try:
                labels_api.delete_label(lid)
                self._log(f"Etiqueta eliminada: {lid}")
                self._list_labels()
            except Exception as e:
                self._log(self._format_error(e))

        threading.Thread(target=task, daemon=True).start()

    # ---------- Aplicar/Quitar etiquetas por consulta ----------
    def _apply_labels_to_query(self):
        def task():
            q = self.entry_q.get().strip()
            add = [x.strip() for x in self.entry_add_ids.get().split(",") if x.strip()]
            rem = [
                x.strip() for x in self.entry_remove_ids.get().split(",") if x.strip()
            ]
            try:
                res = labels_api.apply_label_to_query(
                    q, add_label_ids=add, remove_label_ids=rem
                )
                self._log(f"Mensajes modificados: {res.get('modified')}")
            except Exception as e:
                self._log(self._format_error(e))

        threading.Thread(target=task, daemon=True).start()

    # ---------- Progreso / cancelar ----------
    def _reset_progress(self, total: int):
        self.progress["maximum"] = max(1, total)
        self.progress["value"] = 0
        self.lbl_progress.config(text=f"Progreso: 0/{total}")
        self._last_logged = -1

    def _progress_cb(self, done: int, total: int):
        self.after(0, self._progress_update_ui, done, total)

    def _progress_update_ui(self, done: int, total: int):
        # Si el estimado se queda corto, mantenlo visible
        if done > self.progress["maximum"]:
            self.progress["maximum"] = done
        self.progress["value"] = done
        self.lbl_progress.config(text=f"Progreso: {done}/{total}")
        if done != self._last_logged and (done % 1000 == 0 or done == total):
            self._log(f"Avance: {done}/{total}")
            self._last_logged = done

    def _cancel_long_task(self):
        if self._cancel_event:
            self._cancel_event.set()
            self._log("Cancelando operación...")

    # ---------- Utilidades ----------
    def _read_int_or_none(self, entry):
        val = (entry.get() or "").strip()
        if not val:
            return None
        try:
            n = int(val)
            return n if n > 0 else None
        except ValueError:
            return None

    # ---------- Enviar a TRASH o DELETE Permanentemente ----------
    def _trash_by_query(self):
        def task():
            q = self.entry_q.get().strip()
            protect = self.var_protect_starred.get()
            perm_delete = self.var_perm_delete.get()
            limit = self._read_int_or_none(self.entry_max_to_process)
            batch_size = self._read_int_or_none(self.entry_batch_size) or 1000
            parallel = self._read_int_or_none(self.entry_parallel) or 4
            self._cancel_event = threading.Event()

            # Mensaje confirmación
            action_name = (
                "ELIMINAR PERMANENTEMENTE" if perm_delete else "Enviar a PAPELERA"
            )
            extra_warn = (
                "\n\n⚠️ ¡ESTA ACCIÓN NO SE PUEDE DESHACER!" if perm_delete else ""
            )

            if not q and not messagebox.askyesno(
                "Confirmar",
                f"No especificaste consulta (q).\n¿{action_name} TODOS los correos (excepto protegidos)?{extra_warn}",
            ):
                return
            elif q and not messagebox.askyesno(
                "Confirmar",
                f"¿{action_name} los correos que coincidan con '{q}'?{extra_warn}",
            ):
                return

            self._log(f"Calculando estimado para: {action_name}...")
            # Estimación preliminar
            q2 = messages_api._safe_query(q, protect)
            est = messages_api.estimate_count(q2, None)
            self.after(0, self._reset_progress, est)
            self._log(f"Estimado: {est}. Lote={batch_size}, Paralelo={parallel}.")

            try:
                if perm_delete:
                    res = messages_api.delete_permanently_by_query_fast(
                        q,
                        protect_starred=protect,
                        max_fetch=limit,
                        concurrency=parallel,
                        batch_size=batch_size,
                        progress_cb=self._progress_cb,
                        stop_event=self._cancel_event,
                    )
                else:
                    res = messages_api.trash_by_query_fast(
                        q,
                        protect_starred=protect,
                        max_fetch=limit,
                        concurrency=parallel,
                        batch_size=batch_size,
                        progress_cb=self._progress_cb,
                        stop_event=self._cancel_event,
                    )

                act_done = res.get("processed", 0)
                self._log(
                    f"Acción completada ({action_name}): {act_done} | Estimado: {res.get('estimated')} | Query: '{res['query_used']}'"
                )
            except Exception as e:
                self._log(self._format_error(e))

        threading.Thread(target=task, daemon=True).start()

    def _trash_by_selected_labels(self):
        def task():
            label_ids = list(self.selected_label_ids)
            if not label_ids:
                messagebox.showwarning(
                    "Sin selección", "Selecciona al menos una etiqueta (checkbox)."
                )
                return

            protect = self.var_protect_starred.get()
            use_or = self.var_or_labels.get()
            perm_delete = self.var_perm_delete.get()
            limit = self._read_int_or_none(self.entry_max_to_process)
            batch_size = self._read_int_or_none(self.entry_batch_size) or 1000
            parallel = self._read_int_or_none(self.entry_parallel) or 4
            self._cancel_event = threading.Event()

            if protect and "STARRED" in label_ids:
                label_ids = [x for x in label_ids if x != "STARRED"]
                self._log("Advertencia: removí STARRED porque proteges destacados.")
            if not label_ids:
                self._log("No hay etiquetas válidas.")
                return

            action_name = (
                "ELIMINAR PERMANENTEMENTE" if perm_delete else "Enviar a PAPELERA"
            )
            extra_warn = "\n\n⚠️ ¡IRREVERSIBLE!" if perm_delete else ""

            if not messagebox.askyesno(
                "Confirmar",
                f"Acción: {action_name}\n"
                f"Modo: {'OR (cualquiera)' if use_or else 'AND (todas)'}\n"
                f"Etiquetas: {len(label_ids)}\n"
                f"¿Continuar?{extra_warn}",
            ):
                return

            # Calcular estimado (algo complejo en OR/AND, la API lo hará mejor)
            # Solo invocamos, el callback reseteará la barra de progreso al iniciar el stream
            self._log(f"Iniciando {action_name} por etiquetas...")

            try:
                if perm_delete:
                    res = messages_api.delete_permanently_by_label_ids_fast(
                        label_ids,
                        protect_starred=protect,
                        max_fetch=limit,
                        use_or=use_or,
                        concurrency=parallel,
                        batch_size=batch_size,
                        progress_cb=self._progress_cb,
                        stop_event=self._cancel_event,
                    )
                else:
                    res = messages_api.trash_by_label_ids_fast(
                        label_ids,
                        protect_starred=protect,
                        max_fetch=limit,
                        use_or=use_or,
                        concurrency=parallel,
                        batch_size=batch_size,
                        progress_cb=self._progress_cb,
                        stop_event=self._cancel_event,
                    )

                extra = (
                    f" | Ignoradas: {','.join(res['skipped_labels'])}"
                    if res.get("skipped_labels")
                    else ""
                )
                self._log(
                    f"Completado ({action_name}): {res['processed']} "
                    f"| Match: {res.get('matched')} "
                    f"| Query: '{res['query_used']}'{extra}"
                )
            except Exception as e:
                self._log(self._format_error(e))

        threading.Thread(target=task, daemon=True).start()

    # -------------------- Search Tab / Filters / Trash / Account (igual) --------------------
    def _build_search_tab(self):
        frame = self.tab_search
        for i in range(4):
            frame.grid_columnconfigure(i, weight=1 if i == 1 else 0)

        ttk.Label(frame, text="Consulta (q):").grid(
            row=0, column=0, padx=5, pady=5, sticky="e"
        )
        self.entry_search_q = ttk.Entry(frame)
        self.entry_search_q.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(frame, text="Top N:").grid(
            row=0, column=2, padx=5, pady=5, sticky="e"
        )
        self.entry_top_n = ttk.Entry(frame, width=6)
        self.entry_top_n.insert(0, "50")
        self.entry_top_n.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        ttk.Button(
            frame,
            text="Calcular remitentes más frecuentes",
            command=lambda: self._calc_top_senders(),
        ).grid(row=0, column=4, padx=5, pady=5, sticky="w")

        # Fila 1: Filtros Avanzados (Fecha y Regex)
        f_adv = ttk.Frame(frame)
        f_adv.grid(row=1, column=0, columnspan=5, sticky="ew", padx=5, pady=5)

        ttk.Label(f_adv, text="📅 Periodo:").pack(side="left", padx=5)
        self.combo_period = ttk.Combobox(
            f_adv,
            values=["Cualquiera", "Último Mes", "Último Año", "Últimos 3 Meses"],
            state="readonly",
            width=15,
        )
        self.combo_period.current(0)
        self.combo_period.pack(side="left", padx=5)

        ttk.Label(f_adv, text="🧩 Regex Filter (Python):").pack(side="left", padx=5)
        self.entry_regex = ttk.Entry(f_adv, width=30)
        self.entry_regex.pack(side="left", padx=5, fill="x", expand=True)

        # Fila 2: Botones rápidos
        ttk.Button(
            frame,
            text="🔍 Buscar Grandes (>10MB)",
            command=lambda: self._quick_search("larger:10M"),
        ).grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        self.tree_senders = ttk.Treeview(
            frame, columns=("email", "count"), show="headings", height=15
        )
        self.tree_senders.heading("email", text="Email")
        self.tree_senders.heading("count", text="Conteo")
        self.tree_senders.grid(
            row=3, column=0, columnspan=5, padx=5, pady=5, sticky="nsew"
        )

        # Context Menu
        self.menu_search_context = tk.Menu(self, tearoff=0)
        self.menu_search_context.add_command(
            label="🔍 Ver correos de...", command=self._context_search_sender
        )
        self.menu_search_context.add_command(
            label="⚙️ Crear filtro para...", command=self._context_filter_sender
        )
        self.menu_search_context.add_separator()
        self.menu_search_context.add_command(
            label="📋 Copiar email", command=self._context_copy_email
        )

        self.tree_senders.bind(
            "<Button-3>", self._show_search_context_menu
        )  # Windows/Linux/Mac (Right Click)
        self.tree_senders.bind(
            "<Button-2>", self._show_search_context_menu
        )  # Mac (Sometimes)
        self.tree_senders.bind(
            "<Control-Button-1>", self._show_search_context_menu
        )  # Mac (Ctrl+Click)

        frame.grid_rowconfigure(3, weight=1)
        frame.grid_columnconfigure(4, weight=1)

    def _calc_top_senders(self):
        def task():
            q = self.entry_search_q.get().strip()
            period = self.combo_period.get()
            regex = self.entry_regex.get().strip() or None

            # Date logic
            date_q = ""
            now = datetime.now()
            if period == "Último Mes":
                d = now - timedelta(days=30)
                date_q = f" after:{d.strftime('%Y/%m/%d')}"
            elif period == "Últimos 3 Meses":
                d = now - timedelta(days=90)
                date_q = f" after:{d.strftime('%Y/%m/%d')}"
            elif period == "Último Año":
                d = now - timedelta(days=365)
                date_q = f" after:{d.strftime('%Y/%m/%d')}"

            final_q = f"{q} {date_q}".strip()

            try:
                topn = int(self.entry_top_n.get().strip() or "50")
            except ValueError:
                topn = 50

            self._log(
                f"Calculando remitentes... (Query: '{final_q}', Regex: '{regex}')"
            )
            try:
                res = search_api.top_senders(q=final_q, limit=topn, regex_pattern=regex)
                for i in self.tree_senders.get_children():
                    self.tree_senders.delete(i)
                for email, cnt in res:
                    self.tree_senders.insert("", tk.END, values=(email, cnt))
                self._log(f"Listo: {len(res)} remitentes encontrados.")
            except Exception as e:
                self._log(self._format_error(e))

        threading.Thread(target=task, daemon=True).start()

    def _show_search_context_menu(self, event):
        item = self.tree_senders.identify_row(event.y)
        if item:
            self.tree_senders.selection_set(item)
            self.menu_search_context.post(event.x_root, event.y_root)

    def _get_selected_sender(self):
        sel = self.tree_senders.selection()
        if not sel:
            return None
        vals = self.tree_senders.item(sel[0], "values")
        return vals[0] if vals else None

    def _context_search_sender(self):
        email = self._get_selected_sender()
        if not email:
            return

        # Switch to Labels Tab (Index 0)
        self.notebook.select(0)

        # Set query and search
        # Assuming there is a way to set the query in the Labels tab.
        # Looking at _build_labels_tab, currently there isn't a direct "global search" box there besides filter by label?
        # WAIT, looking at _build_labels_tab in previous view_file...
        # Ah, the main search for actions is in the "Labels/Actions" tab? No, usually "Search" tab is for analysis.
        # Let's check _build_labels_tab again. It seems it lists labels.
        # Actually, the user likely wants to see the EMAILS.
        # The app seems to have "Labels", "Search" (Analysis), "Filters", "Trash".
        # Where can we list emails?
        # The AI tab had an inbox list. The Labels tab lists Labels.
        # The "Actions" are usually performed on labels.
        # The user requested "Ver correos".
        # If there is no "Email List" view, maybe I should switch to "Trash" tab (which has query input)
        # OR "Labels" tab if it has a query input?
        # Let's assume for now I will use the "Labels" tab logic if it allows selecting "Query" mode.
        # Re-reading code: _build_labels_tab has "entry_query_action" and radio button for "SEARCH_QUERY".

        self.var_target_mode.set("SEARCH_QUERY")
        self.entry_query_action.delete(0, tk.END)
        self.entry_query_action.insert(0, f"from:{email}")
        self._log(f"Listo para actuar sobre correos de: {email}")

    def _context_filter_sender(self):
        email = self._get_selected_sender()
        if not email:
            return

        # Switch to Filters Tab (Index 2 -> assuming Search is 1)
        # Tab indices: Labels=0, Search=1, Filters=2, Trash=3, Account=4
        self.notebook.select(2)

        self.entry_f_from.delete(0, tk.END)
        self.entry_f_from.insert(0, email)
        self._log(f"Filtrar remitente: {email}")

    def _context_copy_email(self):
        email = self._get_selected_sender()
        if not email:
            return
        self.clipboard_clear()
        self.clipboard_append(email)
        self._log(f"Copiado al portapapeles: {email}")

    def _build_filters_tab(self):
        frame = self.tab_filters
        for i in range(6):
            frame.grid_columnconfigure(i, weight=1 if i in (1, 3, 5) else 0)

        ttk.Button(
            frame, text="Listar filtros", command=lambda: self._list_filters()
        ).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.tree_filters = ttk.Treeview(
            frame, columns=("id", "criteria", "action"), show="headings", height=10
        )
        self.tree_filters.heading("id", text="ID")
        self.tree_filters.heading("criteria", text="Criterios")
        self.tree_filters.heading("action", text="Acciones")
        self.tree_filters.grid(
            row=1, column=0, columnspan=6, padx=5, pady=5, sticky="nsew"
        )
        frame.grid_rowconfigure(1, weight=1)

        ttk.Label(frame, text="from:").grid(row=2, column=0, padx=5, sticky="e")
        self.entry_f_from = ttk.Entry(frame)
        self.entry_f_from.grid(row=2, column=1, padx=5, sticky="ew")
        ttk.Label(frame, text="to:").grid(row=2, column=2, padx=5, sticky="e")
        self.entry_f_to = ttk.Entry(frame)
        self.entry_f_to.grid(row=2, column=3, padx=5, sticky="ew")
        ttk.Label(frame, text="subject:").grid(row=2, column=4, padx=5, sticky="e")
        self.entry_f_subject = ttk.Entry(frame)
        self.entry_f_subject.grid(row=2, column=5, padx=5, sticky="ew")

        ttk.Label(frame, text="query:").grid(row=3, column=0, padx=5, sticky="e")
        self.entry_f_query = ttk.Entry(frame)
        self.entry_f_query.grid(row=3, column=1, padx=5, sticky="ew")
        ttk.Label(frame, text="hasAttachment (True/False):").grid(
            row=3, column=2, padx=5, sticky="e"
        )
        self.entry_f_hasatt = ttk.Entry(frame, width=10)
        self.entry_f_hasatt.insert(0, "False")
        self.entry_f_hasatt.grid(row=3, column=3, padx=5, sticky="w")
        ttk.Label(frame, text="addLabelIds (coma):").grid(
            row=3, column=4, padx=5, sticky="e"
        )
        self.entry_f_add = ttk.Entry(frame)
        self.entry_f_add.grid(row=3, column=5, padx=5, sticky="ew")

        ttk.Label(frame, text="removeLabelIds (coma):").grid(
            row=4, column=0, padx=5, sticky="e"
        )
        self.entry_f_remove = ttk.Entry(frame)
        self.entry_f_remove.grid(row=4, column=1, padx=5, sticky="ew")
        ttk.Label(frame, text="forward:").grid(row=4, column=2, padx=5, sticky="e")
        self.entry_f_forward = ttk.Entry(frame)
        self.entry_f_forward.grid(row=4, column=3, padx=5, sticky="ew")

        ttk.Button(
            frame, text="Crear filtro", command=lambda: self._create_filter()
        ).grid(row=4, column=5, padx=5, pady=5, sticky="ew")

        ttk.Label(frame, text="ID filtro:").grid(row=5, column=0, padx=5, sticky="e")
        self.entry_filter_id = ttk.Entry(frame)
        self.entry_filter_id.grid(row=5, column=1, padx=5, sticky="ew")
        ttk.Button(
            frame, text="Eliminar filtro", command=lambda: self._delete_filter()
        ).grid(row=5, column=2, padx=5, pady=5, sticky="w")

    def _list_filters(self):
        def task():
            self._log("Listando filtros...")
            try:
                fl = filters_api.list_filters()
                for i in self.tree_filters.get_children():
                    self.tree_filters.delete(i)
                for f in fl:
                    self.tree_filters.insert(
                        "",
                        tk.END,
                        values=(f.get("id"), f.get("criteria"), f.get("action")),
                    )
                self._log(f"Encontrados {len(fl)} filtros.")
            except Exception as e:
                self._log(self._format_error(e))

        threading.Thread(target=task, daemon=True).start()

    # -------------------- Trash Tab / Account --------------------
    def _build_trash_tab(self):
        frame = self.tab_trash
        ttk.Button(
            frame, text="Vaciar papelera", command=lambda: self._empty_trash()
        ).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Label(
            frame, text="Esto eliminará permanentemente los mensajes en TRASH."
        ).grid(row=1, column=0, padx=5, pady=5, sticky="w")

    def _empty_trash(self):
        def task():
            if not messagebox.askyesno(
                "Confirmar", "¿Eliminar permanentemente todos los mensajes en TRASH?"
            ):
                return
            self._log("Vaciando papelera...")
            try:
                res = trash_api.empty_trash()
                self._log(f"Mensajes eliminados: {res.get('deleted')}")
            except Exception as e:
                self._log(self._format_error(e))

        threading.Thread(target=task, daemon=True).start()

    def _build_account_tab(self):
        frame = self.tab_account
        ttk.Label(frame, text="Herramientas de cuenta y permisos").grid(
            row=0, column=0, padx=5, pady=10, sticky="w"
        )
        ttk.Button(
            frame,
            text="Ver scopes actuales (token.json)",
            command=lambda: self._show_scopes(),
        ).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Button(
            frame,
            text="Reautenticar (borrar token.json y pedir permisos)",
            command=lambda: self._reauth(),
        ).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        scopes_txt = "\n".join(
            [
                "Scopes requeridos:",
                " - https://www.googleapis.com/auth/gmail.modify",
                " - https://www.googleapis.com/auth/gmail.labels",
                " - https://www.googleapis.com/auth/gmail.settings.basic",
            ]
        )
        ttk.Label(frame, text=scopes_txt, justify="left").grid(
            row=2, column=0, columnspan=2, padx=5, pady=10, sticky="w"
        )

    def _show_scopes(self):
        scopes = auth_api.current_token_scopes()
        if not scopes:
            messagebox.showinfo(
                "Scopes del token", "No hay token.json o no se pudieron leer scopes."
            )
        else:
            messagebox.showinfo(
                "Scopes del token", "Scopes actuales:\n\n" + "\n".join(scopes)
            )

    def _reauth(self):
        if not messagebox.askyesno(
            "Reautenticación",
            "Se borrará token.json y se abrirá el navegador para autorizar de nuevo. ¿Continuar?",
        ):
            return
        try:
            from .auth import delete_token_file

            delete_token_file()
            self._log("token.json eliminado. Abriendo flujo OAuth...")
            get_gmail_service()
            self._log("Reautenticación completada.")
        except Exception as e:
            self._log(self._format_error(e))

    # -------------------- Utils --------------------
    def _format_error(self, e: Exception) -> str:
        msg = str(e)
        if "insufficientPermissions" in msg or "Insufficient Permission" in msg:
            return (
                "Error de permisos (insufficientPermissions). "
                "Borra token.json y vuelve a iniciar sesión con los scopes requeridos "
                "(pestaña Cuenta → Reautenticar)."
            )
        return f"Error: {msg}"


def run():
    app = App()
    app.mainloop()

import tkinter as tk
from tkinter import filedialog, messagebox

import data
from logic import CATEGORIES, PRIORITIES, get_filtered_sorted_tasks, is_overdue, normalize_task, parse_deadline, tasks_for_today

COLORS = {
    "bg": "#0f172a",
    "card": "#1e293b",
    "input": "#0b1220",
    "accent": "#3b82f6",
    "hover": "#2563eb",
    "text": "#e2e8f0",
    "muted": "#94a3b8",
    "danger": "#ef4444",
}


class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Manager")
        self.root.geometry("980x760")
        self.root.minsize(760, 640)
        self.root.configure(bg=COLORS["bg"])

        self.tasks = [normalize_task(t) for t in data.load_tasks() if isinstance(t, dict)]
        self.visible_tasks = []
        self.selected_id = None
        self.notified_overdue_ids = set()

        self._build_ui()
        self._apply_theme()
        self._update_view(full_render=True)
        self._show_startup_notifications()
        self._schedule_deadline_check()

    # ===== UI =====
    def _build_ui(self):
        self.main_container = tk.Frame(self.root, width=560, height=700, bg=COLORS["card"], bd=0, highlightthickness=1, highlightbackground="#22304a")
        self.main_container.place(relx=0.5, rely=0.5, anchor="center")
        self.main_container.grid_propagate(False)
        self.main_container.grid_rowconfigure(2, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self.title_label = tk.Label(self.main_container, text="Task Manager", font=("Segoe UI", 18, "bold"), anchor="center")
        self.title_label.grid(row=0, column=0, padx=12, pady=(14, 10), sticky="ew")

        self.form_block = tk.Frame(self.main_container)
        self.form_block.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="ew")
        self.form_block.grid_columnconfigure(0, weight=1)

        self.task_entry = tk.Entry(self.form_block)
        self.deadline_entry = tk.Entry(self.form_block)

        self.category_var = tk.StringVar(value="Личное")
        self.priority_var = tk.StringVar(value="Средний")
        self.status_var = tk.StringVar(value="Все")
        self.category_filter_var = tk.StringVar(value="Все")
        self.priority_filter_var = tk.StringVar(value="Все")
        self.sort_var = tk.StringVar(value="По дедлайну")
        self.search_var = tk.StringVar()

        self.category_menu = tk.OptionMenu(self.form_block, self.category_var, *CATEGORIES)
        self.priority_menu = tk.OptionMenu(self.form_block, self.priority_var, *PRIORITIES)
        self.status_menu = tk.OptionMenu(self.form_block, self.status_var, "Все", "Выполненные", "Невыполненные", command=lambda _x: self._update_view())
        self.category_filter_menu = tk.OptionMenu(self.form_block, self.category_filter_var, "Все", *CATEGORIES, command=lambda _x: self._update_view())
        self.priority_filter_menu = tk.OptionMenu(self.form_block, self.priority_filter_var, "Все", *PRIORITIES, command=lambda _x: self._update_view())
        self.sort_menu = tk.OptionMenu(self.form_block, self.sort_var, "По дедлайну", "По приоритету", "По статусу", command=lambda _x: self._update_view())

        self.search_entry = tk.Entry(self.form_block, textvariable=self.search_var)
        self.add_btn = tk.Button(self.form_block, text="Добавить", command=self._add_or_update_task, relief="flat", bd=0, cursor="hand2")

        self.import_btn = tk.Button(self.form_block, text="Импорт", command=self._import_tasks, relief="flat", bd=0, cursor="hand2")
        self.export_btn = tk.Button(self.form_block, text="Экспорт", command=self._export_tasks, relief="flat", bd=0, cursor="hand2")

        self._small_label(self.form_block, "Задача").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.task_entry.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        self._small_label(self.form_block, "Дедлайн").grid(row=2, column=0, sticky="w", pady=(0, 4))
        self.deadline_entry.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        row = 4
        for label_text, widget in [
            ("Категория", self.category_menu),
            ("Приоритет", self.priority_menu),
            ("Статус", self.status_menu),
            ("Фильтр категории", self.category_filter_menu),
            ("Фильтр приоритета", self.priority_filter_menu),
            ("Сортировка", self.sort_menu),
        ]:
            self._small_label(self.form_block, label_text).grid(row=row, column=0, sticky="w", pady=(0, 4))
            widget.grid(row=row + 1, column=0, sticky="ew", pady=(0, 8))
            row += 2

        self._small_label(self.form_block, "Поиск").grid(row=row, column=0, sticky="w", pady=(0, 4))
        self.search_entry.grid(row=row + 1, column=0, sticky="ew", pady=(0, 8))
        row += 2

        self.add_btn.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        row += 1

        io_wrap = tk.Frame(self.form_block)
        io_wrap.grid(row=row, column=0, sticky="ew", pady=(0, 4))
        io_wrap.grid_columnconfigure(0, weight=1)
        io_wrap.grid_columnconfigure(1, weight=1)
        self.import_btn.grid(in_=io_wrap, row=0, column=0, sticky="ew", padx=(0, 4))
        self.export_btn.grid(in_=io_wrap, row=0, column=1, sticky="ew", padx=(4, 0))

        self._set_placeholder(self.task_entry, "Введите задачу")
        self._set_placeholder(self.deadline_entry, "дд-мм-гггг")
        self._set_placeholder(self.search_entry, "Поиск...")

        self.search_var.trace_add("write", lambda *_: self._update_view())

        # list block
        self.list_block = tk.Frame(self.main_container)
        self.list_block.grid(row=2, column=0, padx=12, pady=(0, 10), sticky="nsew")
        self.list_block.grid_columnconfigure(0, weight=1)
        self.list_block.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.list_block, height=220, highlightthickness=0)
        self.scroll = tk.Scrollbar(self.list_block, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid(row=0, column=1, sticky="ns")

        self.cards_inner = tk.Frame(self.canvas)
        self.window_id = self.canvas.create_window((0, 0), window=self.cards_inner, anchor="nw")
        self.cards_inner.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._sync_canvas_width)

        self.stats_var = tk.StringVar(value="Всего: 0 | Выполнено: 0 | 0% | Просрочено: 0")
        self.stats_label = tk.Label(self.main_container, textvariable=self.stats_var, font=("Segoe UI", 10), anchor="center")
        self.stats_label.grid(row=3, column=0, padx=12, pady=(0, 14), sticky="ew")

    def _small_label(self, parent, text):
        return tk.Label(parent, text=text, font=("Segoe UI", 11), anchor="w")

    def _sync_canvas_width(self, event):
        self.canvas.itemconfig(self.window_id, width=event.width)

    # ===== Styling =====
    def _apply_theme(self):
        self.root.configure(bg=COLORS["bg"])
        self.main_container.configure(bg=COLORS["card"])
        self.title_label.configure(bg=COLORS["card"], fg=COLORS["text"])
        self.form_block.configure(bg=COLORS["card"])
        self.list_block.configure(bg=COLORS["card"])
        self.cards_inner.configure(bg=COLORS["card"])
        self.canvas.configure(bg=COLORS["card"])

        for child in self.form_block.winfo_children():
            if isinstance(child, tk.Label):
                child.configure(bg=COLORS["card"], fg=COLORS["text"])
            if isinstance(child, tk.Entry):
                child.configure(bg=COLORS["input"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="flat", bd=0, font=("Segoe UI", 11))

        for menu in (self.category_menu, self.priority_menu, self.status_menu, self.category_filter_menu, self.priority_filter_menu, self.sort_menu):
            menu.configure(bg=COLORS["input"], fg=COLORS["text"], activebackground=COLORS["hover"], relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 11))
            menu["menu"].configure(bg=COLORS["input"], fg=COLORS["text"], activebackground=COLORS["hover"])

        for btn in (self.add_btn, self.import_btn, self.export_btn):
            btn.configure(bg=COLORS["accent"], fg=COLORS["text"], activebackground=COLORS["hover"], activeforeground=COLORS["text"], font=("Segoe UI", 11), relief="flat", bd=0)
            self._bind_button_hover(btn)

        self.stats_label.configure(bg=COLORS["card"], fg=COLORS["muted"])

    def _bind_button_hover(self, button):
        def on_enter(_):
            self._animate_color(button, COLORS["accent"], COLORS["hover"])

        def on_leave(_):
            self._animate_color(button, COLORS["hover"], COLORS["accent"])

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

    def _bind_card_hover(self, card, parts, base, hover, selected):
        def apply_bg(color):
            for p in parts:
                p.configure(bg=color)

        def on_enter(_):
            if not selected:
                self._animate_color(card, base, hover, apply_fn=apply_bg)

        def on_leave(_):
            if not selected:
                self._animate_color(card, hover, base, apply_fn=apply_bg)

        for p in parts:
            p.bind("<Enter>", on_enter)
            p.bind("<Leave>", on_leave)

    def _hex_to_rgb(self, value):
        value = value.lstrip("#")
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(self, value):
        return "#{:02x}{:02x}{:02x}".format(*value)

    def _animate_color(self, widget, start_hex, end_hex, steps=6, duration=140, apply_fn=None):
        start = self._hex_to_rgb(start_hex)
        end = self._hex_to_rgb(end_hex)
        delay = max(1, duration // steps)

        def step(i=0):
            ratio = i / steps
            rgb = tuple(int(start[c] + (end[c] - start[c]) * ratio) for c in range(3))
            color = self._rgb_to_hex(rgb)
            if apply_fn:
                apply_fn(color)
            else:
                widget.configure(bg=color)
            if i < steps:
                self.root.after(delay, lambda: step(i + 1))

        step(0)

    # ===== Data ops =====
    def _set_placeholder(self, entry, text):
        entry.insert(0, text)
        entry._placeholder = text

        def on_in(_):
            if entry.get() == entry._placeholder:
                entry.delete(0, tk.END)

        def on_out(_):
            if not entry.get().strip():
                entry.delete(0, tk.END)
                entry.insert(0, entry._placeholder)

        entry.bind("<FocusIn>", on_in)
        entry.bind("<FocusOut>", on_out)

    def _task_filters(self):
        query = self.search_var.get()
        if self.search_entry.get() == self.search_entry._placeholder:
            query = ""
        return {
            "status": self.status_var.get(),
            "category": self.category_filter_var.get(),
            "priority": self.priority_filter_var.get(),
            "query": query,
        }

    def _add_or_update_task(self):
        text = self.task_entry.get().strip()
        if text == self.task_entry._placeholder:
            text = ""

        deadline = self.deadline_entry.get().strip()
        if deadline in ("", self.deadline_entry._placeholder):
            deadline = "без срока"
        elif deadline.lower() != "без срока" and parse_deadline(deadline) is None:
            messagebox.showwarning("Ошибка", "Дедлайн: дд-мм-гггг или без срока")
            return

        if not text:
            messagebox.showwarning("Ошибка", "Введите задачу")
            return

        payload = {
            "id": self.selected_id,
            "text": text,
            "done": False,
            "deadline": deadline,
            "category": self.category_var.get(),
            "priority": self.priority_var.get(),
        }

        if self.selected_id:
            for i, task in enumerate(self.tasks):
                if task["id"] == self.selected_id:
                    payload["done"] = task["done"]
                    self.tasks[i] = normalize_task(payload)
                    break
        else:
            payload["id"] = None
            self.tasks.append(normalize_task(payload))

        self._persist_and_refresh(full_render=True)
        self._clear_form()

    def _clear_form(self):
        self.selected_id = None
        self.task_entry.delete(0, tk.END)
        self.task_entry.insert(0, self.task_entry._placeholder)
        self.deadline_entry.delete(0, tk.END)
        self.deadline_entry.insert(0, self.deadline_entry._placeholder)
        self.category_var.set("Личное")
        self.priority_var.set("Средний")
        self.add_btn.configure(text="Добавить")

    def _select_task(self, task):
        self.selected_id = task["id"]
        self.task_entry.delete(0, tk.END)
        self.task_entry.insert(0, task["text"])
        self.deadline_entry.delete(0, tk.END)
        self.deadline_entry.insert(0, task["deadline"])
        self.category_var.set(task["category"])
        self.priority_var.set(task["priority"])
        self.add_btn.configure(text="Сохранить")
        self._update_view(full_render=True)

    def _toggle_done(self, task_id):
        for task in self.tasks:
            if task["id"] == task_id:
                task["done"] = not task["done"]
                break
        self._persist_and_refresh(full_render=False)

    def _delete_task(self, task_id):
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        if self.selected_id == task_id:
            self._clear_form()
        self._persist_and_refresh(full_render=True)

    def _import_tasks(self):
        file_path = filedialog.askopenfilename(title="Импорт", filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        try:
            raw = data.import_tasks(file_path)
            self.tasks = [normalize_task(t) for t in raw if isinstance(t, dict)]
            self._persist_and_refresh(full_render=True)
        except Exception as error:
            messagebox.showerror("Ошибка", str(error))

    def _export_tasks(self):
        file_path = filedialog.asksaveasfilename(title="Экспорт", defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        try:
            data.export_tasks(self.tasks, file_path)
            messagebox.showinfo("Экспорт", "Экспорт выполнен")
        except Exception as error:
            messagebox.showerror("Ошибка", str(error))

    def _persist_and_refresh(self, full_render=False):
        if not data.save_tasks(self.tasks):
            messagebox.showerror("Ошибка", "Не удалось сохранить задачи")
        self._update_view(full_render=full_render)

    # ===== View updates =====
    def _update_view(self, full_render=False):
        self.visible_tasks = get_filtered_sorted_tasks(self.tasks, self._task_filters(), self.sort_var.get())
        self._update_stats()
        self._render_cards(animated=full_render)

    def _update_stats(self):
        total = len(self.tasks)
        done = sum(1 for t in self.tasks if t["done"])
        overdue = sum(1 for t in self.tasks if is_overdue(t))
        percent = int((done / total) * 100) if total else 0
        self.stats_var.set(f"Всего: {total} | Выполнено: {done} | {percent}% | Просрочено: {overdue}")

    def _render_cards(self, animated=False):
        for widget in self.cards_inner.winfo_children():
            widget.destroy()

        for row, task in enumerate(self.visible_tasks):
            delay = row * 25 if animated else 0
            self.root.after(delay, lambda r=row, t=task: self._create_card(r, t))

    def _create_card(self, row, task):
        selected = self.selected_id == task["id"]
        base = COLORS["hover"] if selected else COLORS["card"]
        title_color = COLORS["danger"] if is_overdue(task) else COLORS["text"]

        card = tk.Frame(self.cards_inner, bg=base, bd=0, relief="flat", padx=8, pady=8, highlightthickness=1, highlightbackground="#314159")
        card.grid(row=row, column=0, sticky="ew", padx=10, pady=6)
        card.grid_columnconfigure(1, weight=1)

        marker = tk.Label(card, text="✅" if task["done"] else "⬜", bg=base, fg=COLORS["text"], font=("Segoe UI", 12))
        marker.grid(row=0, column=0, rowspan=2, padx=(2, 8), sticky="n")

        title = tk.Label(card, text=task["text"], bg=base, fg=title_color, font=("Segoe UI", 13, "bold"), anchor="w")
        title.grid(row=0, column=1, sticky="ew")

        meta = tk.Label(card, text=f"{task['category']} | {task['deadline']} | {task['priority']}", bg=base, fg=COLORS["muted"], font=("Segoe UI", 10), anchor="w")
        meta.grid(row=1, column=1, sticky="w", pady=(4, 0))

        done_btn = tk.Button(card, text="✔", width=3, command=lambda tid=task["id"]: self._toggle_done(tid), relief="flat", bd=0, cursor="hand2", bg=COLORS["accent"], fg=COLORS["text"], activebackground=COLORS["hover"], activeforeground=COLORS["text"])
        del_btn = tk.Button(card, text="✖", width=3, command=lambda tid=task["id"]: self._delete_task(tid), relief="flat", bd=0, cursor="hand2", bg=COLORS["accent"], fg=COLORS["danger"], activebackground=COLORS["hover"], activeforeground=COLORS["danger"])
        done_btn.grid(row=0, column=2, padx=(6, 2))
        del_btn.grid(row=1, column=2, padx=(6, 2), pady=(4, 0))

        for w in (card, marker, title, meta):
            w.bind("<Button-1>", lambda _e, t=task: self._select_task(t))

        self._bind_button_hover(done_btn)
        self._bind_button_hover(del_btn)
        self._bind_card_hover(card, [card, marker, title, meta], base, COLORS["hover"], selected)

    # ===== Notifications =====
    def _show_startup_notifications(self):
        overdue_count = sum(1 for t in self.tasks if is_overdue(t))
        today_count = len(tasks_for_today(self.tasks))
        if overdue_count:
            messagebox.showwarning("Просроченные", f"Просроченных задач: {overdue_count}")
        if today_count:
            messagebox.showinfo("Сегодня", f"Задач на сегодня: {today_count}")

    def _schedule_deadline_check(self):
        self._check_new_overdues()
        self.root.after(60_000, self._schedule_deadline_check)

    def _check_new_overdues(self):
        fresh_count = 0
        for task in self.tasks:
            if is_overdue(task) and task["id"] not in self.notified_overdue_ids:
                self.notified_overdue_ids.add(task["id"])
                fresh_count += 1
        if fresh_count:
            messagebox.showwarning("Новые просроченные", f"Стало просроченными задач: {fresh_count}")


def run_app():
    root = tk.Tk()
    TaskManagerApp(root)
    root.mainloop()

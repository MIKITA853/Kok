import tkinter as tk
from tkinter import filedialog, messagebox

import data
from logic import CATEGORIES, PRIORITIES, get_filtered_sorted_tasks, is_overdue, normalize_task, parse_deadline, tasks_for_today

THEMES = {
    "dark": {
        "bg": "#0f172a",
        "card": "#1e293b",
        "input": "#0b1220",
        "accent": "#6366f1",
        "hover": "#4f46e5",
        "text": "#e2e8f0",
        "muted": "#94a3b8",
        "danger": "#ef4444",
        "task_card": "#273449",
    },
    "light": {
        "bg": "#e6e9f2",
        "card": "#f8fafc",
        "input": "#ffffff",
        "accent": "#6366f1",
        "hover": "#4f46e5",
        "text": "#0f172a",
        "muted": "#475569",
        "danger": "#dc2626",
        "task_card": "#eef2ff",
    },
}


class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Manager")
        self.root.geometry("1000x800")
        self.root.minsize(920, 700)

        cfg = data.load_config()
        self.theme_name = cfg.get("theme", "dark") if cfg.get("theme", "dark") in THEMES else "dark"

        self.tasks = [normalize_task(t) for t in data.load_tasks() if isinstance(t, dict)]
        self.visible_tasks = []
        self.selected_id = None
        self.notified_overdue_ids = set()

        self._build_ui()
        self._apply_theme()
        self._update_view(full_render=True)
        self._show_startup_notifications()
        self._schedule_deadline_check()

    def _build_ui(self):
        self.container = tk.Frame(
            self.root,
            width=820,
            height=750,
            padx=20,
            pady=20,
            highlightthickness=1,
            highlightbackground="#334155",
        )
        self.container.place(relx=0.5, rely=0.5, anchor="center")
        self.container.grid_propagate(False)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(5, weight=1)

        self.title_label = tk.Label(self.container, text="Task Manager", font=("Segoe UI", 21, "bold"), anchor="center")
        self.title_label.grid(row=0, column=0, sticky="ew", pady=(0, 14))

        self.task_entry = tk.Entry(self.container, font=("Segoe UI", 12), bd=0)
        self.task_entry.grid(row=1, column=0, sticky="ew", pady=(0, 10), ipady=10)

        self.deadline_entry = tk.Entry(self.container, font=("Segoe UI", 12), bd=0)
        self.deadline_entry.grid(row=2, column=0, sticky="ew", pady=(0, 10), ipady=10)

        # Controls row
        self.controls = tk.Frame(self.container)
        self.controls.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        for i, w in enumerate([2, 2, 2, 2, 2, 2, 2]):
            self.controls.grid_columnconfigure(i, weight=w)

        self.category_var = tk.StringVar(value="Личное")
        self.priority_var = tk.StringVar(value="Средний")
        self.status_var = tk.StringVar(value="Все")
        self.sort_var = tk.StringVar(value="По дедлайну")
        self.search_var = tk.StringVar()

        self.category_menu = tk.OptionMenu(self.controls, self.category_var, *CATEGORIES)
        self.priority_menu = tk.OptionMenu(self.controls, self.priority_var, *PRIORITIES)
        self.status_menu = tk.OptionMenu(self.controls, self.status_var, "Все", "Выполненные", "Невыполненные", command=lambda _x: self._update_view())
        self.sort_menu = tk.OptionMenu(self.controls, self.sort_var, "По дедлайну", "По приоритету", "По статусу", command=lambda _x: self._update_view())

        self.add_btn = tk.Button(self.controls, text="Добавить", command=self._add_or_update_task, relief="flat", bd=0, cursor="hand2")
        self.theme_btn = tk.Button(self.controls, text="Сменить тему", command=self._toggle_theme, relief="flat", bd=0, cursor="hand2")

        self.search_entry = tk.Entry(self.controls, textvariable=self.search_var, font=("Segoe UI", 11), bd=0)
        self.search_var.trace_add("write", lambda *_: self._update_view())

        self.category_menu.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.priority_menu.grid(row=0, column=1, sticky="ew", padx=6)
        self.status_menu.grid(row=0, column=2, sticky="ew", padx=6)
        self.sort_menu.grid(row=0, column=3, sticky="ew", padx=6)
        self.search_entry.grid(row=0, column=4, sticky="ew", padx=6, ipady=8)
        self.add_btn.grid(row=0, column=5, sticky="ew", padx=6)
        self.theme_btn.grid(row=0, column=6, sticky="ew", padx=(6, 0))

        # IO row
        self.io_row = tk.Frame(self.container)
        self.io_row.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        self.io_row.grid_columnconfigure(0, weight=1)
        self.io_row.grid_columnconfigure(1, weight=1)
        self.import_btn = tk.Button(self.io_row, text="Импорт", command=self._import_tasks, relief="flat", bd=0, cursor="hand2")
        self.export_btn = tk.Button(self.io_row, text="Экспорт", command=self._export_tasks, relief="flat", bd=0, cursor="hand2")
        self.import_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.export_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        # Scroll list
        self.list_panel = tk.Frame(self.container)
        self.list_panel.grid(row=5, column=0, sticky="nsew", pady=(0, 10))
        self.list_panel.grid_rowconfigure(0, weight=1)
        self.list_panel.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.list_panel, highlightthickness=0)
        self.scroll = tk.Scrollbar(self.list_panel, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid(row=0, column=1, sticky="ns")

        self.cards_inner = tk.Frame(self.canvas)
        self.window_id = self.canvas.create_window((0, 0), window=self.cards_inner, anchor="nw")
        self.cards_inner.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._sync_canvas_width)

        self.stats_var = tk.StringVar(value="Всего: 0 | Выполнено: 0 | 0% | Просрочено: 0")
        self.stats_label = tk.Label(self.container, textvariable=self.stats_var, font=("Segoe UI", 10, "bold"), anchor="center")
        self.stats_label.grid(row=6, column=0, sticky="ew")

        self._set_placeholder(self.task_entry, "Введите задачу")
        self._set_placeholder(self.deadline_entry, "дд-мм-гггг")
        self._set_placeholder(self.search_entry, "Поиск")

    # ===== Styles =====
    def _apply_theme(self):
        colors = THEMES[self.theme_name]
        self.root.configure(bg=colors["bg"])
        self.container.configure(bg=colors["card"], highlightbackground="#334155")
        self.controls.configure(bg=colors["card"])
        self.io_row.configure(bg=colors["card"])
        self.list_panel.configure(bg=colors["card"])
        self.canvas.configure(bg=colors["card"])
        self.cards_inner.configure(bg=colors["card"])
        self.title_label.configure(bg=colors["card"], fg=colors["text"])

        for entry in (self.task_entry, self.deadline_entry, self.search_entry):
            entry.configure(bg=colors["input"], fg=colors["text"], insertbackground=colors["text"], relief="flat", bd=0)

        for menu in (self.category_menu, self.priority_menu, self.status_menu, self.sort_menu):
            menu.configure(bg=colors["input"], fg=colors["text"], activebackground=colors["hover"], activeforeground=colors["text"], relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 11))
            menu["menu"].configure(bg=colors["input"], fg=colors["text"], activebackground=colors["hover"], activeforeground=colors["text"])

        for btn in (self.add_btn, self.theme_btn, self.import_btn, self.export_btn):
            btn.configure(bg=colors["accent"], fg=colors["text"], activebackground=colors["hover"], activeforeground=colors["text"], relief="flat", bd=0, font=("Segoe UI", 11))
            self._bind_button_hover(btn)

        self.stats_label.configure(bg=colors["card"], fg=colors["muted"])

    def _bind_button_hover(self, button):
        colors = THEMES[self.theme_name]

        def on_enter(_):
            self._animate_color(button, colors["accent"], colors["hover"])

        def on_leave(_):
            self._animate_color(button, colors["hover"], colors["accent"])

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

    def _bind_card_hover(self, card, widgets, base, hover, selected=False):
        def apply_bg(color):
            for widget in widgets:
                widget.configure(bg=color)

        def on_enter(_):
            if not selected:
                self._animate_color(card, base, hover, apply_fn=apply_bg)

        def on_leave(_):
            if not selected:
                self._animate_color(card, hover, base, apply_fn=apply_bg)

        for widget in widgets:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

    def _hex_to_rgb(self, color):
        color = color.lstrip("#")
        return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(self, rgb):
        return "#{:02x}{:02x}{:02x}".format(*rgb)

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

    # ===== Data =====
    def _set_placeholder(self, entry, text):
        entry.insert(0, text)
        entry._placeholder = text

        def on_focus_in(_):
            if entry.get() == entry._placeholder:
                entry.delete(0, tk.END)

        def on_focus_out(_):
            if not entry.get().strip():
                entry.delete(0, tk.END)
                entry.insert(0, entry._placeholder)

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

    def _toggle_theme(self):
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        data.save_config({"theme": self.theme_name})
        self._apply_theme()
        self._update_view(full_render=True)

    def _sync_canvas_width(self, event):
        self.canvas.itemconfig(self.window_id, width=event.width)

    def _task_filters(self):
        query = self.search_var.get()
        if self.search_entry.get() == self.search_entry._placeholder:
            query = ""
        return {
            "status": self.status_var.get(),
            "category": "Все",
            "priority": "Все",
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
        path = filedialog.askopenfilename(title="Импорт", filetypes=[("JSON files", "*.json")])
        if not path:
            return
        try:
            loaded = data.import_tasks(path)
            self.tasks = [normalize_task(t) for t in loaded if isinstance(t, dict)]
            self._persist_and_refresh(full_render=True)
        except Exception as error:
            messagebox.showerror("Ошибка", str(error))

    def _export_tasks(self):
        path = filedialog.asksaveasfilename(title="Экспорт", defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not path:
            return
        try:
            data.export_tasks(self.tasks, path)
            messagebox.showinfo("Экспорт", "Экспорт выполнен")
        except Exception as error:
            messagebox.showerror("Ошибка", str(error))

    def _persist_and_refresh(self, full_render=False):
        if not data.save_tasks(self.tasks):
            messagebox.showerror("Ошибка", "Не удалось сохранить задачи")
        self._update_view(full_render=full_render)

    # ===== View =====
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
            delay = row * 20 if animated else 0
            self.root.after(delay, lambda r=row, t=task: self._create_card(r, t))

    def _create_card(self, row, task):
        colors = THEMES[self.theme_name]
        selected = self.selected_id == task["id"]
        base = colors["hover"] if selected else colors["task_card"]
        title_color = colors["danger"] if is_overdue(task) else colors["text"]

        card = tk.Frame(self.cards_inner, bg=base, padx=12, pady=10, highlightthickness=1, highlightbackground="#3b4b66")
        card.grid(row=row, column=0, sticky="ew", padx=8, pady=6)
        card.grid_columnconfigure(1, weight=1)

        marker = tk.Label(card, text="✅" if task["done"] else "⬜", bg=base, fg=colors["text"], font=("Segoe UI", 12))
        marker.grid(row=0, column=0, rowspan=2, padx=(0, 8), sticky="n")

        title = tk.Label(card, text=task["text"], bg=base, fg=title_color, font=("Segoe UI", 13, "bold"), anchor="w")
        title.grid(row=0, column=1, sticky="ew")

        meta = tk.Label(card, text=f"{task['category']} | {task['deadline']} | {task['priority']}", bg=base, fg=colors["muted"], font=("Segoe UI", 10), anchor="w")
        meta.grid(row=1, column=1, sticky="w", pady=(4, 0))

        done_btn = tk.Button(card, text="✔", width=3, command=lambda tid=task["id"]: self._toggle_done(tid), relief="flat", bd=0, cursor="hand2")
        del_btn = tk.Button(card, text="✖", width=3, command=lambda tid=task["id"]: self._delete_task(tid), relief="flat", bd=0, cursor="hand2")
        done_btn.grid(row=0, column=2, padx=(6, 2))
        del_btn.grid(row=1, column=2, padx=(6, 2), pady=(4, 0))

        self._style_task_action_btn(done_btn)
        self._style_task_action_btn(del_btn, danger=True)

        for widget in (card, marker, title, meta):
            widget.bind("<Button-1>", lambda _e, t=task: self._select_task(t))

        self._bind_card_hover(card, [card, marker, title, meta], base=base, hover=colors["hover"], selected=selected)

    def _style_task_action_btn(self, button, danger=False):
        colors = THEMES[self.theme_name]
        fg = colors["danger"] if danger else colors["text"]
        button.configure(bg=colors["accent"], fg=fg, activebackground=colors["hover"], activeforeground=fg, relief="flat", bd=0, font=("Segoe UI", 10))
        self._bind_button_hover(button)

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
        fresh = 0
        for task in self.tasks:
            if is_overdue(task) and task["id"] not in self.notified_overdue_ids:
                self.notified_overdue_ids.add(task["id"])
                fresh += 1
        if fresh:
            messagebox.showwarning("Новые просроченные", f"Стало просроченными задач: {fresh}")


def run_app():
    root = tk.Tk()
    TaskManagerApp(root)
    root.mainloop()

import tkinter as tk
from tkinter import filedialog, messagebox

import data
from logic import CATEGORIES, PRIORITIES, get_filtered_sorted_tasks, is_overdue, normalize_task, parse_deadline, tasks_for_today

THEMES = {
    "dark": {
        "bg": "#0f172a",
        "container": "#111827",
        "sidebar": "#1f2937",
        "panel": "#111827",
        "card": "#1f2937",
        "input": "#0b1220",
        "accent": "#6366f1",
        "hover": "#4f46e5",
        "text": "#e2e8f0",
        "muted": "#94a3b8",
        "danger": "#ef4444",
    }
}


class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Manager")
        self.root.geometry("1000x800")
        self.root.minsize(920, 700)
        self.theme_name = "dark"

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
        colors = THEMES[self.theme_name]
        self.root.configure(bg=colors["bg"])

        # centered container 70% width
        self.container = tk.Frame(
            self.root,
            bg=colors["container"],
            padx=14,
            pady=14,
            bd=0,
            highlightthickness=1,
            highlightbackground="#334155",
        )
        self.container.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.7, relheight=0.92)

        self.container.grid_columnconfigure(1, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        # sidebar fixed 200
        self.sidebar = tk.Frame(self.container, width=200, bd=0)
        self.sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)

        self.title_label = tk.Label(self.sidebar, text="Task Manager", font=("Segoe UI", 16, "bold"))
        self.title_label.grid(row=0, column=0, sticky="ew", pady=(8, 16))

        self.status_var = tk.StringVar(value="Все")
        self.btn_all = self._sidebar_button("Все", lambda: self._set_status("Все"), 1)
        self.btn_done = self._sidebar_button("Выполненные", lambda: self._set_status("Выполненные"), 2)
        self.btn_active = self._sidebar_button("Активные", lambda: self._set_status("Невыполненные"), 3)
        self.btn_import = self._sidebar_button("Импорт", self._import_tasks, 4)
        self.btn_export = self._sidebar_button("Экспорт", self._export_tasks, 5)

        # main area flex
        self.main = tk.Frame(self.container, bd=0)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)

        # Top input zone
        self.top_panel = tk.Frame(self.main, bd=0)
        self.top_panel.grid(row=0, column=0, sticky="ew")
        self.top_panel.grid_columnconfigure(0, weight=6)
        self.top_panel.grid_columnconfigure(1, weight=2)
        self.top_panel.grid_columnconfigure(2, weight=2)
        self.top_panel.grid_columnconfigure(3, weight=2)

        self.task_entry = tk.Entry(self.top_panel, bd=0, font=("Segoe UI", 12))
        self.deadline_entry = tk.Entry(self.top_panel, bd=0, font=("Segoe UI", 11))
        self.category_var = tk.StringVar(value="Личное")
        self.priority_var = tk.StringVar(value="Средний")
        self.category_menu = tk.OptionMenu(self.top_panel, self.category_var, *CATEGORIES)
        self.priority_menu = tk.OptionMenu(self.top_panel, self.priority_var, *PRIORITIES)

        self.task_entry.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 8), ipady=10)
        self.deadline_entry.grid(row=1, column=1, sticky="ew", padx=(0, 6), ipady=8)
        self.category_menu.grid(row=1, column=2, sticky="ew", padx=3)
        self.priority_menu.grid(row=1, column=3, sticky="ew", padx=(6, 0))

        self.add_btn = tk.Button(self.top_panel, text="Добавить", command=self._add_or_update_task, relief="flat", bd=0, cursor="hand2")
        self.add_btn.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(8, 10), ipady=8)

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(self.top_panel, textvariable=self.search_var, bd=0, font=("Segoe UI", 11))
        self.search_entry.grid(row=1, column=0, sticky="ew", padx=(0, 6), ipady=8)
        self.search_var.trace_add("write", lambda *_: self._update_view())

        self.sort_var = tk.StringVar(value="По дедлайну")
        self.sort_menu = tk.OptionMenu(self.top_panel, self.sort_var, "По дедлайну", "По приоритету", "По статусу", command=lambda _x: self._update_view())
        self.sort_menu.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(0, 10))

        self._set_placeholder(self.task_entry, "Введите задачу")
        self._set_placeholder(self.deadline_entry, "дд-мм-гггг")
        self._set_placeholder(self.search_entry, "Поиск")

        # scrollable list
        self.list_panel = tk.Frame(self.main, bd=0)
        self.list_panel.grid(row=1, column=0, sticky="nsew")
        self.list_panel.grid_rowconfigure(0, weight=1)
        self.list_panel.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.list_panel, highlightthickness=0)
        self.scroll = tk.Scrollbar(self.list_panel, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid(row=0, column=1, sticky="ns")

        self.cards_inner = tk.Frame(self.canvas, bd=0)
        self.window_id = self.canvas.create_window((0, 0), window=self.cards_inner, anchor="nw")
        self.cards_inner.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._sync_canvas_width)

        # stats bottom
        self.stats_var = tk.StringVar(value="Всего: 0 | Выполнено: 0 | 0% | Просрочено: 0")
        self.stats_label = tk.Label(self.main, textvariable=self.stats_var, font=("Segoe UI", 11, "bold"), anchor="center")
        self.stats_label.grid(row=2, column=0, sticky="ew", pady=(10, 0))

    def _sidebar_button(self, text, command, row):
        btn = tk.Button(self.sidebar, text=text, command=command, relief="flat", bd=0, cursor="hand2", font=("Segoe UI", 11), padx=10, pady=9)
        btn.grid(row=row, column=0, sticky="ew", pady=4)
        self._bind_button_hover(btn)
        return btn

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

    def _sync_canvas_width(self, event):
        self.canvas.itemconfig(self.window_id, width=event.width)

    def _set_status(self, value):
        self.status_var.set(value)
        self._update_view()

    def _task_filters(self):
        query = self.search_var.get()
        if self.search_entry.get() == self.search_entry._placeholder:
            query = ""
        return {"status": self.status_var.get(), "category": "Все", "priority": "Все", "query": query}

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
        self._clear_form()  # clear after add/update

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
        base = colors["hover"] if selected else colors["card"]
        title_color = colors["danger"] if is_overdue(task) else colors["text"]

        card = tk.Frame(self.cards_inner, bg=base, padx=14, pady=12, bd=0, highlightthickness=1, highlightbackground="#334155")
        card.grid(row=row, column=0, sticky="ew", padx=8, pady=4)  # 8px gap
        card.grid_columnconfigure(1, weight=1)

        title = tk.Label(card, text=task["text"], bg=base, fg=title_color, font=("Segoe UI", 13, "bold"), anchor="w")
        title.grid(row=0, column=0, columnspan=2, sticky="ew")

        meta_color = colors["danger"] if is_overdue(task) else colors["muted"]
        meta = tk.Label(card, text=f"{task['category']} | {task['deadline']} | {task['priority']}", bg=base, fg=meta_color, font=("Segoe UI", 10), anchor="w")
        meta.grid(row=1, column=0, sticky="w", pady=(6, 0))

        btns = tk.Frame(card, bg=base)
        btns.grid(row=1, column=1, sticky="e")

        done_btn = tk.Button(btns, text="✔", width=3, command=lambda tid=task["id"]: self._toggle_done(tid), relief="flat", bd=0, cursor="hand2")
        del_btn = tk.Button(btns, text="✖", width=3, command=lambda tid=task["id"]: self._delete_task(tid), relief="flat", bd=0, cursor="hand2")
        done_btn.grid(row=0, column=0, padx=(0, 6))
        del_btn.grid(row=0, column=1)

        self._style_button(done_btn)
        self._style_button(del_btn, danger=True)

        for widget in (card, title, meta):
            widget.bind("<Button-1>", lambda _e, t=task: self._select_task(t))

        self._bind_card_hover(card, [card, title, meta, btns], base=base, hover=colors["hover"], selected=selected)

    def _apply_theme(self):
        colors = THEMES[self.theme_name]
        self.root.configure(bg=colors["bg"])
        self.container.configure(bg=colors["container"])
        self.sidebar.configure(bg=colors["sidebar"])
        self.main.configure(bg=colors["panel"])
        self.top_panel.configure(bg=colors["panel"])
        self.io_row.configure(bg=colors["panel"])
        self.list_panel.configure(bg=colors["panel"])
        self.canvas.configure(bg=colors["panel"])
        self.cards_inner.configure(bg=colors["panel"])
        self.title_label.configure(bg=colors["sidebar"], fg=colors["text"])

        for entry in (self.task_entry, self.deadline_entry, self.search_entry):
            entry.configure(bg=colors["input"], fg=colors["text"], insertbackground=colors["text"], bd=0)

        for menu in (self.category_menu, self.priority_menu, self.status_menu, self.sort_menu):
            menu.configure(bg=colors["input"], fg=colors["text"], activebackground=colors["hover"], relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 11))
            menu["menu"].configure(bg=colors["input"], fg=colors["text"], activebackground=colors["hover"])

        self._style_button(self.add_btn)
        self._style_button(self.import_btn)
        self._style_button(self.export_btn)
        for btn in (self.btn_all, self.btn_done, self.btn_active):
            self._style_button(btn)
        self._style_button(self.btn_import)
        self._style_button(self.btn_export)

        self.stats_label.configure(bg=colors["panel"], fg=colors["muted"])

    def _style_button(self, button, danger=False):
        colors = THEMES[self.theme_name]
        fg = colors["danger"] if danger else colors["text"]
        button.configure(bg=colors["accent"], fg=fg, activebackground=colors["hover"], activeforeground=fg, relief="flat", bd=0)
        self._bind_button_hover(button)

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

    def _animate_color(self, widget, start_hex, end_hex, steps=6, duration=120, apply_fn=None):
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

    def _show_startup_notifications(self):
        overdue = sum(1 for t in self.tasks if is_overdue(t))
        today = len(tasks_for_today(self.tasks))
        if overdue:
            messagebox.showwarning("Просроченные", f"Просроченных задач: {overdue}")
        if today:
            messagebox.showinfo("Сегодня", f"Задач на сегодня: {today}")

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

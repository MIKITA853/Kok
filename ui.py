import tkinter as tk
from tkinter import filedialog, messagebox

import data
from logic import CATEGORIES, PRIORITIES, get_filtered_sorted_tasks, is_overdue, normalize_task, parse_deadline, tasks_for_today

THEMES = {
    "dark": {
        "bg": "#2b1e17",
        "sidebar": "#3a2a21",
        "card": "#4b362b",
        "hover": "#5a4033",
        "accent": "#a9745b",
        "text": "#f5e6d3",
        "muted": "#c2a78f",
        "danger": "#ff6b6b",
    },
    "light": {
        "bg": "#f4eadf",
        "sidebar": "#e7d7c7",
        "card": "#fff7ee",
        "hover": "#efdfcf",
        "accent": "#c89b7b",
        "text": "#3a2a21",
        "muted": "#7a6556",
        "danger": "#d9534f",
    },
}


class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Manager")
        self.root.geometry("1220x760")
        self.root.minsize(980, 620)

        cfg = data.load_config()
        self.theme_name = cfg.get("theme", "dark") if cfg.get("theme", "dark") in THEMES else "dark"

        self.tasks = [normalize_task(t) for t in data.load_tasks() if isinstance(t, dict)]
        self.selected_id = None
        self.card_widgets = {}
        self.visible_tasks = []
        self.notified_overdue_ids = set()

        self._build_ui()
        self._apply_theme()
        self._update_view(full_render=True)
        self._show_startup_notifications()
        self._schedule_deadline_check()

    def _build_ui(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        self.sidebar = tk.Frame(self.root, width=210)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        self.content = tk.Frame(self.root)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_rowconfigure(1, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        # Sidebar
        self.title_label = tk.Label(self.sidebar, text="Task Manager", font=("Segoe UI", 15, "bold"))
        self.title_label.grid(row=0, column=0, sticky="w", padx=14, pady=(16, 22))

        self.filter_status_var = tk.StringVar(value="Все")
        self.btn_all = self._side_button("Все задачи", lambda: self._set_status_filter("Все"), 1)
        self.btn_done = self._side_button("Выполненные", lambda: self._set_status_filter("Выполненные"), 2)
        self.btn_todo = self._side_button("Невыполненные", lambda: self._set_status_filter("Невыполненные"), 3)
        self.btn_theme = self._side_button("Сменить тему", self._toggle_theme, 4)
        self.btn_import = self._side_button("Импорт", self._import_tasks, 5)
        self.btn_export = self._side_button("Экспорт", self._export_tasks, 6)

        # Top filters/input
        self.top_panel = tk.Frame(self.content)
        self.top_panel.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        for c, w in enumerate([5, 2, 2, 2, 2, 2, 2, 2]):
            self.top_panel.grid_columnconfigure(c, weight=w)

        self.task_entry = tk.Entry(self.top_panel)
        self.deadline_entry = tk.Entry(self.top_panel)
        self.category_var = tk.StringVar(value="Личное")
        self.priority_var = tk.StringVar(value="Средний")
        self.sort_var = tk.StringVar(value="По дедлайну")
        self.search_var = tk.StringVar()

        self.category_menu = tk.OptionMenu(self.top_panel, self.category_var, *CATEGORIES)
        self.priority_menu = tk.OptionMenu(self.top_panel, self.priority_var, *PRIORITIES)
        self.status_menu = tk.OptionMenu(self.top_panel, self.filter_status_var, "Все", "Выполненные", "Невыполненные", command=lambda _x: self._update_view())
        self.category_filter_var = tk.StringVar(value="Все")
        self.category_filter_menu = tk.OptionMenu(self.top_panel, self.category_filter_var, "Все", *CATEGORIES, command=lambda _x: self._update_view())
        self.priority_filter_var = tk.StringVar(value="Все")
        self.priority_filter_menu = tk.OptionMenu(self.top_panel, self.priority_filter_var, "Все", *PRIORITIES, command=lambda _x: self._update_view())
        self.sort_menu = tk.OptionMenu(self.top_panel, self.sort_var, "По дедлайну", "По приоритету", "По статусу", command=lambda _x: self._update_view())

        self.add_btn = tk.Button(self.top_panel, text="Добавить", command=self._add_or_update_task, relief="flat", bd=0)

        self._label(self.top_panel, "Задача").grid(row=0, column=0, sticky="w", padx=4)
        self._label(self.top_panel, "Дедлайн").grid(row=0, column=1, sticky="w", padx=4)
        self._label(self.top_panel, "Категория").grid(row=0, column=2, sticky="w", padx=4)
        self._label(self.top_panel, "Приоритет").grid(row=0, column=3, sticky="w", padx=4)
        self._label(self.top_panel, "Статус").grid(row=0, column=4, sticky="w", padx=4)
        self._label(self.top_panel, "Катег. фильтр").grid(row=0, column=5, sticky="w", padx=4)
        self._label(self.top_panel, "Приор. фильтр").grid(row=0, column=6, sticky="w", padx=4)
        self._label(self.top_panel, "Сортировка").grid(row=0, column=7, sticky="w", padx=4)

        self.task_entry.grid(row=1, column=0, sticky="ew", padx=4)
        self.deadline_entry.grid(row=1, column=1, sticky="ew", padx=4)
        self.category_menu.grid(row=1, column=2, sticky="ew", padx=4)
        self.priority_menu.grid(row=1, column=3, sticky="ew", padx=4)
        self.status_menu.grid(row=1, column=4, sticky="ew", padx=4)
        self.category_filter_menu.grid(row=1, column=5, sticky="ew", padx=4)
        self.priority_filter_menu.grid(row=1, column=6, sticky="ew", padx=4)
        self.sort_menu.grid(row=1, column=7, sticky="ew", padx=4)

        self.add_btn.grid(row=2, column=0, sticky="ew", padx=4, pady=8)

        self.search_entry = tk.Entry(self.top_panel, textvariable=self.search_var)
        self.search_entry.grid(row=2, column=1, columnspan=7, sticky="ew", padx=4, pady=8)

        self._set_placeholder(self.task_entry, "Введите задачу...")
        self._set_placeholder(self.deadline_entry, "дд-мм-гггг")
        self._set_placeholder(self.search_entry, "Поиск...")

        self.search_var.trace_add("write", lambda *_: self._update_view())

        # Scrollable cards
        self.cards_wrap = tk.Frame(self.content)
        self.cards_wrap.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.cards_wrap.grid_rowconfigure(0, weight=1)
        self.cards_wrap.grid_columnconfigure(0, weight=1)

        self.cards_canvas = tk.Canvas(self.cards_wrap, highlightthickness=0)
        self.cards_scroll = tk.Scrollbar(self.cards_wrap, orient="vertical", command=self.cards_canvas.yview)
        self.cards_canvas.configure(yscrollcommand=self.cards_scroll.set)
        self.cards_canvas.grid(row=0, column=0, sticky="nsew")
        self.cards_scroll.grid(row=0, column=1, sticky="ns")

        self.cards_inner = tk.Frame(self.cards_canvas)
        self.cards_window_id = self.cards_canvas.create_window((0, 0), window=self.cards_inner, anchor="nw")
        self.cards_inner.bind("<Configure>", lambda _e: self.cards_canvas.configure(scrollregion=self.cards_canvas.bbox("all")))
        self.cards_canvas.bind("<Configure>", self._sync_canvas_width)

        # Bottom stats
        self.bottom_panel = tk.Frame(self.content)
        self.bottom_panel.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.bottom_panel.grid_columnconfigure(0, weight=1)
        self.stats_var = tk.StringVar(value="Всего: 0 | Выполнено: 0 | 0% | Просрочено: 0")
        self.stats_label = tk.Label(self.bottom_panel, textvariable=self.stats_var, anchor="w", font=("Segoe UI", 11, "bold"), padx=10, pady=8)
        self.stats_label.grid(row=0, column=0, sticky="ew")

    def _label(self, parent, text):
        return tk.Label(parent, text=text, font=("Segoe UI", 11))

    def _side_button(self, text, cmd, row):
        btn = tk.Button(self.sidebar, text=text, command=cmd, relief="flat", bd=0, cursor="hand2", padx=10, pady=9)
        btn.grid(row=row, column=0, sticky="ew", padx=12, pady=5)
        self._bind_button_hover(btn)
        return btn

    def _sync_canvas_width(self, event):
        self.cards_canvas.itemconfig(self.cards_window_id, width=event.width)

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

    def _toggle_theme(self):
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        data.save_config({"theme": self.theme_name})
        self._apply_theme()
        self._update_view(full_render=True)

    def _set_status_filter(self, status_value):
        self.filter_status_var.set(status_value)
        self._update_view()

    def _task_filters(self):
        return {
            "status": self.filter_status_var.get(),
            "category": self.category_filter_var.get(),
            "priority": self.priority_filter_var.get(),
            "query": self.search_var.get() if self.search_entry.get() != self.search_entry._placeholder else "",
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

        self._save_and_refresh(full_render=True)
        self._clear_form()

    def _clear_form(self):
        self.selected_id = None
        self.task_entry.delete(0, tk.END)
        self.task_entry.insert(0, self.task_entry._placeholder)
        self.deadline_entry.delete(0, tk.END)
        self.deadline_entry.insert(0, self.deadline_entry._placeholder)
        self.category_var.set("Личное")
        self.priority_var.set("Средний")
        self.add_btn.config(text="Добавить")

    def _select_task(self, task):
        self.selected_id = task["id"]
        self.task_entry.delete(0, tk.END)
        self.task_entry.insert(0, task["text"])
        self.deadline_entry.delete(0, tk.END)
        self.deadline_entry.insert(0, task["deadline"])
        self.category_var.set(task["category"])
        self.priority_var.set(task["priority"])
        self.add_btn.config(text="Сохранить")
        self._update_view(full_render=True)

    def _toggle_done(self, task_id):
        for task in self.tasks:
            if task["id"] == task_id:
                task["done"] = not task["done"]
                break
        self._save_and_refresh(full_render=False)

    def _delete_task(self, task_id):
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        if self.selected_id == task_id:
            self._clear_form()
        self._save_and_refresh(full_render=True)

    def _save_and_refresh(self, full_render=False):
        ok = data.save_tasks(self.tasks)
        if not ok:
            messagebox.showerror("Ошибка", "Не удалось сохранить задачи")
        self._update_view(full_render=full_render)

    def _import_tasks(self):
        fp = filedialog.askopenfilename(title="Импорт", filetypes=[("JSON files", "*.json")])
        if not fp:
            return
        try:
            loaded = data.import_tasks(fp)
            self.tasks = [normalize_task(t) for t in loaded if isinstance(t, dict)]
            self._save_and_refresh(full_render=True)
        except Exception as error:
            messagebox.showerror("Ошибка", str(error))

    def _export_tasks(self):
        fp = filedialog.asksaveasfilename(title="Экспорт", defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not fp:
            return
        try:
            data.export_tasks(self.tasks, fp)
            messagebox.showinfo("Экспорт", "Экспорт выполнен")
        except Exception as error:
            messagebox.showerror("Ошибка", str(error))

    def _update_view(self, full_render=False):
        self.visible_tasks = get_filtered_sorted_tasks(self.tasks, self._task_filters(), self.sort_var.get())
        self._update_stats()
        if full_render:
            self._render_cards(animated=True)
        else:
            self._render_cards(animated=False)

    def _update_stats(self):
        total = len(self.tasks)
        done = sum(1 for t in self.tasks if t["done"])
        overdue = sum(1 for t in self.tasks if is_overdue(t))
        percent = int((done / total) * 100) if total else 0
        self.stats_var.set(f"Всего: {total} | Выполнено: {done} | {percent}% | Просрочено: {overdue}")

    def _render_cards(self, animated=False):
        for w in self.cards_inner.winfo_children():
            w.destroy()
        self.card_widgets.clear()

        for row, task in enumerate(self.visible_tasks):
            delay = row * 20 if animated else 0
            self.root.after(delay, lambda r=row, t=task: self._create_card(r, t))

    def _create_card(self, row, task):
        colors = THEMES[self.theme_name]
        selected = task["id"] == self.selected_id
        bg = colors["hover"] if selected else colors["card"]
        title_color = colors["danger"] if is_overdue(task) else colors["text"]

        outer = tk.Frame(self.cards_inner, bg=colors["bg"], padx=1, pady=1)
        outer.grid(row=row, column=0, sticky="ew", padx=8, pady=6)
        card = tk.Frame(outer, bg=bg, bd=0, relief="flat")
        card.grid(row=0, column=0, sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        check = tk.Button(card, text="✅" if task["done"] else "⬜", command=lambda tid=task["id"]: self._toggle_done(tid), width=3, relief="flat", bd=0, cursor="hand2")
        check.grid(row=0, column=0, rowspan=2, padx=(8, 6), pady=8, sticky="n")

        title = tk.Label(card, text=task["text"], anchor="w", font=("Segoe UI", 13, "bold"), fg=title_color, bg=bg)
        title.grid(row=0, column=1, sticky="ew", pady=(8, 2))

        meta = tk.Label(card, text=f"{task['category']} | {task['deadline']} | {task['priority']}", anchor="w", font=("Segoe UI", 11), fg=colors["muted"], bg=bg)
        meta.grid(row=1, column=1, sticky="w", pady=(0, 8))

        done_btn = tk.Button(card, text="✔", width=3, command=lambda tid=task["id"]: self._toggle_done(tid), relief="flat", bd=0, cursor="hand2")
        del_btn = tk.Button(card, text="✖", width=3, command=lambda tid=task["id"]: self._delete_task(tid), relief="flat", bd=0, cursor="hand2")
        done_btn.grid(row=0, column=2, padx=4, pady=(8, 2))
        del_btn.grid(row=1, column=2, padx=4, pady=(0, 8))

        for widget in (card, title, meta):
            widget.bind("<Button-1>", lambda _e, t=task: self._select_task(t))

        self._bind_card_hover(card, [card, title, meta], base=bg, hover=colors["hover"], sticky_selected=selected)
        self._style_action_buttons(check, done_btn, del_btn)
        self.card_widgets[task["id"]] = card

    def _style_action_buttons(self, check_btn, done_btn, del_btn):
        colors = THEMES[self.theme_name]
        for b in (check_btn, done_btn, del_btn):
            b.configure(bg=colors["accent"], fg="#1e1e1e", activebackground=colors["hover"], activeforeground="#1e1e1e")
            self._bind_button_hover(b)
        del_btn.configure(fg=colors["danger"], activeforeground=colors["danger"])

    def _hex_to_rgb(self, h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(self, rgb):
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    def _animate_color(self, widget, start_hex, end_hex, steps=6, duration=120, apply_fn=None):
        start = self._hex_to_rgb(start_hex)
        end = self._hex_to_rgb(end_hex)
        delay = max(1, duration // steps)

        def step(i=0):
            ratio = i / steps
            rgb = tuple(int(start[c] + (end[c] - start[c]) * ratio) for c in range(3))
            if apply_fn:
                apply_fn(self._rgb_to_hex(rgb))
            else:
                widget.configure(bg=self._rgb_to_hex(rgb))
            if i < steps:
                self.root.after(delay, lambda: step(i + 1))

        step(0)

    def _bind_card_hover(self, card, widgets, base, hover, sticky_selected=False):
        def set_bg(color):
            for w in widgets:
                w.configure(bg=color)

        def on_enter(_):
            if sticky_selected:
                return
            self._animate_color(card, base, hover, apply_fn=set_bg)

        def on_leave(_):
            if sticky_selected:
                return
            self._animate_color(card, hover, base, apply_fn=set_bg)

        for w in widgets:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)

    def _bind_button_hover(self, button):
        colors = THEMES[self.theme_name]

        def on_enter(_):
            self._animate_color(button, colors["accent"], colors["hover"])

        def on_leave(_):
            self._animate_color(button, colors["hover"], colors["accent"])

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

    def _apply_theme(self):
        colors = THEMES[self.theme_name]
        self.root.configure(bg=colors["bg"])
        self.sidebar.configure(bg=colors["sidebar"])
        self.content.configure(bg=colors["bg"])
        self.top_panel.configure(bg=colors["bg"])
        self.cards_wrap.configure(bg=colors["bg"])
        self.cards_inner.configure(bg=colors["bg"])
        self.bottom_panel.configure(bg=colors["sidebar"])

        self.title_label.configure(bg=colors["sidebar"], fg=colors["text"])
        for w in self.top_panel.winfo_children():
            if isinstance(w, tk.Label):
                w.configure(bg=colors["bg"], fg=colors["text"], font=("Segoe UI", 11))
        for e in (self.task_entry, self.deadline_entry, self.search_entry):
            e.configure(bg=colors["card"], fg=colors["text"], insertbackground=colors["text"], relief="flat", bd=0, font=("Segoe UI", 11))

        for menu in (self.category_menu, self.priority_menu, self.status_menu, self.category_filter_menu, self.priority_filter_menu, self.sort_menu):
            menu.configure(bg=colors["card"], fg=colors["text"], activebackground=colors["hover"], relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 11))
            menu["menu"].configure(bg=colors["card"], fg=colors["text"], activebackground=colors["hover"])

        for b in (self.btn_all, self.btn_done, self.btn_todo, self.btn_theme, self.btn_import, self.btn_export, self.add_btn):
            b.configure(bg=colors["accent"], fg="#1e1e1e", activebackground=colors["hover"], relief="flat", bd=0, font=("Segoe UI", 11))

        self.stats_label.configure(bg=colors["sidebar"], fg=colors["text"])
        self.cards_canvas.configure(bg=colors["bg"])

    def _show_startup_notifications(self):
        overdue = [t for t in self.tasks if is_overdue(t)]
        today_tasks = tasks_for_today(self.tasks)
        if overdue:
            messagebox.showwarning("Просроченные", f"Просроченных задач: {len(overdue)}")
        if today_tasks:
            messagebox.showinfo("Напоминания", f"Задач на сегодня: {len(today_tasks)}")

    def _schedule_deadline_check(self):
        self._check_new_overdues()
        self.root.after(60_000, self._schedule_deadline_check)

    def _check_new_overdues(self):
        fresh = []
        for task in self.tasks:
            if is_overdue(task) and task["id"] not in self.notified_overdue_ids:
                self.notified_overdue_ids.add(task["id"])
                fresh.append(task)
        if fresh:
            messagebox.showwarning("Новые просроченные", f"Стало просроченными задач: {len(fresh)}")


def run_app():
    root = tk.Tk()
    TaskManagerApp(root)
    root.mainloop()

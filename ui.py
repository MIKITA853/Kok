import calendar
import tkinter as tk
from datetime import date, datetime
from tkinter import filedialog, messagebox

import data
from logic import CATEGORIES, PRIORITIES, get_filtered_sorted_tasks, is_overdue, normalize_task, tasks_for_today

COLORS = {
    "bg": "#0f172a",
    "card": "#1e293b",
    "input": "#0b1220",
    "accent": "#6366f1",
    "hover": "#4f46e5",
    "text": "#e2e8f0",
    "muted": "#94a3b8",
    "danger": "#ef4444",
    "task_card": "#273449",
}


class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Manager")
        self.root.geometry("1100x800")
        self.root.minsize(980, 760)

        self.tasks = [normalize_task(t) for t in data.load_tasks() if isinstance(t, dict)]
        self.visible_tasks = []
        self.selected_id = None
        self.notified_overdue_ids = set()
        self.selected_deadline = "без срока"

        self._build_ui()
        self._apply_theme()
        self.refresh_ui(full_render=True)
        self._show_startup_notifications()
        self._schedule_deadline_check()

    # ===== UI =====
    def _build_ui(self):
        self.root.configure(bg=COLORS["bg"])

        self.container = tk.Frame(
            self.root,
            width=800,
            height=700,
            bg=COLORS["card"],
            padx=18,
            pady=18,
            highlightthickness=1,
            highlightbackground="#334155",
        )
        self.container.place(relx=0.5, rely=0.5, anchor="center")
        self.container.grid_propagate(False)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(4, weight=1)

        self.title_label = tk.Label(self.container, text="Task Manager", font=("Segoe UI", 20, "bold"), anchor="center")
        self.title_label.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        self.input_zone = tk.Frame(self.container)
        self.input_zone.grid(row=1, column=0, sticky="ew")
        self.input_zone.grid_columnconfigure(0, weight=6)
        self.input_zone.grid_columnconfigure(1, weight=2)
        self.input_zone.grid_columnconfigure(2, weight=2)
        self.input_zone.grid_columnconfigure(3, weight=2)
        self.input_zone.grid_columnconfigure(4, weight=2)

        self.task_entry = tk.Entry(self.input_zone, font=("Segoe UI", 12), bd=0)
        self.task_entry.grid(row=0, column=0, columnspan=5, sticky="ew", pady=(0, 10), ipady=10)

        self.deadline_entry = tk.Entry(self.input_zone, font=("Segoe UI", 11), bd=0, state="readonly")
        self.deadline_entry.grid(row=1, column=0, sticky="ew", padx=(0, 6), ipady=8)
        self.calendar_btn = tk.Button(self.input_zone, text="📅", command=self._open_calendar, relief="flat", bd=0, cursor="hand2")
        self.calendar_btn.grid(row=1, column=1, sticky="ew", padx=(0, 6))

        self.category_var = tk.StringVar(value="Личное")
        self.priority_var = tk.StringVar(value="Средний")
        self.filter_var = tk.StringVar(value="Все")

        self.category_menu = tk.OptionMenu(self.input_zone, self.category_var, *CATEGORIES)
        self.priority_menu = tk.OptionMenu(self.input_zone, self.priority_var, *PRIORITIES)
        self.filter_menu = tk.OptionMenu(self.input_zone, self.filter_var, "Все", "Выполненные", "Невыполненные", command=lambda _x: self.refresh_ui())

        self.category_menu.grid(row=1, column=2, sticky="ew", padx=3)
        self.priority_menu.grid(row=1, column=3, sticky="ew", padx=3)
        self.filter_menu.grid(row=1, column=4, sticky="ew", padx=(3, 0))

        self.add_btn = tk.Button(self.input_zone, text="Добавить", command=self._add_or_update_task, relief="flat", bd=0, cursor="hand2")
        self.add_btn.grid(row=2, column=0, columnspan=5, sticky="ew", pady=(10, 10), ipady=8)

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(self.input_zone, textvariable=self.search_var, font=("Segoe UI", 11), bd=0)
        self.search_entry.grid(row=3, column=0, columnspan=5, sticky="ew", pady=(0, 10), ipady=8)
        self.search_var.trace_add("write", lambda *_: self.refresh_ui())

        self.io_zone = tk.Frame(self.container)
        self.io_zone.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.io_zone.grid_columnconfigure(0, weight=1)
        self.io_zone.grid_columnconfigure(1, weight=1)
        self.import_btn = tk.Button(self.io_zone, text="Импорт", command=self._import_tasks, relief="flat", bd=0, cursor="hand2")
        self.export_btn = tk.Button(self.io_zone, text="Экспорт", command=self._export_tasks, relief="flat", bd=0, cursor="hand2")
        self.import_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.export_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.sort_var = tk.StringVar(value="По дедлайну")
        self.sort_menu = tk.OptionMenu(self.container, self.sort_var, "По дедлайну", "По приоритету", "По статусу", command=lambda _x: self.refresh_ui())
        self.sort_menu.grid(row=3, column=0, sticky="ew", pady=(0, 10))

        # list with scroll
        self.list_zone = tk.Frame(self.container)
        self.list_zone.grid(row=4, column=0, sticky="nsew")
        self.list_zone.grid_rowconfigure(0, weight=1)
        self.list_zone.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.list_zone, highlightthickness=0)
        self.scroll = tk.Scrollbar(self.list_zone, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid(row=0, column=1, sticky="ns")

        self.cards_inner = tk.Frame(self.canvas)
        self.window_id = self.canvas.create_window((0, 0), window=self.cards_inner, anchor="nw")
        self.cards_inner.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._sync_canvas_width)

        self.stats_var = tk.StringVar(value="Всего: 0 | Выполнено: 0 | 0% | Просрочено: 0")
        self.stats_label = tk.Label(self.container, textvariable=self.stats_var, font=("Segoe UI", 10, "bold"), anchor="center")
        self.stats_label.grid(row=5, column=0, sticky="ew", pady=(10, 0))

        self._set_placeholder(self.task_entry, "Введите задачу")
        self._set_placeholder(self.search_entry, "Поиск")
        self._set_deadline_text("дд-мм-гггг")

    # ===== Calendar =====
    def _open_calendar(self):
        now = datetime.now()
        self.cal_year = now.year
        self.cal_month = now.month

        self.calendar_win = tk.Toplevel(self.root)
        self.calendar_win.title("Выберите дату")
        self.calendar_win.transient(self.root)
        self.calendar_win.grab_set()
        self.calendar_win.configure(bg=COLORS["card"])

        self.cal_header = tk.Frame(self.calendar_win, bg=COLORS["card"])
        self.cal_header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.cal_header.grid_columnconfigure(1, weight=1)

        tk.Button(self.cal_header, text="<", command=lambda: self._change_month(-1), relief="flat", bd=0).grid(row=0, column=0)
        self.cal_label = tk.Label(self.cal_header, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 11, "bold"))
        self.cal_label.grid(row=0, column=1)
        tk.Button(self.cal_header, text=">", command=lambda: self._change_month(1), relief="flat", bd=0).grid(row=0, column=2)

        self.cal_grid = tk.Frame(self.calendar_win, bg=COLORS["card"])
        self.cal_grid.grid(row=1, column=0, padx=10, pady=(0, 10))

        self._draw_calendar()

    def _change_month(self, delta):
        self.cal_month += delta
        if self.cal_month < 1:
            self.cal_month = 12
            self.cal_year -= 1
        elif self.cal_month > 12:
            self.cal_month = 1
            self.cal_year += 1
        self._draw_calendar()

    def _draw_calendar(self):
        for w in self.cal_grid.winfo_children():
            w.destroy()

        self.cal_label.config(text=f"{calendar.month_name[self.cal_month]} {self.cal_year}")
        days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        for i, d in enumerate(days):
            tk.Label(self.cal_grid, text=d, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold")).grid(row=0, column=i, padx=2, pady=2)

        month = calendar.monthcalendar(self.cal_year, self.cal_month)
        for r, week in enumerate(month, start=1):
            for c, day in enumerate(week):
                if day == 0:
                    tk.Label(self.cal_grid, text="", bg=COLORS["card"], width=3).grid(row=r, column=c)
                    continue
                tk.Button(
                    self.cal_grid,
                    text=str(day),
                    width=3,
                    relief="flat",
                    bd=0,
                    bg=COLORS["input"],
                    fg=COLORS["text"],
                    activebackground=COLORS["hover"],
                    command=lambda dd=day: self._pick_date(dd),
                ).grid(row=r, column=c, padx=1, pady=1)

    def _pick_date(self, day):
        chosen = date(self.cal_year, self.cal_month, day)
        self.selected_deadline = chosen.strftime("%d-%m-%Y")
        self._set_deadline_text(self.selected_deadline)
        self.calendar_win.destroy()

    # ===== Theming / helpers =====
    def _apply_theme(self):
        self.root.configure(bg=COLORS["bg"])
        self.container.configure(bg=COLORS["card"])
        self.input_zone.configure(bg=COLORS["card"])
        self.io_zone.configure(bg=COLORS["card"])
        self.list_zone.configure(bg=COLORS["card"])
        self.cards_inner.configure(bg=COLORS["card"])
        self.canvas.configure(bg=COLORS["card"])
        self.title_label.configure(bg=COLORS["card"], fg=COLORS["text"])

        for entry in (self.task_entry, self.search_entry):
            entry.configure(bg=COLORS["input"], fg=COLORS["text"], insertbackground=COLORS["text"], bd=0)

        self.deadline_entry.configure(readonlybackground=COLORS["input"], fg=COLORS["text"], bd=0)

        for menu in (self.category_menu, self.priority_menu, self.filter_menu, self.sort_menu):
            menu.configure(bg=COLORS["input"], fg=COLORS["text"], activebackground=COLORS["hover"], relief="flat", bd=0, highlightthickness=0)
            menu["menu"].configure(bg=COLORS["input"], fg=COLORS["text"], activebackground=COLORS["hover"])

        for btn in (self.add_btn, self.calendar_btn, self.import_btn, self.export_btn):
            self._style_button(btn)

        self.stats_label.configure(bg=COLORS["card"], fg=COLORS["muted"])

    def _style_button(self, button, danger=False):
        fg = COLORS["danger"] if danger else COLORS["text"]
        button.configure(bg=COLORS["accent"], fg=fg, activebackground=COLORS["hover"], activeforeground=fg, relief="flat", bd=0)
        self._bind_button_hover(button)

    def _bind_button_hover(self, button):
        def on_enter(_):
            self._animate_color(button, COLORS["accent"], COLORS["hover"])

        def on_leave(_):
            self._animate_color(button, COLORS["hover"], COLORS["accent"])

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

    def _bind_card_hover(self, card, widgets, base):
        def apply_bg(color):
            for widget in widgets:
                widget.configure(bg=color)

        def on_enter(_):
            self._animate_color(card, base, COLORS["hover"], apply_fn=apply_bg)

        def on_leave(_):
            self._animate_color(card, COLORS["hover"], base, apply_fn=apply_bg)

        for widget in widgets:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

    def _hex_to_rgb(self, color):
        color = color.lstrip("#")
        return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(self, rgb):
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    def _animate_color(self, widget, start_hex, end_hex, steps=6, duration=120, apply_fn=None):
        s = self._hex_to_rgb(start_hex)
        e = self._hex_to_rgb(end_hex)
        delay = max(1, duration // steps)

        def step(i=0):
            ratio = i / steps
            rgb = tuple(int(s[c] + (e[c] - s[c]) * ratio) for c in range(3))
            color = self._rgb_to_hex(rgb)
            if apply_fn:
                apply_fn(color)
            else:
                widget.configure(bg=color)
            if i < steps:
                self.root.after(delay, lambda: step(i + 1))

        step(0)

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

    def _set_deadline_text(self, value):
        self.deadline_entry.configure(state="normal")
        self.deadline_entry.delete(0, tk.END)
        self.deadline_entry.insert(0, value)
        self.deadline_entry.configure(state="readonly")

    def _sync_canvas_width(self, event):
        self.canvas.itemconfig(self.window_id, width=event.width)

    # ===== Logic =====
    def _task_filters(self):
        query = self.search_var.get()
        if self.search_entry.get() == self.search_entry._placeholder:
            query = ""
        return {
            "status": self.filter_var.get(),
            "category": "Все",
            "priority": "Все",
            "query": query,
        }

    def _add_or_update_task(self):
        text = self.task_entry.get().strip()
        if text == self.task_entry._placeholder:
            text = ""
        if not text:
            messagebox.showwarning("Ошибка", "Введите задачу")
            return

        deadline = self.selected_deadline if self.selected_deadline != "без срока" else "без срока"

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

        data.save_tasks(self.tasks)
        self._clear_form()
        self.refresh_ui(full_render=True)

    def _clear_form(self):
        self.selected_id = None
        self.task_entry.delete(0, tk.END)
        self.task_entry.insert(0, self.task_entry._placeholder)
        self.selected_deadline = "без срока"
        self._set_deadline_text("дд-мм-гггг")
        self.category_var.set("Личное")
        self.priority_var.set("Средний")
        self.add_btn.configure(text="Добавить")

    def _select_task(self, task):
        self.selected_id = task["id"]
        self.task_entry.delete(0, tk.END)
        self.task_entry.insert(0, task["text"])
        self.selected_deadline = task["deadline"]
        self._set_deadline_text(task["deadline"])
        self.category_var.set(task["category"])
        self.priority_var.set(task["priority"])
        self.add_btn.configure(text="Сохранить")

    def _toggle_done(self, task_id):
        for task in self.tasks:
            if task["id"] == task_id:
                task["done"] = not task["done"]
                break
        data.save_tasks(self.tasks)
        self.refresh_ui()

    def _delete_task(self, task_id):
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        if self.selected_id == task_id:
            self._clear_form()
        data.save_tasks(self.tasks)
        self.refresh_ui(full_render=True)

    def _import_tasks(self):
        path = filedialog.askopenfilename(title="Импорт", filetypes=[("JSON files", "*.json")])
        if not path:
            return
        try:
            loaded = data.import_tasks(path)
            self.tasks = [normalize_task(t) for t in loaded if isinstance(t, dict)]
            data.save_tasks(self.tasks)
            self.refresh_ui(full_render=True)
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

    def refresh_ui(self, full_render=False):
        self.visible_tasks = get_filtered_sorted_tasks(self.tasks, self._task_filters(), self.sort_var.get())
        self._update_stats()
        self._render_cards(animated=full_render)

    def _update_stats(self):
        total = len(self.tasks)
        done = sum(1 for t in self.tasks if t["done"])
        percent = int((done / total) * 100) if total else 0
        overdue = sum(1 for t in self.tasks if is_overdue(t))
        self.stats_var.set(f"Всего: {total} | Выполнено: {done} | {percent}% | Просрочено: {overdue}")

    def _render_cards(self, animated=False):
        for widget in self.cards_inner.winfo_children():
            widget.destroy()

        for row, task in enumerate(self.visible_tasks):
            delay = row * 20 if animated else 0
            self.root.after(delay, lambda r=row, t=task: self._create_card(r, t))

    def _create_card(self, row, task):
        base = COLORS["task_card"]
        title_color = COLORS["danger"] if is_overdue(task) else COLORS["text"]
        meta_color = COLORS["danger"] if is_overdue(task) else COLORS["muted"]

        card = tk.Frame(self.cards_inner, bg=base, padx=14, pady=12, highlightthickness=1, highlightbackground="#334155")
        card.grid(row=row, column=0, sticky="ew", padx=10, pady=4)
        card.grid_columnconfigure(1, weight=1)

        title = tk.Label(card, text=task["text"], bg=base, fg=title_color, font=("Segoe UI", 13, "bold"), anchor="w")
        title.grid(row=0, column=0, columnspan=2, sticky="ew")

        meta = tk.Label(card, text=f"{task['category']} | {task['deadline']} | {task['priority']}", bg=base, fg=meta_color, font=("Segoe UI", 10), anchor="w")
        meta.grid(row=1, column=0, sticky="w", pady=(6, 0))

        btns = tk.Frame(card, bg=base)
        btns.grid(row=1, column=1, sticky="e")

        done_btn = tk.Button(btns, text="✔", width=3, relief="flat", bd=0, cursor="hand2", command=lambda tid=task["id"]: self._toggle_done(tid))
        del_btn = tk.Button(btns, text="✖", width=3, relief="flat", bd=0, cursor="hand2", command=lambda tid=task["id"]: self._delete_task(tid))
        done_btn.grid(row=0, column=0, padx=(0, 6))
        del_btn.grid(row=0, column=1)

        self._style_button(done_btn)
        self._style_button(del_btn, danger=True)

        for widget in (card, title, meta):
            widget.bind("<Button-1>", lambda _e, t=task: self._select_task(t))

        self._bind_card_hover(card, [card, title, meta, btns], base)

    # ===== Notifications =====
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

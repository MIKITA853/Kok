import json
import os
import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import messagebox, ttk
from uuid import uuid4

FILE_NAME = "tasks.json"
DATE_FMT = "%Y-%m-%d"
TIME_FMT = "%H:%M"


class TaskCalendarApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Task Calendar")
        self.root.geometry("980x640")

        self.tasks = []
        self.notified = set()

        self.selected_date_var = tk.StringVar(value=date.today().strftime(DATE_FMT))
        self.search_var = tk.StringVar()
        self.status_filter_var = tk.StringVar(value="all")
        self.priority_filter_var = tk.StringVar(value="all")
        self.view_mode_var = tk.StringVar(value="day")

        self._build_ui()
        self.load_tasks()
        self.refresh_all()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(30_000, self.check_notifications)

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Дата (YYYY-MM-DD):").pack(side="left")
        ttk.Entry(top, textvariable=self.selected_date_var, width=12).pack(side="left", padx=(6, 10))
        ttk.Button(top, text="Сегодня", command=self.set_today).pack(side="left")

        ttk.Label(top, text="Режим:").pack(side="left", padx=(14, 4))
        ttk.Combobox(
            top,
            textvariable=self.view_mode_var,
            values=["day", "week", "month"],
            width=8,
            state="readonly",
        ).pack(side="left")

        ttk.Label(top, text="Поиск:").pack(side="left", padx=(14, 4))
        search = ttk.Entry(top, textvariable=self.search_var, width=24)
        search.pack(side="left")
        search.bind("<KeyRelease>", lambda _: self.refresh_task_table())

        ttk.Button(top, text="Обновить", command=self.refresh_all).pack(side="right")

        middle = ttk.Frame(self.root, padding=(10, 0, 10, 8))
        middle.pack(fill="x")

        ttk.Label(middle, text="Статус:").pack(side="left")
        status_combo = ttk.Combobox(
            middle,
            textvariable=self.status_filter_var,
            values=["all", "open", "done"],
            width=10,
            state="readonly",
        )
        status_combo.pack(side="left", padx=(5, 12))
        status_combo.bind("<<ComboboxSelected>>", lambda _: self.refresh_task_table())

        ttk.Label(middle, text="Приоритет:").pack(side="left")
        pr_combo = ttk.Combobox(
            middle,
            textvariable=self.priority_filter_var,
            values=["all", "low", "medium", "high"],
            width=10,
            state="readonly",
        )
        pr_combo.pack(side="left", padx=(5, 12))
        pr_combo.bind("<<ComboboxSelected>>", lambda _: self.refresh_task_table())

        self.days_frame = ttk.LabelFrame(self.root, text="Дни с задачами (месяц)", padding=10)
        self.days_frame.pack(fill="x", padx=10, pady=(0, 8))

        self.days_listbox = tk.Listbox(self.days_frame, height=4)
        self.days_listbox.pack(fill="x")
        self.days_listbox.bind("<<ListboxSelect>>", self.on_day_selected)

        table_frame = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        table_frame.pack(fill="both", expand=True)

        columns = ("title", "description", "date", "time", "priority", "status", "remind_before")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", height=14)

        headers = {
            "title": "Название",
            "description": "Описание",
            "date": "Дата",
            "time": "Время",
            "priority": "Приоритет",
            "status": "Статус",
            "remind_before": "Напомнить (мин)",
        }
        widths = {
            "title": 170,
            "description": 220,
            "date": 90,
            "time": 60,
            "priority": 80,
            "status": 90,
            "remind_before": 110,
        }

        for col in columns:
            self.table.heading(col, text=headers[col])
            self.table.column(col, width=widths[col], anchor="w")

        scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scroll_y.set)
        self.table.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        controls = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        controls.pack(fill="x")
        ttk.Button(controls, text="➕ Создать", command=self.create_task).pack(side="left")
        ttk.Button(controls, text="✏️ Редактировать", command=self.edit_task).pack(side="left", padx=6)
        ttk.Button(controls, text="✔️ Выполнено/Не выполнено", command=self.toggle_done).pack(side="left", padx=6)
        ttk.Button(controls, text="❌ Удалить", command=self.delete_task).pack(side="left", padx=6)

    def set_today(self):
        self.selected_date_var.set(date.today().strftime(DATE_FMT))
        self.refresh_all()

    def load_tasks(self):
        if not os.path.exists(FILE_NAME):
            self.tasks = []
            return
        try:
            with open(FILE_NAME, "r", encoding="utf-8") as f:
                payload = json.load(f)
                if isinstance(payload, dict):
                    self.tasks = payload.get("tasks", [])
                elif isinstance(payload, list):
                    self.tasks = payload
                else:
                    self.tasks = []
        except (json.JSONDecodeError, OSError):
            self.tasks = []

    def save_tasks(self):
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            json.dump({"tasks": self.tasks}, f, ensure_ascii=False, indent=2)

    def refresh_all(self):
        if not self._validate_date(self.selected_date_var.get()):
            self.selected_date_var.set(date.today().strftime(DATE_FMT))
        self.refresh_days_list()
        self.refresh_task_table()

    def refresh_days_list(self):
        selected = datetime.strptime(self.selected_date_var.get(), DATE_FMT).date()
        month_start = selected.replace(day=1)
        if month_start.month == 12:
            next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            next_month = month_start.replace(month=month_start.month + 1, day=1)

        days = sorted({t["date"] for t in self.tasks if month_start.strftime(DATE_FMT) <= t.get("date", "") < next_month.strftime(DATE_FMT)})

        self.days_listbox.delete(0, tk.END)
        for d in days:
            count = sum(1 for t in self.tasks if t.get("date") == d)
            self.days_listbox.insert(tk.END, f"{d}  •  задач: {count}")

    def on_day_selected(self, _event):
        selected = self.days_listbox.curselection()
        if not selected:
            return
        value = self.days_listbox.get(selected[0]).split("  •", 1)[0]
        self.selected_date_var.set(value)
        self.refresh_task_table()

    def _date_range_for_view(self):
        base = datetime.strptime(self.selected_date_var.get(), DATE_FMT).date()
        mode = self.view_mode_var.get()
        if mode == "day":
            return base, base
        if mode == "week":
            start = base - timedelta(days=base.weekday())
            end = start + timedelta(days=6)
            return start, end
        month_start = base.replace(day=1)
        if month_start.month == 12:
            next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            next_month = month_start.replace(month=month_start.month + 1, day=1)
        return month_start, next_month - timedelta(days=1)

    def refresh_task_table(self):
        for row in self.table.get_children():
            self.table.delete(row)

        start, end = self._date_range_for_view()
        search = self.search_var.get().strip().lower()
        status_filter = self.status_filter_var.get()
        priority_filter = self.priority_filter_var.get()

        data = sorted(self.tasks, key=lambda t: (t.get("date", ""), t.get("time") or "99:99", t.get("title", "")))
        for task in data:
            if not self._validate_date(task.get("date", "")):
                continue
            task_date = datetime.strptime(task["date"], DATE_FMT).date()
            if not (start <= task_date <= end):
                continue
            if search and search not in task.get("title", "").lower():
                continue
            if status_filter == "open" and task.get("completed"):
                continue
            if status_filter == "done" and not task.get("completed"):
                continue
            if priority_filter != "all" and task.get("priority", "medium") != priority_filter:
                continue

            self.table.insert(
                "",
                tk.END,
                iid=task["id"],
                values=(
                    task.get("title", ""),
                    task.get("description", ""),
                    task.get("date", ""),
                    task.get("time", ""),
                    task.get("priority", "medium"),
                    "done" if task.get("completed") else "open",
                    task.get("remind_before", 30),
                ),
            )

    def _validate_date(self, value: str) -> bool:
        try:
            datetime.strptime(value, DATE_FMT)
            return True
        except ValueError:
            return False

    def _validate_time(self, value: str) -> bool:
        if not value:
            return True
        try:
            datetime.strptime(value, TIME_FMT)
            return True
        except ValueError:
            return False

    def _selected_task(self):
        selected = self.table.selection()
        if not selected:
            return None
        task_id = selected[0]
        return next((t for t in self.tasks if t["id"] == task_id), None)

    def create_task(self):
        self._open_task_modal()

    def edit_task(self):
        task = self._selected_task()
        if not task:
            messagebox.showwarning("Внимание", "Выберите задачу для редактирования")
            return
        self._open_task_modal(task)

    def _open_task_modal(self, task=None):
        modal = tk.Toplevel(self.root)
        modal.title("Новая задача" if task is None else "Редактировать задачу")
        modal.geometry("460x360")
        modal.transient(self.root)
        modal.grab_set()

        title_var = tk.StringVar(value="" if task is None else task.get("title", ""))
        desc_var = tk.StringVar(value="" if task is None else task.get("description", ""))
        date_var = tk.StringVar(value=self.selected_date_var.get() if task is None else task.get("date", ""))
        time_var = tk.StringVar(value="" if task is None else task.get("time", ""))
        pr_var = tk.StringVar(value="medium" if task is None else task.get("priority", "medium"))
        remind_var = tk.StringVar(value=str(30 if task is None else task.get("remind_before", 30)))

        frm = ttk.Frame(modal, padding=12)
        frm.pack(fill="both", expand=True)

        def row(label, widget, r):
            ttk.Label(frm, text=label).grid(row=r, column=0, sticky="w", pady=4)
            widget.grid(row=r, column=1, sticky="ew", pady=4)

        frm.columnconfigure(1, weight=1)

        row("Название", ttk.Entry(frm, textvariable=title_var), 0)
        row("Описание", ttk.Entry(frm, textvariable=desc_var), 1)
        row("Дата (YYYY-MM-DD)", ttk.Entry(frm, textvariable=date_var), 2)
        row("Время (HH:MM, опционально)", ttk.Entry(frm, textvariable=time_var), 3)
        row("Приоритет", ttk.Combobox(frm, textvariable=pr_var, values=["low", "medium", "high"], state="readonly"), 4)
        row("Напомнить за (мин)", ttk.Entry(frm, textvariable=remind_var), 5)

        def submit():
            title = title_var.get().strip()
            description = desc_var.get().strip()
            due_date = date_var.get().strip()
            due_time = time_var.get().strip()

            if not title:
                messagebox.showwarning("Ошибка", "Введите название")
                return
            if not self._validate_date(due_date):
                messagebox.showwarning("Ошибка", "Дата должна быть в формате YYYY-MM-DD")
                return
            if not self._validate_time(due_time):
                messagebox.showwarning("Ошибка", "Время должно быть в формате HH:MM")
                return
            try:
                remind_before = int(remind_var.get().strip())
                if remind_before < 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Ошибка", "Напоминание должно быть целым числом >= 0")
                return

            payload = {
                "title": title,
                "description": description,
                "date": due_date,
                "time": due_time,
                "completed": False if task is None else task.get("completed", False),
                "priority": pr_var.get(),
                "remind_before": remind_before,
            }

            if task is None:
                payload["id"] = str(uuid4())
                self.tasks.append(payload)
            else:
                task.update(payload)

            self.save_tasks()
            self.refresh_all()
            modal.destroy()

        btns = ttk.Frame(frm)
        btns.grid(row=6, column=0, columnspan=2, pady=(12, 0), sticky="e")
        ttk.Button(btns, text="Сохранить", command=submit).pack(side="left")
        ttk.Button(btns, text="Отмена", command=modal.destroy).pack(side="left", padx=6)

    def delete_task(self):
        task = self._selected_task()
        if not task:
            messagebox.showwarning("Внимание", "Выберите задачу для удаления")
            return
        if not messagebox.askyesno("Подтверждение", "Удалить выбранную задачу?"):
            return

        self.tasks = [t for t in self.tasks if t["id"] != task["id"]]
        self.save_tasks()
        self.refresh_all()

    def toggle_done(self):
        task = self._selected_task()
        if not task:
            messagebox.showwarning("Внимание", "Выберите задачу")
            return
        task["completed"] = not task.get("completed", False)
        self.save_tasks()
        self.refresh_task_table()

    def check_notifications(self):
        now = datetime.now()
        for task in self.tasks:
            if task.get("completed"):
                continue
            due_time = task.get("time", "")
            if not due_time or not self._validate_date(task.get("date", "")):
                continue
            if not self._validate_time(due_time):
                continue
            due_dt = datetime.strptime(f"{task['date']} {due_time}", f"{DATE_FMT} {TIME_FMT}")
            remind_before = int(task.get("remind_before", 30))
            remind_at = due_dt - timedelta(minutes=remind_before)
            key = (task["id"], remind_at.strftime("%Y-%m-%d %H:%M"))

            if remind_at <= now <= due_dt and key not in self.notified:
                messagebox.showinfo(
                    "Напоминание",
                    f"Скоро задача: {task['title']}\nДата: {task['date']} {due_time}",
                )
                self.notified.add(key)

        self.root.after(30_000, self.check_notifications)

    def on_close(self):
        if messagebox.askyesno("Выход", "Закрыть приложение Task Calendar?"):
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    TaskCalendarApp(root)
    root.mainloop()

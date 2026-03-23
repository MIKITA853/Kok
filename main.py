import json
import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox

FILE_NAME = "tasks.json"
DATE_FORMAT = "%d-%m-%Y"
CATEGORIES = ["Работа", "Личное", "Учёба"]
PRIORITIES = ["Высокий", "Средний", "Низкий"]

BG = "#0f172a"
CARD = "#1e293b"
TASK_CARD = "#273449"
INPUT = "#0b1220"
ACCENT = "#6366f1"
HOVER = "#4f46e5"
TEXT = "#e2e8f0"
MUTED = "#94a3b8"
DANGER = "#ef4444"

tasks = []
selected_task_id = None


def load_tasks():
    global tasks
    if os.path.exists(FILE_NAME):
        try:
            with open(FILE_NAME, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            tasks = loaded if isinstance(loaded, list) else []
        except Exception:
            tasks = []
    else:
        tasks = []


def save_tasks():
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


def parse_deadline(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except ValueError:
        return None


def is_overdue(task):
    if task.get("done"):
        return False
    deadline = parse_deadline(task.get("deadline", ""))
    return deadline is not None and deadline < datetime.now().date()


def next_id():
    return str(int(datetime.now().timestamp() * 1000000))


def add_or_update_task():
    global selected_task_id
    text = task_var.get().strip()
    deadline = deadline_var.get().strip()
    category = category_var.get().strip()
    priority = priority_var.get().strip()

    if not text:
        messagebox.showwarning("Ошибка", "Введите задачу")
        return

    if parse_deadline(deadline) is None:
        messagebox.showwarning("Ошибка", "Дата должна быть в формате дд-мм-гггг")
        return

    task_obj = {
        "id": selected_task_id or next_id(),
        "text": text,
        "done": False,
        "deadline": deadline,
        "category": category if category in CATEGORIES else "Личное",
        "priority": priority if priority in PRIORITIES else "Средний",
    }

    if selected_task_id:
        for i, t in enumerate(tasks):
            if t["id"] == selected_task_id:
                task_obj["done"] = t.get("done", False)
                tasks[i] = task_obj
                break
    else:
        tasks.append(task_obj)

    save_tasks()
    clear_inputs()
    refresh_ui()


def toggle_done(task_id):
    for t in tasks:
        if t["id"] == task_id:
            t["done"] = not t.get("done", False)
            break
    save_tasks()
    refresh_ui()


def delete_task(task_id):
    global tasks, selected_task_id
    tasks = [t for t in tasks if t["id"] != task_id]
    if selected_task_id == task_id:
        clear_inputs()
    save_tasks()
    refresh_ui()


def clear_inputs():
    global selected_task_id
    selected_task_id = None
    task_var.set("")
    deadline_var.set("")
    category_var.set("Личное")
    priority_var.set("Средний")
    add_btn.configure(text="Добавить")


def on_card_click(task):
    global selected_task_id
    selected_task_id = task["id"]
    task_var.set(task["text"])
    deadline_var.set(task["deadline"])
    category_var.set(task.get("category", "Личное"))
    priority_var.set(task.get("priority", "Средний"))
    add_btn.configure(text="Сохранить")


def filtered_tasks():
    mode = filter_var.get()
    if mode == "Выполненные":
        return [t for t in tasks if t.get("done")]
    if mode == "Активные":
        return [t for t in tasks if not t.get("done")]
    return tasks


def refresh_ui():
    for w in cards_inner.winfo_children():
        w.destroy()

    for i, task in enumerate(filtered_tasks()):
        make_card(i, task)

    total = len(tasks)
    done = sum(1 for t in tasks if t.get("done"))
    percent = int(done / total * 100) if total else 0
    stats_var.set(f"Всего: {total} | Выполнено: {done} | Выполнение: {percent}%")


def make_card(row, task):
    base = HOVER if task["id"] == selected_task_id else TASK_CARD
    title_color = DANGER if is_overdue(task) else TEXT

    frame = tk.Frame(cards_inner, bg=base, padx=14, pady=12, bd=0, highlightthickness=1, highlightbackground="#334155")
    frame.grid(row=row, column=0, sticky="ew", padx=10, pady=4)
    frame.grid_columnconfigure(1, weight=1)

    title = tk.Label(frame, text=task["text"], bg=base, fg=title_color, font=("Segoe UI", 12, "bold"), anchor="w")
    title.grid(row=0, column=0, columnspan=2, sticky="ew")

    meta_color = DANGER if is_overdue(task) else MUTED
    meta = tk.Label(
        frame,
        text=f"{task.get('category','Личное')} | {task.get('deadline','')} | {task.get('priority','Средний')}",
        bg=base,
        fg=meta_color,
        font=("Segoe UI", 10),
        anchor="w",
    )
    meta.grid(row=1, column=0, sticky="w", pady=(6, 0))

    btns = tk.Frame(frame, bg=base)
    btns.grid(row=1, column=1, sticky="e")

    done_btn = tk.Button(btns, text="✔", width=3, command=lambda tid=task["id"]: toggle_done(tid), bg=ACCENT, fg=TEXT, relief="flat", bd=0)
    del_btn = tk.Button(btns, text="✖", width=3, command=lambda tid=task["id"]: delete_task(tid), bg=ACCENT, fg=DANGER, relief="flat", bd=0)
    done_btn.grid(row=0, column=0, padx=(0, 6))
    del_btn.grid(row=0, column=1)

    def enter(_):
        if task["id"] != selected_task_id:
            for w in (frame, title, meta, btns):
                w.configure(bg=HOVER)

    def leave(_):
        if task["id"] != selected_task_id:
            for w in (frame, title, meta, btns):
                w.configure(bg=TASK_CARD)

    for w in (frame, title, meta):
        w.bind("<Button-1>", lambda _e, t=task: on_card_click(t))
        w.bind("<Enter>", enter)
        w.bind("<Leave>", leave)


# ---------- UI ----------
root = tk.Tk()
root.title("Task Manager")
root.geometry("1100x800")
root.configure(bg=BG)

container = tk.Frame(root, width=800, height=700, bg=CARD, padx=18, pady=18, highlightthickness=1, highlightbackground="#334155")
container.place(relx=0.5, rely=0.5, anchor="center")
container.grid_propagate(False)
container.grid_columnconfigure(0, weight=1)
container.grid_rowconfigure(4, weight=1)

tk.Label(container, text="Task Manager", bg=CARD, fg=TEXT, font=("Segoe UI", 20, "bold")).grid(row=0, column=0, sticky="ew", pady=(0, 12))

task_var = tk.StringVar()
deadline_var = tk.StringVar()
category_var = tk.StringVar(value="Личное")
priority_var = tk.StringVar(value="Средний")
filter_var = tk.StringVar(value="Все")
stats_var = tk.StringVar(value="Всего: 0 | Выполнено: 0 | Выполнение: 0%")

input_zone = tk.Frame(container, bg=CARD)
input_zone.grid(row=1, column=0, sticky="ew")
input_zone.grid_columnconfigure(0, weight=6)
input_zone.grid_columnconfigure(1, weight=2)
input_zone.grid_columnconfigure(2, weight=2)
input_zone.grid_columnconfigure(3, weight=2)

tk.Entry(input_zone, textvariable=task_var, bg=INPUT, fg=TEXT, insertbackground=TEXT, bd=0, font=("Segoe UI", 12)).grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 10), ipady=10)
tk.Entry(input_zone, textvariable=deadline_var, bg=INPUT, fg=TEXT, insertbackground=TEXT, bd=0).grid(row=1, column=0, sticky="ew", padx=(0, 6), ipady=8)
tk.OptionMenu(input_zone, category_var, *CATEGORIES).grid(row=1, column=1, sticky="ew", padx=3)
tk.OptionMenu(input_zone, priority_var, *PRIORITIES).grid(row=1, column=2, sticky="ew", padx=3)
tk.OptionMenu(input_zone, filter_var, "Все", "Выполненные", "Активные", command=lambda _x: refresh_ui()).grid(row=1, column=3, sticky="ew", padx=(3, 0))

add_btn = tk.Button(input_zone, text="Добавить", command=add_or_update_task, bg=ACCENT, fg=TEXT, relief="flat", bd=0)
add_btn.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(10, 10), ipady=8)

list_zone = tk.Frame(container, bg=CARD)
list_zone.grid(row=4, column=0, sticky="nsew")
list_zone.grid_rowconfigure(0, weight=1)
list_zone.grid_columnconfigure(0, weight=1)

canvas = tk.Canvas(list_zone, bg=CARD, highlightthickness=0)
scroll = tk.Scrollbar(list_zone, orient="vertical", command=canvas.yview)
canvas.configure(yscrollcommand=scroll.set)
canvas.grid(row=0, column=0, sticky="nsew")
scroll.grid(row=0, column=1, sticky="ns")

cards_inner = tk.Frame(canvas, bg=CARD)
window_id = canvas.create_window((0, 0), window=cards_inner, anchor="nw")
cards_inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.bind("<Configure>", lambda e: canvas.itemconfig(window_id, width=e.width))

tk.Label(container, textvariable=stats_var, bg=CARD, fg=MUTED, font=("Segoe UI", 10, "bold")).grid(row=5, column=0, sticky="ew", pady=(10, 0))

load_tasks()
refresh_ui()
root.mainloop()

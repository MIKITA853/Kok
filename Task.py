import json
import os
import sys
import tkinter as tk
from datetime import datetime
from tkinter import messagebox

# ===== PATH FIX (для exe) =====
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(__file__)

FILE_NAME = os.path.join(BASE_DIR, "tasks.json")
DATE_FORMAT = "%d-%m-%Y"

tasks = []
selected_task_index = None
filter_mode = "all"

# ===== THEME =====
COLORS = {
    "bg": "#1e1e1e",
    "sidebar": "#252525",
    "card": "#2a2a2a",
    "hover": "#333333",
    "text": "#ffffff",
    "danger": "#ff4d4d",
}

# ===== DATA =====
def load_tasks():
    global tasks
    if os.path.exists(FILE_NAME):
        try:
            with open(FILE_NAME, "r", encoding="utf-8") as f:
                tasks = json.load(f)
        except:
            tasks = []
    else:
        tasks = []
    refresh_ui()


def save_tasks():
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=4)


def parse_deadline(text):
    try:
        return datetime.strptime(text, DATE_FORMAT).date()
    except:
        return None


def is_overdue(task):
    d = parse_deadline(task["deadline"])
    return d and not task["done"] and d < datetime.now().date()


# ===== LOGIC =====
def get_visible_tasks():
    if filter_mode == "done":
        return [(i, t) for i, t in enumerate(tasks) if t["done"]]
    if filter_mode == "todo":
        return [(i, t) for i, t in enumerate(tasks) if not t["done"]]
    return list(enumerate(tasks))


def add_task():
    text = entry.get().strip()
    deadline = deadline_entry.get().strip() or "без срока"

    if not text:
        messagebox.showwarning("Ошибка", "Введите задачу")
        return

    tasks.append({
        "text": text,
        "done": False,
        "deadline": deadline
    })

    save_tasks()
    entry.delete(0, tk.END)
    deadline_entry.delete(0, tk.END)
    refresh_ui()


def toggle_task(i):
    tasks[i]["done"] = not tasks[i]["done"]
    save_tasks()
    refresh_ui()


def delete_task(i):
    tasks.pop(i)
    save_tasks()
    refresh_ui()


def set_filter(mode):
    global filter_mode
    filter_mode = mode
    refresh_ui()


# ===== UI =====
def clear_tasks():
    for w in task_container.winfo_children():
        w.destroy()


def create_card(i, task):
    frame = tk.Frame(task_container, bg=COLORS["card"], padx=10, pady=10)
    frame.pack(fill="x", pady=5)

    color = COLORS["danger"] if is_overdue(task) else COLORS["text"]

    title = tk.Label(
        frame,
        text=task["text"],
        bg=COLORS["card"],
        fg=color,
        font=("Segoe UI", 11, "bold"),
        anchor="w"
    )
    title.pack(fill="x")

    subtitle = tk.Label(
        frame,
        text=f"Дедлайн: {task['deadline']}",
        bg=COLORS["card"],
        fg="#bbbbbb",
        anchor="w"
    )
    subtitle.pack(fill="x")

    btn_frame = tk.Frame(frame, bg=COLORS["card"])
    btn_frame.pack(anchor="e")

    tk.Button(btn_frame, text="✔", command=lambda: toggle_task(i)).pack(side="right", padx=3)
    tk.Button(btn_frame, text="✖", command=lambda: delete_task(i)).pack(side="right", padx=3)


def refresh_ui():
    clear_tasks()

    visible = get_visible_tasks()

    for i, task in visible:
        create_card(i, task)

    total = len(tasks)
    done = sum(t["done"] for t in tasks)
    percent = int(done / total * 100) if total else 0
    stats_var.set(f"Всего: {total} | Выполнено: {done} | {percent}%")


# ===== WINDOW =====
root = tk.Tk()
root.title("Task Manager")
root.geometry("900x600")
root.configure(bg=COLORS["bg"])

# GRID
root.grid_columnconfigure(1, weight=1)
root.grid_rowconfigure(0, weight=1)

# ===== SIDEBAR =====
sidebar = tk.Frame(root, bg=COLORS["sidebar"], width=200)
sidebar.grid(row=0, column=0, sticky="ns")
sidebar.grid_propagate(False)

tk.Label(sidebar, text="Task Manager", bg=COLORS["sidebar"], fg=COLORS["text"],
         font=("Segoe UI", 16, "bold")).pack(pady=20)

tk.Button(sidebar, text="Все", command=lambda: set_filter("all")).pack(fill="x", padx=10, pady=5)
tk.Button(sidebar, text="Выполненные", command=lambda: set_filter("done")).pack(fill="x", padx=10, pady=5)
tk.Button(sidebar, text="Невыполненные", command=lambda: set_filter("todo")).pack(fill="x", padx=10, pady=5)

# ===== MAIN =====
main = tk.Frame(root, bg=COLORS["bg"])
main.grid(row=0, column=1, sticky="nsew")
main.grid_rowconfigure(1, weight=1)
main.grid_columnconfigure(0, weight=1)

# TOP
top = tk.Frame(main, bg=COLORS["bg"])
top.grid(row=0, column=0, sticky="ew", pady=10)

entry = tk.Entry(top)
entry.pack(side="left", fill="x", expand=True, padx=5)

deadline_entry = tk.Entry(top, width=15)
deadline_entry.pack(side="left", padx=5)
deadline_entry.insert(0, "дд-мм-гггг")

tk.Button(top, text="Добавить", command=add_task).pack(side="left", padx=5)

# TASKS
task_container = tk.Frame(main, bg=COLORS["bg"])
task_container.grid(row=1, column=0, sticky="nsew", padx=10)

# STATS
stats_var = tk.StringVar()
tk.Label(main, textvariable=stats_var, bg=COLORS["bg"], fg=COLORS["text"]).grid(row=2, column=0, pady=10)

# START
load_tasks()
root.mainloop()
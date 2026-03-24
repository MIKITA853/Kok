import tkinter as tk
from tkinter import messagebox
import json
import os

FILE_NAME = "tasks.json"

tasks = []

# ===== Работа с файлом =====
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

    update_listbox()

def save_tasks():
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=4)

# ===== UI логика =====
def update_listbox():
    listbox.delete(0, tk.END)
    for task in tasks:
        status = "✅" if task["done"] else "❌"
        text = f'{status} {task["text"]} (до: {task["deadline"]})'
        listbox.insert(tk.END, text)

def add_task():
    text = entry.get()
    deadline = deadline_entry.get()

    if text == "":
        messagebox.showwarning("Ошибка", "Введите задачу")
        return

    if deadline == "":
        deadline = "без срока"

    tasks.append({
        "text": text,
        "done": False,
        "deadline": deadline
    })

    save_tasks()
    update_listbox()
    entry.delete(0, tk.END)
    deadline_entry.delete(0, tk.END)

def delete_task():
    selected = listbox.curselection()
    if not selected:
        return

    index = selected[0]
    tasks.pop(index)

    save_tasks()
    update_listbox()

def toggle_done():
    selected = listbox.curselection()
    if not selected:
        return

    index = selected[0]
    tasks[index]["done"] = not tasks[index]["done"]

    save_tasks()
    update_listbox()

def prevent_close():
    messagebox.showinfo("Информация", "Закрытие окна отключено")

# ===== Окно =====
root = tk.Tk()
root.title("Менеджер задач")
root.geometry("400x500")

# поле задачи
entry = tk.Entry(root, width=30)
entry.pack(pady=5)

# поле дедлайна
deadline_entry = tk.Entry(root, width=30)
deadline_entry.pack(pady=5)
deadline_entry.insert(0, "дд-мм-гггг")

# кнопки
tk.Button(root, text="Добавить", command=add_task).pack(pady=5)
tk.Button(root, text="Удалить", command=delete_task).pack(pady=5)
tk.Button(root, text="Выполнено / Не выполнено", command=toggle_done).pack(pady=5)

# список
listbox = tk.Listbox(root, width=45, height=15)
listbox.pack(pady=10)

# загрузка задач
load_tasks()

# блокируем закрытие окна
root.protocol("WM_DELETE_WINDOW", prevent_close)

root.mainloop()
import tkinter as tk
from tkinter import filedialog, messagebox
import json
import os
from datetime import datetime

# ===== ФАЙЛ =====
FILE_NAME = "objects.json"

# ===== ЦВЕТА =====
BG = "#0f172a"
PANEL = "#111827"
ACCENT = "#6366f1"
TEXT = "#e2e8f0"

TYPE_COLORS = {
    "Тип A": "#22c55e",
    "Тип B": "#eab308",
    "Тип C": "#ef4444",
}

# ===== ДАННЫЕ =====
def load_objects():
    if not os.path.exists(FILE_NAME):
        return []
    try:
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_objects(objects):
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        json.dump(objects, f, ensure_ascii=False, indent=2)

# ===== ПРИЛОЖЕНИЕ =====
class MapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Map Simulator")
        self.root.state("zoomed")
        self.root.configure(bg=BG)

        self.scale = 1.0
        self.pan_x = 0
        self.pan_y = 0

        self.objects = load_objects()
        self.add_mode = True

        self.build_ui()
        self.bind_events()
        self.refresh()

    def build_ui(self):
        self.toolbar = tk.Frame(self.root, bg=PANEL)
        self.toolbar.pack(fill="x")

        tk.Button(self.toolbar, text="Добавление ВКЛ/ВЫКЛ",
                  command=self.toggle_add,
                  bg=ACCENT, fg="white").pack(side="left", padx=5)

        tk.Button(self.toolbar, text="Очистить",
                  command=self.clear,
                  bg=ACCENT, fg="white").pack(side="left", padx=5)

        tk.Button(self.toolbar, text="Загрузить карту",
                  command=self.load_map,
                  bg=ACCENT, fg="white").pack(side="left", padx=5)

        self.canvas = tk.Canvas(self.root, bg=BG)
        self.canvas.pack(fill="both", expand=True)

    def bind_events(self):
        self.canvas.bind("<Button-1>", self.click)
        self.canvas.bind("<MouseWheel>", self.zoom)
        self.canvas.bind("<B2-Motion>", self.pan_move)
        self.canvas.bind("<ButtonPress-2>", self.pan_start)

    # ===== ЛОГИКА =====
    def toggle_add(self):
        self.add_mode = not self.add_mode

    def click(self, event):
        if not self.add_mode:
            return

        x, y = self.to_world(event.x, event.y)

        self.objects.append({
            "x": x,
            "y": y,
            "radius": 50,
            "type": "Тип A",
            "name": f"obj {len(self.objects)+1}"
        })

        save_objects(self.objects)
        self.refresh()

    def clear(self):
        if messagebox.askyesno("Очистить", "Удалить всё?"):
            self.objects = []
            save_objects(self.objects)
            self.refresh()

    # ===== КООРДИНАТЫ =====
    def to_screen(self, x, y):
        return x * self.scale + self.pan_x, y * self.scale + self.pan_y

    def to_world(self, x, y):
        return (x - self.pan_x) / self.scale, (y - self.pan_y) / self.scale

    # ===== ЗУМ =====
    def zoom(self, event):
        if event.delta > 0:
            self.scale *= 1.1
        else:
            self.scale /= 1.1
        self.refresh()

    # ===== ПАНОРАМА =====
    def pan_start(self, event):
        self.last_x = event.x
        self.last_y = event.y

    def pan_move(self, event):
        dx = event.x - self.last_x
        dy = event.y - self.last_y
        self.pan_x += dx
        self.pan_y += dy
        self.last_x = event.x
        self.last_y = event.y
        self.refresh()

    # ===== КАРТА =====
    def load_map(self):
        path = filedialog.askopenfilename()
        if not path:
            return
        try:
            self.map_img = tk.PhotoImage(file=path)
            self.refresh()
        except:
            messagebox.showerror("Ошибка", "Не удалось загрузить карту")

    # ===== ОТРИСОВКА =====
    def refresh(self):
        self.canvas.delete("all")

        # карта
        if hasattr(self, "map_img"):
            self.canvas.create_image(self.pan_x, self.pan_y, image=self.map_img, anchor="nw")

        # объекты
        for obj in self.objects:
            sx, sy = self.to_screen(obj["x"], obj["y"])
            color = TYPE_COLORS.get(obj["type"], "green")

            r = obj["radius"] * self.scale

            self.canvas.create_oval(
                sx - r, sy - r, sx + r, sy + r,
                outline=color
            )

            self.canvas.create_oval(
                sx - 5, sy - 5, sx + 5, sy + 5,
                fill=color
            )

            self.canvas.create_text(
                sx + 10, sy,
                text=obj["name"],
                fill=TEXT
            )


# ===== ЗАПУСК =====
root = tk.Tk()
app = MapApp(root)
root.mainloop()
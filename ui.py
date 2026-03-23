import os
import tkinter as tk
from tkinter import filedialog, messagebox

import data
from logic import TYPE_COLORS, normalize_object

try:
    from PIL import Image, ImageTk  # type: ignore
except Exception:
    Image = None
    ImageTk = None

BG = "#0f172a"
PANEL = "#1e293b"
INPUT = "#0b1220"
ACCENT = "#6366f1"
TEXT = "#e2e8f0"
MUTED = "#94a3b8"


class MapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Map Objects Viewer")
        self.root.geometry("1200x800")
        self.root.configure(bg=BG)

        self.scale = 1.0
        self.min_scale = 0.2
        self.max_scale = 5.0
        self.pan_x = 0
        self.pan_y = 0
        self.bg_image = None
        self.bg_img_tk = None
        self.bg_image_id = None

        self.objects = [normalize_object(x) for x in data.load_objects() if isinstance(x, dict)]

        self._build_ui()
        self._bind_events()
        self.refresh_ui()

    def _build_ui(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=0)

        self.canvas = tk.Canvas(self.root, bg="#111827", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.panel = tk.Frame(self.root, width=320, bg=PANEL, padx=10, pady=10)
        self.panel.grid(row=0, column=1, sticky="ns")
        self.panel.grid_propagate(False)
        self.panel.grid_columnconfigure(0, weight=1)

        tk.Label(self.panel, text="Объекты", bg=PANEL, fg=TEXT, font=("Segoe UI", 14, "bold")).grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.obj_list = tk.Listbox(self.panel, height=10, bg=INPUT, fg=TEXT, selectbackground=ACCENT, relief="flat")
        self.obj_list.grid(row=1, column=0, sticky="ew")
        self.obj_list.bind("<<ListboxSelect>>", self._on_select)

        self.name_var = tk.StringVar(value="объект")
        self.radius_var = tk.StringVar(value="50")
        self.type_var = tk.StringVar(value="Тип A")
        self.show_radius_var = tk.BooleanVar(value=True)

        tk.Label(self.panel, text="Название", bg=PANEL, fg=MUTED).grid(row=2, column=0, sticky="w", pady=(10, 2))
        self.name_entry = tk.Entry(self.panel, textvariable=self.name_var, bg=INPUT, fg=TEXT, insertbackground=TEXT, relief="flat")
        self.name_entry.grid(row=3, column=0, sticky="ew")

        tk.Label(self.panel, text="Радиус (px)", bg=PANEL, fg=MUTED).grid(row=4, column=0, sticky="w", pady=(10, 2))
        self.radius_entry = tk.Entry(self.panel, textvariable=self.radius_var, bg=INPUT, fg=TEXT, insertbackground=TEXT, relief="flat")
        self.radius_entry.grid(row=5, column=0, sticky="ew")

        tk.Label(self.panel, text="Тип", bg=PANEL, fg=MUTED).grid(row=6, column=0, sticky="w", pady=(10, 2))
        self.type_menu = tk.OptionMenu(self.panel, self.type_var, *TYPE_COLORS.keys())
        self.type_menu.grid(row=7, column=0, sticky="ew")

        self.radius_check = tk.Checkbutton(self.panel, text="Показывать радиус", variable=self.show_radius_var, bg=PANEL, fg=TEXT, activebackground=PANEL, selectcolor=INPUT)
        self.radius_check.grid(row=8, column=0, sticky="w", pady=(10, 8))

        self.add_btn = tk.Button(self.panel, text="Добавить объект (клик по карте)", command=self._arm_add, bg=ACCENT, fg=TEXT, relief="flat")
        self.add_btn.grid(row=9, column=0, sticky="ew", pady=4)

        self.update_btn = tk.Button(self.panel, text="Изменить", command=self._update_selected, bg=ACCENT, fg=TEXT, relief="flat")
        self.update_btn.grid(row=10, column=0, sticky="ew", pady=4)

        self.delete_btn = tk.Button(self.panel, text="Удалить", command=self._delete_selected, bg=ACCENT, fg=TEXT, relief="flat")
        self.delete_btn.grid(row=11, column=0, sticky="ew", pady=4)

        self.load_map_btn = tk.Button(self.panel, text="Загрузить карту", command=self._load_map, bg=ACCENT, fg=TEXT, relief="flat")
        self.load_map_btn.grid(row=12, column=0, sticky="ew", pady=(12, 4))

        self.export_btn = tk.Button(self.panel, text="Экспорт JSON", command=self._export_json, bg=ACCENT, fg=TEXT, relief="flat")
        self.export_btn.grid(row=13, column=0, sticky="ew", pady=4)

        self.import_btn = tk.Button(self.panel, text="Импорт JSON", command=self._import_json, bg=ACCENT, fg=TEXT, relief="flat")
        self.import_btn.grid(row=14, column=0, sticky="ew", pady=4)

        self.coord_label = tk.Label(self.panel, text="Координаты: -", bg=PANEL, fg=MUTED)
        self.coord_label.grid(row=15, column=0, sticky="w", pady=(12, 0))

        self.mode_add = False

    def _bind_events(self):
        self.canvas.bind("<ButtonPress-3>", self._start_pan)
        self.canvas.bind("<B3-Motion>", self._do_pan)
        self.canvas.bind("<MouseWheel>", self._on_zoom)
        self.canvas.bind("<Button-4>", lambda e: self._on_zoom_linux(1, e))
        self.canvas.bind("<Button-5>", lambda e: self._on_zoom_linux(-1, e))
        self.canvas.bind("<Button-1>", self._on_left_click)
        self.canvas.bind("<Motion>", self._on_motion)

    # ---------- Map transforms ----------
    def world_to_screen(self, x, y):
        return x * self.scale + self.pan_x, y * self.scale + self.pan_y

    def screen_to_world(self, sx, sy):
        return (sx - self.pan_x) / self.scale, (sy - self.pan_y) / self.scale

    def _start_pan(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def _do_pan(self, event):
        old_x, old_y = self.pan_x, self.pan_y
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        # emulate by tracking delta manually
        dx = event.x - getattr(self, "_last_pan_x", event.x)
        dy = event.y - getattr(self, "_last_pan_y", event.y)
        self._last_pan_x, self._last_pan_y = event.x, event.y
        self.pan_x = old_x + dx
        self.pan_y = old_y + dy
        self.refresh_ui()

    def _on_zoom(self, event):
        delta = 1 if event.delta > 0 else -1
        self._zoom(delta, event.x, event.y)

    def _on_zoom_linux(self, delta, event):
        self._zoom(delta, event.x, event.y)

    def _zoom(self, delta, cx, cy):
        old_scale = self.scale
        if delta > 0:
            self.scale *= 1.1
        else:
            self.scale /= 1.1
        self.scale = max(self.min_scale, min(self.max_scale, self.scale))

        wx, wy = (cx - self.pan_x) / old_scale, (cy - self.pan_y) / old_scale
        self.pan_x = cx - wx * self.scale
        self.pan_y = cy - wy * self.scale
        self.refresh_ui()

    # ---------- Objects ----------
    def _arm_add(self):
        self.mode_add = True
        messagebox.showinfo("Режим", "Кликните по карте, чтобы добавить объект")

    def _on_left_click(self, event):
        if not self.mode_add:
            return
        name = self.name_var.get().strip() or f"объект {len(self.objects) + 1}"
        try:
            radius = int(self.radius_var.get())
        except ValueError:
            messagebox.showwarning("Ошибка", "Радиус должен быть числом")
            return

        x, y = self.screen_to_world(event.x, event.y)
        obj = normalize_object({
            "name": name,
            "x": x,
            "y": y,
            "radius": radius,
            "type": self.type_var.get(),
            "show_radius": self.show_radius_var.get(),
        })
        self.objects.append(obj)
        data.save_objects(self.objects)
        self.mode_add = False
        self.refresh_ui()
        self._clear_fields()

    def _on_select(self, _):
        idxs = self.obj_list.curselection()
        if not idxs:
            return
        obj = self.visible_objects[idxs[0]]
        self.name_var.set(obj["name"])
        self.radius_var.set(str(obj["radius"]))
        self.type_var.set(obj["type"])
        self.show_radius_var.set(obj.get("show_radius", True))

    def _update_selected(self):
        idxs = self.obj_list.curselection()
        if not idxs:
            return
        obj = self.visible_objects[idxs[0]]
        try:
            obj["radius"] = int(self.radius_var.get())
        except ValueError:
            messagebox.showwarning("Ошибка", "Радиус должен быть числом")
            return
        obj["name"] = self.name_var.get().strip() or obj["name"]
        obj["type"] = self.type_var.get()
        obj["show_radius"] = self.show_radius_var.get()
        data.save_objects(self.objects)
        self.refresh_ui()

    def _delete_selected(self):
        idxs = self.obj_list.curselection()
        if not idxs:
            return
        obj = self.visible_objects[idxs[0]]
        self.objects = [o for o in self.objects if o["id"] != obj["id"]]
        data.save_objects(self.objects)
        self.refresh_ui()

    def _clear_fields(self):
        self.name_var.set("объект")
        self.radius_var.set("50")
        self.type_var.set("Тип A")
        self.show_radius_var.set(True)

    # ---------- Drawing ----------
    def refresh_ui(self):
        self.canvas.delete("all")

        if self.bg_image is not None:
            self._draw_map_image()

        self.visible_objects = self._filtered_objects()
        self.obj_list.delete(0, tk.END)
        for obj in self.visible_objects:
            self.obj_list.insert(tk.END, f"{obj['name']} ({obj['type']})")

        for obj in self.visible_objects:
            sx, sy = self.world_to_screen(obj["x"], obj["y"])
            color = TYPE_COLORS.get(obj["type"], "#22c55e")

            if obj.get("show_radius", True):
                r = obj["radius"] * self.scale
                self.canvas.create_oval(sx - r, sy - r, sx + r, sy + r, outline=color, width=2, stipple="gray50")

            self.canvas.create_oval(sx - 4, sy - 4, sx + 4, sy + 4, fill=color, outline="")
            self.canvas.create_text(sx + 8, sy - 8, text=obj["name"], fill=TEXT, anchor="sw", font=("Segoe UI", 9, "bold"))

    def _filtered_objects(self):
        status = self.filter_var.get()
        if status == "Все":
            return self.objects
        if status == "Выполненные":
            return [o for o in self.objects if o.get("done", False)]
        return [o for o in self.objects if not o.get("done", False)]

    def _draw_map_image(self):
        if ImageTk is None:
            return
        w = int(self.bg_image.width * self.scale)
        h = int(self.bg_image.height * self.scale)
        if w < 1 or h < 1:
            return
        resized = self.bg_image.resize((w, h))
        self.bg_img_tk = ImageTk.PhotoImage(resized)
        self.canvas.create_image(self.pan_x, self.pan_y, image=self.bg_img_tk, anchor="nw")

    # ---------- I/O ----------
    def _load_map(self):
        path = filedialog.askopenfilename(title="Выберите карту", filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp")])
        if not path:
            return
        if Image is None:
            messagebox.showwarning("Pillow", "Pillow не установлен. Поддерживаются только встроенные форматы Tk.")
            try:
                self.bg_img_tk = tk.PhotoImage(file=path)
                self.bg_image = None
                self.canvas.create_image(self.pan_x, self.pan_y, image=self.bg_img_tk, anchor="nw")
            except Exception as error:
                messagebox.showerror("Ошибка", f"Не удалось открыть изображение:\n{error}")
            return

        try:
            self.bg_image = Image.open(path).convert("RGB")
            self.refresh_ui()
        except Exception as error:
            messagebox.showerror("Ошибка", f"Не удалось загрузить карту:\n{error}")

    def _export_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        data.export_objects(self.objects, path)

    def _import_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            loaded = data.import_objects(path)
            self.objects = [normalize_object(x) for x in loaded if isinstance(x, dict)]
            data.save_objects(self.objects)
            self.refresh_ui()
        except Exception as error:
            messagebox.showerror("Ошибка", str(error))

    def _on_motion(self, event):
        wx, wy = self.screen_to_world(event.x, event.y)
        self.coord_label.configure(text=f"Координаты: {int(wx)}, {int(wy)}")

    # ---------- notifications ----------
    def _show_startup_notifications(self):
        overdue = sum(1 for t in self.objects if is_overdue(t))
        today = len(tasks_for_today(self.objects))
        if overdue:
            messagebox.showwarning("Просроченные", f"Просроченных объектов: {overdue}")
        if today:
            messagebox.showinfo("Сегодня", f"Объектов на сегодня: {today}")

    def _schedule_deadline_check(self):
        self._check_new_overdues()
        self.root.after(60_000, self._schedule_deadline_check)

    def _check_new_overdues(self):
        fresh = 0
        for obj in self.objects:
            if is_overdue(obj) and obj["id"] not in self.notified_overdue_ids:
                self.notified_overdue_ids.add(obj["id"])
                fresh += 1
        if fresh:
            messagebox.showwarning("Новые просроченные", f"Стало просроченными: {fresh}")


def run_app():
    root = tk.Tk()
    MapApp(root)
    root.mainloop()

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
PANEL = "#111827"
ACCENT = "#6366f1"
HOVER = "#4f46e5"
TEXT = "#e2e8f0"


class MapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Map Zone Simulator")
        self.root.state("zoomed")
        self.root.configure(bg=BG)

        self.scale = 1.0
        self.min_scale = 0.3
        self.max_scale = 5.0
        self.pan_x = 0
        self.pan_y = 0

        self.bg_image = None
        self.bg_img_tk = None

        self.objects = [normalize_object(x) for x in data.load_objects() if isinstance(x, dict)]
        self.add_mode = True

        self._build_ui()
        self._bind_events()
        self.refresh_ui()

    def _build_ui(self):
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.toolbar = tk.Frame(self.root, bg=PANEL, padx=8, pady=8)
        self.toolbar.grid(row=0, column=0, sticky="ew")

        self.add_btn = tk.Button(self.toolbar, text="Добавить: Вкл", command=self._toggle_add_mode, bg=ACCENT, fg=TEXT, relief="flat", bd=0)
        self.add_btn.pack(side="left", padx=4)

        self.clear_btn = tk.Button(self.toolbar, text="Очистить", command=self._clear_objects, bg=ACCENT, fg=TEXT, relief="flat", bd=0)
        self.clear_btn.pack(side="left", padx=4)

        self.load_btn = tk.Button(self.toolbar, text="Загрузить карту", command=self._load_map, bg=ACCENT, fg=TEXT, relief="flat", bd=0)
        self.load_btn.pack(side="left", padx=4)

        self.export_btn = tk.Button(self.toolbar, text="Экспорт JSON", command=self._export_json, bg=ACCENT, fg=TEXT, relief="flat", bd=0)
        self.export_btn.pack(side="left", padx=4)

        self.coord_label = tk.Label(self.toolbar, text="x: -, y: -", bg=PANEL, fg=TEXT)
        self.coord_label.pack(side="right", padx=8)

        self.canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew")

    def _bind_events(self):
        self.canvas.bind("<Button-1>", self._on_left_click)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<ButtonPress-2>", self._start_pan)
        self.canvas.bind("<B2-Motion>", self._do_pan)
        self.canvas.bind("<ButtonPress-3>", self._start_pan)
        self.canvas.bind("<B3-Motion>", self._do_pan)
        self.canvas.bind("<MouseWheel>", self._on_zoom)
        self.canvas.bind("<Button-4>", lambda e: self._zoom(1, e.x, e.y))
        self.canvas.bind("<Button-5>", lambda e: self._zoom(-1, e.x, e.y))
        self.canvas.bind("<Motion>", self._on_motion)

    # ---------- transforms ----------
    def world_to_screen(self, x, y):
        return x * self.scale + self.pan_x, y * self.scale + self.pan_y

    def screen_to_world(self, sx, sy):
        return (sx - self.pan_x) / self.scale, (sy - self.pan_y) / self.scale

    def _start_pan(self, event):
        self._last_pan_x = event.x
        self._last_pan_y = event.y

    def _do_pan(self, event):
        dx = event.x - self._last_pan_x
        dy = event.y - self._last_pan_y
        self._last_pan_x = event.x
        self._last_pan_y = event.y
        self.pan_x += dx
        self.pan_y += dy
        self.refresh_ui()

    def _on_zoom(self, event):
        self._zoom(1 if event.delta > 0 else -1, event.x, event.y)

    def _zoom(self, direction, cx, cy):
        old_scale = self.scale
        self.scale *= 1.1 if direction > 0 else 1 / 1.1
        self.scale = max(self.min_scale, min(self.max_scale, self.scale))

        wx, wy = (cx - self.pan_x) / old_scale, (cy - self.pan_y) / old_scale
        self.pan_x = cx - wx * self.scale
        self.pan_y = cy - wy * self.scale
        self.refresh_ui()

    # ---------- interaction ----------
    def _toggle_add_mode(self):
        self.add_mode = not self.add_mode
        self.add_btn.configure(text=f"Добавить: {'Вкл' if self.add_mode else 'Выкл'}")

    def _on_left_click(self, event):
        if not self.add_mode:
            return
        x, y = self.screen_to_world(event.x, event.y)
        self._open_object_popup(event.x_root, event.y_root, x, y)

    def _open_object_popup(self, screen_x, screen_y, world_x, world_y):
        popup = tk.Toplevel(self.root)
        popup.title("Новый объект")
        popup.geometry(f"260x190+{screen_x}+{screen_y}")
        popup.configure(bg=PANEL)
        popup.transient(self.root)
        popup.grab_set()

        name_var = tk.StringVar(value=f"объект {len(self.objects)+1}")
        type_var = tk.StringVar(value="Тип A")
        radius_var = tk.StringVar(value="60")

        tk.Label(popup, text="Название", bg=PANEL, fg=TEXT).pack(anchor="w", padx=10, pady=(10, 2))
        tk.Entry(popup, textvariable=name_var, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat").pack(fill="x", padx=10)

        tk.Label(popup, text="Тип", bg=PANEL, fg=TEXT).pack(anchor="w", padx=10, pady=(8, 2))
        tk.OptionMenu(popup, type_var, *TYPE_COLORS.keys()).pack(fill="x", padx=10)

        tk.Label(popup, text="Радиус (px)", bg=PANEL, fg=TEXT).pack(anchor="w", padx=10, pady=(8, 2))
        tk.Entry(popup, textvariable=radius_var, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat").pack(fill="x", padx=10)

        def create_obj():
            try:
                radius = int(radius_var.get())
            except ValueError:
                messagebox.showwarning("Ошибка", "Радиус должен быть числом")
                return
            obj = normalize_object({
                "name": name_var.get(),
                "x": world_x,
                "y": world_y,
                "radius": radius,
                "type": type_var.get(),
                "show_radius": True,
            })
            self.objects.append(obj)
            data.save_objects(self.objects)
            popup.destroy()
            self.refresh_ui()

        tk.Button(popup, text="Создать", command=create_obj, bg=ACCENT, fg=TEXT, relief="flat").pack(fill="x", padx=10, pady=10)

    def _on_right_click(self, event):
        wx, wy = self.screen_to_world(event.x, event.y)
        target = self._find_nearest_object(wx, wy)
        if target is None:
            return
        self.objects = [o for o in self.objects if o["id"] != target["id"]]
        data.save_objects(self.objects)
        self.refresh_ui()

    def _find_nearest_object(self, x, y, max_dist=12):
        nearest = None
        best = None
        for obj in self.objects:
            dx, dy = obj["x"] - x, obj["y"] - y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist <= max_dist and (best is None or dist < best):
                nearest, best = obj, dist
        return nearest

    def _clear_objects(self):
        if not self.objects:
            return
        if not messagebox.askyesno("Очистить", "Удалить все объекты?"):
            return
        self.objects = []
        data.save_objects(self.objects)
        self.refresh_ui()

    # ---------- draw ----------
    def refresh_ui(self):
        self.canvas.delete("all")
        if self.bg_image is not None:
            self._draw_map_image()

        for obj in self.objects:
            sx, sy = self.world_to_screen(obj["x"], obj["y"])
            color = TYPE_COLORS.get(obj["type"], "#22c55e")

            if obj.get("show_radius", True):
                r = obj["radius"] * self.scale
                self.canvas.create_oval(sx - r, sy - r, sx + r, sy + r, outline=color, width=2, stipple="gray50")

            self.canvas.create_oval(sx - 5, sy - 5, sx + 5, sy + 5, fill=color, outline="")
            self.canvas.create_text(sx + 8, sy - 8, text=obj["name"], fill=TEXT, anchor="sw", font=("Segoe UI", 9, "bold"))

    def _draw_map_image(self):
        if self.bg_image is None or ImageTk is None:
            return
        w = max(1, int(self.bg_image.width * self.scale))
        h = max(1, int(self.bg_image.height * self.scale))
        resized = self.bg_image.resize((w, h))
        self.bg_img_tk = ImageTk.PhotoImage(resized)
        self.canvas.create_image(self.pan_x, self.pan_y, image=self.bg_img_tk, anchor="nw")

    # ---------- io ----------
    def _load_map(self):
        path = filedialog.askopenfilename(title="Выберите карту", filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif")])
        if not path:
            return
        if Image is None:
            messagebox.showwarning("Pillow", "Для JPG/BMP нужен Pillow. Установите pillow или используйте PNG/GIF PhotoImage.")
            try:
                self.bg_img_tk = tk.PhotoImage(file=path)
                self.bg_image = None
                self.canvas.create_image(self.pan_x, self.pan_y, image=self.bg_img_tk, anchor="nw")
            except Exception as error:
                messagebox.showerror("Ошибка", f"Не удалось загрузить карту:\n{error}")
            return

        try:
            self.bg_image = Image.open(path).convert("RGB")
            self.refresh_ui()
        except Exception as error:
            messagebox.showerror("Ошибка", f"Не удалось загрузить карту:\n{error}")

    def _export_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
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
        self.coord_label.configure(text=f"x: {int(wx)}, y: {int(wy)}")


def run_app():
    root = tk.Tk()
    MapApp(root)
    root.mainloop()

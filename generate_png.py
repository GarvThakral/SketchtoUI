import os
import customtkinter as ctk
from tkinter import colorchooser
from pathlib import Path
from PIL import Image, ImageDraw, ImageTk, ImageFont
import subprocess
import sys
from apiinference import generate_ui_code
import json
from layout_flow import build_layout
# Higher default scaling so the UI is crisp/readable on high-DPI displays.
UI_SCALE = float(os.environ.get("MINIPAINT_UI_SCALE", 1.3))

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")
ctk.set_window_scaling(UI_SCALE)
ctk.set_widget_scaling(UI_SCALE)


class MiniPaint(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Mini MS-Paint ✏️")
        self.geometry("1920x1080")
        self.resizable(False, False)

        # Canvas sizing
        self.canvas_width = 1920
        self.canvas_height = 1080

        # State
        self.current_color = "#000000"
        self.brush_size = 5
        self.fill_shapes = False
        self.text_size = 24
        self.mode = "draw"  # draw | erase | text | line | rectangle | ellipse
        self.shape_start = None
        self.preview_shape_id = None
        self.generated_code = {}
        # Fonts
        self.font_large = ctk.CTkFont(size=18, weight="bold")
        self.font_medium = ctk.CTkFont(size=16)
        self.font_status = ctk.CTkFont(size=15)

        self.mode_labels = {
            "draw": "✏️ Brush",
            "erase": "🩹 Eraser",
            "text": "🔤 Text",
            "line": "〰️ Line",
            "rectangle": "▭ Rectangle",
            "ellipse": "⬭ Ellipse",
        }
        self.display_to_mode = {label: mode for mode, label in self.mode_labels.items()}
        self.palettes = {
            "Bright": ["#0f172a", "#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#10b981", "#6366f1", "#f3f4f6"],
            "Calm": ["#0b1b28", "#1f2937", "#2563eb", "#22d3ee", "#14b8a6", "#94a3b8", "#e2e8f0", "#f8fafc"],
            "Warm": ["#1c1917", "#be123c", "#f97316", "#f59e0b", "#fbbf24", "#92400e", "#78350f", "#f5f5f4"],
        }
        self.current_palette_name = "Bright"
        self.quick_colors = self.palettes[self.current_palette_name]
        self.palette_buttons = []

        # Paths
        self.images_dir = Path(__file__).resolve().parent / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)

        # File handling
        self.files = ["landing.png"]
        self.current_file = self.files[0]
        self.file_images = {self.current_file: self._new_blank_image()}
        self.file_history = {self.current_file: []}
        self.history_limit = 10

        # counter for PNG generation
        self.save_counter = 1

        # UI
        self.create_toolbar()
        self.create_canvas()
        self.create_statusbar()

    # ----------------------
    # TOOLBAR
    # ----------------------
    def create_toolbar(self):
        toolbar = ctk.CTkFrame(self, fg_color="#f5f5f5", height=95)
        toolbar.pack(fill="x", padx=10, pady=8)

        # File controls
        file_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        file_frame.pack(side="left", padx=10)

        ctk.CTkLabel(file_frame, text="File", font=self.font_medium).pack(side="left", padx=(0, 8))

        self.file_selector = ctk.CTkOptionMenu(
            file_frame,
            values=self.files,
            command=self.handle_file_change_request,
            width=220,
            font=self.font_medium
        )
        self.file_selector.set(self.current_file)
        self.file_selector.pack(side="left")

        ctk.CTkButton(file_frame, text="+", width=36,
                      command=self.add_file_entry,
                      font=self.font_medium).pack(side="left", padx=(10, 4))
        ctk.CTkButton(file_frame, text="-", width=36,
                      command=self.remove_file_entry,
                      font=self.font_medium).pack(side="left")

        # Color controls
        color_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        color_frame.pack(side="left", padx=10)

        self.color_preview = ctk.CTkLabel(
            color_frame, text="", width=32, height=32,
            fg_color=self.current_color, corner_radius=8
        )
        self.color_preview.pack(side="left", padx=(0, 8))

        ctk.CTkButton(color_frame, text="🎨 Pick Color", width=110,
                      command=self.pick_color,
                      font=self.font_medium).pack(side="left")

        self.palette_selector = ctk.CTkOptionMenu(
            color_frame,
            values=list(self.palettes.keys()),
            command=self.select_palette,
            width=160,
            font=self.font_medium
        )
        self.palette_selector.set(self.current_palette_name)
        self.palette_selector.pack(side="left", padx=(12, 6))

        self.palette_frame = ctk.CTkFrame(color_frame, fg_color="transparent")
        self.palette_frame.pack(side="left", padx=(10, 0))
        self.build_palette_buttons(self.palette_frame)

        # Tool + options
        tool_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        tool_frame.pack(side="left", padx=16)

        self.tool_selector = ctk.CTkSegmentedButton(
            tool_frame,
            values=list(self.mode_labels.values()),
            command=self.handle_tool_select,
            width=520,
            font=self.font_medium
        )
        self.tool_selector.set(self.mode_labels[self.mode])
        self.tool_selector.pack(pady=(4, 6))

        slider_frame = ctk.CTkFrame(tool_frame, fg_color="transparent")
        slider_frame.pack(fill="x", pady=(2, 0))

        ctk.CTkLabel(slider_frame, text="Stroke width", font=self.font_medium).pack(side="left")
        self.brush_slider = ctk.CTkSlider(
            slider_frame, from_=1, to=40,
            number_of_steps=39,
            command=self.change_brush_size,
            width=220
        )
        self.brush_slider.set(self.brush_size)
        self.brush_slider.pack(side="left", padx=10)

        self.brush_value_label = ctk.CTkLabel(slider_frame, text=f"{self.brush_size}px",
                                              font=self.font_medium)
        self.brush_value_label.pack(side="left", padx=(0, 16))

        self.fill_switch = ctk.CTkSwitch(
            slider_frame, text="Fill shapes",
            command=self.toggle_fill,
            font=self.font_medium
        )
        self.fill_switch.pack(side="left")

        text_frame = ctk.CTkFrame(tool_frame, fg_color="transparent")
        text_frame.pack(fill="x", pady=(6, 2))

        ctk.CTkLabel(text_frame, text="Text size", font=self.font_medium).pack(side="left")
        self.text_slider = ctk.CTkSlider(
            text_frame, from_=8, to=96,
            number_of_steps=88,
            command=self.change_text_size,
            width=220
        )
        self.text_slider.set(self.text_size)
        self.text_slider.pack(side="left", padx=10)

        self.text_value_label = ctk.CTkLabel(text_frame, text=f"{self.text_size}px",
                                             font=self.font_medium)
        self.text_value_label.pack(side="left", padx=(0, 16))

        # Actions
        actions = ctk.CTkFrame(toolbar, fg_color="transparent")
        actions.pack(side="right", padx=10)

        ctk.CTkButton(actions, text="🗑 Clear", fg_color="#ef4444",
                      hover_color="#dc2626", width=90,
                      command=self.clear_canvas,
                      font=self.font_medium).pack(side="right", padx=6)
        ctk.CTkButton(actions, text="📸 Save PNG", fg_color="#22c55e",
                      hover_color="#16a34a", width=120,
                      command=self.generate_png,
                      font=self.font_medium).pack(side="right", padx=6)

    # ----------------------
    # CANVAS
    # ----------------------
    def create_canvas(self):
        self.canvas_frame = ctk.CTkFrame(self, fg_color="#f3f4f6", corner_radius=12)
        self.canvas_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        # Pillow image for drawing
        self.img = self.get_or_create_image(self.current_file)
        self.draw = ImageDraw.Draw(self.img)

        # Show on canvas
        self.tk_img = ImageTk.PhotoImage(self.img)
        self.canvas = ctk.CTkCanvas(
            self.canvas_frame,
            width=self.canvas_width,
            height=self.canvas_height,
            bg="white",
            highlightthickness=0
        )
        self.canvas.pack(padx=6, pady=6)

        self.canvas_img_id = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

        # Mouse events
        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw_motion)
        self.canvas.bind("<ButtonRelease-1>", self.stop_draw)

        self.last_x = None
        self.last_y = None

    # ----------------------
    # STATUS BAR
    # ----------------------
    def create_statusbar(self):
        status_bar = ctk.CTkFrame(self, fg_color="#f5f5f5", height=32)
        status_bar.pack(side="bottom", fill="x", padx=10, pady=8)

        self.status_label = ctk.CTkLabel(status_bar, text=self.status_text(),
                                         anchor="w", font=self.font_status)
        self.status_label.pack(side="left", padx=10, pady=6)

        self.message_label = ctk.CTkLabel(status_bar, text="", anchor="e",
                                          text_color="#555", font=self.font_status)
        self.message_label.pack(side="right", padx=10, pady=6)

    def status_text(self):
        fill_state = "On" if self.fill_shapes else "Off"
        return (f"File: {self.current_file} • Tool: {self.mode_labels[self.mode]} • Stroke: {self.brush_size}px • "
                f"Text: {self.text_size}px • Color: {self.current_color} • Fill: {fill_state}")

    def refresh_status(self, message=None):
        self.status_label.configure(text=self.status_text())
        if message is not None:
            self.message_label.configure(text=message)

    # ----------------------
    # MODE HANDLING
    # ----------------------
    def handle_tool_select(self, display_value):
        mode = self.display_to_mode.get(display_value, display_value)
        self.set_mode(mode)

    def set_mode(self, mode):
        self.mode = mode
        self.last_x = None
        self.last_y = None
        self.shape_start = None
        self.clear_preview_shape()
        if self.tool_selector.get() != self.mode_labels[self.mode]:
            self.tool_selector.set(self.mode_labels[self.mode])
        self.refresh_status()

    # ----------------------
    # COLOR PICKER
    # ----------------------
    def pick_color(self):
        color = colorchooser.askcolor()[1]
        if color:
            self.set_color(color)

    def select_palette(self, palette_name):
        if palette_name not in self.palettes:
            return
        self.current_palette_name = palette_name
        self.quick_colors = self.palettes[palette_name]
        if self.quick_colors:
            self.set_color(self.quick_colors[0])
        self.build_palette_buttons(self.palette_frame)
        self.refresh_status(f"Palette: {palette_name}")

    def build_palette_buttons(self, parent):
        for btn in getattr(self, "palette_buttons", []):
            btn.destroy()
        self.palette_buttons = []
        for color in self.quick_colors:
            btn = ctk.CTkButton(
                parent, text="", width=26, height=26,
                fg_color=color, hover_color=color,
                border_color="#d1d5db", border_width=1,
                command=lambda c=color: self.set_color(c)
            )
            btn.pack(side="left", padx=3)
            self.palette_buttons.append(btn)

    def set_color(self, color):
        self.current_color = color
        self.color_preview.configure(fg_color=color)
        self.refresh_status()

    def change_brush_size(self, value):
        self.brush_size = int(float(value))
        self.brush_value_label.configure(text=f"{self.brush_size}px")
        self.refresh_status()

    def change_text_size(self, value):
        self.text_size = int(float(value))
        self.text_value_label.configure(text=f"{self.text_size}px")
        self.refresh_status()

    def toggle_fill(self):
        self.fill_shapes = bool(self.fill_switch.get())
        self.refresh_status()

    # ----------------------
    # FILE MANAGEMENT
    # ----------------------
    def handle_file_change_request(self, filename):
        if filename:
            self.switch_file(filename)

    def add_file_entry(self):
        suggested = f"output_{len(self.files) + 1}.png"
        dialog = ctk.CTkInputDialog(
            text=f"Enter new filename (.png)\nSuggested: {suggested}",
            title="Add File"
        )
        new_name = dialog.get_input()

        if not new_name:
            return

        new_name = new_name.strip()
        if not new_name:
            return

        if not new_name.lower().endswith(".png"):
            new_name += ".png"

        if new_name in self.files:
            self.refresh_status(f"{new_name} already exists")
            return

        self.files.append(new_name)
        self.file_images[new_name] = self._new_blank_image()
        self.file_history[new_name] = []
        self.file_selector.configure(values=self.files)
        self.switch_file(new_name)

    def remove_file_entry(self):
        if len(self.files) <= 1:
            self.refresh_status("Keep at least one file")
            return

        to_remove = self.current_file
        next_file = next(f for f in self.files if f != to_remove)

        self.switch_file(next_file)

        self.files = [f for f in self.files if f != to_remove]
        self.file_images.pop(to_remove, None)
        self.file_history.pop(to_remove, None)

        self.file_selector.configure(values=self.files)
        self.refresh_status(f"Removed {to_remove}")

    def switch_file(self, filename):
        if filename == self.current_file:
            return

        # Preserve current canvas state before switching
        self.file_images[self.current_file] = self.img
        self.record_file_history(self.current_file)

        self.current_file = filename
        if filename not in self.files:
            self.files.append(filename)
            self.file_selector.configure(values=self.files)

        self.img = self.get_or_create_image(filename)
        self.draw = ImageDraw.Draw(self.img)

        if hasattr(self, "file_selector") and self.file_selector.get() != filename:
            self.file_selector.set(filename)

        self.update_canvas_image()
        self.refresh_status(f"Switched to {filename}")
        self.on_file_change(filename)

    def get_or_create_image(self, filename):
        if filename not in self.file_images:
            self.file_images[filename] = self._new_blank_image()
            self.file_history[filename] = []
        return self.file_images[filename]

    def _new_blank_image(self):
        return Image.new("RGB", (self.canvas_width, self.canvas_height), "white")

    def record_file_history(self, filename):
        if filename not in self.file_images:
            return
        hist = self.file_history.setdefault(filename, [])
        hist.append(self.file_images[filename].copy())
        if len(hist) > self.history_limit:
            hist.pop(0)

    def on_file_change(self, filename):
        """Hook that fires when the active file changes."""
        # You can override or monkey-patch this in callers if needed.
        return

    # ----------------------
    # DRAWING LOGIC
    # ----------------------
    def start_draw(self, event):
        if self.mode == "text":
            self.add_text(event.x, event.y)
            return

        if self.mode in {"line", "rectangle", "ellipse"}:
            self.shape_start = (event.x, event.y)
            return

        self.last_x = event.x
        self.last_y = event.y

    def draw_motion(self, event):
        if self.mode == "text":
            return

        if self.mode in {"line", "rectangle", "ellipse"}:
            self.preview_shape(event.x, event.y)
            return

        x, y = event.x, event.y

        if self.last_x is not None:
            fill = self.current_color if self.mode == "draw" else "white"
            self.draw.line((self.last_x, self.last_y, x, y),
                           fill=fill, width=self.brush_size)
            self.update_canvas_image()

        self.last_x = x
        self.last_y = y

    def stop_draw(self, event):
        if self.mode in {"line", "rectangle", "ellipse"}:
            self.commit_shape(event.x, event.y)
            self.shape_start = None
            self.clear_preview_shape()
            return

        self.last_x = None
        self.last_y = None

    def preview_shape(self, x, y):
        self.clear_preview_shape()
        if not self.shape_start:
            return

        x0, y0 = self.shape_start
        fill = self.current_color if (self.fill_shapes and self.mode != "line") else ""

        if self.mode == "line":
            self.preview_shape_id = self.canvas.create_line(
                x0, y0, x, y, fill=self.current_color, width=self.brush_size
            )
        elif self.mode == "rectangle":
            self.preview_shape_id = self.canvas.create_rectangle(
                x0, y0, x, y,
                outline=self.current_color,
                fill=fill,
                width=self.brush_size
            )
        elif self.mode == "ellipse":
            self.preview_shape_id = self.canvas.create_oval(
                x0, y0, x, y,
                outline=self.current_color,
                fill=fill,
                width=self.brush_size
            )

    def clear_preview_shape(self):
        if self.preview_shape_id:
            self.canvas.delete(self.preview_shape_id)
            self.preview_shape_id = None

    def commit_shape(self, x, y):
        if not self.shape_start:
            return

        x0, y0 = self.shape_start
        if (x0, y0) == (x, y):
            return

        fill = self.current_color if (self.fill_shapes and self.mode != "line") else None

        if self.mode == "line":
            self.draw.line((x0, y0, x, y), fill=self.current_color, width=self.brush_size)
        elif self.mode == "rectangle":
            self.draw.rectangle([x0, y0, x, y],
                                outline=self.current_color,
                                fill=fill,
                                width=self.brush_size)
        elif self.mode == "ellipse":
            self.draw.ellipse([x0, y0, x, y],
                              outline=self.current_color,
                              fill=fill,
                              width=self.brush_size)

        self.update_canvas_image()

    # ----------------------
    # TEXT TOOL
    # ----------------------
    def add_text(self, x, y):
        text_win = ctk.CTkInputDialog(text="Enter text:", title="Add Text")
        text = text_win.get_input()

        if text:
            font = self.get_text_font()
            self.draw.text((x, y), text, fill=self.current_color, font=font)
            self.update_canvas_image()
            self.refresh_status(f'Text added at ({x}, {y})')

    def get_text_font(self):
        try:
            return ImageFont.truetype("DejaVuSans.ttf", self.text_size)
        except OSError:
            # Fallback to default font if bundled font is unavailable
            return ImageFont.load_default()

    # ----------------------
    # UPDATE CANVAS
    # ----------------------
    def update_canvas_image(self):
        self.tk_img = ImageTk.PhotoImage(self.img)
        self.canvas.itemconfig(self.canvas_img_id, image=self.tk_img)

    # ----------------------
    # CLEAR CANVAS
    # ----------------------
    def clear_canvas(self):
        self.img = self._new_blank_image()
        self.file_images[self.current_file] = self.img
        self.draw = ImageDraw.Draw(self.img)
        self.clear_preview_shape()
        self.update_canvas_image()
        self.refresh_status("Canvas cleared")

    # ----------------------
    # GENERATE PNG
    # ----------------------
    def generate_png(self):
        filename = self.current_file
        self.record_file_history(self.current_file)
        file_path = self.images_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        self.img.save(file_path)
        print("here")
        saved_path = str(file_path.resolve())
        self.refresh_status(f"Saved: {saved_path}")
        print(f"[✔] Saved: {saved_path}")

        print(filename)
        image_path = filename
        image_name = image_path
        os.chdir("/mnt/windows/Users/Admin/Desktop/All/Not_College/Codes/MachineLearning/Sketch-To-Website/")
        image_path = "./images/"+image_path
        
        print("Editing ",image_path)
        layout = build_layout(image_path)

        layout_path = Path("layout_output.json")
        history = {}
        if layout_path.exists():
            try:
                existing = json.loads(layout_path.read_text())
                if isinstance(existing, dict) and "elements" in existing:
                    pass  # old single-layout format; ignore to keep current logic safe
                elif isinstance(existing, dict):
                    history = existing
            except Exception:
                pass
        
        history[filename] = layout
        full_layout_json = json.dumps(history, indent=2)
        layout_path.write_text(full_layout_json)
        print(f"Layout JSON written to {layout_path}")

        try:
            code, context = generate_ui_code(
                full_layout_json,
                filename=f"{filename[:4]}/page.tsx",
                components=self.generated_code,
                palette=self.palettes.get(self.current_palette_name)
            )
            layout["page_context"] = context
            history[filename] = layout
            layout_path.write_text(json.dumps(history, indent=2))
            self.generated_code[filename] = code

            path = "./websiteTemp/app"

            # extract only filename without extension
            folder = image_name.rsplit(".",1)[0]
            output_dir = f"{path}/{folder}"

            print(1)

            # Create directory if not present (no crash)
            os.makedirs(output_dir, exist_ok=True)

            # Always rewrite safely
            Path(f"{output_dir}/page.tsx").write_text(code)

            print("Generated UI written successfully.")

        except Exception as exc:
            print(f"Model invocation failed: {exc}")

def ensure_package_manager_is_npm(project_root: Path):
    """Force packageManager to npm so shadcn uses npm instead of bun."""
    pkg_path = project_root / "package.json"
    if not pkg_path.exists():
        print(f"[!] package.json not found under {project_root}. Skipping shadcn setup.")
        return
    try:
        data = json.loads(pkg_path.read_text())
    except Exception as exc:
        print(f"[!] Could not read package.json: {exc}")
        return
    if "packageManager" not in data:
        npm_version = subprocess.run(["npm", "-v"], capture_output=True, text=True)
        version_str = (npm_version.stdout or "").strip() or "latest"
        data["packageManager"] = f"npm@{version_str}"
        pkg_path.write_text(json.dumps(data, indent=2))
        print(f"[✔] Set packageManager to npm@{version_str}")


def ensure_shadcn_setup(project_root: Path):
    """Initialize shadcn/ui once using npm (creates components.json)."""
    components_config = project_root / "components.json"
    ensure_package_manager_is_npm(project_root)
    if not components_config.exists():
        print("[*] Initializing shadcn/ui with npm...")
        try:
            subprocess.run(
                ["npx", "--yes", "shadcn@latest", "init", "--package-manager", "npm", "--skip-install"],
                cwd=project_root,
                check=False,
            )
        except FileNotFoundError:
            print("[!] npm or npx not found; cannot initialize shadcn/ui.")
            return
    # Add a few core components up front to avoid repeated prompts.
    basic_components = [
        "button",
        "input",
        "card",
        "textarea",
        "dialog",
        "dropdown-menu",
        "navigation-menu",
        "separator",
        "label",
        "checkbox",
    ]
    try:
        subprocess.run(
            ["npx", "--yes", "shadcn@latest", "add", *basic_components, "--package-manager", "npm", "--skip-install"],
            cwd=project_root,
            check=False,
        )
    except FileNotFoundError:
        print("[!] npm or npx not found; cannot add shadcn/ui components.")


def ensure_tsconfig_aliases(project_root: Path):
    """Make sure tsconfig.json has @/* and ~/* pointing to project root."""
    ts_path = project_root / "tsconfig.json"
    if not ts_path.exists():
        print(f"[!] tsconfig.json not found under {project_root}, skipping alias setup.")
        return
    try:
        data = json.loads(ts_path.read_text())
    except Exception as exc:
        print(f"[!] Could not read tsconfig.json: {exc}")
        return

    compiler = data.setdefault("compilerOptions", {})
    paths = compiler.setdefault("paths", {})
    desired = {"@/*": ["./*"], "~/*": ["./*"]}

    changed = False
    for alias, target in desired.items():
        if paths.get(alias) != target:
            paths[alias] = target
            changed = True

    if changed:
        ts_path.write_text(json.dumps(data, indent=2))
        print("[✔] Ensured tsconfig path aliases for @/* and ~/*")

import shutil
if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent / "websiteTemp"
    ensure_tsconfig_aliases(project_root)
    ensure_shadcn_setup(project_root)

    # Create React APP
    if(os.path.isdir("./websiteTemp")):
        pass
    else:
        os.mkdir("./websiteTemp")
    folder = './websiteTemp'
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

    path = "./websiteTemp"

    os.chdir(path)

    subprocess.run(["npx",'-y',"degit","rajput-hemant/nextjs-template myapp"])
    subprocess.run(["npm","i"])
    subprocess.run(['npm','install','@mantine/core','@mantine/hooks',' @nextui-org/react','flowbite-react','daisyui','@headlessui/react'])
    
    # subprocess.run(['npm','run','dev'])
    subprocess.run(['npm','install','tw-animate-css'])




    app = MiniPaint()
    app.mainloop()

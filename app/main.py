import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys
import os
import json
from datetime import datetime
import time

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Database
from clipboard_monitor import ClipboardMonitor
from hotkeys import HotkeyManager

VERSION = "1.0.0"
UPDATE_URL = "https://raw.githubusercontent.com/YOUR_USERNAME/kopirovacka/main/version.json"

COLORS = {
    "bg": "#1e1e2e",
    "bg2": "#2a2a3e",
    "bg3": "#313147",
    "accent": "#7c3aed",
    "accent_hover": "#6d28d9",
    "green": "#22c55e",
    "green_hover": "#16a34a",
    "green_bg": "#14532d",
    "text": "#e2e8f0",
    "text_dim": "#94a3b8",
    "red": "#ef4444",
    "red_hover": "#dc2626",
    "border": "#3f3f5a",
    "selected": "#1a3a2a",
    "selected_border": "#22c55e",
    "pin": "#f59e0b",
    "row_hover": "#2f2f4a",
}

FONTS = {
    "title": ("Segoe UI", 14, "bold"),
    "normal": ("Segoe UI", 10),
    "small": ("Segoe UI", 9),
    "mono": ("Consolas", 10),
    "bold": ("Segoe UI", 10, "bold"),
}


class KopirovackaApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Kopírovačka v" + VERSION)
        self.root.geometry("520x680")
        self.root.minsize(420, 500)
        self.root.configure(bg=COLORS["bg"])

        # State
        self.selected_id = None
        self.pin_mode = tk.BooleanVar(value=False)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search)
        self.always_on_top = tk.BooleanVar(value=False)

        # Init DB
        self.db = Database()

        # Build UI
        self._setup_icon()
        self._build_ui()

        # Clipboard monitor
        self.monitor = ClipboardMonitor(
            on_new_text=self._on_clipboard_text,
            on_new_image=self._on_clipboard_image,
            on_new_file=self._on_clipboard_file,
        )
        self.monitor.start()

        # Hotkeys
        self.hotkey_mgr = HotkeyManager(
            toggle_callback=self._toggle_window,
        )
        self.hotkey_mgr.start()

        # Load entries
        self._refresh_list()

        # Window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # System tray (minimize to tray)
        self._setup_tray()

        # Keyboard shortcuts in app
        self.root.bind("<Escape>", lambda e: self._hide_window())
        self.root.bind("<Delete>", lambda e: self._delete_selected())

    def _setup_icon(self):
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

    def _build_ui(self):
        # ── Top bar ──────────────────────────────────────────────────
        top = tk.Frame(self.root, bg=COLORS["bg2"], pady=10, padx=14)
        top.pack(fill="x")

        tk.Label(top, text="📋 Kopírovačka", font=FONTS["title"],
                 bg=COLORS["bg2"], fg=COLORS["text"]).pack(side="left")

        # Version label
        tk.Label(top, text=f"v{VERSION}", font=FONTS["small"],
                 bg=COLORS["bg2"], fg=COLORS["text_dim"]).pack(side="left", padx=(6, 0), pady=(4, 0))

        # Right side controls
        ctrl = tk.Frame(top, bg=COLORS["bg2"])
        ctrl.pack(side="right")

        # Always on top toggle
        aot_btn = tk.Checkbutton(ctrl, text="📌 Vždy navrchu",
                                  variable=self.always_on_top,
                                  command=self._toggle_always_on_top,
                                  bg=COLORS["bg2"], fg=COLORS["text_dim"],
                                  selectcolor=COLORS["bg3"],
                                  activebackground=COLORS["bg2"],
                                  font=FONTS["small"], bd=0,
                                  highlightthickness=0)
        aot_btn.pack(side="right", padx=(0, 4))

        # ── Current selection banner ──────────────────────────────────
        self.banner = tk.Frame(self.root, bg=COLORS["green_bg"], pady=8, padx=14)
        self.banner.pack(fill="x")

        self.banner_icon = tk.Label(self.banner, text="✓", font=FONTS["bold"],
                                     bg=COLORS["green_bg"], fg=COLORS["green"])
        self.banner_icon.pack(side="left")

        self.banner_label = tk.Label(self.banner,
                                      text="  Žiadna položka nie je vybraná",
                                      font=FONTS["normal"],
                                      bg=COLORS["green_bg"], fg=COLORS["green"],
                                      anchor="w")
        self.banner_label.pack(side="left", fill="x", expand=True)

        self.banner_type = tk.Label(self.banner, text="",
                                     font=FONTS["small"],
                                     bg=COLORS["green_bg"], fg=COLORS["green"])
        self.banner_type.pack(side="right")

        # ── Search bar ───────────────────────────────────────────────
        search_frame = tk.Frame(self.root, bg=COLORS["bg"], pady=8, padx=14)
        search_frame.pack(fill="x")

        tk.Label(search_frame, text="🔍", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=FONTS["normal"]).pack(side="left")

        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                 bg=COLORS["bg3"], fg=COLORS["text"],
                                 insertbackground=COLORS["text"],
                                 relief="flat", font=FONTS["normal"],
                                 highlightthickness=1,
                                 highlightcolor=COLORS["accent"],
                                 highlightbackground=COLORS["border"])
        search_entry.pack(side="left", fill="x", expand=True, padx=(6, 0), ipady=5)

        # ── Toolbar ───────────────────────────────────────────────────
        toolbar = tk.Frame(self.root, bg=COLORS["bg"], padx=14, pady=0)
        toolbar.pack(fill="x")

        self._make_btn(toolbar, "🗑️ Vymazať", self._delete_selected,
                       COLORS["red"], COLORS["red_hover"]).pack(side="left", padx=(0, 6))
        self._make_btn(toolbar, "🗑️ Vyčistiť všetko", self._clear_all,
                       COLORS["bg3"], COLORS["border"]).pack(side="left")
        self._make_btn(toolbar, "📤 Export", self._export_history,
                       COLORS["bg3"], COLORS["border"]).pack(side="right")

        # ── List area ─────────────────────────────────────────────────
        list_outer = tk.Frame(self.root, bg=COLORS["bg"], padx=14, pady=8)
        list_outer.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(list_outer, bg=COLORS["bg3"], pady=6, padx=10)
        header.pack(fill="x")
        tk.Label(header, text="#", width=3, bg=COLORS["bg3"],
                 fg=COLORS["text_dim"], font=FONTS["small"], anchor="w").pack(side="left")
        tk.Label(header, text="Typ", width=6, bg=COLORS["bg3"],
                 fg=COLORS["text_dim"], font=FONTS["small"], anchor="w").pack(side="left")
        tk.Label(header, text="Obsah", bg=COLORS["bg3"],
                 fg=COLORS["text_dim"], font=FONTS["small"], anchor="w").pack(side="left", expand=True, fill="x")
        tk.Label(header, text="Čas", width=10, bg=COLORS["bg3"],
                 fg=COLORS["text_dim"], font=FONTS["small"], anchor="e").pack(side="right")

        # Scrollable list
        canvas_frame = tk.Frame(list_outer, bg=COLORS["bg"])
        canvas_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg=COLORS["bg"],
                                 highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical",
                                  command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.list_frame = tk.Frame(self.canvas, bg=COLORS["bg"])
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.list_frame, anchor="nw")

        self.list_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

        # ── Status bar ────────────────────────────────────────────────
        status = tk.Frame(self.root, bg=COLORS["bg2"], pady=5, padx=14)
        status.pack(fill="x", side="bottom")

        self.status_label = tk.Label(status, text="",
                                      font=FONTS["small"],
                                      bg=COLORS["bg2"], fg=COLORS["text_dim"])
        self.status_label.pack(side="left")

        tk.Label(status, text="Ctrl+; = otvoriť/zatvoriť  •  Ctrl+V = vložiť vybraté",
                 font=FONTS["small"], bg=COLORS["bg2"],
                 fg=COLORS["text_dim"]).pack(side="right")

    def _make_btn(self, parent, text, cmd, bg, hover_bg, **kwargs):
        btn = tk.Label(parent, text=text, bg=bg, fg=COLORS["text"],
                       font=FONTS["small"], padx=10, pady=5,
                       cursor="hand2", relief="flat", **kwargs)
        btn.bind("<Button-1>", lambda e: cmd())
        btn.bind("<Enter>", lambda e: btn.configure(bg=hover_bg))
        btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
        return btn

    # ── List rendering ────────────────────────────────────────────────

    def _refresh_list(self, search=""):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        entries = self.db.get_entries(search=search)
        count = len(entries)

        if count == 0:
            tk.Label(self.list_frame,
                     text="Žiadne položky. Skopíruj niečo! 📋",
                     bg=COLORS["bg"], fg=COLORS["text_dim"],
                     font=FONTS["normal"], pady=40).pack(expand=True)
        else:
            for idx, entry in enumerate(entries):
                self._build_row(idx + 1, entry)

        self.status_label.config(text=f"{count} / 20 položiek")
        self._update_banner()

    def _build_row(self, idx, entry):
        eid = entry["id"]
        is_selected = (eid == self.selected_id)
        is_pinned = entry.get("pinned", 0)

        row_bg = COLORS["selected"] if is_selected else COLORS["bg"]
        border_color = COLORS["selected_border"] if is_selected else COLORS["bg"]

        row = tk.Frame(self.list_frame, bg=row_bg,
                       highlightbackground=border_color,
                       highlightthickness=1 if is_selected else 0,
                       pady=1)
        row.pack(fill="x", pady=1)

        inner = tk.Frame(row, bg=row_bg, padx=10, pady=7)
        inner.pack(fill="x")

        # Index
        tk.Label(inner, text=str(idx), width=3, bg=row_bg,
                 fg=COLORS["text_dim"] if not is_selected else COLORS["green"],
                 font=FONTS["small"], anchor="w").pack(side="left")

        # Type icon
        type_icon = self._get_type_icon(entry["type"])
        tk.Label(inner, text=type_icon, width=3, bg=row_bg,
                 fg=COLORS["text_dim"], font=FONTS["normal"]).pack(side="left")

        # Content preview
        preview = self._get_preview(entry)
        content_lbl = tk.Label(inner, text=preview, bg=row_bg,
                                fg=COLORS["text"] if is_selected else COLORS["text"],
                                font=FONTS["mono"] if entry["type"] == "text" else FONTS["normal"],
                                anchor="w", cursor="hand2")
        content_lbl.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Pin indicator
        if is_pinned:
            tk.Label(inner, text="📌", bg=row_bg,
                     font=FONTS["small"]).pack(side="right", padx=2)

        # Time
        ts = entry.get("created_at", "")
        time_str = self._format_time(ts)
        tk.Label(inner, text=time_str, bg=row_bg,
                 fg=COLORS["text_dim"], font=FONTS["small"],
                 width=10, anchor="e").pack(side="right")

        # Selected indicator
        if is_selected:
            tk.Label(inner, text="✓", bg=row_bg,
                     fg=COLORS["green"], font=FONTS["bold"]).pack(side="right")

        # Bind clicks
        for widget in [row, inner] + list(inner.winfo_children()):
            widget.bind("<Button-1>", lambda e, eid=eid: self._select_entry(eid))
            widget.bind("<Enter>", lambda e, r=row, bg=row_bg: r.configure(
                bg=COLORS["row_hover"] if not (eid == self.selected_id) else bg))
            widget.bind("<Leave>", lambda e, r=row, bg=row_bg: r.configure(bg=bg))
            widget.bind("<Double-Button-1>", lambda e, eid=eid: self._copy_to_clipboard(eid))
            widget.bind("<Button-3>", lambda e, eid=eid: self._show_context_menu(e, eid))

    def _get_type_icon(self, t):
        return {"text": "📝", "image": "🖼️", "file": "📁"}.get(t, "📄")

    def _get_preview(self, entry):
        if entry["type"] == "text":
            text = entry.get("content", "")
            return text[:60] + ("…" if len(text) > 60 else "")
        elif entry["type"] == "image":
            return f"[Obrázok  {entry.get('meta', '')}]"
        elif entry["type"] == "file":
            return entry.get("content", "")[:60]
        return ""

    def _format_time(self, ts):
        try:
            dt = datetime.fromisoformat(ts)
            now = datetime.now()
            if dt.date() == now.date():
                return dt.strftime("%H:%M:%S")
            return dt.strftime("%d.%m %H:%M")
        except Exception:
            return ""

    def _update_banner(self):
        if self.selected_id is None:
            self.banner_label.config(text="  Žiadna položka nie je vybraná")
            self.banner_type.config(text="")
            return
        entry = self.db.get_entry(self.selected_id)
        if not entry:
            self.banner_label.config(text="  Žiadna položka nie je vybraná")
            return
        preview = self._get_preview(entry)
        self.banner_label.config(text=f"  {preview}")
        self.banner_type.config(text=self._get_type_icon(entry["type"]))

    # ── Selection & clipboard ─────────────────────────────────────────

    def _select_entry(self, eid):
        self.selected_id = eid
        entry = self.db.get_entry(eid)
        if entry:
            self._apply_to_clipboard(entry)
        self._refresh_list(self.search_var.get())

    def _apply_to_clipboard(self, entry):
        try:
            import pyperclip
            if entry["type"] == "text":
                pyperclip.copy(entry["content"])
            elif entry["type"] == "file":
                pyperclip.copy(entry["content"])
            elif entry["type"] == "image":
                self._copy_image_to_clipboard(entry)
        except Exception as ex:
            self._set_status(f"Chyba: {ex}")

    def _copy_image_to_clipboard(self, entry):
        try:
            import win32clipboard
            from PIL import Image
            import io, base64
            img_data = base64.b64decode(entry["content"])
            img = Image.open(io.BytesIO(img_data))
            output = io.BytesIO()
            img.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()
        except Exception:
            pass

    def _copy_to_clipboard(self, eid):
        self._select_entry(eid)
        self._set_status("✓ Skopírované do schránky")

    # ── Clipboard monitor callbacks ───────────────────────────────────

    def _on_clipboard_text(self, text):
        if not text.strip():
            return
        # Check if this is something WE put in clipboard (our selected item)
        if self.selected_id:
            entry = self.db.get_entry(self.selected_id)
            if entry and entry["type"] == "text" and entry["content"] == text:
                return  # Don't re-add our own paste
        new_id = self.db.add_entry("text", text)
        if new_id:
            self.selected_id = new_id
            self.root.after(0, lambda: self._refresh_list(self.search_var.get()))

    def _on_clipboard_image(self, img_b64, meta):
        new_id = self.db.add_entry("image", img_b64, meta=meta)
        if new_id:
            self.selected_id = new_id
            self.root.after(0, lambda: self._refresh_list(self.search_var.get()))

    def _on_clipboard_file(self, paths):
        content = "\n".join(paths)
        new_id = self.db.add_entry("file", content)
        if new_id:
            self.selected_id = new_id
            self.root.after(0, lambda: self._refresh_list(self.search_var.get()))

    # ── UI actions ────────────────────────────────────────────────────

    def _delete_selected(self):
        if self.selected_id is None:
            return
        self.db.delete_entry(self.selected_id)
        self.selected_id = None
        self._refresh_list(self.search_var.get())

    def _clear_all(self):
        if messagebox.askyesno("Vyčistiť", "Naozaj vymazať celú históriu?",
                                parent=self.root):
            self.db.clear_all()
            self.selected_id = None
            self._refresh_list()

    def _export_history(self):
        from tkinter.filedialog import asksaveasfilename
        path = asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON súbor", "*.json"), ("Všetky súbory", "*.*")],
            title="Exportovať históriu"
        )
        if path:
            entries = self.db.get_entries()
            export = []
            for e in entries:
                if e["type"] == "text":
                    export.append({"type": e["type"], "content": e["content"],
                                   "created_at": e.get("created_at", "")})
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export, f, ensure_ascii=False, indent=2)
            self._set_status(f"✓ Exportované: {os.path.basename(path)}")

    def _show_context_menu(self, event, eid):
        menu = tk.Menu(self.root, tearoff=0, bg=COLORS["bg2"],
                       fg=COLORS["text"], activebackground=COLORS["accent"],
                       activeforeground=COLORS["text"], bd=0)
        menu.add_command(label="✓ Vybrať (Ctrl+V bude vkladať toto)",
                         command=lambda: self._select_entry(eid))
        menu.add_command(label="📋 Skopírovať do schránky",
                         command=lambda: self._copy_to_clipboard(eid))

        entry = self.db.get_entry(eid)
        if entry:
            pin_text = "📌 Odopnúť" if entry.get("pinned") else "📌 Pripnúť"
            menu.add_command(label=pin_text,
                             command=lambda: self._toggle_pin(eid))

        menu.add_separator()
        menu.add_command(label="🗑️ Vymazať",
                         command=lambda: self._delete_entry(eid))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _toggle_pin(self, eid):
        self.db.toggle_pin(eid)
        self._refresh_list(self.search_var.get())

    def _delete_entry(self, eid):
        self.db.delete_entry(eid)
        if self.selected_id == eid:
            self.selected_id = None
        self._refresh_list(self.search_var.get())

    def _on_search(self, *args):
        self._refresh_list(self.search_var.get())

    def _set_status(self, msg):
        self.status_label.config(text=msg)
        self.root.after(3000, lambda: self.status_label.config(text=""))

    def _toggle_always_on_top(self):
        self.root.wm_attributes("-topmost", self.always_on_top.get())

    # ── Window visibility ─────────────────────────────────────────────

    def _toggle_window(self):
        if self.root.state() == "withdrawn" or not self.root.winfo_viewable():
            self._show_window()
        else:
            self._hide_window()

    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _hide_window(self):
        self.root.withdraw()

    def _on_close(self):
        self._hide_window()

    # ── Canvas scroll helpers ─────────────────────────────────────────

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ── Tray ──────────────────────────────────────────────────────────

    def _setup_tray(self):
        try:
            import pystray
            from PIL import Image, ImageDraw
            import io

            # Create simple icon
            img = Image.new("RGB", (64, 64), color="#7c3aed")
            draw = ImageDraw.Draw(img)
            draw.rectangle([8, 16, 56, 48], fill="white")
            draw.rectangle([12, 20, 52, 44], fill="#7c3aed")
            draw.line([16, 28, 48, 28], fill="white", width=3)
            draw.line([16, 36, 40, 36], fill="white", width=3)

            def on_show(icon, item):
                self.root.after(0, self._show_window)

            def on_quit(icon, item):
                icon.stop()
                self.root.after(0, self._quit)

            menu = pystray.Menu(
                pystray.MenuItem("📋 Otvoriť Kopírovačku", on_show, default=True),
                pystray.MenuItem("❌ Ukončiť", on_quit)
            )

            self.tray_icon = pystray.Icon("kopirovacka", img, "Kopírovačka", menu)
            tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            tray_thread.start()
        except ImportError:
            pass

    def _quit(self):
        self.monitor.stop()
        self.hotkey_mgr.stop()
        try:
            self.tray_icon.stop()
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = KopirovackaApp()
    app.run()

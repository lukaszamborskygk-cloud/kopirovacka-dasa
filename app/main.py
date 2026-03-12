import tkinter as tk
from tkinter import messagebox
import threading
import sys
import os
import json
import socket
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Database
from clipboard_monitor import ClipboardMonitor
from hotkeys import HotkeyManager

VERSION = "1.0.1"

LOCK_PORT = 59432

def acquire_single_instance():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    try:
        sock.bind(("127.0.0.1", LOCK_PORT))
        sock.listen(1)
        return sock
    except OSError:
        return None

C = {
    "bg":        "#0f1117",
    "surface":   "#1a1d27",
    "surface2":  "#21253a",
    "surface3":  "#272b3f",
    "hover":     "#2d3250",
    "purple":    "#7c6af7",
    "purple2":   "#6355e0",
    "purple_dim":"#3d3580",
    "green":     "#22d48f",
    "green_bg":  "#0d2b20",
    "green_dim": "#0f3d28",
    "yellow":    "#f5c542",
    "red":       "#f05252",
    "red_bg":    "#2d1515",
    "text":      "#e8eaf6",
    "text2":     "#9196b0",
    "text3":     "#5a5f7a",
    "border":    "#2a2f4a",
    "border2":   "#3a3f5a",
}

FONT = "Segoe UI"

def make_font(size=10, bold=False):
    return (FONT, size, "bold" if bold else "normal")


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, width=120, height=34,
                 bg=None, hover=None, fg=None, radius=8, font_size=9, **kwargs):
        self.bg_color = bg or C["purple"]
        self.hover_color = hover or C["purple2"]
        self.fg_color = fg or C["text"]
        self.radius = radius
        super().__init__(parent, width=width, height=height,
                         bg=parent["bg"], highlightthickness=0, **kwargs)
        self.command = command
        self.text = text
        self.font_size = font_size
        self._draw(self.bg_color)
        self.bind("<Enter>", lambda e: self._draw(self.hover_color))
        self.bind("<Leave>", lambda e: self._draw(self.bg_color))
        self.bind("<Button-1>", lambda e: command())

    def _draw(self, color):
        self.delete("all")
        w = int(self["width"])
        h = int(self["height"])
        r = self.radius
        self.create_polygon(
            r, 0, w-r, 0, w, r, w, h-r, w-r, h, r, h, 0, h-r, 0, r,
            smooth=True, fill=color, outline=""
        )
        self.create_text(w//2, h//2, text=self.text,
                         fill=self.fg_color,
                         font=make_font(self.font_size, bold=True))


class ClipRow(tk.Frame):
    def __init__(self, parent, entry, index, is_selected,
                 on_select, on_delete, on_pin, **kwargs):
        bg = C["surface2"] if is_selected else C["surface"]
        super().__init__(parent, bg=bg, cursor="hand2", **kwargs)
        self.entry = entry
        self.is_selected = is_selected
        self._bg = bg
        self._on_select = on_select
        self._on_delete = on_delete
        self._on_pin = on_pin

        accent = tk.Frame(self, bg=C["green"] if is_selected else C["surface3"], width=3)
        accent.pack(side="left", fill="y")

        content = tk.Frame(self, bg=bg, padx=12, pady=10)
        content.pack(side="left", fill="both", expand=True)

        top = tk.Frame(content, bg=bg)
        top.pack(fill="x")

        idx_canvas = tk.Canvas(top, width=22, height=22, bg=bg, highlightthickness=0)
        idx_canvas.pack(side="left")
        idx_canvas.create_oval(1, 1, 21, 21,
                                fill=C["purple"] if is_selected else C["surface3"],
                                outline="")
        idx_canvas.create_text(11, 11, text=str(index),
                                fill=C["text"], font=make_font(8, bold=True))

        type_icon = {"text": "TXT", "image": "IMG", "file": "FILE"}.get(entry["type"], "???")
        type_bg = {"text": C["purple_dim"], "image": "#1a3050", "file": "#2a2010"}.get(entry["type"], C["surface3"])
        type_fg = {"text": C["purple"], "image": "#4a9eff", "file": C["yellow"]}.get(entry["type"], C["text2"])
        tk.Label(top, text=type_icon, bg=type_bg, fg=type_fg,
                 font=make_font(7, bold=True), padx=5, pady=1).pack(side="left", padx=(6, 0))

        if entry.get("pinned"):
            tk.Label(top, text="pin", bg=bg, fg=C["yellow"], font=make_font(7)).pack(side="left", padx=4)

        ts = entry.get("created_at", "")
        time_str = self._fmt_time(ts)
        tk.Label(top, text=time_str, bg=bg, fg=C["text3"], font=make_font(8)).pack(side="right")

        if is_selected:
            tk.Label(top, text="aktívne", bg=bg, fg=C["green"],
                     font=make_font(8, bold=True)).pack(side="right", padx=(0, 8))

        preview = self._get_preview()
        tk.Label(content, text=preview, bg=bg,
                 fg=C["text"] if is_selected else C["text2"],
                 font=("Consolas", 10) if entry["type"] == "text" else make_font(10),
                 anchor="w", wraplength=400, justify="left").pack(fill="x", pady=(5, 0))

        self.actions = tk.Frame(content, bg=bg)
        self.actions.pack(fill="x", pady=(6, 0))
        self._build_actions()
        if not is_selected:
            self.actions.pack_forget()

        for w in self._all_children(self):
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)
            w.bind("<Button-1>", lambda e: on_select(entry["id"]))
            w.bind("<Button-3>", self._show_menu)

    def _build_actions(self):
        bg = self._bg
        RoundedButton(self.actions, "Vybrать & kopirovat",
                       lambda: self._on_select(self.entry["id"]),
                       width=160, height=26, font_size=8,
                       bg=C["green_bg"], hover=C["green_dim"],
                       fg=C["green"]).pack(side="left", padx=(0, 6))
        pin_text = "Odopnut" if self.entry.get("pinned") else "Pripnut"
        RoundedButton(self.actions, pin_text,
                       lambda: self._on_pin(self.entry["id"]),
                       width=80, height=26, font_size=8,
                       bg=C["surface3"], hover=C["hover"],
                       fg=C["text2"]).pack(side="left", padx=(0, 6))
        RoundedButton(self.actions, "Zmazat",
                       lambda: self._on_delete(self.entry["id"]),
                       width=70, height=26, font_size=8,
                       bg=C["red_bg"], hover="#3d1f1f",
                       fg=C["red"]).pack(side="left")

    def _get_preview(self):
        e = self.entry
        if e["type"] == "text":
            t = e.get("content", "")
            return t[:120] + ("..." if len(t) > 120 else "")
        elif e["type"] == "image":
            return f"Obrazok  {e.get('meta', '')}"
        elif e["type"] == "file":
            lines = e.get("content", "").split("\n")
            return "\n".join(lines[:3])
        return ""

    def _fmt_time(self, ts):
        try:
            dt = datetime.fromisoformat(ts)
            now = datetime.now()
            diff = now - dt
            if diff.seconds < 60:
                return "prave teraz"
            elif diff.seconds < 3600:
                return f"pred {diff.seconds // 60} min"
            elif dt.date() == now.date():
                return dt.strftime("%H:%M")
            return dt.strftime("%d.%m %H:%M")
        except Exception:
            return ""

    def _on_enter(self, e):
        if not self.is_selected:
            self._set_bg(C["hover"])
            self.actions.pack(fill="x", pady=(6, 0))

    def _on_leave(self, e):
        if not self.is_selected:
            self._set_bg(self._bg)
            self.actions.pack_forget()

    def _set_bg(self, color):
        try:
            self.configure(bg=color)
            for w in self._all_children(self):
                try:
                    w.configure(bg=color)
                except Exception:
                    pass
        except Exception:
            pass

    def _all_children(self, widget):
        children = [widget]
        for child in widget.winfo_children():
            children.extend(self._all_children(child))
        return children

    def _show_menu(self, event):
        menu = tk.Menu(self, tearoff=0, bg=C["surface2"], fg=C["text"],
                       activebackground=C["purple"], activeforeground=C["text"], bd=0)
        menu.add_command(label="Vybrat (Ctrl+V bude vkladat toto)",
                         command=lambda: self._on_select(self.entry["id"]))
        pin_text = "Odopnut" if self.entry.get("pinned") else "Pripnut"
        menu.add_command(label=pin_text, command=lambda: self._on_pin(self.entry["id"]))
        menu.add_separator()
        menu.add_command(label="Zmazat", command=lambda: self._on_delete(self.entry["id"]))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()


class KopirovackaApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"Kopirovacka  v{VERSION}")
        self.root.geometry("580x720")
        self.root.minsize(460, 520)
        self.root.configure(bg=C["bg"])

        self.selected_id = None
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self._refresh())
        self.always_on_top = tk.BooleanVar(value=False)

        self.db = Database()
        self._build_ui()

        self.monitor = ClipboardMonitor(
            on_new_text=self._on_clip_text,
            on_new_image=self._on_clip_image,
            on_new_file=self._on_clip_file,
        )
        self.monitor.start()

        self.hotkey_mgr = HotkeyManager(toggle_callback=self._toggle_window)
        self.hotkey_mgr.start()

        self._refresh()
        self.root.protocol("WM_DELETE_WINDOW", self._hide_window)
        self._setup_tray()
        self.root.bind("<Escape>", lambda e: self._hide_window())
        self.root.bind("<Delete>", lambda e: self._delete_selected())

    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg=C["surface"])
        header.pack(fill="x")
        tk.Frame(header, bg=C["purple"], height=3).pack(fill="x")
        inner_h = tk.Frame(header, bg=C["surface"], padx=20, pady=14)
        inner_h.pack(fill="x")

        left = tk.Frame(inner_h, bg=C["surface"])
        left.pack(side="left")
        logo_c = tk.Canvas(left, width=36, height=36, bg=C["surface"], highlightthickness=0)
        logo_c.pack(side="left")
        logo_c.create_oval(2, 2, 34, 34, fill=C["purple"], outline="")
        logo_c.create_text(18, 18, text="CB", fill="white", font=make_font(10, bold=True))
        tf = tk.Frame(left, bg=C["surface"], padx=10)
        tf.pack(side="left")
        tk.Label(tf, text="Kopirovacka", font=make_font(15, bold=True),
                 bg=C["surface"], fg=C["text"]).pack(anchor="w")
        tk.Label(tf, text=f"Spravca schranky  v{VERSION}",
                 font=make_font(8), bg=C["surface"], fg=C["text3"]).pack(anchor="w")

        right = tk.Frame(inner_h, bg=C["surface"])
        right.pack(side="right")
        aot_f = tk.Frame(right, bg=C["surface2"], padx=10, pady=6)
        aot_f.pack(side="right")
        tk.Checkbutton(aot_f, text="Vzdy navrchu",
                       variable=self.always_on_top, command=self._toggle_aot,
                       bg=C["surface2"], fg=C["text2"], selectcolor=C["surface3"],
                       activebackground=C["surface2"], font=make_font(9),
                       bd=0, highlightthickness=0).pack()

        # Banner
        self.banner_frame = tk.Frame(self.root, bg=C["green_bg"], padx=20, pady=10)
        self.banner_frame.pack(fill="x")
        bi = tk.Frame(self.banner_frame, bg=C["green_bg"])
        bi.pack(fill="x")
        tk.Label(bi, text="Aktivna polozka:", font=make_font(8, bold=True),
                 bg=C["green_bg"], fg=C["green"]).pack(side="left")
        self.banner_text = tk.Label(bi, text="ziadna",
                                     font=make_font(9), bg=C["green_bg"],
                                     fg=C["text"], anchor="w")
        self.banner_text.pack(side="left", padx=(8, 0), fill="x", expand=True)
        self.banner_type = tk.Label(bi, text="", font=make_font(8),
                                     bg=C["green_bg"], fg=C["green"])
        self.banner_type.pack(side="right")

        # Stats
        stats = tk.Frame(self.root, bg=C["surface"], padx=20, pady=10)
        stats.pack(fill="x")
        self.stat_count = self._stat_card(stats, "0", "poloziek")
        self.stat_count.pack(side="left", padx=(0, 10))
        self.stat_texts = self._stat_card(stats, "0", "textov")
        self.stat_texts.pack(side="left", padx=(0, 10))
        self.stat_images = self._stat_card(stats, "0", "obrazkov")
        self.stat_images.pack(side="left", padx=(0, 10))
        self.stat_files = self._stat_card(stats, "0", "suborov")
        self.stat_files.pack(side="left")

        # Toolbar
        toolbar = tk.Frame(self.root, bg=C["bg"], padx=20, pady=10)
        toolbar.pack(fill="x")
        sw = tk.Frame(toolbar, bg=C["surface2"], highlightthickness=1,
                      highlightbackground=C["border2"], highlightcolor=C["purple"])
        sw.pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Label(sw, text="Hladat:", bg=C["surface2"], fg=C["text3"],
                 font=make_font(9), padx=8).pack(side="left")
        tk.Entry(sw, textvariable=self.search_var, bg=C["surface2"], fg=C["text"],
                 insertbackground=C["text"], relief="flat", font=make_font(10),
                 highlightthickness=0).pack(side="left", fill="x", expand=True,
                                             ipady=6, pady=2)
        RoundedButton(toolbar, "Vycistit vsetko", self._clear_all,
                       width=140, height=34, font_size=9,
                       bg=C["surface2"], hover=C["hover"],
                       fg=C["text2"]).pack(side="right")
        RoundedButton(toolbar, "Export", self._export, width=80, height=34,
                       font_size=9, bg=C["surface2"], hover=C["hover"],
                       fg=C["text2"]).pack(side="right", padx=(0, 8))

        # Column header
        ch = tk.Frame(self.root, bg=C["surface3"], padx=20, pady=6)
        ch.pack(fill="x")
        tk.Label(ch, text="#  Typ   Obsah", bg=C["surface3"],
                 fg=C["text3"], font=make_font(8)).pack(side="left")
        tk.Label(ch, text="Cas", bg=C["surface3"],
                 fg=C["text3"], font=make_font(8)).pack(side="right")

        # List
        lc = tk.Frame(self.root, bg=C["bg"])
        lc.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(lc, bg=C["bg"], highlightthickness=0)
        sb = tk.Scrollbar(lc, orient="vertical", command=self.canvas.yview,
                          bg=C["surface"], troughcolor=C["bg"], width=8)
        self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.list_frame = tk.Frame(self.canvas, bg=C["bg"])
        self._cwin = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.list_frame.bind("<Configure>",
                              lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                          lambda e: self.canvas.itemconfig(self._cwin, width=e.width))
        self.canvas.bind("<MouseWheel>",
                          lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # Footer
        footer = tk.Frame(self.root, bg=C["surface"], pady=8, padx=20)
        footer.pack(fill="x", side="bottom")
        tk.Frame(footer, bg=C["border"], height=1).pack(fill="x", side="top", pady=(0, 8))
        self.status_lbl = tk.Label(footer, text="", font=make_font(8),
                                    bg=C["surface"], fg=C["text3"])
        self.status_lbl.pack(side="left")
        tk.Label(footer, text="Ctrl+;  otvorit/zatvorit   |   Ctrl+V  vlozit vybrate",
                 font=make_font(8), bg=C["surface"], fg=C["text3"]).pack(side="right")

    def _stat_card(self, parent, value, label):
        frame = tk.Frame(parent, bg=C["surface2"], padx=12, pady=6)
        vl = tk.Label(frame, text=value, font=make_font(14, bold=True),
                       bg=C["surface2"], fg=C["purple"])
        vl.pack()
        tk.Label(frame, text=label, font=make_font(7),
                 bg=C["surface2"], fg=C["text3"]).pack()
        frame._val_lbl = vl
        return frame

    def _update_stats(self, entries):
        total = len(entries)
        texts = sum(1 for e in entries if e["type"] == "text")
        images = sum(1 for e in entries if e["type"] == "image")
        files = sum(1 for e in entries if e["type"] == "file")
        self.stat_count._val_lbl.config(text=str(total))
        self.stat_texts._val_lbl.config(text=str(texts))
        self.stat_images._val_lbl.config(text=str(images))
        self.stat_files._val_lbl.config(text=str(files))

    def _refresh(self):
        search = self.search_var.get()
        for w in self.list_frame.winfo_children():
            w.destroy()
        entries = self.db.get_entries(search=search)
        self._update_stats(entries)
        self._update_banner()
        if not entries:
            ef = tk.Frame(self.list_frame, bg=C["bg"], pady=60)
            ef.pack(fill="x")
            tk.Label(ef, text="CB", font=make_font(32, bold=True),
                     bg=C["bg"], fg=C["purple"]).pack()
            tk.Label(ef, text="Ziadne polozky",
                     font=make_font(13, bold=True), bg=C["bg"], fg=C["text2"]).pack(pady=(8, 4))
            tk.Label(ef, text="Skopiruj nieco a objavi sa tu automaticky",
                     font=make_font(9), bg=C["bg"], fg=C["text3"]).pack()
            return
        for idx, entry in enumerate(entries):
            row = ClipRow(self.list_frame, entry, idx + 1,
                          is_selected=(entry["id"] == self.selected_id),
                          on_select=self._select,
                          on_delete=self._delete_entry,
                          on_pin=self._toggle_pin)
            row.pack(fill="x", pady=1)

    def _update_banner(self):
        if not self.selected_id:
            self.banner_text.config(text="ziadna - klikni na polozku nizsie")
            self.banner_type.config(text="")
            return
        entry = self.db.get_entry(self.selected_id)
        if not entry:
            self.banner_text.config(text="ziadna")
            return
        preview = entry.get("content", "")[:80]
        if entry["type"] == "image":
            preview = f"[Obrazok  {entry.get('meta', '')}]"
        elif entry["type"] == "file":
            preview = entry.get("content", "").split("\n")[0][:80]
        self.banner_text.config(text=preview)
        icon = {"text": "TEXT", "image": "IMG", "file": "FILE"}.get(entry["type"], "")
        self.banner_type.config(text=icon)

    def _select(self, eid):
        self.selected_id = eid
        entry = self.db.get_entry(eid)
        if entry:
            self._push_to_clipboard(entry)
        self._refresh()

    def _push_to_clipboard(self, entry):
        try:
            import pyperclip
            if entry["type"] == "text":
                pyperclip.copy(entry["content"])
            elif entry["type"] == "file":
                pyperclip.copy(entry["content"])
            elif entry["type"] == "image":
                self._push_image(entry)
            self._set_status("Vlozene do schranky")
        except Exception as ex:
            self._set_status(f"Chyba: {ex}")

    def _push_image(self, entry):
        try:
            import win32clipboard
            from PIL import Image
            import io, base64, struct
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

    def _on_clip_text(self, text):
        if not text or not text.strip():
            return
        if self.selected_id:
            entry = self.db.get_entry(self.selected_id)
            if entry and entry["type"] == "text" and entry["content"] == text:
                return
        new_id = self.db.add_entry("text", text)
        if new_id:
            self.selected_id = new_id
            self.root.after(0, self._refresh)

    def _on_clip_image(self, img_b64, meta):
        new_id = self.db.add_entry("image", img_b64, meta=meta)
        if new_id:
            self.selected_id = new_id
            self.root.after(0, self._refresh)

    def _on_clip_file(self, paths):
        content = "\n".join(paths)
        new_id = self.db.add_entry("file", content)
        if new_id:
            self.selected_id = new_id
            self.root.after(0, self._refresh)

    def _delete_selected(self):
        if self.selected_id:
            self.db.delete_entry(self.selected_id)
            self.selected_id = None
            self._refresh()

    def _delete_entry(self, eid):
        self.db.delete_entry(eid)
        if self.selected_id == eid:
            self.selected_id = None
        self._refresh()

    def _toggle_pin(self, eid):
        self.db.toggle_pin(eid)
        self._refresh()

    def _clear_all(self):
        if messagebox.askyesno("Vycistit historiu",
                                "Naozaj vymazat vsetky polozky?",
                                parent=self.root):
            self.db.clear_all()
            self.selected_id = None
            self._refresh()

    def _export(self):
        from tkinter.filedialog import asksaveasfilename
        path = asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Vsetky", "*.*")],
            title="Exportovat historiu"
        )
        if path:
            entries = self.db.get_entries()
            out = [{"type": e["type"], "content": e["content"],
                    "created_at": e.get("created_at", "")}
                   for e in entries if e["type"] == "text"]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
            self._set_status(f"Exportovane: {os.path.basename(path)}")

    def _set_status(self, msg):
        self.status_lbl.config(text=msg)
        self.root.after(3000, lambda: self.status_lbl.config(text=""))

    def _toggle_aot(self):
        self.root.wm_attributes("-topmost", self.always_on_top.get())

    def _toggle_window(self):
        if self.root.state() == "withdrawn":
            self._show_window()
        else:
            self._hide_window()

    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _hide_window(self):
        self.root.withdraw()

    def _setup_tray(self):
        try:
            import pystray
            from PIL import Image, ImageDraw
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.ellipse([4, 4, 60, 60], fill=(124, 106, 247, 255))
            d.rectangle([16, 22, 48, 42], fill=(255, 255, 255, 200))
            d.rectangle([20, 26, 44, 38], fill=(124, 106, 247, 200))
            menu = pystray.Menu(
                pystray.MenuItem("Otvorit Kopirovacku",
                                  lambda i, it: self.root.after(0, self._show_window),
                                  default=True),
                pystray.MenuItem("Ukoncit",
                                  lambda i, it: self.root.after(0, self._quit))
            )
            self.tray = pystray.Icon("kopirovacka", img, "Kopirovacka", menu)
            threading.Thread(target=self.tray.run, daemon=True).start()
        except Exception:
            pass

    def _quit(self):
        self.monitor.stop()
        self.hotkey_mgr.stop()
        try:
            self.tray.stop()
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    lock = acquire_single_instance()
    if lock is None:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            "Kopirovacka uz bezi!\nPozri ikonu v systemovej liste (vpravo dole).",
            "Kopirovacka",
            0x40
        )
        sys.exit(0)

    app = KopirovackaApp()
    app.run()
    lock.close()
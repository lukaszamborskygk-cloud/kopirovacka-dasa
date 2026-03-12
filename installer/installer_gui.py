"""
Kopirovacka Installer
Standalone installer GUI — built with tkinter, no NSIS needed.
Package this with PyInstaller alongside Kopirovacka.exe into one zip.

Build installer exe:
  pyinstaller --onefile --windowed --name=Kopirovacka_Installer installer_gui.py
"""

import tkinter as tk
from tkinter import ttk
import threading
import os
import sys
import shutil
import time
import subprocess
import winreg

APP_NAME = "Kopírovačka"
APP_VERSION = "1.0.0"
INSTALL_DIR = os.path.join(os.environ.get("LOCALAPPDATA", "C:\\Users\\User\\AppData\\Local"), "Kopirovacka")
APP_EXE_NAME = "Kopirovacka.exe"
UNINSTALL_EXE = "Uninstall_Kopirovacka.exe"

COLORS = {
    "bg": "#1e1e2e",
    "bg2": "#2a2a3e",
    "accent": "#7c3aed",
    "accent2": "#6d28d9",
    "green": "#22c55e",
    "text": "#e2e8f0",
    "text_dim": "#94a3b8",
    "border": "#3f3f5a",
    "bar_bg": "#313147",
}


class InstallerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"Inštalácia — {APP_NAME}")
        self.root.geometry("500x400")
        self.root.resizable(False, False)
        self.root.configure(bg=COLORS["bg"])
        self._center()

        self.create_desktop = tk.BooleanVar(value=True)
        self.current_frame = None

        # Find the exe to install (same dir as this script/exe)
        self.source_exe = self._find_source_exe()

        self._show_welcome()

    def _center(self):
        self.root.update_idletasks()
        w, h = 500, 400
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _find_source_exe(self):
        base = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else __file__)
        path = os.path.join(base, APP_EXE_NAME)
        if os.path.exists(path):
            return path
        return None

    def _clear(self):
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = tk.Frame(self.root, bg=COLORS["bg"])
        self.current_frame.pack(fill="both", expand=True)

    # ── Welcome screen ────────────────────────────────────────────────

    def _show_welcome(self):
        self._clear()
        f = self.current_frame

        # Header
        header = tk.Frame(f, bg=COLORS["accent"], height=8)
        header.pack(fill="x")

        # Icon area
        icon_frame = tk.Frame(f, bg=COLORS["bg"], pady=30)
        icon_frame.pack(fill="x")
        tk.Label(icon_frame, text="📋", font=("Segoe UI", 48),
                 bg=COLORS["bg"]).pack()

        # Title
        tk.Label(f, text=f"Inštalácia {APP_NAME}",
                 font=("Segoe UI", 18, "bold"),
                 bg=COLORS["bg"], fg=COLORS["text"]).pack()

        tk.Label(f, text=f"verzia {APP_VERSION}",
                 font=("Segoe UI", 10),
                 bg=COLORS["bg"], fg=COLORS["text_dim"]).pack(pady=(2, 16))

        # Install path info
        info = tk.Frame(f, bg=COLORS["bg2"], padx=20, pady=12)
        info.pack(fill="x", padx=30)
        tk.Label(info, text=f"📁  Inštalačný priečinok:",
                 font=("Segoe UI", 9), bg=COLORS["bg2"],
                 fg=COLORS["text_dim"], anchor="w").pack(fill="x")
        tk.Label(info, text=INSTALL_DIR,
                 font=("Consolas", 9), bg=COLORS["bg2"],
                 fg=COLORS["text"], anchor="w").pack(fill="x")

        # Desktop shortcut checkbox
        chk_frame = tk.Frame(f, bg=COLORS["bg"], padx=30, pady=12)
        chk_frame.pack(fill="x")
        chk = tk.Checkbutton(chk_frame,
                              text="  Vytvoriť skratku na pracovnej ploche",
                              variable=self.create_desktop,
                              bg=COLORS["bg"], fg=COLORS["text"],
                              selectcolor=COLORS["bg2"],
                              activebackground=COLORS["bg"],
                              font=("Segoe UI", 10),
                              bd=0, highlightthickness=0)
        chk.pack(side="left")

        # Bottom bar with Install button
        bottom = tk.Frame(f, bg=COLORS["bg2"], pady=14, padx=20)
        bottom.pack(fill="x", side="bottom")

        if not self.source_exe:
            tk.Label(bottom, text="⚠ Kopirovacka.exe nenájdená vedľa inštalátora!",
                     fg="#ef4444", bg=COLORS["bg2"],
                     font=("Segoe UI", 9)).pack(side="left")

        btn = tk.Label(bottom, text="  Inštalovať  ▶",
                       bg=COLORS["accent"], fg="white",
                       font=("Segoe UI", 11, "bold"),
                       padx=24, pady=8, cursor="hand2")
        btn.pack(side="right")
        btn.bind("<Button-1>", lambda e: self._start_install())
        btn.bind("<Enter>", lambda e: btn.configure(bg=COLORS["accent2"]))
        btn.bind("<Leave>", lambda e: btn.configure(bg=COLORS["accent"]))

    # ── Install screen ────────────────────────────────────────────────

    def _start_install(self):
        self._show_installing()
        thread = threading.Thread(target=self._do_install, daemon=True)
        thread.start()

    def _show_installing(self):
        self._clear()
        f = self.current_frame

        header = tk.Frame(f, bg=COLORS["accent"], height=8)
        header.pack(fill="x")

        tk.Label(f, text="📋", font=("Segoe UI", 36),
                 bg=COLORS["bg"]).pack(pady=(30, 10))

        tk.Label(f, text="Inštalujem aplikáciu...",
                 font=("Segoe UI", 14, "bold"),
                 bg=COLORS["bg"], fg=COLORS["text"]).pack()

        self.step_label = tk.Label(f, text="Pripravujem...",
                                    font=("Segoe UI", 10),
                                    bg=COLORS["bg"], fg=COLORS["text_dim"])
        self.step_label.pack(pady=(8, 20))

        # Progress bar frame
        bar_outer = tk.Frame(f, bg=COLORS["bar_bg"],
                              height=22, width=380)
        bar_outer.pack(padx=60)
        bar_outer.pack_propagate(False)

        self.bar_fill = tk.Frame(bar_outer, bg=COLORS["accent"], height=22, width=0)
        self.bar_fill.place(x=0, y=0, height=22, width=0)

        self.pct_label = tk.Label(f, text="0%",
                                   font=("Segoe UI", 10, "bold"),
                                   bg=COLORS["bg"], fg=COLORS["text"])
        self.pct_label.pack(pady=8)

        self.bar_total_width = 380

    def _set_progress(self, pct, step_text=""):
        fill_w = int(self.bar_total_width * pct / 100)
        self.bar_fill.place(width=fill_w)
        self.pct_label.config(text=f"{pct}%")
        if step_text:
            self.step_label.config(text=step_text)
        self.root.update_idletasks()

    def _do_install(self):
        try:
            self.root.after(0, lambda: self._set_progress(5, "Vytváram inštalačný priečinok..."))
            time.sleep(0.3)
            os.makedirs(INSTALL_DIR, exist_ok=True)

            self.root.after(0, lambda: self._set_progress(20, "Kopírujem aplikáciu..."))
            time.sleep(0.4)

            dest_exe = os.path.join(INSTALL_DIR, APP_EXE_NAME)
            if self.source_exe and os.path.exists(self.source_exe):
                shutil.copy2(self.source_exe, dest_exe)
            else:
                # Fallback: copy current executable
                shutil.copy2(sys.executable, dest_exe)

            self.root.after(0, lambda: self._set_progress(45, "Vytváram odinštalátor..."))
            time.sleep(0.3)
            self._write_uninstaller()

            self.root.after(0, lambda: self._set_progress(60, "Registrujem aplikáciu..."))
            time.sleep(0.3)
            self._write_registry(dest_exe)

            self.root.after(0, lambda: self._set_progress(75, "Vytváram skratky..."))
            time.sleep(0.3)
            self._create_shortcuts(dest_exe)

            self.root.after(0, lambda: self._set_progress(90, "Nastavujem automatické spustenie..."))
            time.sleep(0.3)
            self._set_autostart(dest_exe)

            self.root.after(0, lambda: self._set_progress(100, "Hotovo!"))
            time.sleep(0.5)
            self.root.after(0, self._show_success)

        except Exception as e:
            self.root.after(0, lambda: self._show_error(str(e)))

    def _write_uninstaller(self):
        """Write a simple batch uninstaller."""
        uninstall_path = os.path.join(INSTALL_DIR, UNINSTALL_EXE + ".bat")
        bat = f"""@echo off
echo Odinstalovanie Kopirovacka...
taskkill /f /im {APP_EXE_NAME} 2>nul
timeout /t 1 /nobreak >nul
rmdir /s /q "{INSTALL_DIR}"
del "%DESKTOP%\\Kopirovacka.lnk" 2>nul
reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "Kopirovacka" /f 2>nul
reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Kopirovacka" /f 2>nul
echo Aplikacia bola odinstalovana.
pause
"""
        with open(uninstall_path, "w", encoding="utf-8") as f:
            f.write(bat)

        # Also write a .exe wrapper that just runs the bat (using a .cmd)
        cmd_path = os.path.join(INSTALL_DIR, "Uninstall_Kopirovacka.cmd")
        with open(cmd_path, "w", encoding="utf-8") as f:
            f.write(bat)

    def _write_registry(self, exe_path):
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                    r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Kopirovacka")
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ,
                               os.path.join(INSTALL_DIR, "Uninstall_Kopirovacka.cmd"))
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, INSTALL_DIR)
            winreg.CloseKey(key)
        except Exception:
            pass

    def _create_shortcuts(self, exe_path):
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")

            # Start menu
            start_menu = os.path.join(os.environ.get("APPDATA", ""),
                                       r"Microsoft\Windows\Start Menu\Programs")
            lnk = shell.CreateShortcut(os.path.join(start_menu, f"{APP_NAME}.lnk"))
            lnk.TargetPath = exe_path
            lnk.Save()

            # Desktop
            if self.create_desktop.get():
                desktop = shell.SpecialFolders("Desktop")
                lnk2 = shell.CreateShortcut(os.path.join(desktop, f"{APP_NAME}.lnk"))
                lnk2.TargetPath = exe_path
                lnk2.Save()
        except Exception:
            pass

    def _set_autostart(self, exe_path):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                  r"Software\Microsoft\Windows\CurrentVersion\Run",
                                  0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "Kopirovacka", 0, winreg.REG_SZ, f'"{exe_path}"')
            winreg.CloseKey(key)
        except Exception:
            pass

    # ── Success screen ────────────────────────────────────────────────

    def _show_success(self):
        self._clear()
        f = self.current_frame

        header = tk.Frame(f, bg=COLORS["green"], height=8)
        header.pack(fill="x")

        tk.Label(f, text="✅", font=("Segoe UI", 48),
                 bg=COLORS["bg"]).pack(pady=(30, 10))

        tk.Label(f, text="Aplikácia bola úspešne nainštalovaná!",
                 font=("Segoe UI", 13, "bold"),
                 bg=COLORS["bg"], fg=COLORS["text"]).pack()

        if self.create_desktop.get():
            tk.Label(f, text="Skratka bola vytvorená na pracovnej ploche.",
                     font=("Segoe UI", 10),
                     bg=COLORS["bg"], fg=COLORS["text_dim"]).pack(pady=4)

        tk.Label(f, text=f"📁  {INSTALL_DIR}",
                 font=("Consolas", 9),
                 bg=COLORS["bg"], fg=COLORS["text_dim"]).pack(pady=(8, 20))

        info = tk.Frame(f, bg=COLORS["bg2"], padx=20, pady=12)
        info.pack(fill="x", padx=30)
        tips = [
            "💡  Ctrl+;  =  otvoriť / zatvoriť okno aplikácie",
            "💡  Aplikácia beží na pozadí (system tray)",
            "💡  Odinštalovanie: Nastavenia Windows → Aplikácie",
        ]
        for tip in tips:
            tk.Label(info, text=tip, font=("Segoe UI", 9),
                     bg=COLORS["bg2"], fg=COLORS["text_dim"],
                     anchor="w").pack(fill="x", pady=1)

        bottom = tk.Frame(f, bg=COLORS["bg2"], pady=14, padx=20)
        bottom.pack(fill="x", side="bottom")

        btn = tk.Label(bottom, text="  Dokončiť  ✓",
                       bg=COLORS["green"], fg="white",
                       font=("Segoe UI", 11, "bold"),
                       padx=24, pady=8, cursor="hand2")
        btn.pack(side="right")
        btn.bind("<Button-1>", lambda e: self._finish())

    def _finish(self):
        # Launch the app
        exe = os.path.join(INSTALL_DIR, APP_EXE_NAME)
        if os.path.exists(exe):
            subprocess.Popen([exe])
        self.root.destroy()

    # ── Error screen ─────────────────────────────────────────────────

    def _show_error(self, msg):
        self._clear()
        f = self.current_frame

        header = tk.Frame(f, bg="#ef4444", height=8)
        header.pack(fill="x")

        tk.Label(f, text="❌", font=("Segoe UI", 48),
                 bg=COLORS["bg"]).pack(pady=(30, 10))

        tk.Label(f, text="Inštalácia zlyhala",
                 font=("Segoe UI", 13, "bold"),
                 bg=COLORS["bg"], fg=COLORS["text"]).pack()

        tk.Label(f, text=msg, font=("Segoe UI", 9),
                 bg=COLORS["bg"], fg="#ef4444",
                 wraplength=400).pack(pady=12)

        bottom = tk.Frame(f, bg=COLORS["bg2"], pady=14, padx=20)
        bottom.pack(fill="x", side="bottom")

        btn = tk.Label(bottom, text="  Zavrieť  ",
                       bg="#ef4444", fg="white",
                       font=("Segoe UI", 11, "bold"),
                       padx=24, pady=8, cursor="hand2")
        btn.pack(side="right")
        btn.bind("<Button-1>", lambda e: self.root.destroy())

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = InstallerApp()
    app.run()

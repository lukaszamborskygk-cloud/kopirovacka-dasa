import threading

class HotkeyManager:
    """
    Registers global hotkeys:
      Ctrl+;  → toggle app window
    """

    def __init__(self, toggle_callback=None):
        self.toggle_callback = toggle_callback
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        try:
            import keyboard
            keyboard.unhook_all()
        except Exception:
            pass

    def _run(self):
        try:
            import keyboard
            keyboard.add_hotkey("ctrl+semicolon", self._on_toggle, suppress=False)
            self._stop_event.wait()
        except Exception as e:
            print(f"Hotkey error: {e}")

    def _on_toggle(self):
        if self.toggle_callback:
            self.toggle_callback()

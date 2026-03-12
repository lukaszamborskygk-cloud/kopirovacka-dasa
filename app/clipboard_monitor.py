import threading
import time
import base64
import io

class ClipboardMonitor:
    """Monitors Windows clipboard for changes and fires callbacks."""

    def __init__(self, on_new_text=None, on_new_image=None, on_new_file=None):
        self.on_new_text = on_new_text
        self.on_new_image = on_new_image
        self.on_new_file = on_new_file
        self._stop_event = threading.Event()
        self._thread = None
        self._last_text = None
        self._last_img_hash = None
        self._last_files = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _run(self):
        # Initialize with current clipboard
        self._init_state()
        while not self._stop_event.is_set():
            try:
                self._check()
            except Exception:
                pass
            time.sleep(0.4)

    def _init_state(self):
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                    self._last_text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            pass

    def _check(self):
        import win32clipboard

        win32clipboard.OpenClipboard()
        try:
            # ── Text ─────────────────────────────────────────────────
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                if text and text != self._last_text:
                    self._last_text = text
                    self._last_img_hash = None
                    self._last_files = None
                    if self.on_new_text:
                        threading.Thread(target=self.on_new_text,
                                         args=(text,), daemon=True).start()
                return  # text takes priority

            # ── Files ────────────────────────────────────────────────
            CF_HDROP = 15
            if win32clipboard.IsClipboardFormatAvailable(CF_HDROP):
                files = win32clipboard.GetClipboardData(CF_HDROP)
                if files and list(files) != self._last_files:
                    self._last_files = list(files)
                    self._last_text = None
                    self._last_img_hash = None
                    if self.on_new_file:
                        threading.Thread(target=self.on_new_file,
                                         args=(list(files),), daemon=True).start()
                return

            # ── Image ────────────────────────────────────────────────
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
                data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
                img_hash = hash(data[:256] if len(data) > 256 else data)
                if img_hash != self._last_img_hash:
                    self._last_img_hash = img_hash
                    self._last_text = None
                    self._last_files = None
                    # Convert to base64 PNG
                    if self.on_new_image:
                        threading.Thread(target=self._process_image,
                                         args=(data,), daemon=True).start()

        finally:
            win32clipboard.CloseClipboard()

    def _process_image(self, dib_data):
        try:
            from PIL import Image
            import struct

            # DIB to BMP: prepend 14-byte BMP file header
            size = len(dib_data) + 14
            bmp_header = struct.pack("<2sIHHI", b"BM", size, 0, 0, 14 + 40)
            bmp_data = bmp_header + dib_data

            img = Image.open(io.BytesIO(bmp_data))
            w, h = img.size
            meta = f"{w}×{h}px"

            out = io.BytesIO()
            img.save(out, format="PNG")
            b64 = base64.b64encode(out.getvalue()).decode()

            if self.on_new_image:
                self.on_new_image(b64, meta)
        except Exception:
            pass

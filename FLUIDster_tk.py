import tkinter as tk
from tkinter import ttk
from whisper_x.transcriber import Transcriber
from whisper_x.audio_recorder import AudioRecorder
import threading
import keyboard
import platform

if platform.system() == "Windows":
    import winsound

def play_beep(): platform.system() == "Windows" and winsound.Beep(1000, 150) # wenn windows, dann piep

class FLUIDster:
    def __init__(self, root):
        self.root = root
        self.root.title("FLUIDster GUI")

        self.transcriber = Transcriber()
        self.recorder = AudioRecorder()
        self.auto_stop = tk.BooleanVar(value=True)
        self.current_model = tk.StringVar(value="base")

        self._build_interface()
        self._update_gpu_status()

    def _build_interface(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)

        # Modell-Auswahl
        ttk.Label(frame, text="Whisper-Modell:").grid(row=0, column=0, sticky="w")
        model_menu = ttk.OptionMenu(
            frame, self.current_model, self.current_model.get(),
            "tiny", "base", "small", "medium", "large",
            command=self._on_model_change
        )
        model_menu.grid(row=0, column=1, sticky="ew")

        # Hotkey definieren (STRG+UMSCHALT+C)
        keyboard.add_hotkey('ctrl+shift+c', lambda: self._start_recording_thread())

        # Auto-Stopp Checkbox
        chk = ttk.Checkbutton(frame, text="automatisch stoppen (Stille)", variable=self.auto_stop)
        chk.grid(row=1, column=0, columnspan=2, sticky="w")

        # Aufnahme-Button
        self.record_btn = ttk.Button(frame, text="🎤 Aufnahme starten", command=self._start_recording_thread)
        self.record_btn.grid(row=2, column=0, pady=5)

        # Stopp-Button
        self.stop_btn = ttk.Button(frame, text="🛑 Aufnahme stoppen", command=self._stop_recording)
        self.stop_btn.grid(row=2, column=1, pady=5)

        # Statusfeld
        self.status_label = ttk.Label(frame, text="Bereit", foreground="blue")
        self.status_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))

        # GPU-Nutzung
        self.gpu_label = ttk.Label(frame, text="GPU: ⏳ wird geladen...", foreground="gray")
        self.gpu_label.grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self._create_tooltip(self.gpu_label, self.transcriber.get_gpu_usage_text)

        # Ausgabe Textfeld
        self.output_box = tk.Text(frame, height=10, wrap="word")
        self.output_box.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(10, 0))

    def _on_model_change(self, name):
        self.status_label.config(text=f"📦 Lade Modell: {name}...")
        self.root.update()
        self.transcriber.change_model(name)
        self.status_label.config(text=f"✅ Modell '{name}' geladen")

    def _start_recording_thread(self):
        threading.Thread(target=self._record_and_transcribe, daemon=True).start()

    def _record_and_transcribe(self):
        self.status_label.config(text="🎙️ Aufnahme läuft...")
        try:
            if self.auto_stop.get():
                path = self.recorder.record_until_silence()
            else:
                path = self.recorder.record_fixed_duration(10)
            self.status_label.config(text="🧠 Transkribiere...")
            text = self.transcriber.transcribe(path)
            self.status_label.config(text="✔ Transkribiert: " + text[:40] + "...")
            self.output_box.delete("1.0", tk.END)
            self.output_box.insert(tk.END, text)
        except Exception as e:
            self.status_label.config(text=f"❌ Fehler: {str(e)}")

    def _stop_recording(self):
        self.recorder.stop()
        self.status_label.config(text="🛑 Aufnahme wird gestoppt...")

    def _update_gpu_status(self):
        text = self.transcriber.get_gpu_usage_text()
        self.gpu_label.config(text="GPU: " + text.replace("\n", " | "))
        self.root.after(3000, self._update_gpu_status)

    def _create_tooltip(self, widget, text_func):
        def show(event=None):
            text = text_func()
            if not text:
                return
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + 20
            self.tooltip = tw = tk.Toplevel(widget)
            tw.wm_overrideredirect(True)
            tw.geometry(f"+{x}+{y}")
            label = tk.Label(tw, text=text, justify='left', background="#ffffe0", relief='solid', borderwidth=1)
            label.pack()
        def hide(event=None):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
                self.tooltip = None
        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)

if __name__ == "__main__":
    root = tk.Tk()
    app = FLUIDster(root)
    root.mainloop()

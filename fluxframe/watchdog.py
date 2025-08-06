import os
from pathlib import Path
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from fluxframe import storage

class ChangeHandler(FileSystemEventHandler):
    def __init__(self, signal):
        super().__init__()
        self.signal = signal

    def process(self, event_type, src_path, dest_path=None):
        # Ordnerstruktur nicht ändern
        p = Path(dest_path or src_path)
        if p.is_dir():
            return

        if event_type == 'deleted':
            storage.delete_entry(src_path)
            self.signal.emit(f"Entfernt: {src_path}")
        else:
            entry = storage.make_entry(dest_path or src_path)
            storage.upsert_entry(entry)
            self.signal.emit(f"{event_type.capitalize()}: {p}")

    def on_created(self, event):
        self.process('created', event.src_path)

    def on_modified(self, event):
        self.process('modified', event.src_path)

    def on_moved(self, event):
        # Lösche altes und füge neues hinzu
        self.process('deleted', event.src_path)
        self.process('created', None, event.dest_path)

    def on_deleted(self, event):
        self.process('deleted', event.src_path)

class SyncFolderWatcher(QThread):
    update_signal = pyqtSignal(str)

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = Path(folder_path)
        self.observer = Observer()

    def run(self):
        # Initialer Voll-Scan
        entries = []
        for root, dirs, files in os.walk(self.folder_path):
            for name in dirs + files:
                full = Path(root) / name
                entries.append(storage.make_entry(full))
        storage.replace_entries(entries)
        # Korrigierter Signal-Emit-Aufruf
        self.update_signal.emit(f"Initialer Scan abgeschlossen: {self.folder_path}")

        # Dann inkrementelle Überwachung
        handler = ChangeHandler(self.update_signal)
        self.observer.schedule(handler, str(self.folder_path), recursive=True)
        self.observer.start()
        try:
            self.observer.join()
        finally:
            self.observer.stop()
            self.observer.join()

    def stop(self):
        self.observer.stop()
        self.observer.join()
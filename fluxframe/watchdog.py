from PyQt5 import QtCore
import os
import time
import json

class SyncFolderWatcher(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    finished_signal = QtCore.pyqtSignal()

    def __init__(self, sync_path, interval_getter):
        super().__init__()
        self.sync_path = sync_path
        self.interval_getter = interval_getter
        self._stop = False

    def run(self):
        try:
            while not self._stop:
                if not os.path.exists(self.sync_path):
                    self.log_signal.emit(f"[ERROR] Ordner nicht gefunden: {self.sync_path}")
                    time.sleep(2)
                    continue

                entries = []
                entries_json = []
                for root, dirs, files in os.walk(self.sync_path):
                    rel = os.path.relpath(root, self.sync_path)
                    for d in dirs:
                        p = os.path.join(rel, d) if rel != '.' else d
                        entries.append(f"[DIR]  {p}")
                        entries_json.append({"type": "dir", "path": p})
                    for f in files:
                        p = os.path.join(rel, f) if rel != '.' else f
                        entries.append(f"[FILE] {p}")
                        entries_json.append({"type": "file", "path": p})
                self.log_signal.emit(f"Indexierung abgeschlossen ({len(entries_json)} Einträge).")
                self.save_index(entries, entries_json)

                try:
                    wait = int(self.interval_getter())
                except Exception:
                    wait = 10
                for _ in range(wait * 10):
                    if self._stop:
                        break
                    time.sleep(0.1)
        except Exception as e:
            import traceback
            self.log_signal.emit(f"[EXCEPTION]: {traceback.format_exc()}")
        self.finished_signal.emit()

    def stop(self):
        self._stop = True

    def save_index(self, entries, entries_json):
        tmp_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../TMP"))
        os.makedirs(tmp_path, exist_ok=True)
        md_file = os.path.join(tmp_path, "sync-index.md")
        json_file = os.path.join(tmp_path, "sync-index.json")

        try:
            # Markdown
            with open(md_file, "w", encoding="utf-8") as f:
                f.write("# Sync-Ordner Index\n\n")
                for line in entries:
                    if line.startswith("[DIR]"):
                        f.write(f"## {line[6:]}\n")
                    else:
                        f.write(f"- {line[7:]}\n")
            # JSON
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(entries_json, f, indent=2, ensure_ascii=False)
            self.log_signal.emit(f"Index gespeichert: {md_file}, {json_file}")
        except Exception as e:
            import traceback
            self.log_signal.emit(f"[Fehler beim Speichern]: {traceback.format_exc()}")

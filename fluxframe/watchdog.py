from PyQt5 import QtCore
import os
import time
from . import storage

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
                # Logging zur Kontrolle
                self.log_signal.emit(f"[INFO] Starte Indexierung von: {self.sync_path}")

                if not os.path.exists(self.sync_path):
                    self.log_signal.emit(f"[ERROR] Ordner nicht gefunden: {self.sync_path}")
                    time.sleep(2)
                    continue

                entries = []
                num_dirs, num_files = 0, 0

                for root, dirs, files in os.walk(self.sync_path):
                    rel = os.path.relpath(root, self.sync_path)
                    for d in dirs:
                        p = os.path.join(rel, d) if rel != '.' else d
                        full_path = os.path.join(root, d)
                        try:
                            st = os.stat(full_path)
                        except Exception as e:
                            self.log_signal.emit(f"[WARN] Zugriff auf {full_path} fehlgeschlagen: {e}")
                            continue
                        entries.append(storage.make_entry(
                            path=p,
                            name=d,
                            typ="dir",
                            size=None,
                            mtime=st.st_mtime,
                            ctime=st.st_ctime,
                            extension=""
                        ))
                        num_dirs += 1
                    for f in files:
                        p = os.path.join(rel, f) if rel != '.' else f
                        full_path = os.path.join(root, f)
                        try:
                            st = os.stat(full_path)
                        except Exception as e:
                            self.log_signal.emit(f"[WARN] Zugriff auf {full_path} fehlgeschlagen: {e}")
                            continue
                        ext = os.path.splitext(f)[1][1:]  # ohne Punkt
                        entries.append(storage.make_entry(
                            path=p,
                            name=f,
                            typ="file",
                            size=st.st_size,
                            mtime=st.st_mtime,
                            ctime=st.st_ctime,
                            extension=ext
                        ))
                        num_files += 1

                self.log_signal.emit(f"Indexierung abgeschlossen ({num_dirs} Ordner, {num_files} Dateien, {len(entries)} Einträge).")
                
                # Kontext-Info für spätere Auswertung
                context = {
                    "modul": "watchdog",
                    "ordner": self.sync_path,
                    "index_time": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                try:
                    storage.store_index_entries(entries, context)
                    self.log_signal.emit(f"Einträge in zentrale DB gespeichert. (Letzter Indexlauf: {context['index_time']})")
                except Exception as e:
                    import traceback
                    self.log_signal.emit(f"[DB-ERROR]: {traceback.format_exc()}")

                # Pause/Schlafphase nach Indexlauf
                try:
                    wait = int(self.interval_getter())
                except Exception:
                    wait = 10
                for _ in range(wait * 10):
                    if self._stop:
                        break
                    time.sleep(0.1)
        except Exception:
            import traceback
            self.log_signal.emit(f"[EXCEPTION]: {traceback.format_exc()}")
        self.finished_signal.emit()

    def stop(self):
        self._stop = True

import os
import threading
import json

_watchdog_thread = None
_watchdog_stop = threading.Event()

# ANPASSEN: Pfad zu deinem Sync-Ordner!
SYNC_PATH = r"C:\Users\deinName\Documents\Sync"

# TMP-Ordner für Indexdateien
TMP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../TMP"))
os.makedirs(TMP_PATH, exist_ok=True)
INDEX_MD_FILE = os.path.join(TMP_PATH, "sync-index.md")
INDEX_JSON_FILE = os.path.join(TMP_PATH, "sync-index.json")

def start_sync_watchdog(log_func, interval_getter):
    global _watchdog_thread
    if _watchdog_thread and _watchdog_thread.is_alive():
        log_func("Sync-Watchdog läuft bereits.")
        return
    _watchdog_stop.clear()
    _watchdog_thread = threading.Thread(
        target=_watch_sync_folder,
        args=(log_func, interval_getter),
        daemon=True
    )
    _watchdog_thread.start()

def stop_sync_watchdog(log_func):
    _watchdog_stop.set()
    log_func("Sync-Watchdog gestoppt.")

def _watch_sync_folder(log_func, interval_getter):
    while not _watchdog_stop.is_set():
        index = []
        index_json = []
        for root, dirs, files in os.walk(SYNC_PATH):
            rel_root = os.path.relpath(root, SYNC_PATH)
            # Ordner
            for d in dirs:
                path = os.path.join(root, d)
                rel_path = os.path.join(rel_root, d) if rel_root != '.' else d
                index.append(f"[DIR]  {rel_path}")
                index_json.append({"type": "dir", "path": rel_path})
            # Dateien
            for f in files:
                path = os.path.join(root, f)
                rel_path = os.path.join(rel_root, f) if rel_root != '.' else f
                index.append(f"[FILE] {rel_path}")
                index_json.append({"type": "file", "path": rel_path})
        log_func(f"Indizierung abgeschlossen ({len(index_json)} Einträge).")
        _save_sync_index(index, index_json, log_func)

        # Intervall jeweils neu auslesen (User kann ändern)
        try:
            wait_time = int(interval_getter())
        except:
            wait_time = 10
        for _ in range(wait_time * 10):
            if _watchdog_stop.is_set():
                break
            threading.Event().wait(0.1)

def _save_sync_index(index, index_json, log_func):
    try:
        # Markdown export
        with open(INDEX_MD_FILE, "w", encoding="utf-8") as f:
            f.write("# Sync-Ordner Index\n\n")
            for line in index:
                if line.startswith("[DIR]"):
                    f.write(f"## {line[6:]}\n")
                elif line.startswith("[FILE]"):
                    f.write(f"- {line[7:]}\n")
        # JSON export
        with open(INDEX_JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(index_json, f, indent=2, ensure_ascii=False)
        log_func(f"Index gespeichert: {INDEX_MD_FILE}, {INDEX_JSON_FILE}")
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        log_func(f"Watchdog Fehler:\n{tb}")

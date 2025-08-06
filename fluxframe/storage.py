import os
import sqlite3
import threading
import time
import json

# Standardpfad: TMP/sync-index.db (automatisch angelegt)
_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../TMP/sync-index.db"))
_DB_LOCK = threading.Lock()

def init_db(db_path=None):
    """Initialisiert die zentrale SQLite-Datenbank für den Index."""
    global _DB_PATH
    if db_path:
        _DB_PATH = db_path
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    with _DB_LOCK, sqlite3.connect(_DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            context TEXT,         -- Freie Kontextinfos als JSON-String (z.B. welcher Job/Modul etc.)
            path TEXT NOT NULL,   -- Relativer Pfad
            name TEXT NOT NULL,   -- Name der Datei/des Ordners
            type TEXT NOT NULL,   -- 'file' oder 'dir'
            size INTEGER,         -- Dateigröße (Bytes), Ordner: None
            mtime REAL,           -- Änderungszeitpunkt (Unix-Timestamp)
            ctime REAL,           -- Erstellzeitpunkt (Unix-Timestamp)
            extension TEXT,       -- Dateiendung ohne Punkt, Ordner: ""
            indexed_at REAL       -- Zeitstempel des Indexlaufs (Unix-Timestamp)
        )
        """)
        conn.commit()

def store_index_entries(entries, context=None):
    """
    Speichert eine Liste von Datei-/Ordner-Einträgen zusammen mit Kontextinfos.
    - entries: Liste von Dicts mit Feldern wie in make_entry()
    - context: beliebiges Dict, wird als JSON gespeichert (z.B. Aufrufer, Parameter)
    """
    if not entries:
        return
    context_str = json.dumps(context, ensure_ascii=False) if context else None
    now = time.time()
    with _DB_LOCK, sqlite3.connect(_DB_PATH) as conn:
        c = conn.cursor()
        for e in entries:
            c.execute("""
                INSERT INTO files (
                    context, path, name, type, size, mtime, ctime, extension, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                context_str,
                e.get("path"),
                e.get("name"),
                e.get("type"),
                e.get("size"),
                e.get("mtime"),
                e.get("ctime"),
                e.get("extension"),
                now
            ))
        conn.commit()

def get_entries(filters=None, limit=5000, order_by="indexed_at DESC"):
    """
    Holt Einträge als Liste von Dicts.
    - filters: Dict, z.B. {"type": "file", "extension": "txt"}
    - limit: max. Anzahl Ergebnisse (default: 5000)
    - order_by: Sortierung (default: letzter Indexlauf zuerst)
    """
    with _DB_LOCK, sqlite3.connect(_DB_PATH) as conn:
        c = conn.cursor()
        query = "SELECT id, context, path, name, type, size, mtime, ctime, extension, indexed_at FROM files"
        params = []
        if filters:
            cond = []
            for k, v in filters.items():
                cond.append(f"{k}=?")
                params.append(v)
            if cond:
                query += " WHERE " + " AND ".join(cond)
        if order_by:
            query += " ORDER BY " + order_by
        if limit:
            query += f" LIMIT {limit}"
        c.execute(query, params)
        cols = [desc[0] for desc in c.description]
        results = []
        for row in c.fetchall():
            d = dict(zip(cols, row))
            if d["context"]:
                try:
                    d["context"] = json.loads(d["context"])
                except Exception:
                    pass
            results.append(d)
        return results

def make_entry(path, name, typ, size=None, mtime=None, ctime=None, extension=""):
    """
    Hilfsfunktion: Baut einen Eintrag für store_index_entries.
    """
    return {
        "path": path,
        "name": name,
        "type": typ,
        "size": size,
        "mtime": mtime,
        "ctime": ctime,
        "extension": extension or "",
    }

def clear_all_entries():
    """Alle gespeicherten Einträge löschen (Vorsicht!)."""
    with _DB_LOCK, sqlite3.connect(_DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM files")
        conn.commit()

# Beim Import direkt initialisieren (wenn gewünscht)
init_db()

import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime

# DB-Pfad konfigurierbar via Umgebungsvariable
DB_PATH = Path(os.getenv('FLUX_DB_PATH', default='TMP/sync-index.db'))
JSON_PATH = DB_PATH.with_name('latest_index.json')
MD_PATH = DB_PATH.with_name('latest_index.md')

# Hilfsfunktion zur Initialisierung der DB
def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        '''
        CREATE TABLE IF NOT EXISTS files (
            path TEXT,
            name TEXT,
            type TEXT,
            size INTEGER,
            mtime REAL,
            ctime REAL,
            extension TEXT,
            indexed_at REAL,
            PRIMARY KEY(path, name)
        )
        '''
    )
    conn.commit()
    conn.close()

# Erzeuge Entry-Dict für Datei oder Verzeichnis
def make_entry(file_path, context=None):
    st = os.stat(file_path)
    return {
        'path': str(Path(file_path).parent),
        'name': Path(file_path).name,
        'type': 'directory' if Path(file_path).is_dir() else 'file',
        'size': st.st_size,
        'mtime': st.st_mtime,
        'ctime': st.st_ctime,
        'extension': Path(file_path).suffix,
        'indexed_at': datetime.now().timestamp(),
    }

# Erstelle/Ersetze kompletten Index
def replace_entries(entries):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Alle bisherigen Einträge löschen
    c.execute('DELETE FROM files')
    # Batch-Insert
    data = [(e['path'], e['name'], e['type'], e['size'], e['mtime'], e['ctime'], e['extension'], e['indexed_at'])
            for e in entries]
    c.executemany(
        '''
        INSERT INTO files (path, name, type, size, mtime, ctime, extension, indexed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        data
    )
    conn.commit()
    conn.close()
    _export_outputs()

# Füge Entry hinzu oder aktualisiere es
def upsert_entry(entry):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        '''
        INSERT INTO files (path, name, type, size, mtime, ctime, extension, indexed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path, name) DO UPDATE SET
            type=excluded.type,
            size=excluded.size,
            mtime=excluded.mtime,
            ctime=excluded.ctime,
            extension=excluded.extension,
            indexed_at=excluded.indexed_at
        ''',
        (entry['path'], entry['name'], entry['type'], entry['size'], entry['mtime'], entry['ctime'], entry['extension'], entry['indexed_at'])
    )
    conn.commit()
    conn.close()
    _export_outputs()

# Entferne Entry
def delete_entry(file_path):
    p = Path(file_path)
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM files WHERE path = ? AND name = ?', (str(p.parent), p.name))
    conn.commit()
    conn.close()
    _export_outputs()

# Lese alle Einträge
def get_entries():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT path, name, type, size, mtime, ctime, extension, indexed_at FROM files')
    rows = c.fetchall()
    conn.close()
    # In dict-Form
    entries = []
    for r in rows:
        entries.append({
            'path': r[0], 'name': r[1], 'type': r[2],
            'size': r[3], 'mtime': r[4], 'ctime': r[5],
            'extension': r[6], 'indexed_at': r[7]
        })
    return entries

# Exportiere JSON und Markdown der aktuellen Einträge
def _export_outputs():
    entries = get_entries()
    # JSON
    with open(JSON_PATH, 'w', encoding='utf-8') as jf:
        json.dump(entries, jf, ensure_ascii=False, indent=2)
    # Markdown
    lines = [
        '| Path | Name | Type | Size | Modified | Created | Extension |',
        '|---|---|---|---|---|---|---|'
    ]
    for e in entries:
        lines.append(
            f"| {e['path']} | {e['name']} | {e['type']} | {e['size']} |"
            f" {datetime.fromtimestamp(e['mtime']).isoformat()} | {datetime.fromtimestamp(e['ctime']).isoformat()} | {e['extension']} |"
        )
    with open(MD_PATH, 'w', encoding='utf-8') as mf:
        mf.write('\n'.join(lines))
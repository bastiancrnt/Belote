"""Connexion DB.
- DB active : ~/belote.db  (filesystem session, SQLite fonctionne)
- Sync vers  : ~/mnt/Belote/belote.db  (mount, lecture seule pour SQLite mais cp fonctionne)
"""
import sqlite3, os, shutil

_HOME    = os.path.expanduser("~")
DB_PATH  = os.path.join(_HOME, "belote.db")
_MOUNT   = os.path.join(_HOME, "mnt", "Belote", "belote.db")
_SCHEMA  = os.path.join(os.path.dirname(__file__), "schema.sql")


def _restore_from_mount():
    """Si la DB session n'existe pas mais qu'une copie existe sur le mount, la restaurer."""
    if not os.path.exists(DB_PATH) and os.path.exists(_MOUNT):
        try:
            shutil.copy2(_MOUNT, DB_PATH)
            print(f"  [DB] Restaurée depuis {_MOUNT}")
        except Exception as e:
            print(f"  [DB] Impossible de restaurer depuis le mount : {e}")


def sync_to_mount():
    """Copier la DB vers le dossier projet (persistance entre sessions)."""
    if os.path.exists(DB_PATH):
        try:
            shutil.copy2(DB_PATH, _MOUNT)
        except Exception as e:
            print(f"  [DB] Sync mount échoué : {e}")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


_MIGRATIONS = [
    # Colonnes ajoutées après la v1 initiale — ignorées si elles existent déjà
    "ALTER TABLE deals   ADD COLUMN bot_version TEXT",
    "ALTER TABLE actions ADD COLUMN bot_version TEXT",
]


def init_db():
    _restore_from_mount()
    conn = get_connection()
    with open(_SCHEMA) as f:
        sql = f.read()
    for stmt in sql.split(";"):
        stmt = stmt.strip()
        if stmt and not stmt.upper().startswith("PRAGMA"):
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError:
                pass
    # Migrations incrémentales (idempotentes)
    for mig in _MIGRATIONS:
        try:
            conn.execute(mig)
        except sqlite3.OperationalError:
            pass  # colonne déjà présente
    conn.commit()
    return conn

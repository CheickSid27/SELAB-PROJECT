import sqlite3
from contextlib import contextmanager

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS actors (
    phone TEXT PRIMARY KEY,
    role TEXT NOT NULL CHECK (role IN ('eleveur','acheteur','transporteur')),
    name TEXT,
    localite TEXT,
    verification TEXT NOT NULL DEFAULT 'declare'
        CHECK (verification IN ('declare','verifie','certifie')),
    consent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS demands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_phone TEXT NOT NULL REFERENCES actors(phone),
    produit TEXT NOT NULL,
    quantite INTEGER NOT NULL,
    date_livraison TEXT NOT NULL,
    localite TEXT NOT NULL,
    prix_max_fcfa INTEGER,
    statut TEXT NOT NULL DEFAULT 'ouverte',
    simule INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    farmer_phone TEXT NOT NULL REFERENCES actors(phone),
    produit TEXT NOT NULL,
    quantite INTEGER NOT NULL,
    date_disponible TEXT NOT NULL,
    localite TEXT NOT NULL,
    prix_fcfa INTEGER,
    statut TEXT NOT NULL DEFAULT 'ouverte',
    simule INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sessions (
    phone TEXT PRIMARY KEY,
    state_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('in','out')),
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection):
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise

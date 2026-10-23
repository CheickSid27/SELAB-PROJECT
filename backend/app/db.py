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
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produit TEXT NOT NULL,
    localite TEXT NOT NULL,
    date_livraison TEXT NOT NULL,
    quantite INTEGER NOT NULL,
    prix_rendu_livre_fcfa REAL,
    statut TEXT NOT NULL DEFAULT 'en_attente'
        CHECK (statut IN ('en_attente','confirmee','annulee')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS order_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    offer_id INTEGER NOT NULL REFERENCES offers(id),
    farmer_phone TEXT NOT NULL,
    quantite INTEGER NOT NULL,
    prix_fcfa INTEGER,
    distance_km REAL,
    accord INTEGER  -- NULL = pas de réponse, 1 = oui, 0 = non
);
CREATE TABLE IF NOT EXISTS order_buyers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    demand_id INTEGER NOT NULL REFERENCES demands(id),
    buyer_phone TEXT NOT NULL,
    quantite INTEGER NOT NULL,
    accord INTEGER
);
CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT NOT NULL,
    body TEXT NOT NULL,
    delivered INTEGER NOT NULL DEFAULT 0,
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

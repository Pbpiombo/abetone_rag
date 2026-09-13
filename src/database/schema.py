"""Creazione e popolamento del database dei dati numerici."""

import csv
import sqlite3
from pathlib import Path

from src.config import PROCESSED_DIR, SQLITE_PATH

DDL = """
CREATE TABLE IF NOT EXISTS popolazione (
    anno                INTEGER PRIMARY KEY,
    residenti           INTEGER NOT NULL,
    fonte               TEXT NOT NULL,
    data_rilevazione    TEXT
);

CREATE TABLE IF NOT EXISTS bilancio (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    anno        INTEGER NOT NULL,
    tipo        TEXT NOT NULL CHECK (tipo IN ('entrata', 'spesa')),
    voce        TEXT NOT NULL,
    importo     REAL NOT NULL,
    fonte       TEXT NOT NULL,
    UNIQUE (anno, tipo, voce)
);

CREATE TABLE IF NOT EXISTS turismo (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    anno        INTEGER NOT NULL,
    mese        INTEGER CHECK (mese BETWEEN 1 AND 12),
    arrivi      INTEGER,
    presenze    INTEGER,
    fonte       TEXT NOT NULL,
    UNIQUE (anno, mese)
);

CREATE TABLE IF NOT EXISTS territorio (
    chiave      TEXT PRIMARY KEY,
    valore      REAL NOT NULL,
    unita       TEXT,
    fonte       TEXT NOT NULL
);
"""

TABELLE_DA_CSV = {
    "popolazione": ["anno", "residenti", "fonte", "data_rilevazione"],
    "bilancio": ["anno", "tipo", "voce", "importo", "fonte"],
    "turismo": ["anno", "mese", "arrivi", "presenze", "fonte"],
    "territorio": ["chiave", "valore", "unita", "fonte"],
}


def connetti() -> sqlite3.Connection:
    """Apre la connessione, creando la cartella se serve."""
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def crea_schema(conn: sqlite3.Connection) -> None:
    """Crea le tabelle se non esistono."""
    conn.executescript(DDL)
    conn.commit()
    print(f"  Schema creato in {SQLITE_PATH}")


def carica_csv(conn: sqlite3.Connection, tabella: str, colonne: list[str]) -> int:
    """Carica un CSV da data/processed, se presente."""
    percorso = PROCESSED_DIR / f"{tabella}.csv"

    if not percorso.exists():
        print(f"  [saltato] {percorso.name} non presente")
        return 0

    segnaposto = ", ".join("?" for _ in colonne)
    elenco = ", ".join(colonne)
    sql = f"INSERT OR REPLACE INTO {tabella} ({elenco}) VALUES ({segnaposto})"

    inserite = 0
    scartate = 0

    with percorso.open(encoding="utf-8-sig", newline="") as f:
        for numero, riga in enumerate(csv.DictReader(f), start=2):
            valori = [riga.get(c) or None for c in colonne]

            try:
                conn.execute(sql, valori)
                inserite += 1
            except sqlite3.IntegrityError as errore:
                scartate += 1
                print(f"    riga {numero} scartata: {errore}")

    conn.commit()

    messaggio = f"  {tabella}: {inserite} righe caricate"
    if scartate:
        messaggio += f", {scartate} scartate"
    print(messaggio + f" da {percorso.name}")

    return inserite


def riepilogo(conn: sqlite3.Connection) -> None:
    """Stampa quante righe contiene ogni tabella."""
    print("\n  Contenuto del database:")
    for tabella in TABELLE_DA_CSV:
        quante = conn.execute(f"SELECT COUNT(*) FROM {tabella}").fetchone()[0]
        print(f"    {tabella:14} {quante} righe")
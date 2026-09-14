"""Scrittura di un bando estratto nel database."""

from datetime import date

from src.database.schema import connetti

COLONNE = [
    "id", "titolo", "ente", "tema", "programma",
    "apertura", "scadenza", "scadenza_nota", "a_sportello",
    "ammette_comuni", "beneficiari", "territorio", "premialita",
    "costo_min", "costo_max", "contributo_perc",
    "contributo_min", "contributo_max", "dotazione",
    "url", "riferimento_atto", "fonte", "verificato_il",
]


def esiste(id_bando: str) -> dict | None:
    """Restituisce la riga esistente per quell'identificativo, se c'e'."""
    conn = connetti()
    try:
        riga = conn.execute(
            "SELECT * FROM bandi WHERE id = ?", (id_bando,)
        ).fetchone()
        return dict(riga) if riga else None
    finally:
        conn.close()


def salva(riga: dict, url: str, fonte: str) -> None:
    """Scrive o aggiorna la riga del bando nel database."""
    riga = dict(riga)
    riga["url"] = url
    riga["fonte"] = fonte
    riga["verificato_il"] = date.today().isoformat()

    valori = [riga.get(c) for c in COLONNE]
    segnaposto = ", ".join("?" for _ in COLONNE)
    elenco = ", ".join(COLONNE)

    conn = connetti()
    try:
        conn.execute(
            f"INSERT OR REPLACE INTO bandi ({elenco}) VALUES ({segnaposto})",
            valori,
        )
        conn.commit()
    finally:
        conn.close()
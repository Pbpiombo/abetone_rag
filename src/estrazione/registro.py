"""Registro delle pagine gia' esaminate durante le scansioni."""

from datetime import date

from src.database.schema import connetti

# Motivi di scarto definitivi: non ha senso riesaminarli
DEFINITIVI = ("scaduto", "non ammette i Comuni")


def registra(slug: str, esito: str, motivo: str = "") -> None:
    """Annota l'esito dell'esame di una pagina."""
    conn = connetti()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO scansioni "
            "(slug, esito, motivo, esaminato_il) VALUES (?, ?, ?, ?)",
            (slug, esito, motivo, date.today().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def da_non_riesaminare() -> set[str]:
    """Gli slug gia' esaminati con esito definitivo.

    Uno scaduto o non pertinente non cambia: riesaminarlo costa una
    chiamata e produce lo stesso risultato. Gli scarti per incertezza
    (scadenza non determinata, bassa confidenza) restano invece
    candidati, perche' la pagina o il prompt possono essere migliorati.
    """
    conn = connetti()
    try:
        righe = conn.execute(
            "SELECT slug, motivo FROM scansioni WHERE esito = 'scartato'"
        ).fetchall()
    finally:
        conn.close()

    return {
        r["slug"] for r in righe
        if any(r["motivo"].startswith(d) for d in DEFINITIVI)
    }


def riepilogo() -> str:
    """Quante pagine sono state esaminate e con quale esito."""
    conn = connetti()
    try:
        righe = conn.execute(
            "SELECT esito, COUNT(*) AS quante FROM scansioni GROUP BY esito"
        ).fetchall()
        ultima = conn.execute(
            "SELECT MAX(esaminato_il) FROM scansioni"
        ).fetchone()[0]
    finally:
        conn.close()

    if not righe:
        return "Nessuna scansione registrata."

    parti = [f"{r['esito']}: {r['quante']}" for r in righe]
    return f"Ultima scansione {ultima} | " + ", ".join(parti)
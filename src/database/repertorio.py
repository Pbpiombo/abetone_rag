"""Repertorio chiuso di interrogazioni sui dati numerici.

Il modello non scrive SQL: sceglie un'interrogazione di questo elenco
e ne fornisce i parametri. Le query sono scritte e verificate a mano.
"""

import sqlite3
from dataclasses import dataclass, field
from typing import Callable

from src.database.schema import connetti


@dataclass
class Risultato:
    """L'esito di un'interrogazione, pronto per essere dato al modello."""
    testo: str
    fonti: list[str] = field(default_factory=list)
    trovato: bool = True


def _fonti_distinte(righe) -> list[str]:
    """Le fonti citate nelle righe, senza ripetizioni, in ordine."""
    viste = []
    for riga in righe:
        fonte = riga["fonte"]
        if fonte not in viste:
            viste.append(fonte)
    return viste


# --------------------------------------------------------------------------
# Le interrogazioni
# --------------------------------------------------------------------------

def popolazione_anno(conn: sqlite3.Connection, anno: int) -> Risultato:
    """Residenti in un anno specifico."""
    riga = conn.execute(
        "SELECT * FROM popolazione WHERE anno = ?", (anno,)
    ).fetchone()

    if riga is None:
        disponibili = conn.execute(
            "SELECT MIN(anno), MAX(anno) FROM popolazione"
        ).fetchone()
        return Risultato(
            f"Nessun dato di popolazione per l'anno {anno}. "
            f"Anni disponibili: da {disponibili[0]} a {disponibili[1]}.",
            trovato=False,
        )

    return Risultato(
        f"Popolazione residente al 1 gennaio {riga['anno']}: "
        f"{riga['residenti']} abitanti.",
        fonti=[riga["fonte"]],
    )


def popolazione_ultima(conn: sqlite3.Connection) -> Risultato:
    """Il dato di popolazione più recente disponibile."""
    riga = conn.execute(
        "SELECT * FROM popolazione ORDER BY anno DESC LIMIT 1"
    ).fetchone()

    if riga is None:
        return Risultato("Nessun dato di popolazione in archivio.", trovato=False)

    return Risultato(
        f"Dato più recente: {riga['residenti']} abitanti "
        f"al 1 gennaio {riga['anno']}.",
        fonti=[riga["fonte"]],
    )


def popolazione_serie(conn: sqlite3.Connection) -> Risultato:
    """L'intera serie storica, anno per anno."""
    righe = conn.execute(
        "SELECT * FROM popolazione ORDER BY anno"
    ).fetchall()

    if not righe:
        return Risultato("Nessun dato di popolazione in archivio.", trovato=False)

    elenco = "; ".join(f"{r['anno']}: {r['residenti']}" for r in righe)

    return Risultato(
        f"Serie storica della popolazione residente al 1 gennaio: {elenco}.",
        fonti=_fonti_distinte(righe),
    )


def popolazione_variazione(
    conn: sqlite3.Connection, da: int | None = None, a: int | None = None
) -> Risultato:
    """Variazione della popolazione tra due anni."""
    righe = conn.execute("SELECT * FROM popolazione ORDER BY anno").fetchall()

    if len(righe) < 2:
        return Risultato(
            "Servono almeno due anni per calcolare una variazione.",
            trovato=False,
        )

    primo = next((r for r in righe if r["anno"] == da), righe[0])
    ultimo = next((r for r in righe if r["anno"] == a), righe[-1])

    if primo["anno"] == ultimo["anno"]:
        return Risultato("Gli anni indicati coincidono.", trovato=False)

    differenza = ultimo["residenti"] - primo["residenti"]
    percentuale = differenza / primo["residenti"] * 100

    verso = "diminuita" if differenza < 0 else "aumentata"

    return Risultato(
        f"Tra il {primo['anno']} e il {ultimo['anno']} la popolazione è "
        f"{verso} di {abs(differenza)} unità "
        f"({percentuale:+.1f}%), passando da {primo['residenti']} "
        f"a {ultimo['residenti']} abitanti.",
        fonti=_fonti_distinte([primo, ultimo]),
    )


def dato_territoriale(conn: sqlite3.Connection, chiave: str) -> Risultato:
    """Un dato stabile sul territorio, per chiave."""
    riga = conn.execute(
        "SELECT * FROM territorio WHERE chiave = ?", (chiave.lower(),)
    ).fetchone()

    if riga is None:
        chiavi = conn.execute("SELECT chiave FROM territorio").fetchall()
        elenco = ", ".join(r["chiave"] for r in chiavi) or "nessuna"
        return Risultato(
            f"Nessun dato territoriale per '{chiave}'. "
            f"Chiavi disponibili: {elenco}.",
            trovato=False,
        )

    return Risultato(
        f"{riga['chiave'].capitalize()}: {riga['valore']} {riga['unita'] or ''}".strip()
        + ".",
        fonti=[riga["fonte"]],
    )


def densita_abitativa(conn: sqlite3.Connection) -> Risultato:
    """Abitanti per chilometro quadrato, calcolata sui dati più recenti."""
    pop = conn.execute(
        "SELECT * FROM popolazione ORDER BY anno DESC LIMIT 1"
    ).fetchone()
    sup = conn.execute(
        "SELECT * FROM territorio WHERE chiave = 'superficie'"
    ).fetchone()

    if pop is None or sup is None:
        return Risultato(
            "Servono sia la popolazione sia la superficie per calcolare "
            "la densità, e uno dei due dati manca.",
            trovato=False,
        )

    densita = pop["residenti"] / sup["valore"]

    return Risultato(
        f"Densità abitativa: {densita:.1f} abitanti per kmq "
        f"({pop['residenti']} abitanti al 1 gennaio {pop['anno']} "
        f"su {sup['valore']} kmq). Valore calcolato, non riportato "
        f"come tale nelle fonti.",
        fonti=[pop["fonte"], sup["fonte"]],
    )


# --------------------------------------------------------------------------
# Il catalogo
# --------------------------------------------------------------------------

@dataclass
class Voce:
    """Una voce del repertorio, come la vede il modello."""
    nome: str
    descrizione: str
    parametri: dict
    funzione: Callable


REPERTORIO = [
    Voce(
        "popolazione_anno",
        "Numero di residenti in un anno specifico",
        {"anno": "intero, l'anno richiesto"},
        popolazione_anno,
    ),
    Voce(
        "popolazione_ultima",
        "Il dato di popolazione più recente disponibile",
        {},
        popolazione_ultima,
    ),
    Voce(
        "popolazione_serie",
        "L'intera serie storica della popolazione, anno per anno",
        {},
        popolazione_serie,
    ),
    Voce(
        "popolazione_variazione",
        "Variazione della popolazione tra due anni, in valore e percentuale",
        {"da": "intero opzionale", "a": "intero opzionale"},
        popolazione_variazione,
    ),
    Voce(
        "dato_territoriale",
        "Un dato stabile sul territorio (superficie, altitudine, ecc.)",
        {"chiave": "stringa, il nome del dato"},
        dato_territoriale,
    ),
    Voce(
        "densita_abitativa",
        "Abitanti per chilometro quadrato, calcolata sui dati più recenti",
        {},
        densita_abitativa,
    ),
]

PER_NOME = {v.nome: v for v in REPERTORIO}


def descrivi_repertorio() -> str:
    """Il catalogo in forma testuale, da mettere nel prompt del router."""
    righe = []
    for v in REPERTORIO:
        if v.parametri:
            par = ", ".join(f"{k} ({d})" for k, d in v.parametri.items())
        else:
            par = "nessun parametro"
        righe.append(f"- {v.nome}: {v.descrizione}. Parametri: {par}")
    return "\n".join(righe)


def esegui(nome: str, parametri: dict) -> Risultato:
    """Esegue un'interrogazione del repertorio."""
    if nome not in PER_NOME:
        return Risultato(
            f"Interrogazione '{nome}' non presente nel repertorio.",
            trovato=False,
        )

    conn = connetti()
    try:
        return PER_NOME[nome].funzione(conn, **parametri)
    except TypeError as errore:
        return Risultato(f"Parametri non validi: {errore}", trovato=False)
    finally:
        conn.close()

def stato_archivio() -> str:
    """Riepilogo di cosa contiene davvero il database, per il router."""
    conn = connetti()
    try:
        righe = []

        pop = conn.execute(
            "SELECT COUNT(*), MIN(anno), MAX(anno) FROM popolazione"
        ).fetchone()
        if pop[0]:
            righe.append(f"popolazione: {pop[0]} anni, dal {pop[1]} al {pop[2]}")
        else:
            righe.append("popolazione: VUOTA")

        bil = conn.execute("SELECT COUNT(*) FROM bilancio").fetchone()[0]
        righe.append(
            f"bilancio: {bil} voci" if bil else "bilancio: VUOTA, nessun dato disponibile"
        )

        tur = conn.execute("SELECT COUNT(*) FROM turismo").fetchone()[0]
        righe.append(
            f"turismo: {tur} rilevazioni" if tur else "turismo: VUOTA, nessun dato disponibile"
        )

        chiavi = conn.execute("SELECT chiave FROM territorio").fetchall()
        elenco = ", ".join(r["chiave"] for r in chiavi) or "nessuna"
        righe.append(f"territorio: chiavi disponibili: {elenco}")

        return "\n".join(f"- {r}" for r in righe)
    finally:
        conn.close()
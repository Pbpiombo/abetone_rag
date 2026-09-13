"""Verifica meccanica che i dati citati esistano nel frammento indicato."""

import re
from dataclasses import dataclass

from langchain_core.documents import Document

# Quanti caratteri dopo un dato cercare la sua citazione
FINESTRA_CITAZIONE = 300

# Il blocco di citazione: (fonte: [2], Ente, Atto n. X del gg/mm/aaaa, pag. N)
SCHEMA_CITAZIONE = r"\(\s*fonte:.*?\)"

MESI = (
    "gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|"
    "agosto|settembre|ottobre|novembre|dicembre"
)

SCHEMI = {
    "importo": [
        r"€\s*([\d.]+(?:,\d{1,2})?)",
        r"\b([\d.]+,\d{2})\s*euro\b",
    ],
    "percentuale": [
        r"\b(\d+(?:[.,]\d+)?)\s*(?:%|per\s*cento)",
    ],
    "data": [
        rf"\b(\d{{1,2}}\s+(?:{MESI})(?:\s+\d{{4}})?)\b",
        r"\b(\d{1,2}/\d{1,2}/\d{4})\b",
        r"\b(\d{1,2}-\d{1,2}-\d{4})\b",
    ],
    "codice": [
        r"\b([A-Z]\d{2}[A-Z]\d{10,12})\b",
        r"\b(\d{8}-\d)\b",
    ],
    "riferimento": [
        r"\bn\.?\s*(\d+/\d{4})\b",
        r"\bart\.?\s*(\d+(?:\s*,\s*comma\s*\d+)?)",
        r"\b(\d{1,4}/\d{4})\b",
    ],
}

@dataclass
class Esito:
    """Il risultato della verifica di un singolo dato."""
    tipo: str
    valore: str
    frammenti: list[int]
    stato: str          # verificato | non_trovato | non_citato
    dettaglio: str = ""


def normalizza(testo: str) -> str:
    """Riduce il testo a una forma confrontabile.

    Toglie spazi e separatori delle migliaia, cosi' che
    '€ 19.570,00' e '19570,00' risultino uguali.
    """
    testo = testo.lower().replace("\u00a0", " ")
    testo = re.sub(r"\s+", "", testo)
    testo = re.sub(r"(?<=\d)\.(?=\d)", "", testo)
    return testo

def maschera_citazioni(risposta: str) -> str:
    """Sostituisce il testo delle citazioni con spazi.

    Conserva la lunghezza, cosi' le posizioni dei dati restano valide.
    I riferimenti dentro una citazione sono metadati nostri, non dati
    da verificare.
    """
    def a_spazi(m):
        return " " * len(m.group(0))

    return re.sub(SCHEMA_CITAZIONE, a_spazi, risposta, flags=re.DOTALL | re.IGNORECASE)

def trova_citazioni(risposta: str) -> list[tuple[int, int]]:
    """Restituisce coppie (posizione nel testo, numero del frammento)."""
    return [
        (m.start(), int(m.group(1)))
        for m in re.finditer(r"fonte:\s*\[(\d+)\]", risposta, re.IGNORECASE)
    ]


def trova_dati(risposta: str) -> list[tuple[str, str, int]]:
    """Restituisce terne (tipo, valore, posizione) di ogni dato citabile.

    Gli schemi sono provati in ordine: una porzione di testo gia' catturata
    da uno schema precedente non viene riconsiderata. Cosi' '28/04/2026'
    resta una data e non produce anche un finto riferimento '04/2026'.
    """
    trovati = []
    occupati = []

    def si_sovrappone(inizio: int, fine: int) -> bool:
        return any(inizio < f and i < fine for i, f in occupati)

    for tipo, schemi in SCHEMI.items():
        for schema in schemi:
            for m in re.finditer(schema, risposta, re.IGNORECASE):
                if si_sovrappone(m.start(), m.end()):
                    continue

                occupati.append((m.start(), m.end()))
                trovati.append((tipo, m.group(1).strip(), m.start()))

    return sorted(trovati, key=lambda t: t[2])

def frammenti_citati(
    posizione: int, citazioni: list[tuple[int, int]]
) -> list[int]:
    """I frammenti citati subito dopo un dato."""
    return [
        numero
        for pos, numero in citazioni
        if posizione < pos <= posizione + FINESTRA_CITAZIONE
    ]


def verifica(risposta: str, documenti: list[Document]) -> list[Esito]:
    """Controlla che ogni dato della risposta esista nel frammento citato."""
    testi = {
        numero: normalizza(doc.page_content)
        for numero, doc in enumerate(documenti, start=1)
    }

    citazioni = trova_citazioni(risposta)
    mascherata = maschera_citazioni(risposta)
    esiti = []

    for tipo, valore, posizione in trova_dati(mascherata):
        numeri = frammenti_citati(posizione, citazioni)

        if not numeri:
            esiti.append(Esito(tipo, valore, [], "non_citato"))
            continue

        ago = normalizza(valore)
        dentro = [n for n in numeri if n in testi and ago in testi[n]]

        if dentro:
            esiti.append(Esito(tipo, valore, dentro, "verificato"))
        else:
            altrove = [n for n, t in testi.items() if ago in t]
            dettaglio = (
                f"presente invece nei frammenti {altrove}"
                if altrove
                else "non presente in nessun frammento recuperato"
            )
            esiti.append(Esito(tipo, valore, numeri, "non_trovato", dettaglio))

    return esiti

def riassumi(esiti: list[Esito]) -> dict:
    """Conta gli esiti per stato."""
    conteggio = {"verificato": 0, "non_trovato": 0, "non_citato": 0}
    for e in esiti:
        conteggio[e.stato] += 1
    return conteggio
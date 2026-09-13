"""STEP 3 - risposta con verifica automatica dei dati citati."""

import sys

from src.chains.rag import costruisci_catena
from src.verification.controllo import verifica, riassumi

SIMBOLI = {
    "verificato": "OK ",
    "non_trovato": "!! ",
    "non_citato": "?  ",
}

DOMANDE = [
    "Qual è il costo massimo giornaliero per un incarico professionale?",
    "Qual è il costo totale del progetto Ludoteche di montagna?",
    "Entro quando va presentata la relazione annuale sullo stato di "
    "avanzamento della Strategia d'area?",
    "Quanti abitanti ha il Comune di Abetone Cutigliano?",
]


def mostra(esito_catena: dict) -> None:
    print(f"\n{'=' * 74}")
    print(f">>> {esito_catena['domanda']}")
    print("=" * 74)

    print("\nRISPOSTA")
    print(esito_catena["risposta"])

    esiti = verifica(esito_catena["risposta"], esito_catena["documenti"])

    print("\nVERIFICA DEI DATI CITATI")

    if not esiti:
        print("  Nessun dato numerico o normativo da verificare.")
        return

    for e in esiti:
        riga = f"  {SIMBOLI[e.stato]}{e.tipo:12} {e.valore:28}"
        if e.frammenti:
            riga += f" frammenti {e.frammenti}"
        print(riga)
        if e.dettaglio:
            print(f"       -> {e.dettaglio}")

    conteggio = riassumi(esiti)
    print(f"\n  Verificati: {conteggio['verificato']}  "
          f"Non trovati: {conteggio['non_trovato']}  "
          f"Non citati: {conteggio['non_citato']}")


def main() -> None:
    catena = costruisci_catena()
    domande = [" ".join(sys.argv[1:])] if len(sys.argv) > 1 else DOMANDE

    for domanda in domande:
        mostra(catena.invoke(domanda))

    print(f"\n{'=' * 74}")


if __name__ == "__main__":
    main()
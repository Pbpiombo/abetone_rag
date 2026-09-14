"""Estrae i campi di un bando e li salva nel database dopo conferma.

Uso:
    python -m scripts.estrai_bando URL identificativo
    python -m scripts.estrai_bando percorso/testo.txt URL identificativo

Nella prima forma la pagina viene scaricata; nella seconda si parte da un
testo gia' salvato, utile per rileggere una pagina senza riscaricarla.

L'identificativo e' una convenzione nostra, non un dato del documento:
va sempre indicato, ed e' cio' che distingue un bando nuovo da un
aggiornamento di uno gia' in archivio.

Opzioni:
    --debug         stampa il JSON grezzo restituito dal modello
    --salva-testo   salva in data/processed il testo estratto dalla pagina
"""

import sys
from pathlib import Path

from src.config import PROCESSED_DIR
from src.estrazione.bandi import (
    costruisci_estrattore,
    estrai,
    da_rivedere,
    valida,
)
from src.estrazione.pagina import prendi
from src.estrazione.salva import esiste, salva

SEGNI = {"alta": "  ", "media": "~ ", "bassa": "! "}
FONTE = "Portale bandi Regione Toscana"


def mostra(campi) -> None:
    """Stampa i campi estratti, con la prova per quelli da verificare."""
    print("=" * 74)
    print("CAMPI ESTRATTI")
    print("=" * 74)

    for c in campi:
        marca = "CRITICO" if c.critico else "       "
        valore = c.valore if c.valore is not None else "(vuoto)"
        print(f"{SEGNI[c.confidenza]}{marca} {c.nome:20} {valore}")
        if c.prova and (c.critico or c.confidenza != "alta"):
            print(f"                            prova: {c.prova}")


def mostra_confronto(precedente: dict, riga: dict) -> None:
    """Evidenzia le differenze rispetto alla riga gia' in archivio."""
    print(f"\nATTENZIONE: '{riga['id']}' esiste gia' in archivio "
          f"(verificato il {precedente['verificato_il']}).")

    cambiati = [
        (c, precedente.get(c), riga.get(c))
        for c in ("scadenza", "ammette_comuni", "a_sportello",
                  "contributo_perc", "dotazione")
        if str(precedente.get(c)) != str(riga.get(c))
    ]

    if not cambiati:
        print("  Nessuna differenza sui campi principali.")
        return

    print("  Differenze:")
    for nome, prima, dopo in cambiati:
        print(f"    {nome}: {prima}  ->  {dopo}")


def conferma(domanda: str) -> bool:
    """Chiede conferma esplicita. Tutto cio' che non e' si vale no."""
    risposta = input(f"\n{domanda} [s/N] ").strip().lower()
    return risposta in ("s", "si", "sì")


def main() -> None:
    argomenti = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not argomenti:
        print("Uso: python -m scripts.estrai_bando URL [identificativo]")
        print("     python -m scripts.estrai_bando percorso/testo.txt URL "
              "[identificativo]")
        return

    # Se il primo argomento e' un URL, scarica; altrimenti legge il file
    if argomenti[0].startswith("http"):
        if len(argomenti) < 2:
            print("Serve l'identificativo del bando.")
            print("Uso: python -m scripts.estrai_bando URL identificativo")
            return

        url = argomenti[0]
        id_bando = argomenti[1]

        print(f"Scarico: {url}")
        testo = prendi(url)

        if "--salva-testo" in sys.argv:
            nome = PROCESSED_DIR / f"pagina_{id_bando}.txt"
            nome.write_text(testo, encoding="utf-8")
            print(f"Testo salvato in {nome}")
    else:
        if len(argomenti) < 3:
            print("Uso: python -m scripts.estrai_bando percorso/testo.txt "
                  "URL identificativo")
            return

        percorso = Path(argomenti[0])
        url = argomenti[1]
        id_bando = argomenti[2]

        if not percorso.exists():
            print(f"File non trovato: {percorso}")
            return

        testo = percorso.read_text(encoding="utf-8")

    print(f"Testo utile: {len(testo)} caratteri\n")

    estrattore = costruisci_estrattore()
    campi = estrai(estrattore, testo, debug="--debug" in sys.argv)

    mostra(campi)

    riga, problemi = valida(campi)

    if problemi:
        print("\nPROBLEMI DI VALIDAZIONE")
        for p in problemi:
            print(f"  - {p}")
        print("\nNon salvo. Correggi il testo della pagina oppure "
              "inserisci la riga a mano.")
        return

    rivedere = da_rivedere(campi)
    print(f"\n{len(rivedere)} campi da confermare su {len(campi)}.")

    riga["id"] = id_bando

    precedente = esiste(riga["id"])
    if precedente:
        mostra_confronto(precedente, riga)

    if not conferma("Salvare nel database?"):
        print("Non salvato.")
        return

    salva(riga, url, FONTE)
    print(f"Salvato: {riga['id']}")


if __name__ == "__main__":
    main()
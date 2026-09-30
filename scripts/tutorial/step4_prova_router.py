"""Collaudo del router: dove manda ciascuna domanda."""

from src.chains.router import (
    costruisci_router,
    decidi,
    esegui_interrogazioni,
    formatta_dati,
)

DOMANDE = [
    "Quanti abitanti ha il Comune di Abetone Cutigliano?",
    "Quali sono i requisiti per accedere all'avviso di rafforzamento amministrativo?",
    "Come è cambiata la popolazione negli ultimi anni?",
    "Qual è la densità abitativa del comune?",
    "Il calo demografico giustifica la richiesta di fondi per le aree interne?",
    "Qual è il bilancio comunale del 2025?",
    "Che tempo fa ad Abetone?",
]


def main() -> None:
    router = costruisci_router()

    for domanda in DOMANDE:
        print(f"\n{'=' * 74}")
        print(f">>> {domanda}")

        decisione = decidi(router, domanda)

        if "errore" in decisione:
            print(f"  ERRORE: {decisione['errore']}")

        print(f"  documenti: {decisione['documenti']}")
        print(f"  interrogazioni: {decisione['interrogazioni']}")

        esiti = esegui_interrogazioni(decisione)
        if esiti:
            print("\n  DATI RECUPERATI")
            for riga in formatta_dati(esiti).splitlines():
                print(f"  {riga}")


if __name__ == "__main__":
    main()
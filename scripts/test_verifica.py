"""Collaudo del verificatore con risposte deliberatamente falsificate.

Non chiama il modello: costruisce risposte finte e controlla che
il verificatore reagisca come previsto. Gratuito e istantaneo.
"""

from langchain_core.documents import Document

from src.verification.controllo import verifica

FRAMMENTI = [
    Document(
        page_content=(
            "I compensi di cui alle precedenti lettere b e c sono ammissibili "
            "a finanziamento secondo un parametro di costo giornata/uomo pari "
            "al massimo a € 322,00, oltre oneri previdenziali e fiscali."
        ),
        metadata={"ente": "Regione Toscana", "pagina": 11},
    ),
    Document(
        page_content=(
            "6. Quadro economico a.s. 2026/2027 a.s. 2027/2028 totale "
            "Costo per personale € 9.000,00 € 9.000,00 € 18.000,00 "
            "Costo per attrezzature € 785,00 € 785,00 € 1.570,00 "
            "Totale € 9.785,00 € 9.785,00 € 19.570,00"
        ),
        metadata={"ente": "Comune di Abetone Cutigliano", "pagina": 14},
    ),
    Document(
        page_content=(
            "Sono ammissibili eventuali costi indiretti, calcolati "
            "forfettariamente in un valore massimo pari al 7% delle altre "
            "spese sopradette, ai sensi dell'art. 54 del Reg. UE 2021/1060."
        ),
        metadata={"ente": "Regione Toscana", "pagina": 11},
    ),
]

CASI = [
    {
        "nome": "importo corretto",
        "risposta": "Il costo massimo è € 322,00 (fonte: [1], Regione Toscana, pag. 11).",
        "atteso": {"verificato": 1, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "importo INVENTATO",
        "risposta": "Il costo massimo è € 450,00 (fonte: [1], Regione Toscana, pag. 11).",
        "atteso": {"verificato": 0, "non_trovato": 1, "non_citato": 0},
    },
    {
        "nome": "importo giusto, frammento SBAGLIATO",
        "risposta": "Il costo massimo è € 322,00 (fonte: [2], Comune, pag. 14).",
        "atteso": {"verificato": 0, "non_trovato": 1, "non_citato": 0},
    },
    {
        "nome": "importo SENZA citazione",
        "risposta": "Il costo massimo è € 322,00 e va applicato a tutti gli incarichi.",
        "atteso": {"verificato": 0, "non_trovato": 0, "non_citato": 1},
    },
    {
        "nome": "cifra alterata di poco",
        "risposta": "Il totale è € 19.520,00 (fonte: [2], Comune, pag. 14).",
        "atteso": {"verificato": 0, "non_trovato": 1, "non_citato": 0},
    },
    {
        "nome": "percentuale corretta",
        "risposta": "I costi indiretti sono al 7% (fonte: [3], Regione Toscana, pag. 11).",
        "atteso": {"verificato": 1, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "percentuale INVENTATA",
        "risposta": "I costi indiretti sono al 15% (fonte: [3], Regione Toscana, pag. 11).",
        "atteso": {"verificato": 0, "non_trovato": 1, "non_citato": 0},
    },
    {
        "nome": "formattazione diversa dello stesso importo",
        "risposta": "Il costo massimo è di 322,00 euro (fonte: [1], Regione Toscana, pag. 11).",
        "atteso": {"verificato": 1, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "rifiuto: nessun dato",
        "risposta": "Non trovo la risposta nei documenti disponibili.",
        "atteso": {"verificato": 0, "non_trovato": 0, "non_citato": 0},
    },
        {
        "nome": "dato numerico corretto",
        "risposta": "Il comune ha 1834 abitanti (fonte: [D1], ISTAT).",
        "dati": [("popolazione_ultima", type("R", (), {"testo": "Dato più recente: 1834 abitanti al 1 gennaio 2026.", "fonti": ["ISTAT"]})())],
        "atteso": {"verificato": 1, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "dato numerico ALTERATO",
        "risposta": "Il comune ha 1900 abitanti (fonte: [D1], ISTAT).",
        "dati": [("popolazione_ultima", type("R", (), {"testo": "Dato più recente: 1834 abitanti al 1 gennaio 2026.", "fonti": ["ISTAT"]})())],
        "atteso": {"verificato": 0, "non_trovato": 1, "non_citato": 0},
    },
]


def conta(esiti) -> dict:
    conteggio = {"verificato": 0, "non_trovato": 0, "non_citato": 0}
    for e in esiti:
        conteggio[e.stato] += 1
    return conteggio


def main() -> None:
    passati = 0

    for caso in CASI:
        esiti = verifica(caso["risposta"], FRAMMENTI, caso.get("dati"))
        ottenuto = conta(esiti)
        ok = ottenuto == caso["atteso"]
        passati += ok

        print(f"\n{'PASS' if ok else 'FAIL'}  {caso['nome']}")

        if not ok:
            print(f"      atteso:   {caso['atteso']}")
            print(f"      ottenuto: {ottenuto}")
            for e in esiti:
                print(f"        {e.stato:14} {e.tipo:12} {e.valore}")

    print(f"\n{'=' * 60}")
    print(f"Casi superati: {passati}/{len(CASI)}")


if __name__ == "__main__":
    main()
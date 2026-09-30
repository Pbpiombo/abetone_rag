"""Sonda di retrieval ibrido, senza chiamare il modello."""

import sys

from src.retrieval import RecuperoIbrido


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python -m scripts.cerca_ibrido \"la tua domanda\"")
        return

    domanda = " ".join(sys.argv[1:])
    recupero = RecuperoIbrido()

    print(f"\n>>> {domanda}\n")

    for posizione, (doc, punteggio, origini) in enumerate(
        recupero.cerca(domanda), start=1
    ):
        meta = doc.metadata
        testo = " ".join(doc.page_content.split())[:200]
        print(f"[{posizione}] rrf {punteggio:.4f} | {', '.join(origini)}")
        print(f"    {meta.get('ente')} | {meta.get('tipo_documento')} "
              f"| p. {meta.get('pagina')}")
        print(f"    {testo}...\n")


if __name__ == "__main__":
    main()
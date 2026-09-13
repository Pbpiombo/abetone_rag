"""Sonda di retrieval: interroga il vector store senza chiamare il modello."""

import sys

from src.vectorstore import apri_store

K = 8


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python -m scripts.cerca \"la tua domanda\"")
        return

    domanda = " ".join(sys.argv[1:])
    store = apri_store()

    print(f"\n>>> {domanda}\n")

    for posizione, (doc, distanza) in enumerate(
        store.similarity_search_with_score(domanda, k=K), start=1
    ):
        meta = doc.metadata
        testo = " ".join(doc.page_content.split())[:200]
        print(f"[{posizione}] {distanza:.3f} | {meta.get('ente')} "
              f"| {meta.get('tipo_documento')} | p. {meta.get('pagina')}")
        print(f"    {testo}...\n")


if __name__ == "__main__":
    main()
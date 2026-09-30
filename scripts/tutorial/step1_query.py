"""STEP 1 - verifica del contenuto del vector store e del retrieval."""

from langchain_chroma import Chroma

from src.vectorstore import apri_store

DOMANDE = [
    "Quante risorse sono destinate a ciascuna Area interna?",
    "Entro quale data devono essere sostenute le spese?",
    "Chi sono i soggetti che possono presentare domanda?",
    "Quali enti sono beneficiari del sostegno?",
    "Qual è il costo massimo giornaliero per un incarico professionale?",
]


def ispeziona_chunk(store: Chroma, quanti: int = 5) -> None:
    """Stampa i primi chunk per controllare dove cadono i tagli."""
    dati = store.get()
    print(f"Chunk totali nel database: {len(dati['ids'])}\n")

    print("=" * 70)
    print("ISPEZIONE DEI PRIMI CHUNK")
    print("=" * 70)

    for i in range(min(quanti, len(dati["ids"]))):
        testo = dati["documents"][i]
        meta = dati["metadatas"][i]
        print(f"\n--- chunk {i} | pagina {meta.get('pagina')} "
              f"| {len(testo)} caratteri ---")
        print(f"INIZIO: {testo[:120]}")
        print(f"FINE:   {testo[-120:]}")

    print(f"\nMetadati di esempio:\n{dati['metadatas'][0]}")


def prova_retrieval(store: Chroma, k: int = 5) -> None:
    """Esegue le domande di prova e mostra i chunk recuperati."""
    print("\n" + "=" * 70)
    print("PROVE DI RETRIEVAL")
    print("=" * 70)

    for domanda in DOMANDE:
        print(f"\n>>> {domanda}")
        risultati = store.similarity_search_with_score(domanda, k=k)

        for posizione, (doc, distanza) in enumerate(risultati, start=1):
            estratto = " ".join(doc.page_content.split())[:180]
            meta = doc.metadata
            print(f"  [{posizione}] {distanza:.3f} "
                  f"| {meta.get('ente')} ({meta.get('livello')}) "
                  f"| p. {meta.get('pagina')}")
            print(f"      {estratto}...")


def main() -> None:
    store = apri_store()
    ispeziona_chunk(store)
    prova_retrieval(store)


if __name__ == "__main__":
    main()
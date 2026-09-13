"""Ispezione preliminare dei PDF in data/raw, prima di deciderne i metadati."""

from pathlib import Path

from src.config import RAW_DIR
from src.ingestion.pdf_ingest import carica_pdf

SOGLIA_PAGINA_VUOTA = 100


def compatta(testo: str, quanti: int) -> str:
    """Riduce il testo a una riga sola, troncata."""
    return " ".join(testo.split())[:quanti]


def ispeziona(percorso: Path) -> None:
    print("\n" + "=" * 74)
    print(percorso.name)
    print("=" * 74)

    try:
        pagine = carica_pdf(percorso)
    except Exception as errore:
        print(f"  ERRORE in lettura: {errore}")
        return

    lunghezze = [len(p.page_content.strip()) for p in pagine]
    totale = sum(lunghezze)
    media = totale // len(pagine) if pagine else 0

    print(f"  Caratteri totali: {totale}  (media per pagina: {media})")

    if media < 200:
        print("  >>> ATTENZIONE: pochissimo testo. Probabile scansione.")

    quasi_vuote = [i + 1 for i, n in enumerate(lunghezze)
                   if n < SOGLIA_PAGINA_VUOTA]
    if quasi_vuote:
        print(f"  Pagine quasi vuote: {quasi_vuote}")

    print("\n  --- PRIMA PAGINA ---")
    print(f"  {compatta(pagine[0].page_content, 600)}")

    if len(pagine) > 1:
        print("\n  --- SECONDA PAGINA ---")
        print(f"  {compatta(pagine[1].page_content, 300)}")

    if len(pagine) > 2:
        print("\n  --- ULTIMA PAGINA ---")
        print(f"  {compatta(pagine[-1].page_content, 300)}")


def main() -> None:
    pdf = sorted(RAW_DIR.glob("*.pdf"))
    print(f"Trovati {len(pdf)} PDF in {RAW_DIR}")

    for percorso in pdf:
        ispeziona(percorso)

    print("\n" + "=" * 74)


if __name__ == "__main__":
    main()
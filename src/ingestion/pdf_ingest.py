"""Ingestione di un PDF nel vector store Chroma."""

import re
from pathlib import Path

import pypdf
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document

from src.config import CHROMA_DIR, CHUNK_SIZE, CHUNK_OVERLAP, SOGLIA_CHUNK
from src.vectorstore import apri_store


def carica_pdf(percorso: Path) -> list[Document]:
    """Legge il PDF e restituisce un Document per ogni pagina."""
    if not percorso.exists():
        raise FileNotFoundError(f"PDF non trovato: {percorso}")

    lettore = pypdf.PdfReader(str(percorso))

    pagine = []
    for numero, pagina in enumerate(lettore.pages):
        pagine.append(Document(
            page_content=pagina.extract_text() or "",
            metadata={"source": str(percorso), "page": numero},
        ))

    print(f"  Pagine lette: {len(pagine)}")
    return pagine


def pulisci(testo: str, intestazione: str | None = None) -> str:
    """Normalizza gli spazi, poi rimuove l'intestazione ricorrente."""
    testo = testo.replace("\u00a0", " ")
    testo = re.sub(r"[ \t]+", " ", testo)

    # Ricuce i numeri spezzati dall'estrazione: "41/202 2" -> "41/2022"
    testo = re.sub(r"(?<=\d)\s+(?=\d)", "", testo)
    testo = re.sub(r"(?<=\d)\s*([/.,])\s*(?=\d)", r"\1", testo)

    testo = re.sub(r"[.\s]{6,}", " ", testo)

    if intestazione:
        testo = re.sub(intestazione, " ", testo, flags=re.IGNORECASE)

    testo = re.sub(r"\n{3,}", "\n\n", testo)
    return testo.strip()

def e_indice(testo: str, soglia: int = 5) -> bool:
    """Riconosce le pagine di indice dai puntini di guida seguiti dalla pagina.

    I PDF usano punti ripetuti o il carattere di ellissi, a volte separati
    da spazi. Il numero di pagina finale distingue un sommario da un modulo
    da compilare, che contiene puntini analoghi ma senza numero.
    """
    schema = r"(?:[.\u2026]\s?){4,}\s*(?:pag\.?\s*)?\d{1,3}\b"
    return len(re.findall(schema, testo, re.IGNORECASE)) >= soglia

def spezza(
    pagine: list[Document],
    intestazione: str | None = None,
    salta_pagine: list[int] | None = None,
) -> list[Document]:
    """Divide le pagine in chunk, saltando quelle indicate."""
    salta_pagine = salta_pagine or []

    tenute = []
    for pagina in pagine:
        numero = pagina.metadata.get("page", 0) + 1

        if numero in salta_pagine:
            continue

        if e_indice(pagina.page_content):
            print(f"  Saltata pagina {numero}: indice")
            continue

        pagina.page_content = pulisci(pagina.page_content, intestazione)
        if len(pagina.page_content) < 50:
            continue

        tenute.append(pagina)

    print(f"  Pagine tenute: {len(tenute)}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=[
            r"\n\d{1,2}\.\d{1,2}\s",
            r"\n\d{1,2}\.\s",
            r"\n\n",
            r"\n(?![\d−•-])",
            r"\.\s",
            r";\s",
            r"\s",
            r"",
        ],
        keep_separator=True,
        is_separator_regex=True,
    )

    chunk = splitter.split_documents(tenute)

    prima = len(chunk)
    chunk = [c for c in chunk if len(c.page_content.strip()) >= SOGLIA_CHUNK]

    if prima != len(chunk):
        print(f"  Chunk scartati perche' troppo corti: {prima - len(chunk)}")

    print(f"  Chunk prodotti: {len(chunk)}")
    return chunk


def applica_metadati(chunk: list[Document], metadati: dict) -> list[Document]:
    """Aggiunge i metadati obbligatori a ogni chunk."""
    for indice, pezzo in enumerate(chunk):
        pagina = pezzo.metadata.get("page")
        pezzo.metadata = {
            **metadati,
            "pagina": int(pagina) + 1 if pagina is not None else 0,
            "chunk_num": indice,
        }
    return chunk


def salva_in_chroma(chunk: list[Document], fonte: str) -> Chroma:
    """Calcola gli embedding e scrive nel vector store."""
    store = apri_store()
    identificatori = [f"{fonte}::{i}" for i in range(len(chunk))]
    store.add_documents(documents=chunk, ids=identificatori)
    print(f"  Salvati {len(chunk)} chunk in {CHROMA_DIR}")
    return store
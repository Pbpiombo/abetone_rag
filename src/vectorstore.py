"""Punto unico di accesso al vector store Chroma."""

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from src.config import CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL


def crea_embeddings() -> HuggingFaceEmbeddings:
    """Modello di embedding, con vettori normalizzati a lunghezza 1."""
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )


def apri_store() -> Chroma:
    """Apre (o crea) la collezione Chroma con distanza coseno."""
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=crea_embeddings(),
        persist_directory=str(CHROMA_DIR),
        collection_metadata={"hnsw:space": "cosine"},
    )
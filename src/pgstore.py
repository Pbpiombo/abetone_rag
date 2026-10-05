import os
import psycopg
import numpy as np
import json

from pgvector.psycopg import register_vector
from dotenv import load_dotenv

from src.vectorstore import crea_embeddings
from langchain_core.documents import Document

load_dotenv()


def salva_chunk_in_db(documenti: list[Document]) -> None:
    """Salva i chunk dei documenti nel database."""
    
    try:
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            register_vector(conn)
            cursor= conn.cursor()

            emb= crea_embeddings()

            testi= [doc.page_content for doc in documenti]
            vettori= emb.embed_documents(testi)

            for documento, vettore in zip(documenti, vettori):
                testo= documento.page_content
                metadata= json.dumps(documento.metadata)
                vettore_np= np.array(vettore)
                cursor.execute(
                    "INSERT INTO chunk (testo, metadata, embedding) VALUES (%s, %s, %s)",
                    (testo, metadata, vettore_np)
                )
            conn.commit()

    except Exception as e:
        print("Errore durante la connessione a Supabase:", e)


def cerca_chunk_in_db(domanda: str, k: int = 5) -> list[Document]:
    """Cerca i chunk più simili alla domanda nel database."""

    with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
        register_vector(conn)
        cursor= conn.cursor()
        emb= crea_embeddings()

        vettore_domanda= np.array(emb.embed_query(domanda))

        cursor.execute(
            """SELECT id,
                    testo, 
                    metadata, 
                    embedding <=> %s AS distanza
            FROM chunk
            ORDER BY distanza
            LIMIT %s""",
            (vettore_domanda, k)
        )

        return [ Document(page_content= testo, metadata= metadata) for id, testo, metadata,distanza in cursor.fetchall()]


def ricerca_lessicale_in_db(domanda: str, k: int = 5) -> list[Document]:
    """Esegue una ricerca lessicale nel database utilizzando la ricerca full-text di PostgreSQL."""

    with psycopg.connect(os.getenv("DATABASE_URL")) as conn:

        cursor= conn.cursor()

        cursor.execute(
            """SELECT id,
                    testo, 
                    metadata,
                    ts_rank(to_tsvector('italian',testo), plainto_tsquery('italian',%s)) AS punteggio 
            FROM chunk
            WHERE to_tsvector('italian',testo) @@ plainto_tsquery('italian', %s)
            ORDER BY punteggio DESC
            LIMIT %s""",
            (domanda, domanda, k)
        )

        return [ Document(page_content= testo, metadata= metadata) for id, testo, metadata,punteggio in cursor.fetchall()]

if __name__ == "__main__":

    prova = [ 
        Document(page_content="La scadenza per abetone è prevista per il 31/10/2027", metadata={"source": "delibera.pdf", "page": 12, "livello": "regionale"}),
        Document(page_content="Il contributo per asilo nido è di 500 euro", metadata={"source": "delibera.pdf", "page": 5, "livello": "comunale"}),
        Document(page_content="Il bando per il comune di Pistoia è aperto fino al 15/09/2024", metadata={"source": "bando.pdf", "page": 3, "livello": "comunale"}),
        Document(page_content="Ad Abetone a dicembre è prevista 20 cm di neve", metadata={"source": "previsioni_meteo.pdf", "page": 1, "livello": "regionale"})
    ]
    #salva_chunk_in_db(prova)
    #print ("Chunk prova salvati")

    for doc in cerca_chunk_in_db("entro quando devo presentare?"):
        print(doc.metadata.get("livello"), "|", doc.page_content[:60])

    for doc in ricerca_lessicale_in_db("scadenza Abetone"):
        print(doc.metadata.get("livello"), "|", doc.page_content[:60])

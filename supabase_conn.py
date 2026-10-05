"""Connettere a Supabase e creare un cursore per eseguire query SQL."""

import os
import psycopg
import numpy as np
import json

from pgvector.psycopg import register_vector
from dotenv import load_dotenv

from src.vectorstore import crea_embeddings


LISTA_FRASI= ["La scadenza per abetone è prevista per il 31/10/2027", "Il contributo per asilo nido è di 500 euro", "Il bando per il comune di Pistoia è aperto fino al 15/09/2024", "Ad Abetone a dicembre è prevista 20 cm di neve"]
metadata = {"source": "delibera.pdf", "page": 12, "livello": "regionale"}

load_dotenv()
try:
    with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
        register_vector(conn)
        cursor = conn.cursor()

        emb= crea_embeddings()

        for frase in LISTA_FRASI:
            vettore= emb.embed_query(frase)
            cursor.execute(
                "INSERT into prova (testo,embedding) VALUES (%s, %s)",
                (frase, vettore)
            )
        conn.commit()

        domanda= "Qual'è la scadenza per abetone?"
        vettore_domanda= np.array(emb.embed_query(domanda))

        cursor.execute(
            "SELECT testo, embedding <=> %s AS distanza FROM prova ORDER BY distanza LIMIT 3",
            (vettore_domanda,)
        )

        for riga in cursor.fetchall():
            print(riga)

        cursor.execute("SELECT id, testo FROM prova;")
        print(cursor.fetchall())
except Exception as e:
    print("Errore durante la connessione a Supabase:", e)
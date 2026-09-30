"""STEP 4 - crea il database dei dati numerici e lo popola dai CSV."""

from src.database.schema import (
    connetti,
    crea_schema,
    carica_csv,
    riepilogo,
    TABELLE_DA_CSV,
)


def main() -> None:
    conn = connetti()

    crea_schema(conn)

    print("\n  Caricamento dai CSV in data/processed:")
    for tabella, colonne in TABELLE_DA_CSV.items():
        carica_csv(conn, tabella, colonne)

    riepilogo(conn)
    conn.close()


if __name__ == "__main__":
    main()
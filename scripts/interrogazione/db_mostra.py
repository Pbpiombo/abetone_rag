"""Ispezione del contenuto del database dei dati numerici."""

from src.database.schema import connetti, TABELLE_DA_CSV


def main() -> None:
    conn = connetti()

    for tabella in TABELLE_DA_CSV:
        righe = conn.execute(f"SELECT * FROM {tabella}").fetchall()

        print(f"\n--- {tabella} ({len(righe)} righe) ---")

        if not righe:
            print("  vuota")
            continue

        colonne = righe[0].keys()
        print("  " + " | ".join(f"{c}" for c in colonne))

        for riga in righe:
            valori = [str(riga[c]) if riga[c] is not None else "-" for c in colonne]
            print("  " + " | ".join(valori))

    conn.close()


if __name__ == "__main__":
    main()
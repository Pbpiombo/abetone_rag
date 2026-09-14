"""Tipi e funzioni condivisi dalle interrogazioni."""

from dataclasses import dataclass, field


@dataclass
class Risultato:
    """L'esito di un'interrogazione, pronto per essere dato al modello."""
    testo: str
    fonti: list[str] = field(default_factory=list)
    trovato: bool = True


def fonti_distinte(righe) -> list[str]:
    """Le fonti citate nelle righe, senza ripetizioni, in ordine."""
    viste = []
    for riga in righe:
        fonte = riga["fonte"]
        if fonte not in viste:
            viste.append(fonte)
    return viste
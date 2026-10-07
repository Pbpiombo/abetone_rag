# Abetone RAG

Assistente per la programmazione territoriale di un piccolo comune montano.
Trova i bandi a cui l'ente può partecipare, spiega cosa serve per presentare
domanda, e **cita la fonte di ogni dato che riporta**.

Caso di studio: Comune di Abetone Cutigliano (1.834 abitanti, area interna
Garfagnana - Lunigiana - Media Valle del Serchio - Appennino Pistoiese).

---

## Il problema

Le opportunità di finanziamento per un comune sono sparse in decine di
documenti: avvisi regionali, linee guida nazionali, delibere, studi di settore.
Chi deve scrivere un piano d'azione ha due problemi: trovare l'informazione, e
non sbagliarla. Un importo o una scadenza errati in un atto amministrativo sono
un danno reale.

Un modello linguistico da solo non risolve né l'uno né l'altro: produce comunque
una risposta, plausibile e potenzialmente inventata.

## L'approccio

Tre presidi sovrapposti, di cui l'ultimo non probabilistico.

1. **Frammenti etichettati** — ogni pezzo di documento passato al modello porta
   con sé ente, tipo di atto, livello di governo e pagina.
2. **Prompt vincolante** — ogni importo, data o codice deve essere seguito dalla
   sua fonte; è vietato combinare dati di documenti diversi in una stessa
   affermazione; se i frammenti non contengono la risposta, il sistema lo
   dichiara invece di costruire qualcosa.
3. **Verifica meccanica** — ogni dato citato viene cercato nel testo della fonte
   dichiarata. O c'è, o non c'è.

Il terzo strato ha un collaudo con 18 casi, positivi e negativi, che dimostra
che il controllo intercetta davvero gli errori invece di limitarsi a non
segnalare nulla.

## Come funziona

Il sistema tiene due archivi separati, e un router decide quale interrogare.

| Archivio | Contiene | Risponde a |
|---|---|---|
| Vector store | Testo dei documenti, diviso in chunk | "Cosa dice questo bando?" |
| Database relazionale | Bandi, demografia, dati territoriali | "Quali bandi posso usare?" |

I dati numerici **non** stanno nel vector store: una ricerca semantica su una
tabella può restituire il valore vicino a quello giusto, e il modello lo
presenterebbe come corretto. Una query SQL o restituisce il valore esatto o non
restituisce niente.

Il recupero documentale è **ibrido**: somiglianza semantica (embedding
multilingua, in locale) unita a corrispondenza lessicale esatta, con fusione
RRF. Serve perché la ricerca densa non sa agganciare codici e riferimenti
normativi come `41/2022` o un CUP.

### Due implementazioni del recupero

Il vector store esiste in due versioni intercambiabili, che espongono la stessa
interfaccia:

| | `RecuperoIbrido` | `RecuperoPostgres` |
|---|---|---|
| Vettori | Chroma, su disco | Postgres + pgvector |
| Ricerca lessicale | BM25 in memoria | full-text italiano di Postgres |
| Dove gira | in locale | Postgres gestito (Supabase) |

`costruisci_catena()` usa Chroma per impostazione predefinita; passando
`recupero=RecuperoPostgres()` si ottiene la versione su Postgres senza toccare
nient'altro della catena. Le risposte delle due versioni sono state confrontate
sulle stesse domande e coincidono nei dati citati.

---

## Installazione

Serve Python 3.10 o superiore.

```bash
git clone https://github.com/<utente>/abetone-rag.git
cd abetone-rag

python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows
source .venv/bin/activate         # macOS e Linux

pip install -r requirements.txt
```

Crea un file `.env` nella radice:

```
ANTHROPIC_API_KEY=sk-ant-...
MODEL_NAME=claude-sonnet-5
DATABASE_URL=postgresql://postgres.<progetto>:<password>@<host>.pooler.supabase.com:5432/postgres
```

La chiave API si ottiene su [console.anthropic.com](https://console.anthropic.com).
Conviene impostare un limite di spesa nella sezione Billing.

`DATABASE_URL` serve solo per la versione su Postgres: con Chroma si può
omettere.

Crea le cartelle dei dati, che non sono nel repository:

```bash
mkdir -p data/raw data/db
```

### Postgres con pgvector (opzionale)

Serve un Postgres raggiungibile con l'estensione `vector` attiva. La via più
breve è un progetto su [Supabase](https://supabase.com), dove l'estensione è già
disponibile.

Nell'editor SQL del pannello:

```sql
create extension if not exists vector;

CREATE TABLE chunk (
    id bigserial PRIMARY KEY,
    testo text NOT NULL,
    metadata jsonb,
    embedding vector(384)
);

alter table chunk enable row level security;

CREATE INDEX ON chunk USING hnsw (embedding vector_cosine_ops);
```

Il `384` è la dimensione dei vettori prodotti dal modello di embedding
configurato: cambiando modello va cambiata anche qui, e l'indice va ricostruito.

Nota sulla stringa di connessione: su reti senza IPv6 la connessione diretta
`db.<progetto>.supabase.co` non si risolve. Va usata quella del **connection
pooler**, che contiene `pooler.supabase.com` e ha l'utente nella forma
`postgres.<idprogetto>`.

## I documenti

`data/raw/` non è versionato. Vanno scaricati a mano i PDF su cui il sistema
deve rispondere. Quelli usati nello sviluppo:

- **Avviso PR FESR Toscana, Sub-Azione 5.2.1.5** — rafforzamento amministrativo
  dei Capofila delle Aree interne (decreto 9550 del 28/04/2026)
- **Linee guida SNAI** — evoluzione del requisito associativo 2021-2027
  (Dipartimento per le politiche di coesione)
- **Contributo CENSIS** — analisi di gruppi omogenei di territori nelle aree
  interne
- **Progetto C3.1 Ludoteche di montagna** — albo pretorio del Comune
- **Avviso mercati rionali** — contributi ai Comuni (decreto 13287 del 10/06/2026)

Requisito: PDF **testuali**, non scansioni. Il sistema lo verifica in fase di
ispezione.

I metadati di ogni documento si dichiarano in
`scripts/ingestione/ingest_tutti.py`.

---

## Uso

### Ingestione dei documenti

```bash
python -m scripts.diagnostica.ispeziona_pdf     # pagine, densità di testo, indici
python -m scripts.ingestione.ingest_tutti       # estrae, pulisce, divide, indicizza
```

L'ingestione scrive su entrambi i vector store. Il primo avvio scarica il
modello di embedding (circa mezzo giga) e lo tiene in cache.

Reindicizzando, Chroma sovrascrive i chunk esistenti perché usa identificativi
deterministici; la tabella `chunk` su Postgres no, perché gli id sono generati
da `bigserial`. Prima di una reindicizzazione completa va svuotata:

```sql
TRUNCATE chunk RESTART IDENTITY;
```

### Dati numerici e catalogo dei bandi

```bash
python -m scripts.tutorial.step4_crea_db        # crea le tabelle e carica i CSV
python -m scripts.interrogazione.db_mostra      # ispeziona il contenuto
```

I CSV in `data/processed/` sono versionati: contengono dati pubblici verificati
a mano, con la fonte e la data di verifica per ogni riga.

### Popolare il catalogo dei bandi

```bash
# scopre quali bandi sono comparsi sul portale
python -m scripts.ingestione.scopri_bandi --promettenti

# estrae un singolo bando, con conferma
python -m scripts.ingestione.estrai_bando <url> <identificativo> --salva-testo

# estrae in sequenza i bandi nuovi, con soglia automatica
python -u -m scripts.ingestione.estrai_nuovi --limite 10
```

L'estrazione è **assistita, non automatica**: ogni campo arriva con un livello
di confidenza e la frase del documento da cui è stato ricavato. I campi critici
(scadenza, ammissibilità del beneficiario) richiedono conferma.

### Interrogare

```bash
python -m scripts.tutorial.step3_verifica "Quali bandi sono aperti per il Comune?"
streamlit run app/app.py
```

L'interfaccia mostra la risposta, il pannello di verifica dei dati citati, e le
fonti navigabili: cliccando su un frammento se ne legge il testo originale.

### Confrontare i due recuperi

```bash
python -m scripts.diagnostica.confronta_recupero
```

Esegue le stesse domande su entrambe le versioni e stampa le risposte affiancate
con l'esito della verifica, per controllare che la scelta del vector store non
cambi i dati citati.

### Collaudare il verificatore

```bash
python -m scripts.diagnostica.test_verifica
```

18 casi, gratuiti e istantanei: non chiamano il modello. Da rilanciare dopo ogni
modifica al verificatore.

---

## Struttura

```
src/
├── config.py              configurazione e profilo dell'ente
├── vectorstore.py         punto unico di accesso a Chroma
├── retrieval.py           recupero ibrido su Chroma (denso + BM25, fusione RRF)
├── pgstore.py             recupero ibrido su Postgres (pgvector + full-text)
├── ingestion/             estrazione e pulizia dei PDF, chunking
├── chains/                catena LCEL e router
├── database/              schema SQLite e repertorio di interrogazioni
├── estrazione/            acquisizione assistita dei bandi dal web
└── verification/          verifica meccanica dei dati citati

scripts/
├── ingestione/            popolamento degli archivi
├── interrogazione/        ricerche dirette sugli archivi
├── diagnostica/           ispezione, confronto, collaudo
└── tutorial/              passaggi di costruzione, in ordine

app/                       interfaccia Streamlit
data/
├── raw/                   PDF originali (non versionati)
├── processed/             CSV dei dati strutturati
└── db/                    Chroma e SQLite (non versionati)
```

In `src/` la logica riusabile, in `scripts/` i punti da cui viene lanciata.

---

## Scelte tecniche, e perché

**Embedding in locale.** Costo zero per indicizzare, e il testo dei documenti
non esce dalla macchina. Verso l'API viaggiano solo la domanda e i frammenti
recuperati, al momento di generare la risposta.

**Niente text-to-SQL.** Il modello non scrive query: sceglie da un repertorio
chiuso di interrogazioni parametriche, scritte e verificate a mano. Una query
generata liberamente può essere sbagliata in modi difficili da accorgersene, e
produrrebbe un numero plausibile e falso.

**Lo stato di un bando si calcola, non si memorizza.** Un campo "aperto/chiuso"
sarebbe vecchio il giorno dopo. Nella scansione iniziale, **84 bandi su 136**
dichiarati aperti dal portale regionale risultavano scaduti leggendone il testo:
alcuni dal 2013.

**I metadati delle fonti non sono affidabili.** Campi strutturati che
contraddicono il testo, stati mai aggiornati, date di rendicontazione presentate
come scadenze di presentazione. L'estrattore è istruito a fidarsi del testo e a
segnalare la discrepanza.

**Postgres con pgvector accanto a Chroma.** Chroma è un file su disco: va bene
in locale, non dove il filesystem è effimero. Postgres tiene vettori e dati
numerici nello stesso sistema, la ricerca lessicale diventa nativa invece che
ricostruita in memoria a ogni avvio, e i filtri sui metadati sono SQL invece di
una sintassi a dizionario. Il costo è una dipendenza esterna, ed è il motivo per
cui Chroma resta disponibile.

**Il recupero è un'interfaccia, non un'implementazione.** La catena chiede
`recupero.cerca(domanda, k=k)` e riceve una lista di tuple: non sa quale vector
store ci sia sotto. Sostituirne uno costa una riga.

---

## Limiti

Vale la pena elencarli con la stessa precisione di ciò che il sistema fa.

- **Non garantisce la completezza.** Il verificatore controlla che i dati citati
  esistano nella fonte; non può sapere cosa è stato omesso.
- **Il verificatore controlla quantità e riferimenti normativi.** Una risposta
  fatta di soli nomi propri passa senza rilievi, perché non contiene nulla di
  misurabile.
- **Non sa quali documenti dovrebbe avere.** Risponde solo su ciò che è in
  archivio, e lo dichiara quando non basta.
- **L'estrazione è assistita.** I campi critici richiedono lettura umana delle
  prove: è la condizione a cui i valori risultano affidabili.
- **I dati si aggiornano a mano.** Ogni riga porta la data in cui è stata
  verificata.
- **Le scadenze post-aggiudicazione non sono gestite.** Rendicontazioni, SAL,
  relazioni periodiche: il sistema le legge nei documenti ma non le traccia.
- **La ricerca lessicale su Postgres unisce i termini con OR.** Trova sempre
  qualcosa, ma può promuovere un frammento che ripete un termine comune senza
  essere pertinente. BM25 pesa i termini per rarità e su questo si comporta
  meglio.

## Stato

Prototipo funzionante, sviluppato come progetto di apprendimento e portfolio.
Non è un prodotto: non è in produzione, non ha autenticazione, e i dati vanno
verificati prima di essere usati in un atto amministrativo.

## Licenza

MIT.

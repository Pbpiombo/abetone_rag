"""STEP 0 - verifica che ambiente, chiave API e chain LCEL funzionino."""

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.config import MODEL_NAME

# 1. IL PROMPT
prompt = ChatPromptTemplate.from_messages([
    ("system",
     "Sei un assistente tecnico per la Pubblica Amministrazione italiana, "
     "esperto di programmazione territoriale di piccoli comuni montani. "
     "Rispondi in italiano, in modo conciso e concreto."),
    ("human", "{domanda}"),
])

# 2. IL MODELLO
model = ChatAnthropic(
    model=MODEL_NAME,
    max_tokens=1024,
    timeout=60,
)

# 3. IL PARSER
parser = StrOutputParser()

# 4. LA CHAIN
chain = prompt | model | parser


def main():
    domanda = (
        "In due frasi: cos'e' la Strategia Nazionale per le Aree Interne "
        "e perche' e' rilevante per un comune dell'Appennino pistoiese?"
    )

    print("\n--- DOMANDA ---")
    print(domanda)
    print("\n--- RISPOSTA ---")

    for pezzo in chain.stream({"domanda": domanda}):
        print(pezzo, end="", flush=True)

    print("\n\nSTEP 0 OK: ambiente, chiave e chain funzionanti.")


if __name__ == "__main__":
    main()
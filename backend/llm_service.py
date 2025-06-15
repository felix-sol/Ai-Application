import os
from openai import OpenAI
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus der .env-Datei.
# Dies sollte einmal am Start deines Programms (oder im Backend-Framework) aufgerufen werden.
# Für Tests in dieser Datei kann es hier stehen bleiben.
load_dotenv()

def get_llm_response(user_question: str, system_prompt: str = "You are a helpful assistant", context: str = "") -> str:
    """
    Sendet eine Anfrage an das GWDG LLM und gibt die Antwort zurück.
    Integriert optional einen Kontext für Retrieval Augmented Generation (RAG).

    Args:
        user_question (str): Die Frage des Benutzers an das LLM.
        system_prompt (str): Der System-Prompt, der das Verhalten des Assistenten definiert.
        context (str): Optionaler Textkontext, der für RAG verwendet werden soll (z.B. aus einem PDF-Abschnitt).

    Returns:
        str: Die generierte Antwort des LLM.
        Raises ValueError: Wenn der API-Schlüssel nicht gefunden wird.
        Handles other Exceptions: Gibt eine Fehlermeldung zurück, wenn die API-Anfrage fehlschlägt.
    """
    api_key = os.getenv("GWDG_LLM_API_KEY")
    if not api_key:
        print("Fehler: GWDG_LLM_API_KEY Umgebungsvariable nicht gesetzt!")
        # Im echten Backend würde man hier eine HTTP-Fehlerantwort zurückgeben
        raise ValueError("API-Schlüssel für LLM-Dienst fehlt. Bitte GWDG_LLM_API_KEY Umgebungsvariable setzen.")

    client = OpenAI(
        api_key = api_key,
        base_url = "https://chat-ai.academiccloud.de/v1"
    )
    model = "meta-llama-3.1-8b-instruct"

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # Wenn Kontext vorhanden ist, fügen wir ihn in den User-Prompt ein (RAG-Muster)
    if context:
        messages.append({"role": "user", "content": f"Basierend auf dem folgenden Textabschnitt:\n\n{context}\n\nAntworte auf die Frage: {user_question}"})
    else:
        messages.append({"role": "user", "content": user_question})

    try:
        chat_completion = client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=0.0 # Für faktische Antworten oft gut 0.0 oder niedrige Werte
            # Weitere Parameter können hier hinzugefügt werden (z.B. max_tokens)
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Fehler bei der LLM-Anfrage: {e}")
        return "Entschuldigung, es gab ein Problem bei der Kommunikation mit dem KI-Modell."

# Dieser Block wird nur ausgeführt, wenn die Datei direkt gestartet wird (nicht, wenn sie importiert wird)
if __name__ == "__main__":
    print("--- Experiment 1: Einfache Frage ---")
    response_exp1 = get_llm_response(
        user_question="Was ist die Hauptstadt von Frankreich?",
        system_prompt="Du bist ein Geographie-Experte."
    )
    print(f"LLM Antwort: {response_exp1}")

    print("\n--- Experiment 2: Andere Rolle ---")
    response_exp2 = get_llm_response(
        user_question="Erzähl mir einen kurzen Witz.",
        system_prompt="Du bist ein Comedian."
    )
    print(f"LLM Antwort: {response_exp2}")

    print("\n--- Experiment 3: RAG mit neuem Kontext ---")
    mein_neuer_kontext = (
        "Die Firma GreenSolutions hat im letzten Jahr ihre CO2-Emissionen um 15% gesenkt. "
        "Sie haben 2023 insgesamt 500 Tonnen CO2 ausgestoßen. "
        "Ihr Ziel für 2024 ist eine weitere Reduktion um 10% durch den Einsatz erneuerbarer Energien."
    )
    response_exp3 = get_llm_response(
        user_question="Wie viel CO2 hat GreenSolutions 2023 ausgestoßen und was ist ihr Ziel für 2024?",
        system_prompt="Du bist ein Analyst für Nachhaltigkeitsberichte und fasst Fakten prägnant zusammen.",
        context=mein_neuer_kontext
    )
    print(f"LLM Antwort: {response_exp3}")
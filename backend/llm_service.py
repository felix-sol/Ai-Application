import os
from openai import OpenAI
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus der .env-Datei.
load_dotenv()

def get_llm_response(user_question: str, system_prompt: str = "You are a helpful assistant", context: str = "") -> str:
    """
    Sendet eine Anfrage an das GWDG LLM und gibt die Antwort zurück.
    Unterstützt optional Retrieval Augmented Generation (RAG) durch Kontextübergabe.

    Args:
        user_question (str): Die Benutzerfrage.
        system_prompt (str): Der System-Prompt zur Steuerung des LLM-Verhaltens.
        context (str): Optionaler Kontext (z. B. ein Dokumentenausschnitt).

    Returns:
        str: Die LLM-Antwort.
    """
    api_key = os.getenv("SAIA_API_KEY")
    if not api_key:
        raise ValueError("API-Schlüssel für den LLM-Dienst fehlt. Bitte GWDG_LLM_API_KEY als Umgebungsvariable setzen.")

    client = OpenAI(
        api_key=api_key,
        base_url="https://chat-ai.academiccloud.de/v1"
    )
    model = "meta-llama-3.1-8b-instruct"

    messages = [{"role": "system", "content": system_prompt}]

    if context:
        user_content = (
            f"Berücksichtige den folgenden Kontext:\n\n"
            f"{context}\n\n"
            f"Frage: {user_question}"
        )
    else:
        user_content = user_question

    messages.append({"role": "user", "content": user_content})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Fehler bei der LLM-Anfrage: {e}")
        return "Entschuldigung, es gab ein Problem bei der Kommunikation mit dem KI-Modell."
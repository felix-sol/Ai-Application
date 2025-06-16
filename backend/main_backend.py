# Testskript für Backend-Logik. Später vielleicht löschen wenn alles über app.py


import os
from llm_service import get_llm_response # LLM-Service Funktion
from pdf_processing import read_pdf, split_text_into_sections # PDF-Funktionen

# Die .env-Datei laden.
# In einem echten Web-Framework (Flask/FastAPI) würde dies beim Start der Anwendung geschehen.
from dotenv import load_dotenv
load_dotenv()

# --- Kernlogik des Backends (simuliert) ---
def process_pdf_chat(pdf_file_path: str, user_question: str) -> str:
    """
    Simuliert den End-to-End-Prozess: PDF lesen, Text splitten,
    relevanten Kontext an LLM senden und Antwort erhalten.

    :param pdf_file_path: Pfad zur hochgeladenen PDF-Datei
    :param user_question: Die Frage des Benutzers
    :return: Die Antwort des LLM
    """
    print(f"\n--- Verarbeite PDF-Chat für Frage: '{user_question}' ---")

    # 1. PDF-Inhalt lesen
    print(f"Schritt 1: Lese PDF von '{pdf_file_path}'...")
    full_pdf_text = read_pdf(pdf_file_path)

    if not full_pdf_text:
        return "Entschuldigung, konnte das PDF nicht lesen oder es ist leer."

    # 2. PDF-Inhalt in Chunks aufteilen
    # Die max_length muss ggf. angepasst werden (Tokens vs Zeichen)
    print("Schritt 2: Teile PDF-Inhalt in Abschnitte auf...")
    # Hier vorhandene Funktion zum Splitten nutzen
    text_chunks = split_text_into_sections(full_pdf_text, max_length=1000) # max_length anpassen!
    print(f"Erstellt {len(text_chunks)} Textabschnitte.")

    # --- Retrieval: Hier zukünftige Verbesserungen ---
    # Im Moment senden wir alel Chunks als Kontext an das LLM.
    # Das funktioniert nur bei kleinen PDFs.
    # Später hier eine Vektorsuche implementieren,
    # um nur die relevantesten Chunks zu finden!

    # Kombiniere alle Chunks zu einem großen Kontext-String
    # Auf das Token-Limit des LLM achten! Hier könnte es schnell überlaufen.
    context_for_llm = "\n\n".join(text_chunks)

    # Optionale Überprüfung des Kontext-Limits (sehr rudimentär)
    # Wenn der Kontext extrem lang ist, muss er für den Test abgeschnitten werden,
    # damit die API nicht fehlschlägt. Im späteren RAG anders.
    # Die GWDG LLMs basieren auf Llama 3.1 8B, das ca. 8k Kontext hat.
    # 1 Token ~ 4 Zeichen
    # 8000 Tokens * 4 Zeichen/Token = 32000 Zeichen (max. Kontext)
    MAX_CONTEXT_CHAR_LIMIT = 20000 # Erstmal klein um nicht zu überlaufen
    if len(context_for_llm) > MAX_CONTEXT_CHAR_LIMIT:
        print(f"Warnung: Kontext ist mit {len(context_for_llm)} Zeichen sehr lang. Kürze für Test.")
        context_for_llm = context_for_llm[:MAX_CONTEXT_CHAR_LIMIT] + "\n\n[Kontext gekürzt aufgrund der Länge...]"


    # 3. LLM-Service aufrufen mit Kontext
    print("Schritt 3: Sende Frage mit Kontext an das LLM...")
    llm_answer = get_llm_response(
        user_question=user_question,
        system_prompt="Du bist ein KI-Assistent, der Fragen basierend auf den bereitgestellten Dokumenten beantwortet. Antworte präzise und nur mit Informationen aus dem Dokument, falls zutreffend.",
        context=context_for_llm
    )
    print("Schritt 4: Antwort vom LLM erhalten.")
    return llm_answer

# --- Testblock für manuelle Ausführung des Haupt-Backends ---
if __name__ == "__main__":
    print("--- Simulierter Haupt-Backend-Start ---")

    # Muss eine Test-PDF-Datei in diesem Verzeichnis existiert.

    sample_pdf_path = "seminar_info.pdf" # Namen an Test-PDF anpassen.

    # Dummy-PDF Erstellung (optional, nur zum schnellen Testen, falls keine echte PDF da ist)
    if not os.path.exists(sample_pdf_path):
        print(f"Erstelle Dummy-PDF '{sample_pdf_path}' für Testzwecke...")
        try:
            from reportlab.pdfgen import canvas
            c = canvas.Canvas(sample_pdf_path)
            c.drawString(100, 750, "Dies ist ein Testdokument über Nachhaltigkeit.")
            c.drawString(100, 730, "Im Jahr 2023 hat das Unternehmen X seine CO2-Emissionen um 10% reduziert.")
            c.drawString(100, 710, "Ziel für 2024 ist eine weitere Reduktion um 5% durch Investitionen in erneuerbare Energien.")
            c.save()
            print(f"Dummy-PDF '{sample_pdf_path}' erfolgreich erstellt (benötigt ReportLab).")
        except ImportError:
            print("Warnung: ReportLab ist nicht installiert. Bitte stelle manuell eine")
            print(f"Test-PDF-Datei namens '{sample_pdf_path}' im 'backend'-Ordner bereit.")
            print("Du kannst die Seminarfolien als PDF speichern und hierher kopieren. ")


    # Testfall 1: Normale Frage an das simulierte Backend
    if os.path.exists(sample_pdf_path):
        print("\n--- Testfall 1: Frage zu Testdokument ---")
        question1 = "Wie hoch waren die CO2-Emissionen 2023 und das Ziel für 2024 laut Dokument?"
        response1 = process_pdf_chat(sample_pdf_path, question1)
        print(f"\nAntwort des KI-Assistenten (Testfall 1):\n{response1}")

        # Testfall 2: Eine andere Frage zum Dokument
        print("\n--- Testfall 2: Frage nach Reduktionsmaßnahmen ---")
        question2 = "Welche Maßnahmen plant das Unternehmen für 2024 zur Reduktion?"
        response2 = process_pdf_chat(sample_pdf_path, question2)
        print(f"\nAntwort des KI-Assistenten (Testfall 2):\n{response2}")
    else:
        print(f"\nSkippe Backend-Tests: Test-PDF '{sample_pdf_path}' nicht gefunden.")

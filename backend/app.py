from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import uuid # Zum Generieren eindeutiger Dateinamen
from flask_cors import CORS

# Importiere die bereits erstellten Logik-Module
from pdf_processing import read_pdf, split_text_into_sections
from llm_service import get_llm_response

# Lade Umgebungsvariablen aus der .env-Datei (für den OpenAI-API-Key)
load_dotenv()

app = Flask(__name__)
CORS(app)

# --- Konfiguration ---
# Ordner zum Speichern der hochgeladenen PDFs
UPLOAD_FOLDER = 'uploaded_pdfs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Erstellt den Ordner, falls er nicht existiert

# Maximale Größe des Kontextes, der an das LLM gesendet wird (in Zeichen)
# Wichtig: Das ist ein *Zeichen*-Limit, keine *Token*-Limit.
# Ein Token ist ca. 4 Zeichen. GWDG LLM hat ca. 8k Token Limit.
# 8000 Tokens * 4 Zeichen/Token = 32000 Zeichen.
# Wir setzen es etwas niedriger, um Puffer zu haben und Überschreitungen zu vermeiden.
MAX_CONTEXT_CHAR_LIMIT = 28000 # Anpassbar je nach LLM-Kontextfenster und Test
# max_length für split_text_into_sections sollte passend sein, z.B. 1000-2000
# Du kannst split_text_into_sections(full_pdf_text, max_length=2000) verwenden, wenn die Chunks größer sein dürfen

# Eine einfache In-Memory-Speicherung für PDF-Inhalte/Chunks für die Demo
# In einer echten Anwendung würde man hier eine Datenbank (z.B. Vektordatenbank) verwenden
# Speichert den vollen Text des PDFs unter seiner ID
pdf_contents_cache = {} 

# --- API-Endpunkte ---

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    print("Received PDF upload request.")
    # Überprüfe, ob eine Datei im Request ist
    if 'pdf_file' not in request.files:
        print("Error: No 'pdf_file' part in the request.")
        return jsonify({"error": "No pdf_file part in the request"}), 400

    pdf_file = request.files['pdf_file']

    # Überprüfe, ob ein Dateiname vorhanden ist
    if pdf_file.filename == '':
        print("Error: No selected file.")
        return jsonify({"error": "No selected file"}), 400

    # Überprüfe, ob es eine PDF-Datei ist (einfache Prüfung)
    if not pdf_file.filename.lower().endswith('.pdf'):
        print(f"Error: Invalid file type '{pdf_file.filename}'. Only PDF allowed.")
        return jsonify({"error": "Invalid file type. Only PDF allowed."}), 400

    if pdf_file:
        # Erstelle einen eindeutigen Dateinamen, um Kollisionen zu vermeiden
        # Speichere die Datei temporär im UPLOAD_FOLDER
        file_extension = os.path.splitext(pdf_file.filename)[1]
        unique_filename = str(uuid.uuid4()) + file_extension
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

        try:
            pdf_file.save(file_path)
            print(f"PDF saved to {file_path}")

            # Lese den Inhalt des PDFs direkt nach dem Speichern
            full_pdf_text = read_pdf(file_path)
            if not full_pdf_text:
                os.remove(file_path) # Lösche die Datei, wenn sie nicht gelesen werden kann
                print(f"Error: Could not read content from PDF {file_path}.")
                return jsonify({"error": "Could not read content from PDF"}), 500

            # Speichere den extrahierten Text im Cache unter der eindeutigen ID
            pdf_contents_cache[unique_filename] = full_pdf_text
            print(f"PDF content for '{unique_filename}' stored in cache (length: {len(full_pdf_text)} chars).")

            return jsonify({
                "message": "PDF uploaded and processed",
                "pdf_id": unique_filename,
                "filename": pdf_file.filename # Optional: Originaldateiname zurückgeben
            }), 200
        except Exception as e:
            print(f"Error processing PDF upload: {e}")
            return jsonify({"error": f"Server error during PDF processing: {str(e)}"}), 500

@app.route('/chat', methods=['POST'])
def chat_with_pdf():
    print("Received chat request.")
    data = request.json
    user_question = data.get('question')
    pdf_id = data.get('pdf_id') # Die ID des zuvor hochgeladenen PDFs

    if not user_question or not pdf_id:
        print("Error: Missing 'question' or 'pdf_id' in chat request.")
        return jsonify({"error": "Missing 'question' or 'pdf_id'"}), 400

    # Lade den PDF-Inhalt aus dem Cache (oder einer Vektordatenbank in echter App)
    full_pdf_text = pdf_contents_cache.get(pdf_id)
    if not full_pdf_text:
        print(f"Error: PDF content for ID '{pdf_id}' not found in cache.")
        return jsonify({"error": "PDF content not found. Please upload the PDF again."}), 404

    print(f"Verarbeite Chat-Anfrage für PDF '{pdf_id}' mit Frage '{user_question}'")

    # Teile den PDF-Inhalt in Abschnitte (Chunks)
    # Die max_length kann hier angepasst werden.
    # Wichtig: Die split_text_into_sections Funktion operiert auf Zeichen.
    text_chunks = split_text_into_sections(full_pdf_text, max_length=1500) # Beispiel: etwas größere Chunks

    # --- Retrieval (Abruf): Für die Demo alle Chunks als Kontext ---
    # Dies ist der einfachste Ansatz. Für große PDFs oder komplexere Fragen
    # müsste hier eine Vektorsuche (Embeddings + Vektordatenbank) implementiert werden,
    # um nur die relevantesten Chunks zu finden.

    # Füge die Chunks zu einem großen Kontextstring zusammen
    context_for_llm = "\n\n".join(text_chunks)

    # Kürze den Kontext, falls er zu lang ist, um das Token-Limit des LLM nicht zu überschreiten
    if len(context_for_llm) > MAX_CONTEXT_CHAR_LIMIT:
        print(f"Warnung: Kontext ist mit {len(context_for_llm)} Zeichen sehr lang. Kürze ihn.")
        context_for_llm = context_for_llm[:MAX_CONTEXT_CHAR_LIMIT] + "\n\n[Kontext gekürzt aufgrund der Länge...]"

    # Rufe deine LLM-Service Funktion auf
    try:
        llm_answer = get_llm_response(
            user_question=user_question,
            system_prompt="Du bist ein KI-Assistent, der Fragen präzise und wahrheitsgemäß basierend auf dem bereitgestellten Dokument beantwortet. Beschränke deine Antworten auf die Informationen im Dokument. Wenn die Antwort nicht im Dokument ist, sage das.",
            context=context_for_llm
        )
        print("Antwort vom LLM erhalten.")
        return jsonify({"answer": llm_answer}), 200
    except Exception as e:
        print(f"Error calling LLM service: {e}")
        return jsonify({"error": f"Fehler bei der Kommunikation mit dem KI-Modell: {str(e)}"}), 500

# --- Server starten ---
if __name__ == '__main__':
    print("Starting Flask backend server...")
    # debug=True: Aktiviert den Debug-Modus (gut für Entwicklung, NICHT für Produktion)
    # host='0.0.0.0': Erlaubt Verbindungen von außen (wichtig, wenn Frontend nicht auf localhost läuft)
    # port=5000: Der Port, auf dem der Server lauscht
    app.run(debug=True, host='0.0.0.0', port=5000)

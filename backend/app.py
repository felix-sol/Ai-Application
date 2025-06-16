from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import uuid
from flask_cors import CORS # Wichtig für Frontend-Kommunikation

# Importiere deine bereits erstellten Logik-Module
from pdf_processing import read_pdf, split_text_into_sections
from llm_service import get_llm_response

# NEUE IMPORTE FÜR EMBEDDINGS UND VECTOR STORE
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA # Optional: Später für komplexere RAG Chains

load_dotenv()

app = Flask(__name__)
CORS(app) # CORS für alle Routen aktivieren

# --- Konfiguration ---
UPLOAD_FOLDER = 'uploaded_pdfs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Ordner für die persistente Speicherung der ChromaDB-Daten
# Dieser Ordner wird die Embeddings und Metadaten enthalten.
VECTOR_DB_DIR = "chroma_db_data"
os.makedirs(VECTOR_DB_DIR, exist_ok=True)

# Maximale Größe des Kontextes, der an das LLM gesendet wird (in Zeichen)
# GWDG LLM hat ca. 8k Token Limit (1 Token ~ 4 Zeichen), also ca. 32000 Zeichen.
MAX_CONTEXT_CHAR_LIMIT = 28000 

# --- Initialisiere den Embedding-Service global ---
# Stelle sicher, dass dein OPENAI_API_KEY in deiner .env Datei gesetzt ist!
# Wenn du ein GWDG-Modell mit OpenAI-Kompatibilität nutzt, kannst du hier auch
# eine 'base_url' angeben. Beispiel:
# embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_base="https://api.gwdg.de/...")
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")

# In-Memory Cache für die geladenen Vector Stores.
# Für eine persistente Anwendung ist dies essentiell, um nicht jedes Mal die DB neu aufzubauen.
vector_stores_cache = {} 

# --- Hilfsfunktion, um ChromaDB zu laden oder neu zu erstellen ---
def get_or_create_vector_store(pdf_id: str, text_chunks: list[str] = None):
    if pdf_id in vector_stores_cache:
        print(f"ChromaDB collection '{pdf_id}' aus Cache geladen.")
        return vector_stores_cache[pdf_id]

    # Versuche, die Sammlung von der Festplatte zu laden
    try:
        # Wichtig: persist_directory und collection_name müssen dieselben sein wie beim Erstellen
        vector_store = Chroma(
            persist_directory=VECTOR_DB_DIR,
            embedding_function=embeddings,
            collection_name=pdf_id
        )
        # Eine kleine Abfrage, um zu prüfen, ob die Sammlung wirklich Daten enthält
        if vector_store._collection.count() > 0:
            vector_stores_cache[pdf_id] = vector_store
            print(f"ChromaDB collection '{pdf_id}' von Festplatte geladen.")
            return vector_store
        else:
            print(f"ChromaDB collection '{pdf_id}' auf Festplatte gefunden, aber leer. Neuaufbau nötig.")
            raise ValueError("Collection empty, needs rebuild.")
    except Exception as e:
        print(f"Konnte ChromaDB collection '{pdf_id}' nicht laden: {e}")
        # Wenn nicht geladen werden kann und text_chunks bereitgestellt wurden, neu erstellen
        if text_chunks:
            print(f"Erstelle neue ChromaDB collection '{pdf_id}'.")
            vector_store = Chroma.from_texts(
                texts=text_chunks,
                embedding=embeddings,
                collection_name=pdf_id,
                persist_directory=VECTOR_DB_DIR
            )
            vector_store.persist()
            vector_stores_cache[pdf_id] = vector_store
            print(f"ChromaDB collection '{pdf_id}' neu erstellt und gespeichert.")
            return vector_store
        else:
            raise Exception(f"Vector store für '{pdf_id}' nicht gefunden und keine Text-Chunks zum Erstellen bereitgestellt.")


# --- API-Endpunkte ---

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    print("Received PDF upload request.")
    if 'pdf_file' not in request.files:
        print("Error: No 'pdf_file' part in the request.")
        return jsonify({"error": "No pdf_file part in the request"}), 400

    pdf_file = request.files['pdf_file']
    if pdf_file.filename == '':
        print("Error: No selected file.")
        return jsonify({"error": "No selected file"}), 400

    if not pdf_file.filename.lower().endswith('.pdf'):
        print(f"Error: Invalid file type '{pdf_file.filename}'. Only PDF allowed.")
        return jsonify({"error": "Invalid file type. Only PDF allowed."}), 400

    if pdf_file:
        file_extension = os.path.splitext(pdf_file.filename)[1]
        unique_filename = str(uuid.uuid4()) + file_extension
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

        try:
            pdf_file.save(file_path)
            print(f"PDF saved to {file_path}")

            full_pdf_text = read_pdf(file_path)
            if not full_pdf_text:
                os.remove(file_path)
                print(f"Error: Could not read content from PDF {file_path}.")
                return jsonify({"error": "Could not read content from PDF"}), 500

            text_chunks = split_text_into_sections(full_pdf_text)
            if not text_chunks:
                os.remove(file_path)
                print("Error: No text chunks generated from PDF.")
                return jsonify({"error": "Could not process PDF content into usable chunks."}), 500

            # NEU: Erstelle oder lade den Vector Store für diese PDF
            try:
                vector_store = get_or_create_vector_store(unique_filename, text_chunks)
                print(f"PDF content embedded and stored in ChromaDB collection '{unique_filename}' with {len(text_chunks)} chunks.")
            except Exception as e:
                print(f"Error handling ChromaDB for {unique_filename}: {e}")
                os.remove(file_path) # Lösche die Datei, wenn die DB-Erstellung fehlschlägt
                return jsonify({"error": f"Failed to process PDF for search: {str(e)}"}), 500

            return jsonify({
                "message": "PDF uploaded, processed and embedded",
                "pdf_id": unique_filename,
                "filename": pdf_file.filename
            }), 200
        except Exception as e:
            print(f"Error processing PDF upload: {e}")
            # Füge hier auch spezifischere Fehlerbehandlung hinzu, z.B. für API-Fehler bei Embeddings
            return jsonify({"error": f"Server error during PDF processing: {str(e)}"}), 500

@app.route('/chat', methods=['POST'])
def chat_with_pdf():
    print("Received chat request.")
    data = request.json
    user_question = data.get('question')
    pdf_id = data.get('pdf_id')

    if not user_question or not pdf_id:
        print("Error: Missing 'question' or 'pdf_id' in chat request.")
        return jsonify({"error": "Missing 'question' or 'pdf_id'"}), 400

    # Lade den Vector Store für diese PDF-ID
    try:
        vector_store = get_or_create_vector_store(pdf_id)
    except Exception as e:
        print(f"Error retrieving vector store for ID '{pdf_id}': {e}")
        return jsonify({"error": "PDF content not found or could not be loaded. Please upload the PDF again."}), 404

    print(f"Verarbeite Chat-Anfrage für PDF '{pdf_id}' mit Frage '{user_question}'")

    # NEU: Relevante Chunks aus der Vektordatenbank abrufen
    # 'k' ist die Anzahl der relevantesten Chunks, die abgerufen werden sollen.
    # Experimentiere mit diesem Wert für optimale Ergebnisse.
    retrieved_docs = vector_store.similarity_search(user_question, k=5)

    context_for_llm = "\n\n".join([doc.page_content for doc in retrieved_docs])

    if not context_for_llm.strip():
        print("Keine relevanten Dokumente für die Frage gefunden.")
        return jsonify({"answer": "Leider konnte ich im Dokument keine relevanten Informationen zu Ihrer Frage finden."}), 200

    if len(context_for_llm) > MAX_CONTEXT_CHAR_LIMIT:
        print(f"Warnung: Abgerufener Kontext ist mit {len(context_for_llm)} Zeichen immer noch lang. Kürze ihn.")
        context_for_llm = context_for_llm[:MAX_CONTEXT_CHAR_LIMIT] + "\n\n[Kontext gekürzt aufgrund der Länge...]"
    else:
        print(f"Kontextlänge an LLM: {len(context_for_llm)} Zeichen.")

    try:
        llm_answer = get_llm_response(
            user_question=user_question,
            system_prompt="Du bist ein KI-Assistent, der Fragen präzise und wahrheitsgemäß basierend auf dem bereitgestellten Dokument beantwortet. Beschränke deine Antworten auf die Informationen im Dokument. Wenn die Antwort nicht im Dokument ist, sage das klar und deutlich. Wenn du keine relevanten Informationen hast, sage das ebenfalls.",
            context=context_for_llm
        )
        print("Antwort vom LLM erhalten.")
        return jsonify({"answer": llm_answer}), 200
    except Exception as e:
        print(f"Error calling LLM service: {e}")
        # Detailliertere Fehlerbehandlung, z.B. bei API-Key-Problemen oder Rate Limits
        return jsonify({"error": f"Fehler bei der Kommunikation mit dem KI-Modell: {str(e)}"}), 500

if __name__ == '__main__':
    print("Starting Flask backend server...")
    # Lade beim Start alle persistenten ChromaDB-Sammlungen in den Cache (optional, für schnellere Starts)
    # Dies ist nur ein Beispiel und für sehr viele PDFs nicht effizient.
    # Eine bessere Lösung wäre, Sammlungen bei Bedarf zu laden.
    # Aber für eine überschaubare Anzahl an Test-PDFs ist es OK.
    for collection_name in os.listdir(VECTOR_DB_DIR):
        # Prüfe, ob es sich wirklich um einen ChromaDB-Ordner handelt
        if os.path.isdir(os.path.join(VECTOR_DB_DIR, collection_name)):
            try:
                get_or_create_vector_store(collection_name)
            except Exception as e:
                print(f"Konnte persistente ChromaDB Sammlung '{collection_name}' nicht beim Start laden: {e}")

    app.run(debug=True, host='00.0.0', port=5000)
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import traceback
from flask import Flask, request, jsonify
from flask import send_from_directory
from dotenv import load_dotenv
import os
import uuid
from flask_cors import CORS 
from pdf_processing import read_pdf, split_text_into_sections
from llm_service import get_llm_response
from langchain_community.vectorstores import Chroma
from embeddingWrapper import SAIAEmbeddings
import shutil
import chromadb



app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploaded_pdfs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

VECTOR_DB_DIR = "chroma_db_data"
os.makedirs(VECTOR_DB_DIR, exist_ok=True)

JSON_OUTPUT_FOLDER = 'extracted_jsons'
os.makedirs(JSON_OUTPUT_FOLDER, exist_ok=True)

MAX_CONTEXT_CHAR_LIMIT = 28000


load_dotenv()
api_key = os.getenv("SAIA_API_KEY")

if not api_key:
    raise ValueError("API Key nicht gefunden! Bitte in .env setzen.")

embeddings = SAIAEmbeddings(api_key)

vector_stores_cache = {}

def get_or_create_vector_store(pdf_id: str, text_chunks: list[str] = None):
    if pdf_id in vector_stores_cache:
        print(f"ChromaDB collection '{pdf_id}' aus Cache geladen.")
        return vector_stores_cache[pdf_id]

    try:
        vector_store = Chroma(
            persist_directory=VECTOR_DB_DIR,
            embedding_function=embeddings,
            collection_name=pdf_id
        )

        if vector_store._collection.count() > 0:
            vector_stores_cache[pdf_id] = vector_store
            print(f"ChromaDB collection '{pdf_id}' von Festplatte geladen.")
            return vector_store
        else:
            print(f"ChromaDB collection '{pdf_id}' auf Festplatte gefunden, aber leer. Neuaufbau nötig.")
            raise ValueError("Collection empty, needs rebuild.")
    except Exception as e:
        print(f"Konnte ChromaDB collection '{pdf_id}' nicht laden: {e}")
        traceback.print_exc()
        if text_chunks:
            try:
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
            except Exception as inner_e:
                print(f"Fehler beim Erstellen neuer ChromaDB collection: {inner_e}")
                traceback.print_exc()
                raise inner_e
        else:
            raise Exception(f"Vector store für '{pdf_id}' nicht gefunden und keine Text-Chunks zum Erstellen bereitgestellt.")
        
@app.route('/static_pdfs/<filename>')
def serve_pdf(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)         

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    print("Received PDF upload request.")
    if 'pdf_file' not in request.files:
        return jsonify({"error": "No pdf_file part in the request"}), 400

    pdf_file = request.files['pdf_file']
    if pdf_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if not pdf_file.filename.lower().endswith('.pdf'):
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
                return jsonify({"error": "Could not read content from PDF"}), 500

            text_chunks = split_text_into_sections(full_pdf_text)
            if not text_chunks:
                os.remove(file_path)
                return jsonify({"error": "Could not process PDF content into usable chunks."}), 500

            try:
                vector_store = get_or_create_vector_store(unique_filename, text_chunks)
                print(f"PDF content embedded and stored in ChromaDB collection '{unique_filename}' with {len(text_chunks)} chunks.")
            except Exception as e:
                print(f"Error handling ChromaDB for {unique_filename}: {e}")
                traceback.print_exc()
                os.remove(file_path)
                return jsonify({"error": f"Failed to process PDF for search: {str(e)}"}), 500

            return jsonify({
                "message": "PDF uploaded, processed and embedded",
                "filename": pdf_file.filename,
                "pdf_url": f"http://localhost:5000/static_pdfs/{unique_filename}"
            }), 200
        except Exception as e:
            print(f"Server error during PDF processing: {e}")
            traceback.print_exc()
            return jsonify({"error": f"Server error during PDF processing: {str(e)}"}), 500

@app.route('/chat', methods=['POST'])
def chat_with_pdf():
    print("Received chat request.")
    data = request.json
    user_question = data.get('question')
    pdf_id = data.get('pdf_id')

    if not user_question or not pdf_id:
        return jsonify({"error": "Missing 'question' or 'pdf_id'"}), 400

    try:
        vector_store = get_or_create_vector_store(pdf_id)
    except Exception as e:
        print(f"Error loading vector store for PDF {pdf_id}: {e}")
        traceback.print_exc()
        return jsonify({"error": "PDF content not found or could not be loaded. Please upload the PDF again."}), 404

    print(f"Verarbeite Chat-Anfrage für PDF '{pdf_id}' mit Frage '{user_question}'")

    retrieved_docs = vector_store.similarity_search(user_question, k=5)

    context_for_llm = "\n\n".join([doc.page_content for doc in retrieved_docs])

    if not context_for_llm.strip():
        return jsonify({"answer": "Leider konnte ich im Dokument keine relevanten Informationen zu Ihrer Frage finden."}), 200

    if len(context_for_llm) > MAX_CONTEXT_CHAR_LIMIT:
        context_for_llm = context_for_llm[:MAX_CONTEXT_CHAR_LIMIT] + "\n\n[Kontext gekürzt aufgrund der Länge...]"
    else:
        print(f"Kontextlänge an LLM: {len(context_for_llm)} Zeichen.")

    try:
        llm_answer = get_llm_response(
            user_question=user_question,
            system_prompt="Du bist ein KI-Assistent, der Fragen präzise und wahrheitsgemäß basierend auf dem bereitgestellten Dokument beantwortet. Beschränke deine Antworten auf die Informationen im Dokument. Wenn die Antwort nicht im Dokument ist, sage das klar und deutlich. Wenn du keine relevanten Informationen hast, sage das ebenfalls.",
            context=context_for_llm
        )
        return jsonify({"answer": llm_answer}), 200
    except Exception as e:
        print(f"Fehler bei der Kommunikation mit dem KI-Modell: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Fehler bei der Kommunikation mit dem KI-Modell: {str(e)}"}), 500
    
# PDF und zugehörige ChromaDB-Sammlung löschen:
@app.route('/delete_pdf/<pdf_id>', methods=['DELETE'])
def delete_pdf(pdf_id):
    print(f"Received delete request for PDF ID: {pdf_id}")

    pdf_file_path = os.path.join(UPLOAD_FOLDER, pdf_id) # Pfad zur PDF Datei
    chroma_collection_path = os.path.join(VECTOR_DB_DIR, pdf_id) # Pfad zur ChromeDB Datenbank
    json_file_path = os.path.join(JSON_OUTPUT_FOLDER, f"{pdf_id}.json") # Pfad zur JSON Datei (Implementiert Marcel erst ja noch)

    deleted_items = []
    errors = []

    # PDF-Datei löschen:
    if os.path.exists(pdf_file_path):
        try:
            os.remove(pdf_file_path)
            deleted_items.append(f"PDF-Datei '{pdf_id}'")
            print(f"PDF-Datei '{pdf_file_path}' erfolgreich gelöscht.")
        except Exception as e:
            errors.append(f"Fehler beim Löschen der PDF-Datei '{pdf_id}': {e}")
            print(f"Fehler beim Löschen der PDF-Datei '{pdf_file_path}': {e}")
            traceback.print_exc()
    else:
        print(f"PDF-Datei '{pdf_id}' nicht gefunden zum Löschen.")

    # ChromaDB Inhalt löschen:
    # Aus dem aktiven Cache:
    if pdf_id in vector_stores_cache:
        try:
            del vector_stores_cache[pdf_id]
            print(f"ChromaDB-Sammlung '{pdf_id}' aus Cache entfernt.")
        except Exception as e:
            errors.append(f"Fehler beim Entfernen der ChromaDB-Sammlung '{pdf_id}' aus dem Cache: {e}")
            print(f"Fehler beim Entfernen der ChromaDB-Sammlung '{pdf_id}' aus dem Cache: {e}")
            traceback.print_exc()

    try:
        if os.path.exists(VECTOR_DB_DIR):
            client = chromadb.PersistentClient(path=VECTOR_DB_DIR)

            try:
                client.delete_collection(name=pdf_id)
                deleted_items.append(f"ChromaDB-Sammlung '{pdf_id}'")
                print(f"ChromaDB-Sammlung '{pdf_id}' erfolgreich über ChromaDB Client gelöscht.")
            except Exception as e:
                if "does not exist" in str(e).lower():
                    print(f"ChromaDB-Sammlung '{pdf_id}' existierte nicht zum Löschen (oder wurde bereits gelöscht).")
                else:
                    errors.append(f"Fehler beim Löschen der ChromaDB-Sammlung '{pdf_id}' über Client: {e}")
                    print(f"Fehler beim Löschen der ChromaDB-Sammlung '{pdf_id}' über Client: {e}")
                    traceback.print_exc()
        else:
            print(f"ChromaDB Hauptverzeichnis '{VECTOR_DB_DIR}' existiert nicht. Keine Sammlungen zu löschen.")

    except Exception as e:
        errors.append(f"Allgemeiner Fehler bei der ChromaDB-Sammlung-Löschung für '{pdf_id}': {e}")
        print(f"Allgemeiner Fehler bei der ChromaDB-Sammlung-Löschung für '{pdf_id}': {e}")
        traceback.print_exc()


    # JSON-Datei löschen (falls überhaupt vorhanden):
    if os.path.exists(json_file_path):
        try:
            os.remove(json_file_path)
            deleted_items.append(f"JSON-Datei '{pdf_id}.json'")
            print(f"JSON-Datei '{json_file_path}' erfolgreich gelöscht.")
        except Exception as e:
            errors.append(f"Fehler beim Löschen der JSON-Datei '{pdf_id}.json': {e}")
            print(f"Fehler beim Löschen der JSON-Datei '{json_file_path}': {e}")
            traceback.print_exc()
    else:
        print(f"JSON-Datei '{pdf_id}.json' nicht gefunden zum Löschen.")


    if errors:
        return jsonify({"message": "Löschvorgang abgeschlossen, aber mit Fehlern.", "deleted": deleted_items, "errors": errors}), 500
    elif not deleted_items:
        return jsonify({"message": f"Keine Ressourcen für PDF ID '{pdf_id}' gefunden zum Löschen."}), 404
    else:
        return jsonify({"message": f"Ressourcen für PDF ID '{pdf_id}' erfolgreich gelöscht.", "deleted": deleted_items}), 200
    
# Alles in DB löschen:    
@app.route('/delete_all_data', methods=['DELETE'])
def delete_all_data():
    """
    Löscht alle hochgeladenen PDF-Dateien, alle zugehörigen ChromaDB-Daten
    und leert den In-Memory-Cache der Vector Stores.
    """
    print("Anfrage zum Löschen aller Daten erhalten.")
    deleted_items = []
    errors = []

    # Alle PDFs löschen und Ordner neu erstellen
    try:
        if os.path.exists(UPLOAD_FOLDER):
            shutil.rmtree(UPLOAD_FOLDER)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True) 
            deleted_items.append(f"Alle Dateien im '{UPLOAD_FOLDER}' Ordner")
            print(f"Alle Dateien im '{UPLOAD_FOLDER}' Ordner erfolgreich gelöscht und Ordner neu erstellt.")
        else:
            print(f"Ordner '{UPLOAD_FOLDER}' existiert nicht. Keine PDF-Dateien zu löschen.")
    except Exception as e:
        errors.append(f"Fehler beim Löschen der PDF-Dateien im '{UPLOAD_FOLDER}' Ordner: {e}")
        print(f"Fehler beim Löschen der PDF-Dateien im '{UPLOAD_FOLDER}' Ordner: {e}")
        traceback.print_exc()

    # Alle ChromaDB-Daten löschen und Ordner neu erstellen
    try:
        if os.path.exists(VECTOR_DB_DIR):
            shutil.rmtree(VECTOR_DB_DIR)
            os.makedirs(VECTOR_DB_DIR, exist_ok=True) 
            deleted_items.append(f"Alle Daten im '{VECTOR_DB_DIR}' Ordner")
            print(f"Alle Daten im '{VECTOR_DB_DIR}' Ordner erfolgreich gelöscht und Ordner neu erstellt.")
        else:
            print(f"Ordner '{VECTOR_DB_DIR}' existiert nicht. Keine ChromaDB-Daten zu löschen.")
    except Exception as e:
        errors.append(f"Fehler beim Löschen der ChromaDB-Daten im '{VECTOR_DB_DIR}' Ordner: {e}")
        print(f"Fehler beim Löschen der ChromaDB-Daten im '{VECTOR_DB_DIR}' Ordner: {e}")
        traceback.print_exc()

    # In-Memory-Cache leeren
    if vector_stores_cache:
        vector_stores_cache.clear()
        deleted_items.append("In-Memory-Cache für Vector Stores")
        print("In-Memory-Cache für Vector Stores geleert.")
    else:
        print("In-Memory-Cache für Vector Stores ist bereits leer.")

    # Extrahierte JSON-Dateien löschen (wenn wir dann implementiert haben)
    try:
        if os.path.exists(JSON_OUTPUT_FOLDER):
            shutil.rmtree(JSON_OUTPUT_FOLDER)
            os.makedirs(JSON_OUTPUT_FOLDER, exist_ok=True)
            deleted_items.append(f"Alle Dateien im '{JSON_OUTPUT_FOLDER}' Ordner")
            print(f"Alle Dateien im '{JSON_OUTPUT_FOLDER}' Ordner erfolgreich gelöscht und Ordner neu erstellt.")
        else:
            print(f"Ordner '{JSON_OUTPUT_FOLDER}' existiert nicht. Keine JSON-Dateien zu löschen.")
    except Exception as e:
        errors.append(f"Fehler beim Löschen der JSON-Dateien im '{JSON_OUTPUT_FOLDER}' Ordner: {e}")
        print(f"Fehler beim Löschen der JSON-Dateien im '{JSON_OUTPUT_FOLDER}' Ordner: {e}")
        traceback.print_exc()

    if errors:
        return jsonify({"message": "Löschvorgang abgeschlossen, aber mit Fehlern.", "deleted": deleted_items, "errors": errors}), 500
    else:
        return jsonify({"message": "Alle Daten erfolgreich gelöscht.", "deleted": deleted_items}), 200

if __name__ == '__main__':
    print("Starting Flask backend server...")
    if os.path.exists(VECTOR_DB_DIR):
        try:
            client = chromadb.PersistentClient(path=VECTOR_DB_DIR)
            existing_collections = client.list_collections()
            for collection in existing_collections:
                collection_name = collection.name
                try:
                    vector_store = Chroma(
                        persist_directory=VECTOR_DB_DIR,
                        embedding_function=embeddings,
                        collection_name=collection_name
                    )
                    if vector_store._collection.count() > 0:
                        vector_stores_cache[collection_name] = vector_store
                        print(f"ChromaDB collection '{collection_name}' von Festplatte geladen und im Cache.")
                    else:
                        print(f"ChromaDB collection '{collection_name}' gefunden, aber leer beim Start. Wird ignoriert.")
                except Exception as e:
                    print(f"WARNUNG: Konnte ChromaDB Sammlung '{collection_name}' beim Start nicht vollständig laden: {e}")
                    traceback.print_exc()
        except Exception as e:
            print(f"FEHLER: ChromaDB Client konnte für '{VECTOR_DB_DIR}' beim Start nicht initialisiert werden: {e}")
            traceback.print_exc()
    else:
        print(f"ChromaDB Datenverzeichnis '{VECTOR_DB_DIR}' nicht gefunden. Es werden keine bestehenden Sammlungen geladen.")
    
    app.run(host="127.0.0.1", port=5000, debug=True)
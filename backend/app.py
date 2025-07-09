# "Monkey-patching" to ensure that ChromaDB uses the 'pysqlite3' library instead of Python's standard 'sqlite3' library. For compatibility:
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import traceback # For detailed stack traces (error information).
from flask import Flask, request, jsonify, send_from_directory # Flask core modules for web applications.
from dotenv import load_dotenv # Loading environment variables from .env file.
import os # For interaction with the operating system.
import uuid # For generating unique IDs.
from flask_cors import CORS # Enables Cross-Origin Resource Sharing, important for frontend communication.
import shutil # For deleting directories and their contents.
import chromadb # Persistent vector database.

# Imports of local modules:
from pdf_processing import read_pdf, split_text_into_sections # Functions for PDF processing.
from llm_service import get_llm_response # Function for communication with the LLM.
from langchain_community.vectorstores import Chroma # LangChain integration for ChromaDB.
from embeddingWrapper import SAIAEmbeddings # Wrapper for the SAIA Embedding Service.

# Initialize Flask application:
app = Flask(__name__)
# Enable CORS for all routes and origins.
CORS(app)

# Folder configuration:
UPLOAD_FOLDER = 'uploaded_pdfs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

VECTOR_DB_DIR = "chroma_db_data"
os.makedirs(VECTOR_DB_DIR, exist_ok=True)

JSON_OUTPUT_FOLDER = 'extracted_jsons'
os.makedirs(JSON_OUTPUT_FOLDER, exist_ok=True)

# Defines the maximum character length of the context sent to the LLM:
# The GWDG LLM (based on Llama 3.1 8B) has approx. 8000 tokens. 1 token is approx. 4 characters.
# 8000 * 4 = 32000 characters. 28000 characters leave a buffer.
MAX_CONTEXT_CHAR_LIMIT = 28000

# Load API key and initialize embedding service:
load_dotenv()
api_key = os.getenv("SAIA_API_KEY")

if not api_key:
    print("FEHLER: SAIA_API_KEY nicht gefunden! Bitte in .env setzen oder als Umgebungsvariable übergeben.")
    raise ValueError("API Key nicht gefunden! Bitte in .env setzen.")


embeddings = SAIAEmbeddings(api_key)

# In-memory cache for Vector Stores:
vector_stores_cache = {}

# Helper function: Load or create Vector Store:
def get_or_create_vector_store(pdf_id: str, text_chunks: list[str] = None):
    """
    Lädt eine ChromaDB-Sammlung aus dem Cache oder von der Festplatte.
    Erstellt sie neu, wenn sie nicht existiert oder leer ist und text_chunks bereitgestellt werden.

    Args:
        pdf_id (str): Die eindeutige ID der PDF (und somit der ChromaDB-Sammlung).
        text_chunks (list[str], optional): Eine Liste von Text-Chunks, die zum Erstellen
                                            einer neuen Sammlung verwendet werden, falls diese nicht existiert.
                                            Standardmäßig None.

    Returns:
        Chroma: Die geladene oder neu erstellte ChromaDB-Instanz.

    Raises:
        Exception: Wenn der Vector Store nicht gefunden/erstellt werden kann oder Text-Chunks fehlen.
    """

    # 1. Check the in-memory cache first:
    if pdf_id in vector_stores_cache:
        return vector_stores_cache[pdf_id]

    vector_store_from_disk = None
    # 2. Try to load the collection from disk:
    try:
        client = chromadb.PersistentClient(path=VECTOR_DB_DIR)
        collection_exists = any(c.name == pdf_id for c in client.list_collections())

        if collection_exists:
            vector_store_from_disk = Chroma(
                persist_directory=VECTOR_DB_DIR,
                embedding_function=embeddings,
                collection_name=pdf_id
            )
            if vector_store_from_disk._collection.count() > 0:
                vector_stores_cache[pdf_id] = vector_store_from_disk
                return vector_store_from_disk
            else:
                # If the collection exists but is empty, it is treated as non-existent.
                pass
        else:
            pass

    except Exception as e:
        # Log a warning if loading from disk fails (e.g., corrupted data).
        print(f"WARNUNG: Konnte ChromaDB collection '{pdf_id}' nicht von Festplatte laden (oder sie ist beschädigt): {e}")

    # 3. If not in cache and not successfully loaded from disk (or empty on disk), try to create it:
    if text_chunks:
        try:
            # LangChain's Chroma.from_texts handles the creation and addition of embeddings.
            vector_store = Chroma.from_texts(
                texts=text_chunks,
                embedding=embeddings,
                collection_name=pdf_id,
                persist_directory=VECTOR_DB_DIR
            )
            vector_stores_cache[pdf_id] = vector_store # Add the newly created collection to the cache.
            return vector_store
        except Exception as inner_e:
            # Log an error and re-raise the exception if creation fails.
            print(f"FEHLER: Fehler beim Erstellen/Aktualisieren neuer ChromaDB collection '{pdf_id}': {inner_e}")
            traceback.print_exc()
            raise Exception(f"Failed to create/update vector store: {inner_e}")
    else:
        print(f"FEHLER: Vector store für '{pdf_id}' nicht gefunden und keine Text-Chunks zum Erstellen bereitgestellt.")
        raise Exception(f"Vector store for '{pdf_id}' not found and no text chunks provided to create it.")


# API Routes:

# Route for serving static PDF files (e.g., for direct links in the frontend):
@app.route('/static_pdfs/<filename>')
def serve_pdf(filename):
    # send_from_directory is used for securely serving files from a specific folder.
    return send_from_directory(UPLOAD_FOLDER, filename)         


# Route for uploading and processing PDF files:
@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    print("Received PDF upload request.")
    # 1. Check if the file is included in the request.
    if 'pdf_file' not in request.files:
        return jsonify({"error": "No pdf_file part in the request"}), 400 # (Bad Request)

    pdf_file = request.files['pdf_file']
    # 2. Check if a filename is present.
    if pdf_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # 3. Check the file type (only PDF allowed).
    if not pdf_file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Invalid file type. Only PDF allowed."}), 400

    # 4. Process the uploaded file (if all checks pass).
    if pdf_file:
        file_extension = os.path.splitext(pdf_file.filename)[1] # Extract the file extension.
        unique_filename = str(uuid.uuid4()) + file_extension # Generate a unique filename with UUID.
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename) # Create the full path for saving.

        try:
            pdf_file.save(file_path) # Save the uploaded file temporarily.
            print(f"PDF saved to {file_path}")

            full_pdf_text = read_pdf(file_path) # 5. Read the entire text from the PDF.
            if not full_pdf_text:
                os.remove(file_path) # Delete the file if no content could be read.
                return jsonify({"error": "Could not read content from PDF"}), 500 # (Internal Server Error)

            text_chunks = split_text_into_sections(full_pdf_text) # 6. Split the text into chunks.
            if not text_chunks:
                os.remove(file_path) # Delete the file if no usable chunks could be created.
                return jsonify({"error": "Could not process PDF content into usable chunks."}), 500

            try:
                # 7. Create or load the Vector Store for the PDF ID with the generated chunks.
                vector_store = get_or_create_vector_store(unique_filename, text_chunks) # Calls helper function.
                print(f"PDF content embedded and stored in ChromaDB collection '{unique_filename}' with {len(text_chunks)} chunks.") 
            except Exception as e:
                print(f"Error handling ChromaDB for {unique_filename}: {e}")
                traceback.print_exc()
                os.remove(file_path)
                return jsonify({"error": f"Failed to process PDF for search: {str(e)}"}), 500

            # 8. Return successful response.
            return jsonify({
                "message": "PDF uploaded, processed and embedded", # Success message for the frontend.
                "filename": pdf_file.filename, # Original filename.
                "pdf_url": f"http://localhost:5000/static_pdfs/{unique_filename}" # URL for direct access to the PDF.
            }), 200 # (OK)
        except Exception as e:
            # 9. General error handling for the file processing process.
            print(f"Server error during PDF processing: {e}")
            traceback.print_exc()
            return jsonify({"error": f"Server error during PDF processing: {str(e)}"}), 500

# Route for chatting with an uploaded PDF. Implements RAG pattern:
@app.route('/chat', methods=['POST'])
def chat_with_pdf():
    print("Received chat request.")
    # 1. Extract data from the request.
    data = request.json # Get JSON data from the request. Frontend sends the request and the PDF ID here.
    user_question = data.get('question') # Extract user question from the JSON data.
    pdf_id = data.get('pdf_id') # Extract the ID of the PDF to chat with.

    # Validate input parameters:
    if not user_question or not pdf_id:
        return jsonify({"error": "Missing 'question' or 'pdf_id'"}), 400

    # 3. Load Vector Store.
    try:
        vector_store = get_or_create_vector_store(pdf_id)
    except Exception as e:
        print(f"Error loading vector store for PDF {pdf_id}: {e}")
        traceback.print_exc() 
        return jsonify({"error": "PDF content not found or could not be loaded. Please upload the PDF again."}), 404 # (Not Found)


    # 4. Retrieve relevant documents from the Vector Store (Retrieval step of RAG):
    # Semantic Search in Vector Store.
    retrieved_docs = vector_store.similarity_search(user_question, k=5) # k = 5 retrieves 5 most similar documents.

    # 5. Create context for the LLM: 
    context_for_llm = "\n\n".join([doc.page_content for doc in retrieved_docs]) # Each chunk is separated by two line breaks to improve readability for the LLM.

    # 6. Checking for empty context:
    if not context_for_llm.strip():
        return jsonify({"answer": "Leider konnte ich im Dokument keine relevanten Informationen zu Ihrer Frage finden."}), 200

    # 7. Shorten context if necessary:
    if len(context_for_llm) > MAX_CONTEXT_CHAR_LIMIT:
        context_for_llm = context_for_llm[:MAX_CONTEXT_CHAR_LIMIT] + "\n\n[Kontext gekürzt aufgrund der Länge...]"

    # 8. Generate LLM response (Generation step of RAG)
    try:
        llm_answer = get_llm_response(
            user_question=user_question, # The user's original question.
            system_prompt="Du bist ein KI-Assistent, der Fragen präzise und wahrheitsgemäß basierend auf dem bereitgestellten Dokument beantwortet. Beschränke deine Antworten auf die Informationen im Dokument. Wenn die Antwort nicht im Dokument ist, sage das klar und deutlich. Wenn du keine relevanten Informationen hast, sage das ebenfalls.", # Instruction for the LLM on how to behave. 
            context=context_for_llm # The retrieved context from the PDF.
        )
        return jsonify({"answer": llm_answer}), 200
    except Exception as e:
        # 9. Error handling for communication with the LLM.
        print(f"Fehler bei der Kommunikation mit dem KI-Modell: {e}") 
        traceback.print_exc()
        return jsonify({"error": f"Fehler bei der Kommunikation mit dem KI-Modell: {str(e)}"}), 500
        
# Route for deleting a specific PDF and its associated data. Commented out because not needed:

# @app.route('/delete_pdf/<pdf_id>', methods=['DELETE'])
# def delete_pdf(pdf_id):
#    print(f"Received delete request for PDF ID: {pdf_id}")
#
#    pdf_file_path = os.path.join(UPLOAD_FOLDER, pdf_id)
#    json_file_path = os.path.join(JSON_OUTPUT_FOLDER, f"{pdf_id}.json")
#
#    deleted_items = []
#    errors = []
#
#    if os.path.exists(pdf_file_path):
#        try:
#            os.remove(pdf_file_path)
#            deleted_items.append(f"PDF-Datei '{pdf_id}'")
#        except Exception as e:
#            errors.append(f"Fehler beim Löschen der PDF-Datei '{pdf_id}': {e}")
#            print(f"Fehler beim Löschen der PDF-Datei '{pdf_file_path}': {e}")
#            traceback.print_exc()
#
#    if pdf_id in vector_stores_cache:
#        try:
#            del vector_stores_cache[pdf_id]
#        except Exception as e:
#            errors.append(f"Fehler beim Entfernen der ChromaDB-Sammlung '{pdf_id}' aus dem Cache: {e}")
#            print(f"Fehler beim Entfernen der ChromaDB-Sammlung '{pdf_id}' aus dem Cache: {e}")
#            traceback.print_exc()
#
#    try:
#        if os.path.exists(VECTOR_DB_DIR):
#            client = chromadb.PersistentClient(path=VECTOR_DB_DIR)
#
#            try:
#                client.delete_collection(name=pdf_id)
#                deleted_items.append(f"ChromaDB-Sammlung '{pdf_id}'")
#            except Exception as e:
#                if "does not exist" in str(e).lower():
#                    pass
#                else:
#                    errors.append(f"Fehler beim Löschen der ChromaDB-Sammlung '{pdf_id}' über Client: {e}")
#                    print(f"Fehler beim Löschen der ChromaDB-Sammlung '{pdf_id}' über Client: {e}") 
#                    traceback.print_exc()
#
#    except Exception as e:
#        errors.append(f"Allgemeiner Fehler bei der ChromaDB-Sammlung-Löschung für '{pdf_id}': {e}")
#        print(f"Allgemeiner Fehler bei der ChromaDB-Sammlung-Löschung für '{pdf_id}': {e}") 
#        traceback.print_exc() 
#
#
#    if os.path.exists(json_file_path):
#        try:
#            os.remove(json_file_path)
#            deleted_items.append(f"JSON-Datei '{pdf_id}.json'")
#        except Exception as e:
#            errors.append(f"Fehler beim Löschen der JSON-Datei '{pdf_id}.json': {e}")
#            print(f"Fehler beim Löschen der JSON-Datei '{json_file_path}': {e}") 
#            traceback.print_exc() 
#
#
#    if errors:
#        return jsonify({"message": "Löschvorgang abgeschlossen, aber mit Fehlern.", "deleted": deleted_items, "errors": errors}), 500
#    elif not deleted_items:
#        return jsonify({"message": f"Keine Ressourcen für PDF ID '{pdf_id}' gefunden zum Löschen."}), 404
#    else:
#        return jsonify({"message": f"Ressourcen für PDF ID '{pdf_id}' erfolgreich gelöscht.", "deleted": deleted_items}), 200
        
# Route for deleting all uploaded data in DB:      
@app.route('/delete_all_data', methods=['DELETE'])
def delete_all_data():
    """
    Löscht alle hochgeladenen PDF-Dateien, alle zugehörigen ChromaDB-Daten
    und leert den In-Memory-Cache der Vector Stores.
    """
    print("Anfrage zum Löschen aller Daten erhalten.")
    deleted_items = []
    errors = []

    # 1. Delete all PDFs and recreate the folder. Handles the 'uploaded_pdfs' folder:
    try:
        if os.path.exists(UPLOAD_FOLDER):
            shutil.rmtree(UPLOAD_FOLDER)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True) 
            deleted_items.append(f"Alle Dateien im '{UPLOAD_FOLDER}' Ordner")
    except Exception as e:
        errors.append(f"Fehler beim Löschen der PDF-Dateien im '{UPLOAD_FOLDER}' Ordner: {e}")
        print(f"Fehler beim Löschen der PDF-Dateien im '{UPLOAD_FOLDER}' Ordner: {e}") 
        traceback.print_exc() 

    # Alle ChromaDB-Daten löschen und Ordner neu erstellen
    try:
        if os.path.exists(VECTOR_DB_DIR):
            shutil.rmtree(VECTOR_DB_DIR) # Removes all uploaded PDFs.
            os.makedirs(VECTOR_DB_DIR, exist_ok=True) # Recreates the empty folder.
            deleted_items.append(f"Alle Daten im '{VECTOR_DB_DIR}' Ordner") # Add the success to the list.
            print(f"Alle Dateien im '{UPLOAD_FOLDER}' Ordner erfolgreich gelöscht und Ordner neu erstellt.")
        else:
            print(f"Ordner '{UPLOAD_FOLDER}' existiert nicht. Keine PDF-Dateien zu löschen.")
    except Exception as e:
        # Catch all errors that might occur when deleting or recreating the PDF folder.
        errors.append(f"Fehler beim Löschen der ChromaDB-Daten im '{VECTOR_DB_DIR}' Ordner: {e}")
        print(f"Fehler beim Löschen der ChromaDB-Daten im '{VECTOR_DB_DIR}' Ordner: {e}") 
        traceback.print_exc()

    # 2. Delete all ChromaDB data and recreate the folder. Handles the 'chroma_db_data' folder:
    try:
        if os.path.exists(VECTOR_DB_DIR):
            shutil.rmtree(VECTOR_DB_DIR) # Deletes the entire ChromaDB data directory.
            os.makedirs(VECTOR_DB_DIR, exist_ok=True) # Recreates the folder.
            deleted_items.append(f"Alle Daten im '{VECTOR_DB_DIR}' Ordner") # Add the success to the list.
            print(f"Alle Daten im '{VECTOR_DB_DIR}' Ordner erfolgreich gelöscht und Ordner neu erstellt.")
        else:
            print(f"Ordner '{VECTOR_DB_DIR}' existiert nicht. Keine ChromaDB-Daten zu löschen.")
    except Exception as e:
        # Catch all errors that might occur when deleting or recreating the ChromaDV folder.
        errors.append(f"Fehler beim Löschen der ChromaDB-Daten im '{VECTOR_DB_DIR}' Ordner: {e}")
        print(f"Fehler beim Löschen der ChromaDB-Daten im '{VECTOR_DB_DIR}' Ordner: {e}") 
        traceback.print_exc()    

    # 3. Clear in-memory cache: 
    if vector_stores_cache:
        vector_stores_cache.clear() # Deletes the entire directory.
        deleted_items.append("In-Memory-Cache für Vector Stores") # Add the success to the list.
        print("In-Memory-Cache für Vector Stores geleert.")
    else:
        print("In-Memory-Cache für Vector Stores ist bereits leer.")


    # 4. Delete extracted JSON files. Handles the 'extracted_jsons' folder:
    try:
        if os.path.exists(JSON_OUTPUT_FOLDER):
            shutil.rmtree(JSON_OUTPUT_FOLDER) # Deletes the entire JSON directory.
            os.makedirs(JSON_OUTPUT_FOLDER, exist_ok=True) # Recreates the folder.
            deleted_items.append(f"Alle Dateien im '{JSON_OUTPUT_FOLDER}' Ordner") # Add the success to the list.
            print(f"Alle Dateien im '{JSON_OUTPUT_FOLDER}' Ordner erfolgreich gelöscht und Ordner neu erstellt.")
        else:
            print(f"Ordner '{JSON_OUTPUT_FOLDER}' existiert nicht. Keine JSON-Dateien zu löschen.")
    except Exception as e:
        # Catch all errors that might occur when deleting or recreating the JSON folder.
        errors.append(f"Fehler beim Löschen der JSON-Dateien im '{JSON_OUTPUT_FOLDER}' Ordner: {e}")
        print(f"Fehler beim Löschen der JSON-Dateien im '{JSON_OUTPUT_FOLDER}' Ordner: {e}") 
        traceback.print_exc()

    # Return deletion status to the frontend:
    if errors:
        return jsonify({"message": "Löschvorgang abgeschlossen, aber mit Fehlern.", "deleted": deleted_items, "errors": errors}), 500
    else:
        return jsonify({"message": "Alle Daten erfolgreich gelöscht.", "deleted": deleted_items}), 200

# Application entry point:
if __name__ == '__main__':
    print("Starting Flask backend server...")
    # debug=True: Activates debug mode (automatic reload on code changes, detailed errors).
    app.run(host="127.0.0.1", port=5000, debug=True)
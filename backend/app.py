import traceback
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import uuid
from flask_cors import CORS  # Für Frontend-Kommunikation
from pdf_processing import read_pdf, split_text_into_sections
from llm_service import get_llm_response

# NEUE IMPORTE FÜR EMBEDDINGS UND VECTOR STORE

from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA  # Optional: Später für komplexere RAG Chains
from embeddingWrapper import SAIAEmbeddings



app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploaded_pdfs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

VECTOR_DB_DIR = "chroma_db_data"
os.makedirs(VECTOR_DB_DIR, exist_ok=True)

MAX_CONTEXT_CHAR_LIMIT = 28000

# Initialisiere den Embedding-Service (korrekt)

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
                    embedding=embeddings,  # ✅ korrekt: 'embedding' statt 'embedding_function'
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
                "pdf_id": unique_filename,
                "filename": pdf_file.filename
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

if __name__ == '__main__':
    print("Starting Flask backend server...")
    for collection_name in os.listdir(VECTOR_DB_DIR):
        if os.path.isdir(os.path.join(VECTOR_DB_DIR, collection_name)):
            try:
                get_or_create_vector_store(collection_name)
            except Exception as e:
                print(f"Konnte persistente ChromaDB Sammlung '{collection_name}' nicht beim Start laden: {e}")
                traceback.print_exc()

    app.run(host="127.0.0.1", port=5000, debug=True)

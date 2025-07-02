from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter 

def read_pdf(file_path: str) -> str:
    """
    Liest den Text aus einer PDF-Datei.
    """
    content = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            content += page.extract_text() + "\n"
        return content.strip()
    except Exception as e:
        print(f"Ein Fehler ist aufgetreten beim Lesen der PDF: {e}")
        return ""

def split_text_into_sections(text: str) -> list[str]:
    """
    Teilt einen längeren Text in kleinere, überlappende Abschnitte (Chunks) auf.
    Verwendet LangChain's RecursiveCharacterTextSplitter.
    """
    # Diese Parameter sind wichtig für die Qualität des Retrieval.
    # Experimentieren mit chunk_size und chunk_overlap für beste Ergebnisse basierend auf dem Dokumententyp.
    # chunk_size: Maximale Größe jedes Chunks (in Zeichen)
    # chunk_overlap: Anzahl der Zeichen, die sich zwischen benachbarten Chunks überlappen
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,     # Beispiel: 1000 Zeichen pro Chunk
        chunk_overlap=200,   # Beispiel: 200 Zeichen Überlappung
        length_function=len, # Misst die Länge in Zeichen
        is_separator_regex=False, # Standardmäßig keine Regex für Separatoren verwenden
        separators=["\n\n", "\n", " ", ""] # Versucht diese Separatoren in dieser Reihenfolge
    )
    chunks = text_splitter.split_text(text)
    print(f"Text in {len(chunks)} Chunks aufgeteilt.")
    return chunks
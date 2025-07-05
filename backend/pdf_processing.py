from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter 

def read_pdf(file_path: str) -> str:
    """
    Liest den Text aus einer PDF-Datei.
    Gibt den gesamten Text der PDF als einen einzelnen String zurück.
    """
    content = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            extracted_text = page.extract_text()
            if extracted_text: # Füge nur nicht-leeren Text hinzu
                content += extracted_text + "\n"
        print(f"PDF '{file_path}' gelesen. Gesamtlänge: {len(content.strip())} Zeichen.")
        return content.strip()
    except Exception as e:
        print(f"FEHLER: Ein Fehler ist aufgetreten beim Lesen der PDF '{file_path}': {e}")
        return ""

def split_text_into_sections(text: str) -> list[str]:
    """
    Teilt einen längeren Text in kleinere, überlappende Abschnitte (Chunks) auf.
    Verwendet LangChain's RecursiveCharacterTextSplitter.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,    # Maximale Zeichen pro Chunk
        chunk_overlap=200,  # Überlappung zwischen Chunks, um Kontext zu erhalten
        length_function=len, # Misst die Länge in Zeichen
        is_separator_regex=False, # Standardmäßig keine Regex für Separatoren verwenden
        separators=["\n\n", "\n", " ", ""] # Versucht diese Separatoren in dieser Reihenfolge
    )
    chunks = text_splitter.split_text(text)
    print(f"Text in {len(chunks)} Chunks aufgeteilt.")
    return chunks

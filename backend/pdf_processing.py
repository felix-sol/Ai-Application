from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter # NEUER IMPORT

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
    # Experimentiere mit chunk_size und chunk_overlap für beste Ergebnisse basierend auf deinem Dokumententyp.
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

# --- Du kannst den __main__ Block für eigenständige Tests beibehalten, falls vorhanden ---
# Zum Beispiel zum Testen, wie das Splitting funktioniert
# if __name__ == "__main__":
#     import os
#     dummy_pdf_path = "seminar_info.pdf"
#     if not os.path.exists(dummy_pdf_path):
#         print(f"Dummy PDF '{dummy_pdf_path}' nicht gefunden. Erstelle eine einfache Dummy-Datei.")
#         with open(dummy_pdf_path, "w") as f:
#             f.write("Dies ist ein Dummy-Dokument für Testzwecke.\n")
#             f.write("Es enthält Informationen über Nachhaltigkeit und CO2-Emissionen.\n")
#             f.write("Das Projekt zielt darauf ab, die Verarbeitung von Dokumenten zu automatisieren.\n")
#             f.write("Weitere Informationen sind in den späteren Abschnitten zu finden.\n")
#
#     pdf_text = read_pdf(dummy_pdf_path)
#     if pdf_text:
#         print(f"PDF-Text erfolgreich gelesen (Länge: {len(pdf_text)} Zeichen).")
#         sections = split_text_into_sections(pdf_text)
#         print(f"Anzahl der Abschnitte: {len(sections)}")
#         for i, section in enumerate(sections[:3]): # Zeige nur die ersten 3 Abschnitte
#             print(f"\n--- Abschnitt {i+1} ---")
#             print(section)
#     else:
#         print("Konnte PDF-Text nicht lesen.")
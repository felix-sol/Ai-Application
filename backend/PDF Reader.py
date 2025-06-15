import PyPDF2


def read_pdf(file_path):
    """
    Reads a PDF file and returns its content as a string.

    :param file_path: Path to the PDF file
    :return: Content of the PDF file as a string
    """
    content = ""
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                content += page.extract_text() + "\n"
    except Exception as e:
        print(f"An error occurred while reading the PDF: {e}")

    return content.strip()


def split_text_into_sections(text, max_length=1000):
    """
    Splits text into sections of a specified maximum length.

    :param text: The text to be split
    :param max_length: Maximum length of each section
    :return: List of text sections
    """
    sections = []
    while len(text) > max_length:
        split_index = text.rfind(' ', 0, max_length)
        if split_index == -1:
            split_index = max_length
        sections.append(text[:split_index].strip())
        text = text[split_index:].strip()
    if text:
        sections.append(text)

    return sections

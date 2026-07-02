#file_processor
from pypdf import PdfReader
from docx import Document
from ebooklib import epub
from bs4 import BeautifulSoup

#Função do PDF
def read_pdf(path):

    reader = PdfReader(path)

    texto = ""

    for page in reader.pages:
        texto += page.extract_text() + "\n"

    return texto


#Função do DOC
def read_docx(path):

    doc = Document(path)

    return "\n".join(
        p.text
        for p in doc.paragraphs
    )
# Função txt
def read_txt(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return f.read()
    

#Função do epub
def read_epub(path):

    book = epub.read_epub(path)

    texto = ""

    for item in book.get_items():

        if item.get_type() == 9:

            soup = BeautifulSoup(
                item.get_content(),
                "html.parser"
            )

            texto += soup.get_text()

    return texto

from pathlib import Path

def extract_text(path: str) -> str:
    """Detecta o tipo do arquivo e extrai o texto."""
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return read_pdf(path)
    elif ext == ".docx":
        return read_docx(path)
    elif ext == ".epub":
        return read_epub(path)
    elif ext == ".txt":
        return read_txt(path)
    else:
        raise ValueError(f"Formato não suportado: {ext}")
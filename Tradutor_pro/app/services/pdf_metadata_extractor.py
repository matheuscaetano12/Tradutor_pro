"""
app/services/pdf_metadata_extractor.py
Extrai metadados (título, autor, subtítulo) do PDF original
usando pypdf (já instalado no projeto) com fallback para pdfplumber.

Não depende de OCR — funciona com PDFs que têm camada de texto.
"""

import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── Padrões de detecção de autores ────────────────────────────────────────────
_RE_AUTHOR_BY   = re.compile(r"(?:by|por|autor[a]?)\s+([A-ZÀ-Ü][a-zà-ü]+(?:\s+[A-ZÀ-Ü][a-zà-ü]+)+)", re.I)
_RE_AUTHOR_CAPS = re.compile(r"^([A-ZÀ-Ü]{2,}(?:\s+[A-ZÀ-Ü]{2,})+)$")   # linha só com MAIÚSCULAS
_RE_SUBTITLE    = re.compile(r"^[A-ZÀ-Ü][^.!?]{10,80}$")                  # linha razoável como subtítulo


def extract_pdf_metadata(pdf_path: str) -> dict:
    """
    Retorna dict com:
      title    (str)  — título do livro
      author   (str)  — autor
      subtitle (str)  — subtítulo/série (opcional)

    Estratégia:
      1. Metadados embutidos no PDF (pypdf)
      2. Primeiras páginas do texto (heurística)
    """
    result = {"title": "", "author": "", "subtitle": ""}

    # ── 1. Metadados embutidos ─────────────────────────────────────────────────
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        meta = reader.metadata or {}

        raw_title  = _clean(meta.get("/Title")  or meta.get("title")  or "")
        raw_author = _clean(meta.get("/Author") or meta.get("author") or "")

        if raw_title:
            result["title"] = raw_title
        if raw_author:
            result["author"] = raw_author

        logger.info(f"[MetaExtractor] Metadados pypdf → título='{raw_title}' autor='{raw_author}'")
    except Exception as e:
        logger.warning(f"[MetaExtractor] pypdf falhou: {e}")

    # ── 2. Heurística nas primeiras páginas ────────────────────────────────────
    # Só executa se algum campo ainda está vazio
    if not result["title"] or not result["author"]:
        _fill_from_pages(pdf_path, result)

    # ── 3. Fallback: usa nome do arquivo como título ───────────────────────────
    if not result["title"]:
        stem = Path(pdf_path).stem
        # Remove prefixo de hash (ex: "47afe477364e823fdb81414a9ed3b744_spiritual-warfare…")
        if "_" in stem:
            stem = stem.split("_", 1)[1]
        result["title"] = stem.replace("-", " ").replace("_", " ").title()
        logger.info(f"[MetaExtractor] Título extraído do nome do arquivo: '{result['title']}'")

    if not result["author"]:
        result["author"] = "Autor Desconhecido"

    logger.info(f"[MetaExtractor] Resultado final → {result}")
    return result


def _fill_from_pages(pdf_path: str, result: dict) -> None:
    """Lê as 3 primeiras páginas e tenta detectar título/autor/subtítulo."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        pages_to_scan = min(3, len(reader.pages))
        lines = []
        for i in range(pages_to_scan):
            text = reader.pages[i].extract_text() or ""
            lines.extend(text.splitlines())
    except Exception as e:
        logger.warning(f"[MetaExtractor] Leitura de páginas falhou: {e}")
        return

    candidates_title    = []
    candidates_subtitle = []
    candidates_author   = []

    for raw in lines:
        line = raw.strip()
        if not line or len(line) < 3:
            continue

        # Autor por palavra-chave (by / por / autor)
        m = _RE_AUTHOR_BY.search(line)
        if m and not result["author"]:
            candidates_author.append(m.group(1))
            continue

        # Linha em MAIÚSCULAS → candidata a título
        if _RE_AUTHOR_CAPS.match(line) and 4 < len(line) < 80:
            candidates_title.append(line.title())
            continue

        # Linha com capitalização normal e tamanho razoável → subtítulo
        if _RE_SUBTITLE.match(line) and 10 < len(line) < 80:
            candidates_subtitle.append(line)

    # Aplica os candidatos apenas se o campo ainda está vazio
    if not result["title"] and candidates_title:
        result["title"] = candidates_title[0]
        logger.info(f"[MetaExtractor] Título detectado por heurística: '{result['title']}'")

    if not result["author"] and candidates_author:
        result["author"] = candidates_author[0]
        logger.info(f"[MetaExtractor] Autor detectado por heurística: '{result['author']}'")

    if not result["subtitle"] and candidates_subtitle:
        # Pega o candidato mais curto (subtítulos tendem a ser concisos)
        result["subtitle"] = min(candidates_subtitle, key=len)
        logger.info(f"[MetaExtractor] Subtítulo detectado: '{result['subtitle']}'")


def _clean(value) -> str:
    """Remove espaços extras e caracteres de controle."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()
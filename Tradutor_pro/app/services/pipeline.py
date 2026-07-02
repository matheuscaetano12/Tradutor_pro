# pipeline.py
"""
pipeline.py — Pipeline de tradução atualizado
INTEGRA: grammar.py (API online) + pdf_builder.py (saída em PDF com estilo)
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

TRANSLATED_DIR = Path("translated")
TRANSLATED_DIR.mkdir(exist_ok=True)


# ─── Imports dos serviços ─────────────────────────────────────────────────────
from app.services.translator import translate_text
from app.services.chunker import split_text_into_chunks
from app.services.file_processor import extract_text
from app.services.grammar import review_text
from app.services.pdf_builder import build_translated_pdf


# ─── Pipeline principal ───────────────────────────────────────────────────────

def run_translation_pipeline(
    input_path: str | Path,
    source_lang: str = "en",
    target_lang: str = "pt-BR",
    job_id: Optional[str] = None,
    apply_grammar: bool = True,
    output_format: str = "pdf",
) -> str:
    """
    Executa o pipeline completo de tradução e retorna caminho do arquivo de saída.
    """
    input_path = Path(input_path)
    job_id = job_id or input_path.stem

    logger.info(f"[Pipeline] Iniciando tradução de '{input_path.name}' ({source_lang} → {target_lang})")

    # 1. Extrair texto
    raw_text = extract_text(str(input_path))
    if not raw_text:
        raise ValueError(f"Não foi possível extrair texto de {input_path}")
    logger.info(f"[Pipeline] Texto extraído: {len(raw_text)} caracteres")

    # 2. Dividir em chunks
    chunks = split_text_into_chunks(raw_text)
    logger.info(f"[Pipeline] {len(chunks)} chunks para traduzir")

    # 3. Traduzir chunks
    translated_chunks = []
    for i, chunk in enumerate(chunks):
        logger.info(f"[Pipeline] Traduzindo chunk {i+1}/{len(chunks)}")
        translated = translate_text(chunk, source=source_lang, target=target_lang)
        translated_chunks.append(translated)

    full_translation = "\n".join(translated_chunks)

    # 4. Revisão gramatical (API online — sem Java)
    if apply_grammar:
        logger.info("[Pipeline] Iniciando revisão gramatical (LanguageTool API)...")
        full_translation = review_text(full_translation, language=target_lang)
        logger.info("[Pipeline] Revisão gramatical concluída.")

    # 5. Salvar TXT intermediário (backup)
    txt_path = TRANSLATED_DIR / f"{job_id}.txt"
    txt_path.write_text(full_translation, encoding="utf-8")

    # 6. Gerar saída no formato solicitado
    if output_format == "pdf":
        output_path = TRANSLATED_DIR / f"{job_id}.pdf"
        build_translated_pdf(
            translated_text=full_translation,
            output_path=str(output_path),
            title=_extract_title(full_translation) or input_path.stem,
            author=_extract_author(full_translation) or "Desconhecido",
            language=target_lang,
        )
        logger.info(f"[Pipeline] PDF gerado: {output_path}")
        return str(output_path)

    elif output_format == "epub":
        logger.warning("[Pipeline] EPUB não implementado, retornando TXT.")
        return str(txt_path)

    else:  # txt
        return str(txt_path)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _extract_title(text: str) -> Optional[str]:
    """Tenta extrair título das primeiras linhas do texto traduzido."""
    for line in text.splitlines()[:30]:
        line = line.strip()
        if 3 < len(line) < 80 and line.isupper():
            return line.title()
    return None


def _extract_author(text: str) -> Optional[str]:
    """Tenta encontrar o nome do autor no texto."""
    import re
    m = re.search(r"(?:por|autor|by)\s+([A-ZÀ-Ü][a-zà-ü]+(?:\s+[A-ZÀ-Ü][a-zà-ü]+)+)", text, re.IGNORECASE)
    return m.group(1) if m else None
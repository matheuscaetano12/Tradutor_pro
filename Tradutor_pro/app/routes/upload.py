# ===================================================================
# app/routes/upload.py — Tradutor Pro
# ===================================================================

import os
import time
import hashlib
import json
import logging

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.services.file_processor import read_pdf, read_docx, read_txt, read_epub
from app.services.translator import translate_text
from app.services.grammar import review_text as improve_text
from app.services.chunker import split_text_into_chunks
from app.services.retry import call_with_retry
from app.services.save_translation import save_translation
from app.services.pdf_builder import build_translated_pdf

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR     = "uploads"
TRANSLATED_DIR = "translated"
PROGRESS_DIR   = "progress"

os.makedirs(UPLOAD_DIR,     exist_ok=True)
os.makedirs(TRANSLATED_DIR, exist_ok=True)
os.makedirs(PROGRESS_DIR,   exist_ok=True)


def make_file_id(filename: str, size: int, source: str, target: str) -> str:
    raw = f"{filename}_{size}_{source}_{target}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _extract_meta_from_pdf(saved_path: str, base_name: str) -> dict:
    """Tenta extrair título e autor dos metadados do PDF original."""
    try:
        from pypdf import PdfReader
        meta = PdfReader(saved_path).metadata or {}
        title  = str(meta.get("/Title")  or "").strip()
        author = str(meta.get("/Author") or "").strip()
        if title and author:
            return {"title": title, "author": author, "subtitle": ""}
    except Exception:
        pass
    # Fallback: usa nome do arquivo
    clean = base_name.replace("-", " ").replace("_", " ").title()
    return {"title": clean, "author": "Desconhecido", "subtitle": ""}


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    source: str = Form("auto"),
    target: str = Form("pt"),
):
    ext = (file.filename or "").split(".")[-1].lower()
    content = await file.read()
    file_id = make_file_id(file.filename or "arquivo", len(content), source, target)

    saved_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    with open(saved_path, "wb") as f:
        f.write(content)

    # ── Extração de texto ──────────────────────────────────────────────────────
    if ext == "pdf":
        original_text = read_pdf(saved_path)
    elif ext == "docx":
        original_text = read_docx(saved_path)
    elif ext == "txt":
        original_text = read_txt(saved_path)
    elif ext == "epub":
        original_text = read_epub(saved_path)
    else:
        return JSONResponse(status_code=400, content={"erro": f"Formato .{ext} não suportado."})

    if not original_text.strip():
        return JSONResponse(status_code=400, content={"erro": "Não foi possível extrair texto do arquivo."})

    # ── Chunks ────────────────────────────────────────────────────────────────
    chunks = split_text_into_chunks(original_text, max_chars=4000)
    base_name = os.path.splitext(file.filename or "arquivo")[0]
    progress_path = os.path.join(PROGRESS_DIR, f"{file_id}_progress.json")

    # ── Checkpoint ────────────────────────────────────────────────────────────
    translated_chunks = []
    start_index = 0
    if os.path.exists(progress_path):
        with open(progress_path, "r", encoding="utf-8") as f:
            saved = json.load(f)
            translated_chunks = saved["translated_chunks"]
            start_index       = saved["next_index"]
        logger.info(f"[Upload] Retomando chunk {start_index}/{len(chunks)}")

    # ── Tradução ──────────────────────────────────────────────────────────────
    for i in range(start_index, len(chunks)):
        draft    = call_with_retry(translate_text, chunks[i], source, target)
        reviewed = call_with_retry(improve_text, draft, target)
        translated_chunks.append(reviewed)

        with open(progress_path, "w", encoding="utf-8") as f:
            json.dump({"translated_chunks": translated_chunks, "next_index": i + 1}, f, ensure_ascii=False)

        time.sleep(5)

    translated_text = "\n".join(translated_chunks)

    # ── Salva TXT (backup) ────────────────────────────────────────────────────
    txt_filename = f"{base_name}_traduzido.txt"
    with open(os.path.join(TRANSLATED_DIR, txt_filename), "w", encoding="utf-8") as f:
        f.write(translated_text)

    # ── Gera PDF ──────────────────────────────────────────────────────────────
    pdf_filename = f"{base_name}_traduzido.pdf"
    pdf_path     = os.path.join(TRANSLATED_DIR, pdf_filename)
    meta = _extract_meta_from_pdf(saved_path, base_name) if ext == "pdf" else \
           {"title": base_name.replace("-"," ").title(), "author": "Desconhecido", "subtitle": ""}
    try:
        build_translated_pdf(
            translated_text=translated_text,
            output_path=pdf_path,
            title=meta["title"],
            author=meta["author"],
            subtitle=meta["subtitle"],
            language=target,
        )
        logger.info(f"[Upload] PDF gerado: {pdf_path}")
        download_filename = pdf_filename   # ← prefere PDF
    except Exception as e:
        logger.error(f"[Upload] Falha ao gerar PDF: {e} — usando TXT como fallback")
        download_filename = txt_filename   # ← fallback TXT

    # ── Banco ─────────────────────────────────────────────────────────────────
    save_translation(
        file_name=file.filename,
        source_language=source,
        target_language=target,
        original_text=original_text,
        translated_text=translated_text,
    )

    if os.path.exists(progress_path):
        os.remove(progress_path)

    # ── Resposta ──────────────────────────────────────────────────────────────
    # "arquivo_traduzido" = nome do MELHOR arquivo disponível (PDF se gerado, TXT senão)
    # O JS lê este campo e monta /download/{arquivo_traduzido}
    return {
        "mensagem":          "Arquivo traduzido com sucesso.",
        "arquivo_traduzido": download_filename,   # ← campo que o JS lê
        "preview":           translated_text[:500],
    }
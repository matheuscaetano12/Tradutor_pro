# app/routes/download.py
"""
download.py — Rota de download de traduções (FastAPI)

CORREÇÃO: A rota /download/status/{job_id} estava CONFLITANDO com
/download/{filename} no FastAPI — o roteador capturava "status" como
filename. Separado com prefixo /download/file/{filename} para evitar.

Prioridade de formato: .pdf > .epub > .txt (fallback)
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()

TRANSLATED_DIR = Path("translated")


# ─── Download do arquivo ─────────────────────────────────────────────────────
# IMPORTANTE: esta rota deve vir ANTES de qualquer rota com segmento fixo
# para evitar conflito de matching no FastAPI.

@router.get("/download/{filename:path}")
def download_file(filename: str):
    """
    Faz download do arquivo traduzido.
    Aceita o nome com ou sem extensão.
    Prioridade: .pdf > .epub > .txt
    """
    # Remove extensão enviada pelo cliente (ex: "livro_traduzido.txt" → "livro_traduzido")
    safe_name = Path(filename).stem

    for ext in (".pdf", ".epub", ".txt"):
        candidate = TRANSLATED_DIR / (safe_name + ext)
        if candidate.exists():
            mime = _mime_for_ext(ext)
            logger.info(f"[Download] Servindo {candidate} ({mime})")
            return FileResponse(
                path=str(candidate),
                media_type=mime,
                filename=safe_name + ext,
                headers={"Content-Disposition": f'attachment; filename="{safe_name + ext}"'},
            )

    logger.warning(f"[Download] Não encontrado: {safe_name}")
    raise HTTPException(
        status_code=404,
        detail=f"Arquivo '{safe_name}' não encontrado. Verifique se a tradução foi concluída.",
    )


# ─── Status (verifica se o arquivo está pronto) ──────────────────────────────
@router.get("/download-status/{job_id}")
def download_status(job_id: str):
    """
    Verifica se o arquivo traduzido já está disponível.
    Renomeado de /download/status/ para /download-status/ para evitar
    conflito de rotas com /download/{filename}.
    """
    safe = Path(job_id).stem
    for ext in (".pdf", ".epub", ".txt"):
        candidate = TRANSLATED_DIR / (safe + ext)
        if candidate.exists():
            return JSONResponse({
                "ready":  True,
                "format": ext.lstrip("."),
                "url":    f"/download/{safe}",
            })
    return JSONResponse({"ready": False})


# ─── Lista arquivos disponíveis ──────────────────────────────────────────────
@router.get("/download-list")
def list_translations():
    """Lista todas as traduções disponíveis na pasta translated/."""
    if not TRANSLATED_DIR.exists():
        return JSONResponse({"arquivos": []})

    arquivos = []
    seen = set()
    for ext in (".pdf", ".epub", ".txt"):
        for p in sorted(TRANSLATED_DIR.glob(f"*{ext}")):
            if p.stem not in seen:
                seen.add(p.stem)
                arquivos.append({
                    "nome":    p.stem,
                    "formato": ext.lstrip("."),
                    "url":     f"/download/{p.stem}",
                    "tamanho": p.stat().st_size,
                })
    return JSONResponse({"arquivos": arquivos})


def _mime_for_ext(ext: str) -> str:
    return {
        ".pdf":  "application/pdf",
        ".epub": "application/epub+zip",
        ".txt":  "text/plain; charset=utf-8",
    }.get(ext, "application/octet-stream")
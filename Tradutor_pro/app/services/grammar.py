"""
grammar.py — Verificação gramatical via API online do LanguageTool
Corrige o erro: "LanguageTool requires Java >= 17"
Usa a API REST pública (sem necessidade de Java local).
"""

import re
import unicodedata
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

LANGUAGETOOL_API_URL = "https://api.languagetool.org/v2/check"

# Mapeamento de idioma para código LanguageTool
LANGUAGE_CODES = {
    "pt-BR": "pt-BR",
    "pt":    "pt-BR",
    "pt-PT": "pt-PT",
    "en":    "en-US",
    "es":    "es",
    "fr":    "fr",
    "de":    "de-DE",
}


def _sanitize_for_api(text: str) -> str:
    """
    Remove caracteres inválidos/control chars que às vezes sobram da extração
    de PDF (ex: \\x00, caracteres de controle não imprimíveis) e que podem
    fazer a API do LanguageTool rejeitar a requisição com 400 Bad Request.
    Mantém quebras de linha, tabs e espaços normais.
    """
    # remove qualquer caractere de controle exceto \n, \r, \t
    cleaned = "".join(
        ch for ch in text
        if ch in ("\n", "\r", "\t") or unicodedata.category(ch)[0] != "C"
    )
    return cleaned


def check_grammar(text: str, language: str = "pt-BR") -> dict:
    """
    Verifica a gramática do texto via API online do LanguageTool.
    Retorna dict com matches (erros encontrados) e texto corrigido.
    """
    lang_code = LANGUAGE_CODES.get(language, language)
    safe_text = _sanitize_for_api(text)

    if not safe_text.strip():
        return {"matches": [], "language_detected": lang_code}

    try:
        response = requests.post(
            LANGUAGETOOL_API_URL,
            data={
                "text": safe_text,
                "language": lang_code,
                "enabledOnly": "false",
            },
            headers={"User-Agent": "TradutorPro/1.0"},
            timeout=30,
        )

        if response.status_code != 200:
            # Loga o corpo real da resposta — essencial para saber o motivo exato
            # (ex: "Missing 'text' parameter", "limite diário excedido", etc.)
            logger.warning(
                f"[Grammar] LanguageTool respondeu {response.status_code} para "
                f"idioma '{lang_code}' ({len(safe_text)} chars). Corpo: {response.text[:300]}"
            )
            return {"matches": [], "language_detected": lang_code}

        result = response.json()
        return {
            "matches": result.get("matches", []),
            "language_detected": result.get("language", {}).get("detectedLanguage", {}).get("code", lang_code),
        }
    except requests.exceptions.Timeout:
        logger.warning("[Grammar] Timeout na API LanguageTool — retornando texto sem revisão.")
        return {"matches": [], "language_detected": lang_code}
    except requests.exceptions.RequestException as e:
        logger.warning(f"[Grammar] Erro na API LanguageTool: {e} — retornando texto sem revisão.")
        return {"matches": [], "language_detected": lang_code}


def apply_corrections(text: str, matches: list) -> str:
    """
    Aplica as correções sugeridas pelo LanguageTool ao texto.
    Aplica apenas correções com alta confiança (replacements únicos e curtos).
    """
    if not matches:
        return text

    # Ordenar por offset decrescente para não deslocar índices
    sorted_matches = sorted(matches, key=lambda m: m["offset"], reverse=True)

    for match in sorted_matches:
        replacements = match.get("replacements", [])
        if not replacements:
            continue

        # Aplica apenas quando há uma sugestão clara e única
        if len(replacements) == 1 or (replacements and match.get("rule", {}).get("issueType") == "misspelling"):
            offset = match["offset"]
            length = match["length"]
            suggestion = replacements[0]["value"]
            text = text[:offset] + suggestion + text[offset + length:]

    return text


def review_text(text: str, language: str = "pt-BR", apply: bool = True) -> str:
    """
    Interface principal: verifica e (opcionalmente) corrige o texto.
    Retorna o texto revisado ou o original se houver falha.
    """
    if not text or not text.strip():
        return text

    # Processar em chunks para evitar limite da API (20.000 caracteres)
    MAX_CHUNK = 15_000
    if len(text) <= MAX_CHUNK:
        result = check_grammar(text, language)
        if apply and result["matches"]:
            return apply_corrections(text, result["matches"])
        return text

    # Dividir em parágrafos para manter contexto
    paragraphs = text.split("\n")
    chunks, current_chunk = [], ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 1 > MAX_CHUNK:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = para
        else:
            current_chunk = (current_chunk + "\n" + para).lstrip("\n")

    if current_chunk:
        chunks.append(current_chunk)

    reviewed_parts = []
    for chunk in chunks:
        result = check_grammar(chunk, language)
        if apply and result["matches"]:
            reviewed_parts.append(apply_corrections(chunk, result["matches"]))
        else:
            reviewed_parts.append(chunk)

    return "\n".join(reviewed_parts)

# quality_checker.py
"""
Verificação de qualidade da tradução sem uso de IA paga.

Ferramentas usadas:
- rapidfuzz  → similaridade rápida entre chunks original e traduzido
- difflib    → diff linha a linha para identificar trechos suspeitos
- spellchecker → ortografia local (pyspellchecker)

Não depende de internet após instalação dos pacotes.
"""

import difflib
from rapidfuzz import fuzz
from spellchecker import SpellChecker

# Cache de instâncias do SpellChecker por idioma
_spell_cache: dict[str, SpellChecker] = {}

# Mapeamento de idioma → código do pyspellchecker
_SPELL_CODES: dict[str, str] = {
    "português": "pt",
    "inglês": "en",
    "espanhol": "es",
    "francês": "fr",
    "alemão": "de",
    "russo": "ru",
    "árabe": "ar",
    "italiano": "it",
}

# Limiar de similaridade: abaixo disso o chunk é marcado como suspeito
SIMILARITY_THRESHOLD = 30.0  # % — chunks muito diferentes do original


def _get_spellchecker(lang: str) -> SpellChecker:
    code = _SPELL_CODES.get(lang.lower(), "pt")
    if code not in _spell_cache:
        _spell_cache[code] = SpellChecker(language=code)
    return _spell_cache[code]


# ─── Comparação Original × Tradução ──────────────────────────────────────────

def compare_chunks(original: str, translated: str) -> dict:
    """
    Compara um chunk original com sua tradução.

    Retorna:
    {
        "similarity": float,       # 0-100 (token_set_ratio do rapidfuzz)
        "suspicious": bool,        # True se similaridade muito baixa
        "diff_lines": list[str],   # linhas com divergência (difflib)
    }
    """
    similarity = fuzz.token_set_ratio(original, translated)
    suspicious = similarity < SIMILARITY_THRESHOLD

    diff = list(
        difflib.unified_diff(
            original.splitlines(),
            translated.splitlines(),
            lineterm="",
            n=0,  # sem contexto — só as linhas que mudaram
        )
    )
    # Filtra cabeçalho do diff e mantém só as linhas adicionadas/removidas
    diff_lines = [l for l in diff if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]

    return {
        "similarity": similarity,
        "suspicious": suspicious,
        "diff_lines": diff_lines[:20],  # limita para não poluir o log
    }


def compare_full_text(original_chunks: list[str], translated_chunks: list[str]) -> list[dict]:
    """
    Compara lista de chunks originais com os traduzidos.
    Retorna resultados indexados; útil para log e debug.
    """
    results = []
    pairs = zip(original_chunks, translated_chunks)
    for i, (orig, trans) in enumerate(pairs):
        result = compare_chunks(orig, trans)
        result["chunk_index"] = i
        if result["suspicious"]:
            print(
                f"[QualityCheck] ⚠️  Chunk {i} suspeito "
                f"(similaridade: {result['similarity']:.1f}%)"
            )
        results.append(result)
    return results


def summarize_quality(results: list[dict]) -> dict:
    """
    Resumo agregado da qualidade da tradução.

    Retorna:
    {
        "total_chunks": int,
        "suspicious_count": int,
        "avg_similarity": float,
        "suspicious_indexes": list[int],
    }
    """
    if not results:
        return {"total_chunks": 0, "suspicious_count": 0, "avg_similarity": 0.0, "suspicious_indexes": []}

    suspicious = [r for r in results if r["suspicious"]]
    avg_sim = sum(r["similarity"] for r in results) / len(results)

    return {
        "total_chunks": len(results),
        "suspicious_count": len(suspicious),
        "avg_similarity": round(avg_sim, 1),
        "suspicious_indexes": [r["chunk_index"] for r in suspicious],
    }


# ─── Ortografia Local ────────────────────────────────────────────────────────

def check_spelling(text: str, lang: str = "português") -> list[str]:
    """
    Retorna lista de palavras com possível erro ortográfico.

    Usa pyspellchecker — funciona offline após instalação.
    """
    try:
        spell = _get_spellchecker(lang)
        words = text.split()
        # pyspellchecker ignora números e palavras muito curtas automaticamente
        misspelled = spell.unknown(words)
        return sorted(misspelled)
    except Exception as e:
        print(f"[SpellCheck] Aviso: falha ao verificar ortografia. Erro: {e}")
        return []


def spelling_report(text: str, lang: str = "português") -> dict:
    """
    Relatório de ortografia: palavras erradas e sugestões de correção.
    """
    try:
        spell = _get_spellchecker(lang)
        words = text.split()
        misspelled = spell.unknown(words)
        return {
            word: spell.candidates(word) or set()
            for word in sorted(misspelled)
        }
    except Exception:
        return {}
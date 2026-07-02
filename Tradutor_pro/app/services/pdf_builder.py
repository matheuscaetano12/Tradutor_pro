"""
pdf_builder.py — Gera PDF profissional a partir do texto traduzido.
Trata títulos fragmentados em múltiplas linhas (padrão do Google Translate).

Coloca em app/services/pdf_builder.py

Dependências:
    pip install reportlab
"""

import re
import logging
from pathlib import Path
from typing import Optional

from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    HRFlowable, KeepTogether, Frame, PageTemplate,
)
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase import pdfmetrics

logger = logging.getLogger(__name__)

# ── Paleta ────────────────────────────────────────────────────────────────────
C_BG      = colors.HexColor("#1a1a2e")   # azul escuro (capa)
C_GOLD    = colors.HexColor("#e8d5b7")   # dourado antigo
C_BLUE    = colors.HexColor("#a8c5da")   # azul claro
C_BROWN   = colors.HexColor("#8b4513")   # marrom bíblico
C_BLACK   = colors.HexColor("#1a1a1a")
C_GRAY    = colors.HexColor("#888888")
C_LGRAY   = colors.HexColor("#3d3d3d")

PAGE_W, PAGE_H = A5

# ── Textos localizados ──────────────────────────────────────────────────────
# Usados tanto para detectar estrutura no texto já traduzido (capítulo/parte)
# quanto para montar capa, sumário e cabeçalhos no idioma de destino.
CHAPTER_WORD = {
    "pt-BR": "Capítulo", "pt": "Capítulo", "pt-PT": "Capítulo",
    "en": "Chapter",
    "es": "Capítulo",
    "fr": "Chapitre",
    "de": "Kapitel",
}
PART_WORD = {
    "pt-BR": "Parte", "pt": "Parte", "pt-PT": "Parte",
    "en": "Part",
    "es": "Parte",
    "fr": "Partie",
    "de": "Teil",
}
BY_WORD = {
    "pt-BR": "por", "pt": "por", "pt-PT": "por",
    "en": "by",
    "es": "por",
    "fr": "par",
    "de": "von",
}
TOC_TITLE_WORD = {
    "pt-BR": "Sumário", "pt": "Sumário", "pt-PT": "Índice",
    "en": "Table of Contents",
    "es": "Índice",
    "fr": "Table des matières",
    "de": "Inhaltsverzeichnis",
}
LANGUAGE_DISPLAY_NAME = {
    "pt-BR": "Português do Brasil", "pt": "Português", "pt-PT": "Português",
    "en": "Inglês",
    "es": "Espanhol",
    "fr": "Francês",
    "de": "Alemão",
}


def _t(mapping: dict, language: str, fallback_key: str = "en") -> str:
    """Busca um texto localizado, com fallback para inglês e depois pt-BR."""
    return mapping.get(language) or mapping.get(fallback_key) or mapping.get("pt-BR") or ""


# ── Estilos ───────────────────────────────────────────────────────────────────
def _build_styles() -> dict:
    return {
        "cover_title": ParagraphStyle("CoverTitle",
            fontSize=22, fontName="Helvetica-Bold",
            textColor=C_GOLD, alignment=TA_CENTER,
            spaceAfter=8, leading=30,
        ),
        "cover_sub": ParagraphStyle("CoverSub",
            fontSize=12, fontName="Helvetica",
            textColor=C_BLUE, alignment=TA_CENTER,
            spaceAfter=6, leading=16,
        ),
        "cover_author": ParagraphStyle("CoverAuthor",
            fontSize=11, fontName="Helvetica-Oblique",
            textColor=C_GOLD, alignment=TA_CENTER,
        ),
        "part_heading": ParagraphStyle("PartHeading",
            fontSize=13, fontName="Helvetica-Bold",
            textColor=C_GOLD, alignment=TA_CENTER,
            spaceBefore=20, spaceAfter=10,
            borderPadding=8,
        ),
        "chapter_label": ParagraphStyle("ChapterLabel",
            fontSize=10, fontName="Helvetica",
            textColor=C_BROWN, alignment=TA_CENTER,
            spaceBefore=30, spaceAfter=4,
        ),
        "chapter_title": ParagraphStyle("ChapterTitle",
            fontSize=15, fontName="Helvetica-Bold",
            textColor=C_BROWN, alignment=TA_CENTER,
            spaceBefore=4, spaceAfter=16, leading=20,
        ),
        "body": ParagraphStyle("Body",
            fontSize=10, fontName="Helvetica",
            textColor=C_BLACK, alignment=TA_JUSTIFY,
            spaceBefore=3, spaceAfter=3,
            leading=15, firstLineIndent=18,
        ),
        "scripture": ParagraphStyle("Scripture",
            fontSize=9.5, fontName="Helvetica-Oblique",
            textColor=C_LGRAY, alignment=TA_JUSTIFY,
            leftIndent=22, rightIndent=22,
            spaceBefore=8, spaceAfter=8, leading=14,
        ),
        "toc_title": ParagraphStyle("TOCTitle",
            fontSize=16, fontName="Helvetica-Bold",
            textColor=C_BROWN, alignment=TA_CENTER,
            spaceAfter=20,
        ),
        "toc_part": ParagraphStyle("TOCPart",
            fontSize=11, fontName="Helvetica-Bold",
            textColor=C_BG, spaceBefore=10, spaceAfter=2,
        ),
        "toc_chapter": ParagraphStyle("TOCChapter",
            fontSize=10, fontName="Helvetica",
            textColor=C_BLACK, spaceBefore=2, spaceAfter=2,
            leftIndent=14,
        ),
        "page_num": ParagraphStyle("PageNum",
            fontSize=8, fontName="Helvetica",
            textColor=C_GRAY, alignment=TA_CENTER,
        ),
    }


# ── Parser robusto ────────────────────────────────────────────────────────────
# Padrões do texto gerado pelo Google Translate (títulos partidos em linhas)
# Agora construídos dinamicamente por idioma, já que o texto de entrada aqui
# já está traduzido (ex: "Chapitre 1" em francês, não "Capítulo 1").

_RE_CHAP_NUM    = re.compile(r"^(\d{1,2})\s+(.{3,60})$")               # "1 Dois Reinos..."
_RE_SCRIPTURE   = re.compile(r"\(\s*(NVI|NAS|KJV|TLB|ARC|ARA|NKJV)\s*\)", re.I)
_RE_PAGE_NUM    = re.compile(r"^\d{1,3}\s*$")                           # linhas só com número


def _build_patterns(language: str) -> dict:
    """Monta os regex de estrutura (parte/capítulo) usando a palavra certa
    para o idioma de destino da tradução."""
    chap_word = _t(CHAPTER_WORD, language)
    part_word = _t(PART_WORD, language)
    return {
        "chap_word": chap_word,
        "part_word": part_word,
        "PARTE_LABEL": re.compile(rf"^{re.escape(part_word)}\s+\d+\s*:?\s*$", re.I),
        "PARTE_FULL":  re.compile(rf"^{re.escape(part_word)}\s+(\d+)\s*[:\-–]?\s*(.*)", re.I),
        "CHAP_LABEL":  re.compile(rf"^{re.escape(chap_word)}\s+(\d+)\s*$", re.I),
        "CHAP_FULL":   re.compile(rf"^{re.escape(chap_word)}\s+(\d+)\s*[:\-–]?\s*(.*)", re.I),
    }


def _join_wrapped_lines(lines: list[str], patterns: dict, book_header_re: Optional[re.Pattern] = None) -> list[str]:
    """
    O PDF original (coluna estreita) quebra frases no meio.
    Junta linhas curtas consecutivas que NÃO são títulos/capítulos.
    """
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Linha vazia → parágrafo
        if not line:
            result.append("")
            i += 1
            continue

        # Cabeçalhos — nunca junta
        is_heading = (
            patterns["PARTE_LABEL"].match(line) or
            patterns["PARTE_FULL"].match(line) or
            patterns["CHAP_LABEL"].match(line) or
            patterns["CHAP_FULL"].match(line) or
            _RE_PAGE_NUM.match(line) or
            (book_header_re and book_header_re.match(line))
        )
        if is_heading:
            result.append(line)
            i += 1
            continue

        # Linha curta sem ponto final → possivelmente continuação
        # Acumula até encontrar linha que termina com pontuação ou é muito longa
        accumulated = line
        while i + 1 < len(lines):
            next_line = lines[i + 1]
            if not next_line:
                break
            if (
                patterns["PARTE_LABEL"].match(next_line) or
                patterns["PARTE_FULL"].match(next_line) or
                patterns["CHAP_LABEL"].match(next_line) or
                patterns["CHAP_FULL"].match(next_line) or
                _RE_PAGE_NUM.match(next_line) or
                (book_header_re and book_header_re.match(next_line))
            ):
                break
            # Se a linha atual termina com hífen (palavra partida)
            if accumulated.endswith("-"):
                accumulated = accumulated[:-1] + next_line
            # Se a linha atual é muito curta (< 55 chars) sem pontuação final
            elif len(accumulated) < 55 and not accumulated[-1] in ".!?:;\"'":
                accumulated = accumulated + " " + next_line
            else:
                break
            i += 1

        result.append(accumulated)
        i += 1

    return result


def _parse_sections(text: str, language: str = "pt-BR", book_title: str = "") -> list[dict]:
    """
    Retorna lista de seções:
    {"type": "part"|"chapter"|"scripture"|"para"|"blank", "content": str,
     "num": str (capítulos), "title": str}

    `language` define em qual idioma o texto JÁ TRADUZIDO está, para que os
    marcadores de estrutura ("Chapter"/"Chapitre"/"Kapitel"/etc.) sejam
    reconhecidos corretamente.
    """
    patterns  = _build_patterns(language)
    chap_word = patterns["chap_word"]
    part_word = patterns["part_word"]

    # Cabeçalho de página repetido (ex: título do livro no topo de cada página
    # do PDF original). Como o título já vem traduzido, casamos com o título
    # informado; se não houver título, não filtramos nada por esse critério.
    book_header_re = re.compile(rf"^{re.escape(book_title)}\s*$", re.I) if book_title else None

    raw_lines = [l.rstrip("\r") for l in text.split("\n")]

    # Remove cabeçalhos/rodapés repetidos e números de página isolados
    cleaned = []
    for line in raw_lines:
        s = line.strip()
        if _RE_PAGE_NUM.match(s) or (book_header_re and book_header_re.match(s)):
            continue
        cleaned.append(s)

    # Junta linhas fragmentadas
    joined = _join_wrapped_lines(cleaned, patterns, book_header_re)

    sections = []
    i = 0
    current_part_title = ""

    while i < len(joined):
        line = joined[i].strip()

        # Linha vazia
        if not line:
            i += 1
            continue

        # ── PARTE ────────────────────────────────────────────────────────────
        # Padrão: "Parte 1" na linha, depois "Parte 1: TÍTULO" na próxima
        if patterns["PARTE_LABEL"].match(line):
            # Pula o "Parte X" sozinho, pega a próxima que tem o título completo
            i += 1
            continue

        m = patterns["PARTE_FULL"].match(line)
        if m:
            num = m.group(1)
            title = m.group(2).strip()
            # Título pode estar fragmentado nas linhas seguintes
            while i + 1 < len(joined) and joined[i + 1].strip() and \
                  not patterns["PARTE_FULL"].match(joined[i + 1]) and \
                  not patterns["CHAP_LABEL"].match(joined[i + 1]) and \
                  not patterns["CHAP_FULL"].match(joined[i + 1]) and \
                  len(joined[i + 1].strip()) < 40:
                title = title + " " + joined[i + 1].strip()
                i += 1
            current_part_title = f"{part_word} {num}: {title.upper()}"
            sections.append({"type": "part", "content": current_part_title, "num": num, "title": title})
            i += 1
            continue

        # ── CAPÍTULO ─────────────────────────────────────────────────────────
        # Padrão A: "Capítulo 1" sozinho, próxima linha = "1 Dois Opostos / Reinos"
        m = patterns["CHAP_LABEL"].match(line)
        if m:
            chap_num = m.group(1)
            title = ""
            # Próxima linha costuma ser "N Título..."
            if i + 1 < len(joined):
                next_line = joined[i + 1].strip()
                mn = _RE_CHAP_NUM.match(next_line)
                if mn and mn.group(1) == chap_num:
                    title = mn.group(2).strip()
                    i += 1
                    # Título pode continuar na linha seguinte (fragmentado)
                    if i + 1 < len(joined):
                        nxt = joined[i + 1].strip()
                        if nxt and len(nxt) < 40 and not patterns["CHAP_LABEL"].match(nxt) \
                           and not patterns["PARTE_FULL"].match(nxt) and not nxt[0].isupper() or \
                           (nxt and len(nxt) < 25):
                            title = title + " " + nxt
                            i += 1
            sections.append({"type": "chapter", "content": f"{chap_word} {chap_num}", "num": chap_num, "title": title})
            i += 1
            continue

        # Padrão B: "Capítulo 1 — Título" numa linha só
        m = patterns["CHAP_FULL"].match(line)
        if m and m.group(2).strip():
            chap_num = m.group(1)
            title = m.group(2).strip()
            sections.append({"type": "chapter", "content": f"{chap_word} {chap_num}", "num": chap_num, "title": title})
            i += 1
            continue

        # ── CITAÇÃO BÍBLICA ───────────────────────────────────────────────────
        if _RE_SCRIPTURE.search(line):
            sections.append({"type": "scripture", "content": line})
            i += 1
            continue

        # ── PARÁGRAFO NORMAL ──────────────────────────────────────────────────
        sections.append({"type": "para", "content": line})
        i += 1

    return sections


# ── Capa ──────────────────────────────────────────────────────────────────────
def _build_cover(styles: dict, title: str, author: str, subtitle: str, language: str = "pt-BR") -> list:
    by_word      = _t(BY_WORD, language)
    lang_display = _t(LANGUAGE_DISPLAY_NAME, language)

    story = []
    story.append(Spacer(1, PAGE_H * 0.10))
    story.append(HRFlowable(width="100%", thickness=2, color=C_GOLD))
    story.append(Spacer(1, 18))
    story.append(Paragraph(title.upper(), styles["cover_title"]))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="55%", thickness=1, color=C_GOLD))
    story.append(Spacer(1, 12))
    if subtitle:
        story.append(Paragraph(subtitle, styles["cover_sub"]))
        story.append(Spacer(1, 12))
    story.append(Paragraph(f"{by_word} {author}", styles["cover_author"]))
    story.append(Spacer(1, 30))
    story.append(HRFlowable(width="100%", thickness=2, color=C_GOLD))
    story.append(Spacer(1, 12))
    story.append(Paragraph(lang_display, styles["cover_sub"]))
    story.append(PageBreak())
    return story


# ── Sumário ───────────────────────────────────────────────────────────────────
def _build_toc(styles: dict, sections: list, language: str = "pt-BR") -> list:
    toc_word  = _t(TOC_TITLE_WORD, language)
    chap_word = _t(CHAPTER_WORD, language)

    story = []
    story.append(Paragraph(toc_word, styles["toc_title"]))
    story.append(HRFlowable(width="75%", thickness=1, color=C_BROWN))
    story.append(Spacer(1, 14))

    for sec in sections:
        if sec["type"] == "part":
            story.append(Spacer(1, 6))
            story.append(Paragraph(sec["content"], styles["toc_part"]))
        elif sec["type"] == "chapter":
            label = f"{chap_word} {sec['num']}"
            if sec.get("title"):
                label += f" — {sec['title']}"
            story.append(Paragraph(label, styles["toc_chapter"]))

    story.append(PageBreak())
    return story


# ── Corpo ─────────────────────────────────────────────────────────────────────
def _build_body(styles: dict, sections: list, language: str = "pt-BR") -> list:
    chap_word = _t(CHAPTER_WORD, language)
    story = []

    for sec in sections:
        t = sec["type"]
        c = sec["content"]

        if t == "part":
            story.append(PageBreak())
            story.append(Spacer(1, PAGE_H * 0.25))
            story.append(HRFlowable(width="100%", thickness=1, color=C_GOLD))
            story.append(Spacer(1, 12))
            story.append(Paragraph(c, styles["part_heading"]))
            story.append(Spacer(1, 12))
            story.append(HRFlowable(width="100%", thickness=1, color=C_GOLD))
            story.append(PageBreak())

        elif t == "chapter":
            story.append(PageBreak())
            story.append(Spacer(1, 20))
            story.append(Paragraph(f"— {chap_word} {sec['num']} —", styles["chapter_label"]))
            story.append(HRFlowable(width="35%", thickness=1, color=C_BROWN))
            story.append(Spacer(1, 8))
            if sec.get("title"):
                story.append(Paragraph(sec["title"], styles["chapter_title"]))
            story.append(Spacer(1, 14))

        elif t == "scripture":
            story.append(Spacer(1, 4))
            story.append(Paragraph(c, styles["scripture"]))
            story.append(Spacer(1, 4))

        elif t == "para":
            story.append(Paragraph(c, styles["body"]))

    return story


# ── Cabeçalho / Rodapé ────────────────────────────────────────────────────────
class _BookCanvas(rl_canvas.Canvas):
    def __init__(self, filename, title="", author="", **kwargs):
        super().__init__(filename, **kwargs)
        self._doc_title  = title
        self._doc_author = author
        self._page_count = 0

    def showPage(self):
        self._page_count += 1
        self._draw_decorations()
        super().showPage()

    def _draw_decorations(self):
        p = self._page_count
        # Pula capa (p=1) e sumário (p=2)
        if p <= 2:
            return

        w, h = PAGE_W, PAGE_H
        self.saveState()
        self.setFont("Helvetica", 7)
        self.setFillColor(C_GRAY)

        # Cabeçalho
        self.setStrokeColor(C_BROWN)
        self.setLineWidth(0.5)
        self.line(1.4 * cm, h - 1.15 * cm, w - 1.4 * cm, h - 1.15 * cm)
        if p % 2 == 0:
            self.drawString(1.4 * cm, h - 0.95 * cm, self._doc_author.upper())
        else:
            self.drawRightString(w - 1.4 * cm, h - 0.95 * cm, self._doc_title.upper())

        # Rodapé com número de página (começa em 1 após sumário)
        self.line(1.4 * cm, 1.15 * cm, w - 1.4 * cm, 1.15 * cm)
        self.drawCentredString(w / 2, 0.75 * cm, str(p - 2))

        self.restoreState()


# ── Função principal ──────────────────────────────────────────────────────────
def build_translated_pdf(
    translated_text: str,
    output_path: str,
    title: str = "Guerra Espiritual",
    author: str = "Derek Prince",
    subtitle: str = "Uma Análise Bíblica da Batalha Espiritual",
    language: str = "pt-BR",
) -> str:
    output_path = str(output_path)

    styles   = _build_styles()
    sections = _parse_sections(translated_text, language=language, book_title=title)

    parts    = sum(1 for s in sections if s["type"] == "part")
    chapters = sum(1 for s in sections if s["type"] == "chapter")
    paras    = sum(1 for s in sections if s["type"] == "para")
    logger.info(f"[PDFBuilder] idioma={language} | {parts} partes | {chapters} capítulos | {paras} parágrafos")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A5,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.2 * cm,
        title=title,
        author=author,
        subject=subtitle,
        creator="TraductorPro",
    )

    toc_sections = [s for s in sections if s["type"] in ("part", "chapter")]

    story = []
    story += _build_cover(styles, title, author, subtitle, language)
    story += _build_toc(styles, toc_sections, language)
    story += _build_body(styles, sections, language)

    def make_canvas(filename, **kwargs):
        return _BookCanvas(filename, title=title, author=author, pagesize=A5)

    doc.build(story, canvasmaker=make_canvas)
    logger.info(f"[PDFBuilder] PDF gerado: {output_path}")
    return output_path


# ── CLI de teste ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    inp = sys.argv[1] if len(sys.argv) > 1 else "traduzido.txt"
    out = sys.argv[2] if len(sys.argv) > 2 else "output.pdf"
    with open(inp, encoding="utf-8", errors="replace") as f:
        text = f.read()
    result = build_translated_pdf(text, out)
    print(f"PDF gerado: {result}")
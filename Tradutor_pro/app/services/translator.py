# translator.py
from deep_translator import GoogleTranslator

# Mapeamento de nomes amigáveis para códigos do Google Translate
LANG_CODES = {
    "português": "pt",
    "inglês": "en",
    "espanhol": "es",
    "francês": "fr",
    "alemão": "de",
    "italiano": "it",
    "japonês": "ja",
    "chinês": "zh-CN",
    "russo": "ru",
    "árabe": "ar",
}


def _get_lang_code(lang_name: str) -> str:
    """Converte nome de idioma para código ISO."""
    return LANG_CODES.get(lang_name.lower(), lang_name)


def translate_text(text: str, source: str, target: str) -> str:
    """
    Tradução via Google Translate (gratuita, sem limite de tokens de IA).

    A revisão gramatical e a verificação de qualidade são feitas
    em etapas separadas pelo pipeline — veja grammar.py e quality_checker.py.
    """
    src_code = _get_lang_code(source)
    tgt_code = _get_lang_code(target)
    return GoogleTranslator(source=src_code, target=tgt_code).translate(text)

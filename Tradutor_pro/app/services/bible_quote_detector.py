#bible_quote_detector
import re

def is_bible_quote(text):

    return bool(
        re.match(r"^\d+\s", text)
    )
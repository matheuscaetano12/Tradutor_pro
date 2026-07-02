# chunker.py

def split_text_into_chunks(text: str, max_chars: int = 3500) -> list[str]:
    """
    Divide o texto em chunks respeitando parágrafos e frases.
    
    - max_chars=3500 dá margem segura para o limite de 5000 do Google Translate
    - Nunca corta no meio de uma frase
    - Preserva parágrafos inteiros sempre que possível
    """
    paragraphs = text.split("\n")
    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        # Parágrafo cabe no chunk atual
        if len(current_chunk) + len(paragraph) + 1 <= max_chars:
            current_chunk += paragraph + "\n"

        # Parágrafo não cabe — salva o atual e começa novo
        elif current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph + "\n"

            # Parágrafo sozinho ainda é maior que o limite (raro, mas possível)
            if len(current_chunk) > max_chars:
                current_chunk = _split_by_sentences(current_chunk, max_chars, chunks)

        # Chunk vazio e parágrafo já é grande demais
        else:
            current_chunk = _split_by_sentences(paragraph + "\n", max_chars, chunks)

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def _split_by_sentences(text: str, max_chars: int, chunks: list) -> str:
    """
    Fallback: divide por frases quando um parágrafo é maior que max_chars.
    Retorna o restante que ainda não foi adicionado aos chunks.
    """
    # Separadores de frase em ordem de preferência
    for sep in (". ", "! ", "? ", "; ", ", "):
        sentences = text.split(sep)
        if len(sentences) > 1:
            current = ""
            for i, sentence in enumerate(sentences):
                # Reconstrói o separador (exceto na última parte)
                part = sentence + (sep if i < len(sentences) - 1 else "")
                if len(current) + len(part) <= max_chars:
                    current += part
                else:
                    if current:
                        chunks.append(current.strip())
                    current = part
            return current  # retorna o restante para continuar acumulando

    # Último recurso: corte duro (não deveria chegar aqui em texto normal)
    while len(text) > max_chars:
        chunks.append(text[:max_chars].strip())
        text = text[max_chars:]
    return text
    paragraphs = text.split("\n")
    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 1 > max_chars and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = ""

        current_chunk += paragraph + "\n"

        while len(current_chunk) > max_chars:
            chunks.append(current_chunk[:max_chars].strip())
            current_chunk = current_chunk[max_chars:]

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks
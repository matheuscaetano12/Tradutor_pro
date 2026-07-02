# retry.py
"""
Retry com backoff exponencial — sem dependência de OpenAI/Groq/Mistral.

Agora trata apenas erros do Google Translate (deep-translator),
que é o único serviço externo que permanece no pipeline.
"""

import time

# Erros do deep-translator
try:
    from deep_translator.exceptions import RequestError as GoogleRequestError
except ImportError:
    GoogleRequestError = None

# Mensagens de limite — quando aparecem, não adianta fazer retry
LIMIT_HINTS = [
    "quota",
    "daily",
    "exceeded",
    "limit exceeded",
    "too many requests",
    "429",
]


def _is_hard_limit(error: Exception) -> bool:
    """Detecta se o erro é limite permanente (não adianta esperar)."""
    msg = str(error).lower()
    return any(hint in msg for hint in LIMIT_HINTS)


def call_with_retry(func, *args, max_retries: int = 8, base_delay: float = 5.0, **kwargs):
    """
    Chama func(*args, **kwargs) com backoff exponencial.

    Trata:
    - RequestError do Google Translate (rede / timeout / rate limit)
    - Qualquer Exception genérica com retry limitado

    Aborta imediatamente se detectar limite de quota esgotada.
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)

        except Exception as e:
            last_error = e

            # Limite de quota — não adianta esperar
            if _is_hard_limit(e):
                raise Exception(
                    "⚠️ Limite de requisições do Google Translate atingido. "
                    "Aguarde alguns minutos e tente novamente. "
                    "A tradução foi salva até o último checkpoint."
                ) from e

            # Erros do Google Translate — retry com backoff linear suave
            if GoogleRequestError and isinstance(e, GoogleRequestError):
                wait = base_delay * (attempt + 1)  # 5, 10, 15, 20...
                print(f"[Retry {attempt + 1}/{max_retries}] Google Translate falhou. Aguardando {wait:.0f}s...")
                time.sleep(wait)
                continue

            # Erros não recuperáveis — propaga imediatamente
            raise

    raise Exception(
        f"Limite de tentativas excedido ({max_retries}x). "
        f"Último erro: {last_error}"
    )
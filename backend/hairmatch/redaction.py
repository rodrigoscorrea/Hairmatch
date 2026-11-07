"""
Redaction of personal data in free text (#194, TEL-44, TEL-45, TEL-86).

The patterns and their order are the ones the OTel Collector applies (docker/observability/otel/config.yaml,
#193), so the same data is masked the same way at both barriers and is searched by the same marker in Loki.
The app adds one rule the Collector lacks: the WhatsApp identifier (`<digits>@s.whatsapp.net`).
A digit sequence shaped like a phone, CPF or CNPJ is masked even when it is not personal data: the safe side.
"""
import re

# (pattern, marker), in the order they are applied: the JWT first (it contains pieces that look like an e-mail
# and numbers), then the e-mail, CNPJ, CPF and the phone last. The WhatsApp identifier goes before the e-mail
# rule, which would otherwise take `<digits>@s.whatsapp.net` for an address.
REPLACEMENTS = tuple(
    (re.compile(pattern), marker)
    for pattern, marker in (
        (r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', '[jwt]'),
        (r'\d+@s\.whatsapp\.net', '[telefone]'),
        (r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', '[email]'),
        (r'\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b', '[cnpj]'),
        (r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b', '[cpf]'),
        (r'(\+?55\s?)?\(?\b\d{2}\)?\s?9?\d{4}-?\d{4}\b', '[telefone]'),
    )
)

_URL = re.compile(r'(https?://[^/\s\'"<>]+)(/[^\s\'"<>]*)?')
# urllib3 words a connection error as "... Max retries exceeded with url: /ws/69000000/json/ (Caused by ...)": a bare path.
_URL_PATH = re.compile(r'(\burl: )(/[^\s\'"<>)]*)')
_ARN = re.compile(r'arn:aws[\w-]*:[^\s\'",]+')


def redact(text):
    """`text` with the JWT, e-mail, CNPJ, CPF, phone and WhatsApp number replaced by their markers."""
    for pattern, marker in REPLACEMENTS:
        text = pattern.sub(marker, text)
    return text


def scrub_urls(text):
    """Keeps the scheme and the host of every URL in `text` and drops the path and the query string (a CEP lives in a path)."""
    text = _URL.sub(lambda match: match.group(1) + ('/[path]' if match.group(2) else ''), text)
    return _URL_PATH.sub(r'\1/[path]', text)


def scrub_arns(text):
    """Replaces every AWS ARN (an SNS endpoint ARN identifies a device)."""
    return _ARN.sub('[arn]', text)


def sanitize_text(text):
    """Everything a span string goes through: URLs, ARNs, then the personal-data patterns."""
    return redact(scrub_arns(scrub_urls(text)))

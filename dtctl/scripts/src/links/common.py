"""Shared normalization for Dynatrace evidence links."""

from urllib.parse import urlsplit, urlunsplit


def normalize_environment_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("environment URL must be an absolute https URL")
    if parsed.query or parsed.fragment:
        raise ValueError("environment URL must not contain a query or fragment")
    base_path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, base_path, "", ""))


def normalize_dql(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if not normalized.strip():
        raise ValueError("DQL file must not be empty")
    for line in normalized.splitlines():
        quote_character: str | None = None
        escaped = False
        for index, character in enumerate(line):
            if escaped:
                escaped = False
                continue
            if character == "\\" and quote_character is not None:
                escaped = True
                continue
            if character in {'"', "'"}:
                if quote_character == character:
                    quote_character = None
                elif quote_character is None:
                    quote_character = character
                continue
            if character == "|" and quote_character is None and line[:index].strip():
                raise ValueError(
                    "put every DQL pipeline command on its own line before linking"
                )
    return normalized

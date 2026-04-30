import re


PII_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
]

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore previous instructions", re.IGNORECASE),
    re.compile(r"reveal system prompt", re.IGNORECASE),
    re.compile(r"developer instructions", re.IGNORECASE),
]


def contains_disallowed_pii(text: str) -> bool:
    return any(pattern.search(text) for pattern in PII_PATTERNS)


def contains_prompt_injection(text: str) -> bool:
    return any(pattern.search(text) for pattern in PROMPT_INJECTION_PATTERNS)


def validate_user_message(text: str) -> tuple[bool, str]:
    if contains_disallowed_pii(text):
        return (
            False,
            "I cannot process sensitive identifiers like card or SSN data. Please remove them and try again.",
        )

    if contains_prompt_injection(text):
        return (
            False,
            "I can help with Meridian support tasks, but I cannot follow unsafe instruction override attempts.",
        )

    return True, ""

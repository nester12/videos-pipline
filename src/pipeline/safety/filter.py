import re

BLOCKED = {
    'dangerous challenge': 'dangerous challenge',
    'weapon': 'weapons', 'gun': 'weapons', 'knife': 'weapons',
    'drug': 'drugs', 'cocaine': 'drugs', 'heroin': 'drugs',
    'gambling': 'gambling', 'casino': 'gambling', 'betting': 'gambling',
    'explicit sex': 'explicit sexual content', 'porn': 'explicit sexual content',
    'self harm': 'self-harm', 'suicide': 'self-harm',
}


def is_safe_topic(text: str) -> tuple[bool, str]:
    normalized = re.sub(r'\s+', ' ', text.lower()).strip()
    for phrase, reason in BLOCKED.items():
        if phrase in normalized:
            return False, reason
    return True, ''

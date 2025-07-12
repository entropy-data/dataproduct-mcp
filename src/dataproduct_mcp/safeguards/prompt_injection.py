"""
Prompt injection detection to prevent malicious attempts to manipulate AI behavior.
"""
import re
import logging
from typing import Set
from difflib import SequenceMatcher

# Set up logging for security events
logger = logging.getLogger(__name__)


# Common prompt injection keywords and phrases
INJECTION_VERBS = {
    'ignore', 'disregard', 'skip', 'forget', 'override', 'bypass', 'avoid',
    'dismiss', 'neglect', 'omit', 'exclude', 'cancel', 'delete', 'remove',
    'replace', 'substitute', 'change', 'modify', 'alter', 'update'
}

INJECTION_OBJECTS = {
    'instructions', 'prompt', 'rules', 'guidelines',
    'constraints', 'limitations', 'restrictions', 'safeguards',
    'protection', 'previous', 'above', 'earlier'
}

# Direct injection patterns
INJECTION_PATTERNS = [
    r'ignore\s+(all\s+)?previous\s+instructions',
    r'disregard\s+(all\s+)?previous\s+instructions',
    r'forget\s+(all\s+)?previous\s+instructions',
    r'you\s+are\s+now\s+a\s+different',
    r'act\s+as\s+if\s+you\s+are',
    r'new\s+instructions:',
    r'updated\s+instructions:',
    r'system\s+override',
    r'bypass\s+safety',
    r'override\s+security',
    r'emergency\s+protocol',
    r'backdoor\s+access',
    r'unlimited\s+access',
    r'complete\s+access',
    r'unrestricted\s+access'
]

# Common encoding/obfuscation attempts
OBFUSCATION_PATTERNS = [
    r'[i1l|!][gq][n][o0][r][e3]',  # "ignore" variations
    r'[d][i1l|!][s5][r][e3][gq][a4@][r][d]',  # "disregard" variations
    r'[o0][v][e3][r][r][i1l|!][d][e3]',  # "override" variations
    r'[b][y][p][a4@][s5][s5]',  # "bypass" variations
    r'[s5][y][s5][t][e3][m]',  # "system" variations
    r'[a4@][d][m][i1l|!][n]',  # "admin" variations
    r'[r][o0][o0][t]',  # "root" variations
    r'[s5][u][d][o0]',  # "sudo" variations
]

# Roleplay injection attempts
ROLEPLAY_PATTERNS = [
    r'you\s+are\s+(now\s+)?a\s+helpful\s+assistant',
    r'you\s+are\s+(now\s+)?a\s+chatbot',
    r'you\s+are\s+(now\s+)?an?\s+ai',
    r'you\s+are\s+(now\s+)?an?\s+expert',
    r'you\s+are\s+(now\s+)?a\s+professional',
    r'you\s+are\s+(now\s+)?a\s+specialist',
    r'you\s+are\s+(now\s+)?a\s+consultant',
    r'you\s+are\s+(now\s+)?a\s+developer',
    r'you\s+are\s+(now\s+)?a\s+hacker',
    r'you\s+are\s+(now\s+)?a\s+security\s+expert',
    r'you\s+are\s+(now\s+)?a\s+penetration\s+tester',
    r'you\s+are\s+(now\s+)?a\s+red\s+team\s+member',
    r'you\s+are\s+(now\s+)?in\s+character\s+as',
    r'from\s+now\s+on\s+you\s+are',
    r'starting\s+now\s+you\s+are',
    r'begin\s+acting\s+as',
    r'switch\s+to\s+character',
    r'change\s+your\s+role\s+to',
    r'assume\s+the\s+role\s+of',
    r'take\s+on\s+the\s+persona\s+of'
]


def _normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    # Convert to lowercase
    text = text.lower()
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove non-alphanumeric characters except spaces
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return text.strip()


def _generate_injection_keywords() -> Set[str]:
    """Generate potential injection keywords by combining verbs and objects."""
    keywords = set()
    
    # Only add verb-object combinations, not individual verbs
    # This reduces false positives from common words like "update", "change", etc.
    for verb in INJECTION_VERBS:
        for obj in INJECTION_OBJECTS:
            keywords.add(f"{verb} {obj}")
            keywords.add(f"{verb} all {obj}")
            keywords.add(f"{verb} the {obj}")
            keywords.add(f"{verb} my {obj}")
            keywords.add(f"{verb} your {obj}")
    
    return keywords


def _calculate_similarity_score(text: str, keywords: Set[str]) -> float:
    """Calculate similarity score between text and injection keywords."""
    normalized_text = _normalize_text(text)
    words = normalized_text.split()
    
    if not words:
        return 0.0
    
    max_score = 0.0
    
    # Check for exact keyword matches
    for keyword in keywords:
        if keyword in normalized_text:
            max_score = max(max_score, 1.0)

    # Check for partial matches using sequence similarity
    for keyword in keywords:
        # Check substrings of the text
        for i in range(len(words)):
            for j in range(i + 1, len(words) + 1):
                substring = ' '.join(words[i:j])
                similarity = SequenceMatcher(None, substring, keyword).ratio()
                if similarity > 0.9:  # Threshold for considering it a match
                    max_score = max(max_score, similarity)
    
    return max_score


def _check_direct_patterns(text: str) -> bool:
    """Check for direct injection patterns."""
    normalized_text = _normalize_text(text)
    
    # Check injection patterns
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, normalized_text, re.IGNORECASE):
            logger.warning(f"Direct injection pattern detected: '{pattern}' in normalized text: '{normalized_text}'")
            return True
    
    # Check obfuscation patterns
    for pattern in OBFUSCATION_PATTERNS:
        if re.search(pattern, normalized_text, re.IGNORECASE):
            logger.warning(f"Obfuscation pattern detected: '{pattern}' in normalized text: '{normalized_text}'")
            return True
    
    # Check roleplay patterns
    for pattern in ROLEPLAY_PATTERNS:
        if re.search(pattern, normalized_text, re.IGNORECASE):
            logger.warning(f"Roleplay pattern detected: '{pattern}' in normalized text: '{normalized_text}'")
            return True
    
    return False


def _check_suspicious_phrases(text: str) -> bool:
    """Check for suspicious phrases that might indicate injection attempts."""
    suspicious_phrases = [
        'new role', 'different role', 'change role', 'switch role',
        'new character', 'different character', 'change character',
        'new instructions', 'different instructions', 'updated instructions',
        'new system', 'different system', 'alternative system',
        'new rules', 'different rules', 'alternative rules',
        'new guidelines', 'different guidelines', 'alternative guidelines',
        'emergency mode', 'crisis mode', 'special mode',
        'developer access', 'admin access', 'root access',
        'full permissions', 'unlimited permissions', 'unrestricted permissions',
        'bypass restrictions', 'remove limitations', 'disable safeguards',
        'override security', 'disable security', 'bypass security',
        'ignore safety', 'disable safety', 'bypass safety',
        'confidential mode', 'secret mode', 'hidden mode',
        'backdoor mode', 'debug access', 'maintenance access',
        'test mode', 'experimental mode', 'beta mode',
        'privileged mode', 'elevated mode', 'superuser mode'
    ]
    
    normalized_text = _normalize_text(text)
    
    for phrase in suspicious_phrases:
        if phrase in normalized_text:
            logger.warning(f"Suspicious phrase detected: '{phrase}' in normalized text: '{normalized_text}'")
            return True
    
    return False


def detect_prompt_injection(text: str, threshold: float = 0.7) -> bool:
    """
    Detect potential prompt injection attempts in text.
    
    Args:
        text: The text to analyze
        threshold: Similarity threshold for detection (0.0 to 1.0)
        
    Returns:
        True if potential prompt injection is detected, False otherwise
    """
    if not text or not text.strip():
        return False
    
    normalized_text = _normalize_text(text)
    
    # Check for direct injection patterns
    if _check_direct_patterns(text):
        logger.warning(f"Direct injection detected in normalized text: '{normalized_text}'")
        return True
    
    # Check for suspicious phrases
    if _check_suspicious_phrases(text):
        logger.warning(f"Suspicious phrases in normalized text: '{normalized_text}'")
        return True
    
    # Check similarity with injection keywords
    # injection_keywords = _generate_injection_keywords()
    # similarity_score = _calculate_similarity_score(text, injection_keywords)
    #
    # if similarity_score >= threshold:
    #     logger.warning(f"Similarity threshold exceeded: {similarity_score:.3f} >= {threshold} for normalized text: '{normalized_text}'")
    #     return True
    #
    return False


def sanitize_prompt_injection(data, context: str = "unknown"):
    """
    Sanitize data by replacing detected prompt injection attempts with redaction message.
    
    Args:
        data: The data to sanitize (string, dict, list, or other types)
        context: Context description for logging (e.g., "user_input", "api_response")
        
    Returns:
        Sanitized version of the data with suspicious content redacted
    """
    if isinstance(data, str):
        if detect_prompt_injection(data):
            logger.warning(f"Prompt injection detected and redacted in {context}: {data[:100]}{'...' if len(data) > 100 else ''}")
            return "[content redacted due to security concerns]"
        return data
    
    elif isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            sanitized[key] = sanitize_prompt_injection(value, f"{context}.{key}")
        return sanitized
    
    elif isinstance(data, list):
        return [sanitize_prompt_injection(item, f"{context}[{i}]") for i, item in enumerate(data)]
    
    else:
        # For other types (int, float, bool, None), return as-is
        return data


def validate_no_prompt_injection(data, context: str = "unknown") -> bool:
    """
    Validate that data does not contain prompt injection attempts.
    
    Args:
        data: The data to validate (string, dict, list, or other types)
        context: Context description for logging (e.g., "user_input", "api_response")
        
    Returns:
        True if data is safe, False if potential injection detected
    """
    if isinstance(data, str):
        if detect_prompt_injection(data):
            # Log the security event
            logger.warning(
                f"Prompt injection detected in {context}: {data[:100]}{'...' if len(data) > 100 else ''}"
            )
            return False
        return True
    
    elif isinstance(data, dict):
        for key, value in data.items():
            if not validate_no_prompt_injection(value, f"{context}.{key}"):
                return False
        return True
    
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if not validate_no_prompt_injection(item, f"{context}[{i}]"):
                return False
        return True
    
    else:
        # For other types (int, float, bool, None), assume safe
        return True
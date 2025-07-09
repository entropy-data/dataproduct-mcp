"""
Read-only guard to prevent write statements and other dangerous SQL operations.
"""
import re
from typing import Tuple


# SQL keywords that indicate write operations
WRITE_KEYWORDS = {
    'insert', 'update', 'delete', 'drop', 'create', 'alter', 'truncate',
    'grant', 'revoke', 'merge', 'replace', 'upsert'
}

# Additional dangerous patterns
DANGEROUS_PATTERNS = [
    r';\s*(exec|execute|xp_cmdshell|sp_executesql)',
    r'--.*(\n|$)',  # SQL comments that could hide malicious code
    r'/\*.*\*/',    # Block comments
    r'\bunion\s+select\b',
    r'\bunion\s+all\s+select\b',
    r';\s*[a-zA-Z]',  # Multiple statements
]


def validate_readonly_query(query: str) -> bool:
    """
    Validate that a query is read-only and safe to execute.
    
    Args:
        query: The SQL query to validate
        
    Returns:
        True if query is safe, False otherwise
    """
    if not query or not query.strip():
        return False
    
    query_lower = query.lower().strip()
    
    # Check for write keywords
    for keyword in WRITE_KEYWORDS:
        if re.search(r'\b' + keyword + r'\b', query_lower):
            return False
    
    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return False
    
    # Must start with SELECT, WITH, or SHOW
    if not re.match(r'^\s*(select|with|show)\b', query_lower):
        return False
    
    return True
import re
from typing import Tuple, Optional


RATE_LIMIT_PATTERNS = [
    re.compile(r"rate[\s\-_]?limit", re.IGNORECASE),
    re.compile(r"usage[\s\-_]?limit", re.IGNORECASE),
    re.compile(r"hit\s+your\s+(usage\s+)?limit", re.IGNORECASE),
    re.compile(r"too\s+many\s+requests", re.IGNORECASE),
    re.compile(r"quota\s+exceeded", re.IGNORECASE),
    re.compile(r"429\s+Too\s+Many\s+Requests", re.IGNORECASE),
    re.compile(r"please\s+wait\s+before\s+sending\s+another\s+message", re.IGNORECASE),
    re.compile(r"try\s+again\s+later", re.IGNORECASE),
    re.compile(r"resets\s+(at|in)\s+\d+", re.IGNORECASE),
    re.compile(r"capacity\s+exceeded", re.IGNORECASE),
]

AUTH_EXPIRED_PATTERNS = [
    re.compile(r"oauth\s+session\s+expired", re.IGNORECASE),
    re.compile(r"failed\s+to\s+authenticate", re.IGNORECASE),
    re.compile(r"not\s+logged\s+in", re.IGNORECASE),
    re.compile(r"token\s+expired", re.IGNORECASE),
]


class OutputDetector:
    """Detects rate limits and authentication failures from Claude CLI outputs."""

    @classmethod
    def check_line(cls, line: str) -> Tuple[bool, Optional[str]]:
        """
        Returns (is_event, event_type)
        event_type can be 'rate_limit', 'auth_expired', or None.
        """
        if not line:
            return False, None

        for pattern in RATE_LIMIT_PATTERNS:
            if pattern.search(line):
                return True, "rate_limit"

        for pattern in AUTH_EXPIRED_PATTERNS:
            if pattern.search(line):
                return True, "auth_expired"

        return False, None

"""Security/privacy patterns shared by the whole devlogkit pipeline.

Two layers, matching docs/devlog-policy.md:
  1. Metadata-level (Phase 1, unchanged): scan commit subject + file names.
  2. Diff-content-level (Phase 2, new): scan the actual text of a diff hunk
     before any fragment of it is allowed into a Sanitized Change Summary.
     Layer 2 only ever runs on files that already passed the path denylist
     in this module — a file matching PATH_DENYLIST_PATTERNS never has its
     diff read at all, regardless of what secret scanning might find.
"""
import re

# --- Layer 1: commit-message / file-name metadata (Phase 1) ---------------

SECRET_MESSAGE_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"secret", r"password", r"passwd", r"token", r"api[\s_-]?key",
        r"access[\s_-]?key", r"credential", r"oauth", r"private[\s_-]?key",
        r"aws_access_key_id", r"aws_secret_access_key", r"bearer", r"ssh[\s_-]?key",
    ]
]
SECRET_FILENAME_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"(^|[\\/])\.env(\.|$|[\\/])", r"\.pem$", r"\.key$",
        r"credential", r"secret",
    ]
]


def contains_secret_pattern(text):
    return any(p.search(text) for p in SECRET_MESSAGE_PATTERNS)


def filename_is_secret_like(path):
    return any(p.search(path) for p in SECRET_FILENAME_PATTERNS)


# --- Layer 2: path denylist gating whether a diff may be read at all ------

# Deliberately broad / over-exclusive: a false positive here just means a
# file's diff content isn't used for extra detail (its name/stat still
# appear in the article via the existing Phase 1 metadata path), so there
# is no safety cost to erring toward "don't read it".
PATH_DENYLIST_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"(^|[\\/])\.env(\.|$|[\\/])",
        r"\.pem$", r"\.key$", r"\.pfx$", r"\.p12$", r"\.pkcs12$",
        r"(^|[\\/])id_rsa", r"(^|[\\/])id_ed25519", r"(^|[\\/])id_dsa",
        r"credential", r"secret", r"password", r"\.htpasswd",
        r"(^|[\\/])\.aws([\\/]|$)", r"(^|[\\/])\.ssh([\\/]|$)",
        r"(^|[\\/])\.kube([\\/]|$)",
        r"(^|[\\/])(internal|private)[_-]?config",
        r"(^|[\\/])(private|personal)[_-]?data",
        # Lockfiles / generated / vendored / build output: not secret, but
        # never useful signal for "what changed conceptually", and often
        # huge (wasted read for no article value).
        r"\.lock$", r"(^|[\\/])(package-lock\.json|skills-lock\.json|composer\.lock)$",
        r"(^|[\\/])(node_modules|vendor|dist|build|target|__pycache__|\.venv|venv)([\\/]|$)",
        r"\.min\.(js|css)$",
        # Binary-ish extensions (git show would emit "Binary files differ"
        # for these anyway, but skip the subprocess call rather than
        # relying on parsing that message).
        r"\.(png|jpg|jpeg|gif|webp|ico|pdf|zip|tar|gz|7z|exe|dll|so|dylib|bin|db|sqlite3?|woff2?|ttf|otf|mp4|mp3|wav)$",
    ]
]

# Extra patterns for scanning actual diff LINE content (not just paths).
# Broader than SECRET_MESSAGE_PATTERNS because diff content can contain the
# literal secret *value*, not just a word describing one.
SECRET_VALUE_PATTERNS = [
    re.compile(p) for p in [
        r"AKIA[0-9A-Z]{16}",                       # AWS access key ID
        r"ASIA[0-9A-Z]{16}",                        # AWS STS temp key ID
        r"sk-[A-Za-z0-9]{20,}",                     # OpenAI/Anthropic-style secret key prefix
        r"ghp_[A-Za-z0-9]{30,}",                    # GitHub personal access token
        r"xox[baprs]-[A-Za-z0-9-]{10,}",            # Slack token
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",      # PEM private key block
        r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",  # JWT-shaped
    ]
] + [
    re.compile(p, re.IGNORECASE) for p in [
        r"(api[_-]?key|secret|token|password|passwd)\s*[:=]\s*['\"][^'\"]{6,}['\"]",
    ]
]


def is_denylisted_path(path):
    return any(p.search(path) for p in PATH_DENYLIST_PATTERNS)


def scan_lines_for_secrets(lines):
    """Return True if any line looks like it contains a secret VALUE (not
    just a word about secrets — that's SECRET_MESSAGE_PATTERNS' job on
    commit subjects). Used to veto using a diff hunk's content even for
    files that passed the path denylist, since a denylist can never be
    exhaustive (e.g. a secret accidentally pasted into an otherwise-normal
    source file)."""
    for line in lines:
        if any(p.search(line) for p in SECRET_VALUE_PATTERNS):
            return True
    return False

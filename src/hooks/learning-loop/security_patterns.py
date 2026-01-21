"""
Security patterns for AdvisoryVerifier.
Separated into its own file for easier editing and maintenance.
"""

# Risky patterns for advisory verification
RISKY_PATTERNS = {
    'code': [
        (r'eval\s*\(', 'eval() detected - potential code injection risk'),
        (r'exec\s*\(', 'exec() detected - potential code injection risk'),
        (r'subprocess.*shell\s*=\s*True', 'shell=True in subprocess - potential command injection'),
        # Password patterns - multiple formats
        (r'password\s*[:=]\s*["\'][^"\']+["\']', 'Hardcoded password detected'),
        (r'"password"\s*:\s*"[^"]+"', 'Hardcoded password in JSON'),
        (r'["\']password:\s*[^"\']{3,}["\']', 'Password value in string literal'),
        # API keys and tokens
        (r'["\']?api[_-]?key["\']?\s*[:=]\s*["\'][^"\']+["\']', 'Hardcoded API key detected'),
        (r'["\']?secret["\']?\s*[:=]\s*["\'][^"\']+["\']', 'Hardcoded secret detected'),
        (r'["\']?token["\']?\s*[:=]\s*["\'][^"\']+["\']', 'Hardcoded token detected'),
        (r'["\']?credential[s]?["\']?\s*[:=]\s*["\'][^"\']+["\']', 'Hardcoded credentials detected'),
        (r'Bearer\s+[A-Za-z0-9_-]{20,}', 'Hardcoded bearer token'),
        (r'(PRIVATE_KEY|PRIV_KEY)\s*=', 'Private key assignment detected'),
        # SQL injection
        (r'SELECT.*\+.*user', 'Potential SQL injection - string concatenation in query'),
    ],
    'file_operations': [
        (r'rm\s+-rf\s+/', 'Dangerous recursive delete from root'),
        (r'chmod\s+777', 'Overly permissive file permissions'),
        (r'>\s*/etc/', 'Writing to system config directory'),
    ],
    'deserialization': [
        (r'pickle\.loads?\s*\(', 'pickle.load/loads - insecure deserialization risk'),
        (r'yaml\.load\s*\([^,)]*\)(?!\s*,\s*Loader)', 'yaml.load without SafeLoader - code execution risk'),
        (r'marshal\.loads?\s*\(', 'marshal.load - insecure deserialization'),
    ],
    'cryptography': [
        (r'hashlib\.md5\s*\(', 'MD5 hash - cryptographically weak, avoid for security'),
        (r'hashlib\.sha1\s*\(', 'SHA1 hash - cryptographically weak for passwords'),
        (r'random\.(randint|random|choice|shuffle)\s*\(', 'random module - not cryptographically secure, use secrets module'),
    ],
    'command_injection': [
        (r'os\.system\s*\(', 'os.system - prefer subprocess with shell=False'),
        (r'os\.popen\s*\(', 'os.popen - potential command injection'),
    ],
    'path_traversal': [
        (r'\.\.[/\\]\.\.[/\\]', 'Path traversal pattern (../ or ..\\) detected'),
        (r'open\s*\([^)]*\+[^)]*user', 'File open with user input concatenation - validate path'),
    ],
    'network': [
        (r'verify\s*=\s*False', 'SSL/TLS verification disabled'),
        (r'ssl\._create_unverified_context', 'Unverified SSL context - insecure'),
        (r'requests\.(get|post|put|delete|patch|head|options)\s*\((?![^)]*timeout)[^)]*\)', 'requests call without timeout - may hang indefinitely'),
    ],
    'xml_security': [
        (r'xml\.etree\.ElementTree\.parse\s*\(', 'XML parse without DTD protection - potential XXE vulnerability'),
        (r'\w+\.parse\s*\(\s*[a-zA-Z_]\w*', 'Variable passed to .parse() - verify XXE protection if parsing XML'),
        (r'xml\.dom\.minidom\.parse\s*\(', 'XML parse without DTD protection - potential XXE vulnerability'),
        (r'lxml\.etree\.parse\s*\(', 'lxml XML parse - verify resolve_entities=False for XXE protection'),
    ],
}

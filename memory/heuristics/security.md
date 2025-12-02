# Heuristics: security

Generated from failures, successes, and observations in the **security** domain.

---

## H-79: Always sanitize user input used in file paths - use character whitelisting not blacklisting

**Confidence**: 0.95
**Source**: failure
**Created**: 2025-12-01  # TIME-FIX-2: Use consistent date

Domain parameter path traversal attack demonstrated that any user input used in file paths must be sanitized. Use tr -cd '[:alnum:]-' to whitelist safe characters. Remove null bytes, newlines, and path separators. Validate length. Fail securely if sanitization results in empty string.

---


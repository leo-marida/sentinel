"""
Seed the vuln_knowledge table with OWASP Top 10 CWE entries.
Run once after setting up the database:
    cd backend
    .venv\Scripts\python seed_vuln_knowledge.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import AsyncOpenAI
from app.config import settings
from app.db.client import get_supabase

VULNS = [
    {
        "cve_id": "CWE-89",
        "title": "SQL Injection",
        "description": "User-supplied data is inserted into SQL queries without proper sanitisation, allowing attackers to manipulate database queries.",
        "remediation": "Use parameterised queries or prepared statements. Never concatenate user input into SQL strings. Use an ORM with proper escaping.",
        "severity": "critical",
        "tags": ["injection", "owasp-a03", "database"],
    },
    {
        "cve_id": "CWE-79",
        "title": "Cross-Site Scripting (XSS)",
        "description": "Application includes untrusted data in web pages without proper validation, allowing attackers to execute scripts in victims' browsers.",
        "remediation": "Escape all output using context-aware encoding. Use Content Security Policy headers. Validate and sanitise all user inputs.",
        "severity": "high",
        "tags": ["xss", "owasp-a03", "injection"],
    },
    {
        "cve_id": "CWE-78",
        "title": "OS Command Injection",
        "description": "Application constructs OS commands using externally-influenced input, allowing attackers to execute arbitrary commands on the host.",
        "remediation": "Avoid shell commands entirely. If unavoidable, use allowlists for valid inputs and never pass user input directly to shell functions.",
        "severity": "critical",
        "tags": ["injection", "owasp-a03", "command-injection"],
    },
    {
        "cve_id": "CWE-22",
        "title": "Path Traversal",
        "description": "Application uses user-controlled input to construct file paths without neutralising path traversal sequences like '../'.",
        "remediation": "Resolve canonical paths and verify they start with the expected base directory. Use allowlists for permitted filenames.",
        "severity": "high",
        "tags": ["path-traversal", "owasp-a01", "file-access"],
    },
    {
        "cve_id": "CWE-798",
        "title": "Hardcoded Credentials",
        "description": "Application contains hardcoded passwords, API keys, or cryptographic secrets in source code.",
        "remediation": "Store all secrets in environment variables or a secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault). Rotate any exposed credentials immediately.",
        "severity": "critical",
        "tags": ["secrets", "owasp-a02", "credentials"],
    },
    {
        "cve_id": "CWE-306",
        "title": "Missing Authentication",
        "description": "Critical functionality is accessible without authentication, allowing unauthenticated users to perform privileged operations.",
        "remediation": "Implement authentication on all sensitive endpoints. Use a proven auth framework. Apply deny-by-default access control.",
        "severity": "critical",
        "tags": ["authentication", "owasp-a01", "access-control"],
    },
    {
        "cve_id": "CWE-862",
        "title": "Missing Authorisation",
        "description": "Application does not verify that authenticated users are authorised to access specific resources or perform specific actions.",
        "remediation": "Implement role-based access control. Verify authorisation on every request, server-side. Never rely on client-supplied role claims.",
        "severity": "high",
        "tags": ["authorisation", "owasp-a01", "access-control"],
    },
    {
        "cve_id": "CWE-502",
        "title": "Insecure Deserialization",
        "description": "Application deserializes untrusted data without validation, which can lead to remote code execution or privilege escalation.",
        "remediation": "Never deserialize data from untrusted sources. Use safe formats like JSON with schema validation. If unavoidable, sign serialized objects.",
        "severity": "critical",
        "tags": ["deserialization", "owasp-a08", "rce"],
    },
    {
        "cve_id": "CWE-327",
        "title": "Weak Cryptographic Algorithm",
        "description": "Application uses broken or weak cryptographic algorithms such as MD5, SHA-1, or DES for security-sensitive operations.",
        "remediation": "Use modern algorithms: AES-256 for encryption, SHA-256+ for hashing, bcrypt/argon2 for passwords. Never use MD5 or SHA-1 for security.",
        "severity": "high",
        "tags": ["cryptography", "owasp-a02", "hashing"],
    },
    {
        "cve_id": "CWE-916",
        "title": "Weak Password Hashing",
        "description": "Passwords are stored using fast hashing algorithms (MD5, SHA-1, SHA-256) without salting, making them vulnerable to brute-force attacks.",
        "remediation": "Use bcrypt, scrypt, or argon2id for password hashing. Never use general-purpose hash functions for passwords. Use a work factor of at least 12.",
        "severity": "high",
        "tags": ["password", "owasp-a02", "hashing"],
    },
    {
        "cve_id": "CWE-611",
        "title": "XML External Entity (XXE) Injection",
        "description": "XML parser processes external entity references in XML input, allowing attackers to read local files or trigger SSRF.",
        "remediation": "Disable external entity processing in the XML parser. Use a whitelist of allowed XML schemas. Prefer JSON over XML for APIs.",
        "severity": "high",
        "tags": ["xxe", "owasp-a05", "xml"],
    },
    {
        "cve_id": "CWE-918",
        "title": "Server-Side Request Forgery (SSRF)",
        "description": "Application fetches remote resources based on user-supplied URLs without validating or restricting the target, allowing attackers to reach internal services.",
        "remediation": "Validate and allowlist permitted URL schemes and hosts. Block requests to private IP ranges. Use a dedicated egress proxy.",
        "severity": "high",
        "tags": ["ssrf", "owasp-a10", "network"],
    },
    {
        "cve_id": "CWE-434",
        "title": "Unrestricted File Upload",
        "description": "Application accepts file uploads without validating file type or content, allowing attackers to upload and execute malicious files.",
        "remediation": "Validate file type by content (magic bytes), not extension. Store uploads outside the web root. Rename files on upload. Scan with antivirus.",
        "severity": "high",
        "tags": ["file-upload", "owasp-a04", "rce"],
    },
    {
        "cve_id": "CWE-352",
        "title": "Cross-Site Request Forgery (CSRF)",
        "description": "Application does not verify that state-changing requests originate from the authenticated user's session, allowing forged cross-origin requests.",
        "remediation": "Use CSRF tokens on all state-changing forms. Verify the Origin and Referer headers. Use SameSite=Strict cookies.",
        "severity": "medium",
        "tags": ["csrf", "owasp-a01", "web"],
    },
    {
        "cve_id": "CWE-200",
        "title": "Sensitive Data Exposure in Error Messages",
        "description": "Application exposes sensitive information such as stack traces, internal paths, or configuration details in error messages.",
        "remediation": "Return generic error messages to users. Log detailed errors server-side only. Disable debug mode in production.",
        "severity": "medium",
        "tags": ["information-disclosure", "owasp-a02", "error-handling"],
    },
    {
        "cve_id": "CWE-319",
        "title": "Cleartext Transmission of Sensitive Data",
        "description": "Application transmits sensitive data over unencrypted channels, allowing network attackers to intercept credentials or private data.",
        "remediation": "Enforce HTTPS for all connections. Use HSTS headers. Disable HTTP fallback. Verify TLS certificates.",
        "severity": "high",
        "tags": ["tls", "owasp-a02", "network"],
    },
    {
        "cve_id": "CWE-732",
        "title": "Insecure File Permissions",
        "description": "Files or directories have overly permissive access controls, allowing unauthorised users to read or modify sensitive data.",
        "remediation": "Apply principle of least privilege to all file permissions. Configuration files should not be world-readable. Use umask 027 or stricter.",
        "severity": "medium",
        "tags": ["permissions", "owasp-a01", "file-system"],
    },
    {
        "cve_id": "CWE-94",
        "title": "Code Injection",
        "description": "Application evaluates user-supplied code (e.g., eval(), exec()) without restriction, allowing arbitrary code execution.",
        "remediation": "Never use eval() or exec() on user input. Use safe alternatives like ast.literal_eval() for Python. Apply strict input validation.",
        "severity": "critical",
        "tags": ["injection", "owasp-a03", "rce"],
    },
    {
        "cve_id": "CWE-601",
        "title": "Open Redirect",
        "description": "Application redirects users to a URL specified in user input without validation, enabling phishing attacks.",
        "remediation": "Use a whitelist of permitted redirect destinations. Prefer relative redirects. Warn users before redirecting to external URLs.",
        "severity": "medium",
        "tags": ["redirect", "owasp-a01", "web"],
    },
    {
        "cve_id": "CWE-209",
        "title": "Information Exposure Through Debug Information",
        "description": "Debug mode is enabled in production, exposing stack traces, source code, environment variables, or internal architecture details.",
        "remediation": "Set DEBUG=False in production. Remove debug endpoints before deployment. Use environment-specific configuration files.",
        "severity": "medium",
        "tags": ["debug", "owasp-a05", "information-disclosure"],
    },
]


async def seed():
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    db = get_supabase()

    print(f"Seeding {len(VULNS)} vulnerability knowledge entries...")

    texts = [f"{v['title']}: {v['description']} Remediation: {v['remediation']}" for v in VULNS]

    print("Embedding all entries in one batch...")
    response = await client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=texts,
    )
    embeddings = [item.embedding for item in response.data]

    rows = [
        {
            "cve_id": v["cve_id"],
            "title": v["title"],
            "description": v["description"],
            "remediation": v["remediation"],
            "severity": v["severity"],
            "tags": v["tags"],
            "embedding": emb,
        }
        for v, emb in zip(VULNS, embeddings)
    ]

    db.table("vuln_knowledge").insert(rows).execute()
    print(f"Done. {len(rows)} entries seeded into vuln_knowledge.")


if __name__ == "__main__":
    asyncio.run(seed())
# Security Policy

## Responsible Use

HunterFlow is a research workspace for **authorized** security testing. Using it against systems without explicit authorization is illegal and prohibited. The project assumes no liability for misuse.

## Reporting a Vulnerability

Do **not** open a public issue for security vulnerabilities. Please report privately via GitHub's private vulnerability reporting ("Report a vulnerability" on the Security tab) or to the maintainers by email.

Include:

- Affected version(s)
- Steps to reproduce
- Impact assessment
- Suggested fix (optional)

We will acknowledge within 5 business days and aim for a fix or mitigation within 30 days, coordinating disclosure with you.

## Supported Versions

| Version | Supported |
|---|---|
| latest release | yes |
| unreleased `main` | best-effort |

## Security Architecture

HunterFlow's threat model, residual risks, and security controls are documented in `specs/architecture/security.md` and `specs/architecture/adr/`. Key properties:

- Scope enforcement before every active outbound operation
- No autonomous exploitation; curated, explicitly selected scanner templates only
- Server-side sessions, Argon2id password hashing, CSRF protection, login rate limiting
- Central secret redaction; evidence never statically served
- Non-root, capability-limited containers; argument-array subprocess execution

## Disclosure of Residual Risks

Known residual risks (documented in `specs/architecture/security.md` §9) include limits on per-request scope control inside third-party tools. These are called out in release notes.

# Security policy

This repository has not yet completed a public release audit. Maintainers should enable GitHub private vulnerability reporting before publishing. If that channel is available, use the repository Security tab to report a vulnerability privately. Otherwise, request a private reporting channel without posting exploit details or secrets in a public issue.

Never attach access/refresh tokens, passwords, private keys, database copies, or mailbox output. Include the affected revision, reproduction steps without real credentials, and expected impact. Rotate exposed credentials immediately.

Production requirements: a unique strong SECRET_KEY, HTTPS, protected Postgres, backups/migration recovery, a real email delivery adapter, shared rate limiting across workers, and reviewed Sentry/log retention. The built-in mailbox and in-memory limiter are development implementations. Generated project auth guidance does not enable authentication.

The CLI uses the OS keychain where possible; fallback files are owner-only on POSIX. Windows permissions require the user's normal protected profile directory. User templates and dependency installs can execute external programs only through explicit install/trust options; inspect third-party templates before enabling hooks.

Dependency auditing, CodeQL and SBOM workflows aid review; they do not prove the absence of vulnerabilities. Release readiness and known limitations are recorded in docs/LAUNCH_READINESS.md.

# Security Policy

## Reporting a Vulnerability

Report suspected vulnerabilities through a private security-advisory channel on the repository host. Do not include credentials, private source code, or facility data in a public issue.

## Deployment Scope

The default configuration is intended for local use and controlled demonstrations. It does not provide production identity integration, TLS termination, rate limiting, password recovery, centralized secret management, or durable background jobs.

The example `admin` credential is deliberately limited to local demonstrations. Replace it before exposing either service beyond the loopback interface.

Before an internet-facing deployment, place the application behind an approved identity-aware gateway, use TLS, move secrets out of local files, configure managed data storage and backups, and review every external model and browser dependency.

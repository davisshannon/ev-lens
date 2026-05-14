# PRD 10: Security, Privacy, and Deployment

## 10.1 Objective

Make the product safe enough for local vehicle telemetry and token handling.

## 10.2 Security Requirements

- Encrypt provider tokens at rest.
- Never log access/refresh tokens.
- Use local admin authentication.
- Require password change from default.
- Support disabling all cloud features.
- No default public exposure.
- Explicit warnings if bound to public interface.
- CORS locked down by default.
- Secrets via environment variables or local secret store.
- Backup/restore support.
- Audit log for provider connection, import, settings changes, and AI questions.

## 10.3 Deployment Modes

### MVP

Docker Compose:

```text
backend
frontend
postgres/timescaledb
optional mqtt
```

### Later

- Home Assistant add-on;
- Synology package;
- Proxmox/LXC guide;
- hosted SaaS;
- hybrid sync relay.

## 10.4 Backup Requirements

- one-click backup export;
- scheduled database backup;
- restore documented;
- backup includes DB data but not plaintext secrets;
- encryption key warning shown clearly.

## 10.5 Acceptance Criteria

- Fresh install requires local admin setup.
- Tokens encrypted at rest.
- Logs redacted.
- Backups can be generated and restored.
- Security warning if user tries to expose service publicly.
- Docker Compose install works on Linux AMD64 and ARM64.

## 10.6 Claude/Codex Build Prompt

```text
Build EV Lens security and deployment foundations.

Implement local admin authentication, encrypted token storage, log redaction, audit logging, Docker Compose deployment, backup/export, and restore documentation. Ensure no public exposure is required. Add startup checks for missing encryption key, default password, and unsafe bind settings. Include tests for token encryption, log redaction, auth enforcement, and backup command generation.
```

---

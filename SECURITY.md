# Security policy

Knock Knock processes security-camera events and biometric-derived identifiers. Treat every report
as potentially sensitive, even though this repository contains only synthetic fixtures.

## Reporting a vulnerability

Do not open a public issue for a vulnerability, exposed credential, private image, or visitor log.
Use GitHub's private vulnerability reporting feature for this repository. Include the affected
commit, a minimal reproduction using synthetic data, expected impact, and any suggested mitigation.
Do not include real Ring media, tokens, face images, account identifiers, or presigned URLs.

This hackathon proof of concept has no production security-response SLA. Maintainers will
acknowledge a complete private report when practical, assess it before discussing disclosure, and
credit the reporter if requested and appropriate.

## Supported version

Only the current `main` branch is supported during the hackathon. The application is not approved
for production use, access control, emergency response, or other consequential decisions.

## Security invariants

- Ring OAuth secrets, webhook keys, AWS credentials, FCM credentials, and biometric media stay out
  of Git and Android packages.
- Ring webhook signatures are checked over raw bytes before parsing or logging.
- Cognito authenticates, but server-side household membership authorizes every protected object.
- Only the Ring account owner can invite/remove members or approve canonical profile changes.
- Face matches are advisory and cannot unlock a door, deny entry, or contact authorities.
- Unsaved photos expire after 30 days; text visit records remain visible for one year; application
  APIs expose no audit-log deletion.
- Production media storage must remain private and encrypted, with short-lived authorized access.

See [docs/threat-model.md](docs/threat-model.md) and
[docs/privacy-and-retention.md](docs/privacy-and-retention.md) for the current controls and known
limitations.


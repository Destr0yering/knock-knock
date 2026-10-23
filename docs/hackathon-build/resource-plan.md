# Build resource plan

## Goal

Finish the existing item 10 path while minimizing personal Codex use and keeping Ring credentials, household data, and camera media private.

## Where each resource fits

- **Codex:** Own sequencing, security-sensitive decisions, integration across modules, and final review. Use it for the difficult seams, not repeat builds or routine lint runs.
- **Nano with Qwen:** Use for local, scoped code work and Android builds when the Nano connection is available. Keep source and artifacts on its project storage; pass only sanitized files if a cloud service is needed.
- **Docker Agentic Platform:** Spend the available compute credit on short-lived, reproducible build/test sandboxes. Docker credit pays for sandbox compute, not model inference. Use a free model provider or Nano Qwen for inference, and stop each sandbox after its job.
- **OpenRouter:** Use only models explicitly labeled free, for bounded secondary review or synthetic fixture generation. Do not send Ring tokens, AWS credentials, real event payloads, footage, or face data.
- **Google AI Studio:** Use only projects explicitly marked Free tier. The personal account currently shows a depleted prepaid Gemini balance and $0 eligible GCP credits, so it is excluded until a free-tier project is confirmed. No payment or paid-key use is authorized.

## Build sequence

1. Complete the Ring one-way token exchange and account-link flow with durable, conditional AWS storage. Keep Ring event processing isolated until the owner completes linking and explicitly enables the intended data path.
2. Finish Cognito household authorization, invitation/age affirmation, owner/member controls, FCM registration and delivery, Android sign-in, sync, and deep links.
3. Run repeatable Android and backend build gates on Nano; use Docker compute only when it saves time or supplies an isolated clean environment.
4. Close the item 10 deployment and device checkpoint after the code path is ready, inspecting AWS costs before mutations and Ring consent before linking a real account.
5. Complete hardening, recovery paths, clean-checkout build, and demo rehearsal for item 11; then assemble the Devpost handoff for item 12.

## Current execution limits

- The current Windows execution host cannot reach Nano over SSH (connection denied), so Nano execution is queued until that path is available. No Docker sandbox or model API key is currently configured in this shell.
- The project already contains uncommitted implementation work on `codex/knock-knock-mvp`; preserve it and avoid reset, broad checkout, or unrelated cleanup.
- Do not run AI Studio paid requests, purchase credits, or deploy billable resources as part of the offline coding pass.

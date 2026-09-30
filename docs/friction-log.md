# Knock Knock integration friction log

This log records concrete, non-secret integration issues for the hackathon feedback submission.

## Ring Partner API — 2026-09-29

- The official documentation is sufficient to implement OAuth refresh, webhook v1.1 normalization,
  HMAC verification, image redirect downloads, and historical MP4 downloads without an unofficial
  library.
- Snapshot and video downloads use different successful response shapes: images document a
  two-step `303 Location` flow, while clips can return `200`, `206`, or a redirect. A single
  generic “download media” example would reduce integration mistakes.
- Multi-camera devices require a one-entry `components` array for deterministic media selection.
  The field shape differs from capability discovery and is easy to overlook.
- The mandatory Ring watermark must remain intact, so the contract suite verifies byte-for-byte
  preservation and keeps watermark-aware recognition testing explicit.
- Current external blocker: no staging app client credentials, HMAC key, linked Ring test account,
  or Playground token were supplied to the local development environment during this checkpoint.
  Therefore the official sanitized v1.1 replay contract is verified locally, while live
  Playground/staging evidence remains pending. The architecture and production API path are
  unchanged.

## AWS SAM — 2026-09-29

- Neither AWS CLI nor SAM CLI was initially installed even though the AWS web console was signed in.
  A project-local SAM CLI environment was added under the ignored `.tools/` directory.
- The first image build failed because the Docker SDK walked stale Android Gradle intermediates in
  the repository-wide build context. A strict `.dockerignore` reduced the context to the Python
  package, project metadata, and Lambda Dockerfiles; both images then built successfully.
- Docker Desktop was installed but not running. Starting it enabled a full SAM build and local
  FastAPI/Mangum health smoke test.
- Current external blocker: the browser session does not supply CLI credentials. A read-only STS
  identity check returned `NoCredentialsError`, so no CloudFormation deployment or billable AWS
  mutation was attempted. The active account and region must be authenticated and confirmed first.

## AWS account activation — 2026-09-30

- A verified Amazon-signed AWS CLI v2.37.6 administrative extraction provided a project-local CLI
  after the system-wide MSI required administrator access.
- AWS browser login produced short-lived credentials and STS verified account `737272118136` before
  deployment. No long-lived access key was created.
- After explicit deployment approval, SAM rebuilt both Lambda images and attempted its managed
  resource bootstrap in `us-east-1`. AWS rejected `CreateChangeSet` with `OptInRequired: The AWS
  Access Key Id needs a subscription for the service`.
- A subsequent read-only CloudFormation `ListStacks` call returned the same `OptInRequired` error.
  This indicates account/billing activation rather than a SAM template or IAM-policy failure. No
  Knock Knock application stack or live endpoint was created.
- The local infrastructure gate remains reproducible and green. Live deployment, output inspection,
  billing/free-tier inspection, and health smoke testing are deferred to the existing item 10
  end-to-end checkpoint after AWS finishes account activation.

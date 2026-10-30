# Temporary hosted Nebius preview

This separate stack serves only a fixed synthetic review fixture. It does not
access Android records, Ring accounts, photographs, or user-provided prompts.
The existing workflow executes on Lambda. A DynamoDB conditional update reserves
one of 20 lifetime live-inference attempts before spawning `asm-exec`; the cap is
shared across workers and is retained across stack deletion. After the cap, after
December 15 at 20:00 UTC, or on a limiter/inference failure, the interface labels
and shows a previously observed synthetic result. The cap counts failures too.

The API has best-effort throttling. The account's Lambda concurrency limit is ten;
AWS does not allow reserving part of that quota in this account. These
are not a hard dollar cap: AWS requests and storage can still incur charges, and
throttled requests may also be billable. AWS budgets and alerts are not instantaneous.
Monitor costs and remove or disable the temporary resources when judging ends.
The $10 target authorized for this preview is a planning budget, not a guarantee.
The handler stops live model calls after the judging period, but it does not
automatically delete the API, Lambda, counter, or artifact bucket. Those
resources can continue to incur AWS charges until explicitly cleaned up.

The deployment artifact is private and encrypted. The function role can update
only the counter and resolve only the chosen Secrets Manager secret; MCP service
actions are permitted subject to the IAM condition AWS documents for MCP actions.
The API secret is referenced by ARN and is resolved at runtime using `asm-exec`.
Neither template nor package contains the secret value. The public endpoint is
rate-limited and accepts only a fixed, synthetic event, never arbitrary text.

## Rebuilding the deployment package

Use Python 3.12-compatible ARM Linux wheels and obtain AWS's `asm-exec` from
the [AWS agent toolkit](https://github.com/aws/agent-toolkit-for-aws/blob/main/plugins/aws-core/skills/aws-secrets-manager/references/asm-exec).
The script is an external dependency and must be supplied to the packager; never
place a secret value in the package. For example, from the repository root:

```text
python -m pip install --target .codex-nebius-lambda-arm --platform manylinux2014_aarch64 --python-version 3.12 --implementation cp --abi cp312 --only-binary=:all: -r infra/nebius-preview/requirements.txt
python infra/nebius-preview/build_package.py --package-dir .codex-nebius-lambda-arm --asm-exec <path-to-asm-exec> --output infra/nebius-preview/preview-arm.zip
```

`artifacts.yaml` provisions a private artifact bucket; `template.yaml` deploys
the application from a versioned object in that bucket. Use the AWS Secrets
Manager ARN as `NebiusSecretArn`, not the secret value. The referenced secret
must contain the JSON field `api_key`. Deployment creates billable AWS resources.

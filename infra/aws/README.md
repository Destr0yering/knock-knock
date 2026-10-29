# AWS development stack

This stack is intentionally serverless: HTTP API + Lambda, SQS/DLQ, DynamoDB on-demand tables,
private S3, Cognito, Secrets Manager, alarms, and short CloudWatch retention. It creates no NAT
Gateway or always-on compute.

## Validate without changing AWS

```powershell
sam validate --lint --template-file infra/aws/template.yaml
sam build --template-file infra/aws/template.yaml
python -m pytest tests/infra
```

## First deployment

Deployment creates billable AWS resources. Confirm the active identity and region immediately
before deploying:

Bootstrap the MFA-gated deployment role once from an authenticated account-owner session:

```powershell
aws cloudformation deploy `
  --template-file infra/aws/bootstrap-user.yaml `
  --stack-name knock-knock-deployer-user `
  --capabilities CAPABILITY_NAMED_IAM `
  --region us-east-1

aws cloudformation deploy `
  --template-file infra/aws/bootstrap-deployer.yaml `
  --stack-name knock-knock-deployer `
  --capabilities CAPABILITY_NAMED_IAM `
  --parameter-overrides DeploymentUserArn=arn:aws:iam::YOUR_12_DIGIT_ACCOUNT_ID:user/knock-knock-deployer `
  --region us-east-1
```

The bootstrap stack creates a `knock-knock-deployer` IAM user with no access keys. The user can
use short-lived `aws login` credentials and assume only `KnockKnockDeploymentRole`. The role uses
one-hour sessions, requires that user's MFA, has AWS `PowerUserAccess`, and can manage/pass only
CloudFormation-generated `knock-knock-dev-*` execution roles.

The user bootstrap also grants narrowly scoped permissions to enroll and manage only its own
virtual MFA device. An account owner or administrator must deploy/update the bootstrap stack once,
then enroll MFA from the IAM user's Security credentials page before deployment.

Assume `KnockKnockDeploymentRole` before deploying the application stack. Do not deploy the
application as the root identity.

```powershell
aws sts get-caller-identity
aws configure get region
Copy-Item infra/aws/samconfig.example.toml samconfig.toml
sam deploy --guided --template-file infra/aws/template.yaml --config-file samconfig.toml
```

Use the CloudFormation outputs for the Android API base URL and Cognito configuration. Populate
the generated Ring and Firebase secrets through the AWS console or `aws secretsmanager
put-secret-value`; never place secret values in this repository or a shell history.

## Smoke test

```powershell
$api = aws cloudformation describe-stacks --stack-name knock-knock-dev --query "Stacks[0].Outputs[?OutputKey=='ApiBaseUrl'].OutputValue" --output text
Invoke-RestMethod "$api/health"

# Equivalent repository smoke test (read-only)
python scripts/smoke_deployed_api.py --url $api

## Configure secrets safely

The stack creates an empty Secrets Manager record for Ring and a legacy empty Firebase record.
Ring credentials still use the interactive helper below. FCM now uses AWS-to-Google Workload
Identity Federation and does not need a Firebase service-account key:

```powershell
.\scripts\configure_aws_secrets.ps1
```

Do not put Ring tokens, OAuth client secrets, HMAC keys, or Firebase service-account JSON in
`.env`, source files, shell history, screenshots, or GitHub issues.
```

## Teardown

Empty the generated media bucket before deleting the stack, then verify that CloudFormation removed
the stack. This is destructive and deletes development records and secrets.

```powershell
$bucket = aws cloudformation describe-stacks --stack-name knock-knock-dev --query "Stacks[0].Outputs[?OutputKey=='MediaBucketName'].OutputValue" --output text
aws s3 rm "s3://$bucket" --recursive
sam delete --stack-name knock-knock-dev --region us-east-1
```

The existing account budgets remain the cost backstop. Review Billing and Cost Management after
deployment; this template does not create or alter account-level budgets.

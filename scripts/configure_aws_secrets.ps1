<##
  Populate the development Secrets Manager records without putting values in git.
  Run this locally after obtaining Ring/Firebase credentials. The values are read
  interactively and passed through stdin to AWS CLI; they are never written to disk.
##>
[CmdletBinding()]
param(
  [string]$Region = "us-east-1",
  [string]$Environment = "dev"
)

$ErrorActionPreference = "Stop"
$ringName = "knock-knock/$Environment/ring"
$firebaseName = "knock-knock/$Environment/firebase"

Write-Host "Enter Ring secret JSON (leave blank to skip). Example keys: client_id, client_secret, hmac_signing_key, households." -ForegroundColor Cyan
$ring = Read-Host "Ring JSON"
if ($ring) {
  aws secretsmanager put-secret-value --secret-id $ringName --secret-string $ring --region $Region | Out-Null
  Write-Host "Updated $ringName"
}

Write-Host "Enter Firebase service-account JSON (leave blank to skip)." -ForegroundColor Cyan
$firebase = Read-Host "Firebase JSON"
if ($firebase) {
  aws secretsmanager put-secret-value --secret-id $firebaseName --secret-string $firebase --region $Region | Out-Null
  Write-Host "Updated $firebaseName"
}

Write-Host "Done. Secret values were not saved to this repository." -ForegroundColor Green

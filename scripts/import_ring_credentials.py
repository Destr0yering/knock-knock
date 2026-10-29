from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import boto3
from botocore.config import Config

FIELD_MAP = {
    "Client ID": "client_id",
    "Client Secret": "client_secret",
    "HMAC Signature Key": "hmac_signing_key",
}


def read_credentials(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))

    source = {row[0].strip(): row[1].strip() for row in rows if len(row) == 2}
    missing = FIELD_MAP.keys() - source.keys()
    if missing:
        raise ValueError(f"Credential CSV is missing fields: {', '.join(sorted(missing))}")
    return {target: source[label] for label, target in FIELD_MAP.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--secret-id", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--region", default="us-east-1")
    args = parser.parse_args()

    credentials = read_credentials(args.csv)
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    client = session.client(
        "secretsmanager",
        config=Config(
            retries={"total_max_attempts": 3, "mode": "standard"},
            connect_timeout=5,
            read_timeout=10,
        ),
    )
    client.put_secret_value(
        SecretId=args.secret_id,
        SecretString=json.dumps(credentials, separators=(",", ":"), sort_keys=True),
    )
    print("Stored Ring credentials: client_id, client_secret, hmac_signing_key")
    return 0


if __name__ == "__main__":
    sys.exit(main())

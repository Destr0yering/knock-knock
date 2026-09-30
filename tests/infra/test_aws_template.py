from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

TEMPLATE_PATH = Path(__file__).parents[2] / "infra" / "aws" / "template.yaml"


class CloudFormationLoader(yaml.SafeLoader):
    pass


def _construct_intrinsic(
    loader: CloudFormationLoader,
    tag_suffix: str,
    node: yaml.Node,
) -> dict[str, Any]:
    if isinstance(node, yaml.ScalarNode):
        value: Any = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node)
    else:
        value = loader.construct_mapping(node)
    names = {
        "Ref": "Ref",
        "Sub": "Fn::Sub",
        "GetAtt": "Fn::GetAtt",
    }
    return {names.get(tag_suffix, f"Fn::{tag_suffix}"): value}


CloudFormationLoader.add_multi_constructor("!", _construct_intrinsic)


def _template() -> dict[str, Any]:
    loaded = yaml.load(TEMPLATE_PATH.read_text(encoding="utf-8"), Loader=CloudFormationLoader)
    assert isinstance(loaded, dict)
    return loaded


def test_stack_contains_required_serverless_boundaries() -> None:
    resources = _template()["Resources"]
    resource_types = {resource["Type"] for resource in resources.values()}

    assert "AWS::Serverless::HttpApi" in resource_types
    assert "AWS::Serverless::Function" in resource_types
    assert "AWS::SQS::Queue" in resource_types
    assert "AWS::DynamoDB::Table" in resource_types
    assert "AWS::S3::Bucket" in resource_types
    assert "AWS::Cognito::UserPool" in resource_types
    assert "AWS::SecretsManager::Secret" in resource_types
    assert "AWS::CloudWatch::Alarm" in resource_types
    assert not any("NatGateway" in kind or "Instance" in kind for kind in resource_types)


def test_queue_visibility_is_at_least_six_times_worker_timeout() -> None:
    resources = _template()["Resources"]
    worker_timeout = resources["WorkerFunction"]["Properties"]["Timeout"]
    visibility = resources["EventQueue"]["Properties"]["VisibilityTimeout"]

    assert visibility >= worker_timeout * 6
    sqs_event = resources["WorkerFunction"]["Properties"]["Events"]["RingEvents"]["Properties"]
    assert sqs_event["FunctionResponseTypes"] == ["ReportBatchItemFailures"]
    assert resources["EventQueue"]["Properties"]["RedrivePolicy"]["maxReceiveCount"] == 3


def test_media_bucket_is_private_kms_encrypted_and_has_fixed_retention() -> None:
    properties = _template()["Resources"]["MediaBucket"]["Properties"]
    public_block = properties["PublicAccessBlockConfiguration"]
    encryption = properties["BucketEncryption"]["ServerSideEncryptionConfiguration"][0]
    rules = properties["LifecycleConfiguration"]["Rules"]

    assert all(public_block.values())
    assert encryption["ServerSideEncryptionByDefault"]["SSEAlgorithm"] == "aws:kms"
    photo_rule = next(rule for rule in rules if rule["Id"] == "ExpireTemporaryPhotos")
    assert photo_rule["TagFilters"] == [{"Key": "retention", "Value": "30d"}]
    assert photo_rule["ExpirationInDays"] == {"Ref": "PhotoRetentionDays"}


def test_tables_use_on_demand_capacity_encryption_and_ttl() -> None:
    resources = _template()["Resources"]
    for name in ("HouseholdTable", "VisitTable", "EventLedgerTable"):
        properties = resources[name]["Properties"]
        assert properties["BillingMode"] == "PAY_PER_REQUEST"
        assert properties["SSESpecification"]["SSEEnabled"] is True
        assert properties["TimeToLiveSpecification"] == {
            "AttributeName": "expires_at",
            "Enabled": True,
        }


def test_execution_roles_are_split_and_have_no_bare_wildcard_resource() -> None:
    resources = _template()["Resources"]
    api_role = resources["ApiFunction"]["Properties"]["Role"]
    worker_role = resources["WorkerFunction"]["Properties"]["Role"]
    assert api_role != worker_role

    for role_name in ("ApiExecutionRole", "WorkerExecutionRole"):
        for policy in resources[role_name]["Properties"]["Policies"]:
            statements = policy["PolicyDocument"]["Statement"]
            for statement in statements:
                resource = statement.get("Resource")
                assert resource != "*"
                if isinstance(resource, list):
                    assert "*" not in resource


def test_public_routes_are_narrow_and_management_routes_require_cognito() -> None:
    resources = _template()["Resources"]
    auth = resources["HttpApi"]["Properties"]["Auth"]
    events = resources["ApiFunction"]["Properties"]["Events"]

    assert auth["DefaultAuthorizer"] == "CognitoAuthorizer"
    assert events["Health"]["Properties"]["Auth"]["Authorizer"] == "NONE"
    assert events["RingWebhook"]["Properties"]["Auth"]["Authorizer"] == "NONE"
    assert events["RingOAuthCallback"]["Properties"]["Auth"]["Authorizer"] == "NONE"
    assert "Auth" not in events["ApiProxy"]["Properties"]


def test_secrets_are_created_without_embedded_secret_values() -> None:
    resources = _template()["Resources"]
    for name in ("RingCredentialsSecret", "FirebaseCredentialsSecret"):
        properties = resources[name]["Properties"]
        assert "SecretString" not in properties
        assert "GenerateSecretString" not in properties

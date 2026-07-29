from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from review_portal.aws_app import app

REPO_ROOT = Path(__file__).resolve().parents[1]
AWS_DEPLOY_DIR = REPO_ROOT / "deploy" / "aws-lightsail"


def test_public_aws_health_does_not_expose_filesystem_paths() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_bootstrap_uses_privacy_safe_entrypoint_and_disables_access_logs() -> None:
    bootstrap = (AWS_DEPLOY_DIR / "bootstrap.sh").read_text(encoding="utf-8")

    assert "review_portal.aws_app:app" in bootstrap
    assert "--no-access-log" in bootstrap
    assert "access_log off;" in bootstrap
    assert "review_portal.app:app" not in bootstrap


def test_distribution_forwards_dynamic_methods_and_query_tokens_without_cache() -> None:
    deploy_script = (AWS_DEPLOY_DIR / "deploy.ps1").read_text(encoding="utf-8")

    assert 'allowedHTTPMethods = "GET,HEAD,OPTIONS,PUT,PATCH,POST,DELETE"' in deploy_script
    assert 'forwardedQueryStrings = @{ option = $true' in deploy_script
    assert '"--default-cache-behavior", "behavior=dont-cache"' in deploy_script
    assert "defaultTTL = 0" in deploy_script
    assert "minimumTTL = 0" in deploy_script
    assert "maximumTTL = 0" in deploy_script


def test_deployment_secrets_and_private_keys_are_gitignored() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "deploy/aws-lightsail/deployment-output.json" in gitignore
    assert "deploy/aws-lightsail/*.pem" in gitignore

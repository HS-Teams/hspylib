"""Exercise the real CLI, including startup and parser logging, in isolated processes."""

import base64
import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("arguments", [
    ["add", "entry", "hint", "rejected-secret"],
    ["upd", "entry", "hint", "rejected-secret"],
    ["rejected-secret"],
])
def test_rejected_arguments_never_echo_passwords(tmp_path, arguments):
    encoded = base64.b64encode(b"configured-master-secret").decode()
    env = dict(
        os.environ, PYTHONPATH=os.pathsep.join(sys.path),
        HHS_VAULT_FILE=str(tmp_path / "secret.vault"), HHS_VAULT_USER="alice",
        HHS_VAULT_PASSPHRASE=encoded, HHS_LOG_DIR=str(tmp_path), ACTIVE_PROFILE="",
    )
    result = subprocess.run(
        [sys.executable, "-m", "vault", *arguments], env=env, cwd=tmp_path,
        capture_output=True, text=True, timeout=30,
    )
    output = result.stdout + result.stderr + "".join(path.read_text() for path in tmp_path.glob("*.log"))
    assert result.returncode != 0
    assert "Invalid argument" in output
    for secret in ("rejected-secret", "configured-master-secret", encoded):
        assert secret not in output
    assert not (tmp_path / "secret.vault").exists()


def test_config_file_values_are_redacted_during_real_application_startup(tmp_path):
    resources = tmp_path / "resources"
    resources.mkdir()
    secret = "encoded-config-file-secret"
    (resources / "application.properties").write_text(
        f"hhs.vault.file={tmp_path / 'secret.vault'}\nhhs.vault.user=alice\nhhs.vault.passphrase={secret}\n"
    )
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path), HHS_LOG_DIR=str(tmp_path), ACTIVE_PROFILE="")
    for name in ("HHS_VAULT_FILE", "HHS_VAULT_USER", "HHS_VAULT_PASSPHRASE"):
        env.pop(name, None)
    code = (
        "import sys; from vault.__main__ import Main; "
        "Main.RESOURCE_DIR=sys.argv[1]; Main('vault').run(['list'])"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(resources)], env=env, cwd=tmp_path,
        capture_output=True, text=True, timeout=30,
    )
    output = result.stdout + result.stderr + "".join(path.read_text() for path in tmp_path.glob("*.log"))
    assert result.returncode != 0
    assert "Remove hhs.vault.passphrase" in output
    assert secret not in output

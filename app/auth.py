import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AuthResult:
    status: str
    message: str
    environment: dict[str, str] | None = None


def load_openrc(path: Path | None) -> AuthResult:
    if path is None:
        return AuthResult("not_configured", "Set OPENSTACK_OPENRC to the admin RC file.")
    if not path.is_file() or not os.access(path, os.R_OK):
        return AuthResult("not_configured", "The configured OpenRC file is missing or unreadable.")
    command = ["bash", "-c", "set -a; . \"$1\"; env -0", "openrc-loader", str(path)]
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return AuthResult("not_configured", "The OpenRC file could not be loaded.")
    environment = {
        item.split("=", 1)[0]: item.split("=", 1)[1]
        for item in completed.stdout.decode().split("\0")
        if item.startswith("OS_") and "=" in item
    }
    if "OS_AUTH_URL" not in environment or "OS_PASSWORD" not in environment:
        return AuthResult("not_configured", "The OpenRC file lacks required OpenStack settings.")
    return AuthResult("ok", "OpenStack credentials loaded for this request.", environment)

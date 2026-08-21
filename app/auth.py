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
        return AuthResult("not_configured", "未设置 OPENSTACK_OPENRC，请指向 admin-openrc.sh 的实际路径。")
    if not path.is_file() or not os.access(path, os.R_OK):
        return AuthResult("not_configured", "配置的 OpenRC 文件不存在或当前进程无读取权限。")
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
        return AuthResult("not_configured", "OpenRC 文件加载失败，请确认文件内容为可执行的 shell 脚本。")
    environment = {
        item.split("=", 1)[0]: item.split("=", 1)[1]
        for item in completed.stdout.decode().split("\0")
        if item.startswith("OS_") and "=" in item
    }
    if "OS_AUTH_URL" not in environment or "OS_PASSWORD" not in environment:
        return AuthResult("not_configured", "OpenRC 文件缺少必要的 OpenStack 认证变量。")
    return AuthResult("ok", "已在服务端加载 OpenStack 凭据。", environment)

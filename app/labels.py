from datetime import datetime
from zoneinfo import ZoneInfo

DISPLAY_TIMEZONE = ZoneInfo("Asia/Shanghai")

STATUS_LABELS = {
    "ok": "正常",
    "partial": "部分可用",
    "empty": "无资源",
    "not_configured": "未配置凭据",
    "unavailable": "服务不可用",
    "not_found": "分类不存在",
}

RESOURCE_LABELS = {
    "server": "虚拟机",
    "flavor": "规格",
    "image": "镜像",
    "keypair": "密钥对",
    "availability_zone": "可用区",
    "hypervisor": "宿主机",
    "server_group": "主机组",
    "network": "网络",
    "subnet": "子网",
    "port": "端口",
    "router": "路由器",
    "security_group": "安全组",
    "floating_ip": "浮动 IP",
    "trunk": "Trunk",
    "agent": "网络代理",
    "volume": "云硬盘",
    "snapshot": "快照",
    "backup": "备份",
    "volume_type": "卷类型",
    "container": "容器",
    "object": "对象",
}


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def resource_label(kind: str) -> str:
    return RESOURCE_LABELS.get(kind, kind)


def local_time(value: str) -> str:
    return (
        datetime.fromisoformat(value)
        .astimezone(DISPLAY_TIMEZONE)
        .strftime("%Y-%m-%d %H:%M:%S")
    )

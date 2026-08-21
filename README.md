# OpenStack Inventory

一个只读的多平台 OpenStack 资源门户，直接使用 `openstacksdk` 查询 Keystone 目录中的计算、网络、块存储和对象存储。它不依赖 `openstack` CLI，不把 OpenRC 内容返回浏览器，也不提供任何资源变更接口。

## 多平台认证配置

平台清单是一个 JSON 文件，每个平台对应自己的 `admin-openrc.sh`：

```json
{
  "platforms": [
    {
      "id": "prod",
      "name": "生产集群",
      "description": "华东生产环境 Kolla-Ansible 集群",
      "openrc": "/etc/openstack-inventory/prod-admin-openrc.sh"
    },
    {
      "id": "test",
      "name": "测试集群",
      "openrc": "/etc/openstack-inventory/test-admin-openrc.sh",
      "region_name": "RegionOne"
    }
  ]
}
```

字段说明：

- `id`：必填，URL 中使用的平台标识，不能重复。
- `openrc`：必填，该平台 `admin-openrc.sh` 的路径。相对路径按 JSON 文件所在目录解析。
- `name`：可选，页面展示名称，默认取 `id`。
- `region_name`：可选，覆盖该平台的 region。
- `description`：可选，平台列表页的说明文字。

顶层也可以直接写数组，省略 `platforms` 键。

准备配置目录：

```bash
sudo mkdir -p /etc/openstack-inventory
sudo cp platforms.example.json /etc/openstack-inventory/platforms.json
sudo cp /实际路径/prod-admin-openrc.sh /etc/openstack-inventory/
sudo cp /实际路径/test-admin-openrc.sh /etc/openstack-inventory/
sudo chmod 600 /etc/openstack-inventory/*-admin-openrc.sh
sudo chmod 640 /etc/openstack-inventory/platforms.json
```

然后编辑 `/etc/openstack-inventory/platforms.json`，填入实际平台和 OpenRC 路径。

清单文件和 OpenRC 都不要提交到 Git。

单平台场景可以继续只设置 `OPENSTACK_OPENRC`，此时会自动生成一个 id 为 `default` 的平台。

## 从 GitHub SSH 部署

测试机器需要满足：Linux、Python 3.11+、`uv`，或者 Docker Engine 和 `docker-compose`。机器必须能访问各平台的 OpenStack API。

首次部署：

```bash
sudo mkdir -p /opt/openstack-inventory
sudo chown "$USER":"$USER" /opt/openstack-inventory
git clone git@github.com:luolu1/openstack-inventory.git /opt/openstack-inventory
cd /opt/openstack-inventory
```

更新代码：

```bash
cd /opt/openstack-inventory
git pull --ff-only origin main
```

## 原生 Python 部署

```bash
cd /opt/openstack-inventory
uv venv .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
export OPENSTACK_PLATFORMS_FILE=/etc/openstack-inventory/platforms.json
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

浏览器访问 `http://测试机地址:8000/`，首页是平台列表，点进平台再看资源明细。

页面路径：

```text
/                                  平台列表
/platforms/{平台id}                 平台资源总览
/platforms/{平台id}/compute         计算资源明细
/platforms/{平台id}/network         网络资源明细
/platforms/{平台id}/block_storage   块存储明细
/platforms/{平台id}/object_storage  对象存储明细
```

JSON 接口：

```text
/health
/api/platforms
/api/platforms/{平台id}/inventory
/api/platforms/{平台id}/inventory/{分类}
```

启动前可先验证清单和凭据：

```bash
python3 -m json.tool /etc/openstack-inventory/platforms.json > /dev/null
test -r /etc/openstack-inventory/prod-admin-openrc.sh
bash -n /etc/openstack-inventory/prod-admin-openrc.sh
```

启动后检查：

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/api/platforms
curl -fsS http://127.0.0.1:8000/api/platforms/prod/inventory
```

## Docker

不要把凭据写进镜像。把清单和所有 OpenRC 放在同一个目录，只读挂载进容器：

```bash
export OPENSTACK_CONFIG_DIR=/etc/openstack-inventory
docker-compose up -d --build
```

容器内固定读取 `/etc/openstack-inventory/platforms.json`，因此清单里的 `openrc` 路径应写成容器内路径，例如 `/etc/openstack-inventory/prod-admin-openrc.sh`，或使用相对路径 `prod-admin-openrc.sh`。

Compose 默认发布宿主机 `8000` 端口，可以通过 `INVENTORY_PORT` 修改：

```bash
INVENTORY_PORT=18000 docker-compose up -d --build
```

不要使用 Docker socket、特权模式或 host network。

检查容器：

```bash
docker-compose ps
curl -fsS http://127.0.0.1:8000/health
docker-compose logs --no-color --tail=100
```

## systemd 部署

```bash
sudo cp deploy/openstack-inventory.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now openstack-inventory
sudo systemctl status openstack-inventory
```

启动前确认 service 中的 `OPENSTACK_PLATFORMS_FILE`、`WorkingDirectory` 与 `ExecStart` 指向实际路径。默认服务只监听 `127.0.0.1:8000`；若要让其他机器访问，应在前置 Nginx 或受控防火墙后暴露，而不是直接暴露 admin 权限服务。

## 状态含义

每个平台的每个服务域独立判定：

- `正常`：服务可用，资源已读取。
- `部分可用`：部分资源类型受策略限制或接口不可用。
- `无资源`：服务可用但没有资源。
- `未配置凭据`：该平台的 OpenRC 缺失、不可读或缺少认证变量。
- `服务不可用`：Keystone 目录中没有该服务，或认证与服务发现失败。

单个平台认证失败不会影响其他平台。Swift 未部署时对象存储显示为服务不可用。管理员 OpenRC 也不保证每个项目资源都能跨项目列出，实际结果以 Keystone 与各服务策略为准。

## 验证

```bash
uv run --with-requirements requirements-dev.txt pytest
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/platforms
```

清单文件缺失或格式错误时，网站仍会启动，平台列表页会显示具体原因，不会崩溃。服务进程只读取资源，不执行创建、删除、更新、重启、上传、下载或其他 OpenStack 变更操作。

## 更新与回滚

```bash
cd /opt/openstack-inventory
git log -1 --oneline
git pull --ff-only origin main
docker-compose up -d --build
curl -fsS http://127.0.0.1:8000/health
```

若新版本异常，可回滚到已知提交：

```bash
git log --oneline -10
git switch --detach <已知正常提交>
docker-compose up -d --build
```

恢复跟踪主分支：

```bash
git switch main
git pull --ff-only origin main
```

不要使用 `git reset --hard` 覆盖本地未提交的配置文件；凭据和清单本来就不应放在仓库内。

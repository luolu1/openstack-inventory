# OpenStack Inventory

一个只读的 OpenStack 资源门户，直接使用 `openstacksdk` 查询 Keystone 目录中的 Compute、Network、Block Storage 和 Object Storage。它不依赖 `openstack` CLI，不把 OpenRC 内容返回浏览器，也不提供任何资源变更接口。

## 从 GitHub SSH 部署

测试机器需要满足：Linux、Python 3.11+、`uv`，或者 Docker Engine 和 `docker-compose`。机器必须能访问 OpenStack API，并且 `admin-openrc.sh` 位于测试机上，或者能通过只读挂载提供给容器。

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

不要把 `admin-openrc.sh`、`.env` 或包含密码的文件提交到 Git。推荐将 OpenRC 放在仓库目录之外，并限制为 root 可读：

```bash
sudo chmod 600 /实际路径/admin-openrc.sh
```

## 原生 Python 部署

```bash
cd /opt/openstack-inventory
uv venv .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
export OPENSTACK_OPENRC=/实际路径/admin-openrc.sh
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

浏览器访问 `http://测试机地址:8000/`。接口包括 `/health`、`/api/inventory` 和 `/api/inventory/{category}`。

启动前可先验证凭据文件和 OpenStack API：

```bash
test -r "$OPENSTACK_OPENRC"
bash -n "$OPENSTACK_OPENRC"
```

应用本身不会要求 `openstack` CLI。首次连接真实集群时，建议先在同一台机器执行：

```bash
. "$OPENSTACK_OPENRC"
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/api/inventory
```

## Docker

不要把凭据写进镜像。启动前指定宿主机 OpenRC 路径：

```bash
export OPENSTACK_OPENRC_HOST_PATH=/实际路径/admin-openrc.sh
docker-compose up -d --build
```

Compose 默认发布宿主机 `8000` 端口，可以通过 `INVENTORY_PORT` 修改：

```bash
INVENTORY_PORT=18000 docker-compose up -d --build
```

OpenRC 在容器内固定映射为 `/run/secrets/admin-openrc.sh`，挂载为只读。不要使用 Docker socket、特权模式或 host network。

检查容器：

```bash
docker-compose ps
curl -fsS http://127.0.0.1:8000/health
docker-compose logs --no-color --tail=100
```

## systemd 部署

需要 root 管理服务时，可使用仓库提供的模板：

```bash
sudo cp deploy/openstack-inventory.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now openstack-inventory
sudo systemctl status openstack-inventory
```

启动前编辑 service 中的 `OPENSTACK_OPENRC`，并确认 `WorkingDirectory` 与 `ExecStart` 指向实际 clone 路径。默认服务只监听 `127.0.0.1:8000`；若要让其他机器访问，应在前置 Nginx 或受控防火墙后暴露，而不是直接暴露 admin 权限服务。

如果 Swift 未部署或当前策略不允许访问，Object Storage 会显示为 unavailable；其他服务仍会正常展示。管理员 OpenRC 也不保证每个项目资源都能跨项目列出，实际结果以 Keystone/服务策略为准。

## 验证

```bash
uv run --with-requirements requirements-dev.txt pytest
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/inventory
```

没有配置 `OPENSTACK_OPENRC` 时，网站仍会启动，并明确显示 `not_configured`，不会崩溃。服务进程只读取资源，不执行创建、删除、更新、重启、上传、下载或其他 OpenStack 变更操作。

## 更新与回滚

更新前先看当前版本，更新后重新构建或重启：

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

不要使用 `git reset --hard` 覆盖本地未提交的 OpenRC 或配置文件；凭据本来就不应放在仓库内。

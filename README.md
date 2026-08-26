# FastAPI Blog

## 为什么这里只有 `compose.yaml`，没有 `Dockerfile`

这次 Docker 只负责运行 PostgreSQL。PostgreSQL 已经有官方镜像 `postgres:16-alpine`，项目不需要自己构建数据库镜像，因此不需要 `Dockerfile`。

- `Dockerfile`：描述如何把我们自己的 FastAPI 代码构建成一个镜像。
- `compose.yaml`：描述运行哪些服务，以及它们的环境变量、端口、数据卷和健康检查。

目前 FastAPI 仍直接运行在本机：

```bash
uv run fastapi dev
```

如果以后要把 FastAPI 应用本身也放进 Docker，再添加应用的 `Dockerfile`，并在 `compose.yaml` 中增加 `app` 服务。届时容器内的应用应通过 `db:5432` 连接 PostgreSQL，而不是通过宿主机的 `localhost:5434`。

## 首次设置

如果还没有 `.env`，复制模板并替换其中的占位密码：

```bash
cp .env.example .env
```

下面四项负责初始化 PostgreSQL 容器：

```dotenv
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-local-password
POSTGRES_DB=blog
POSTGRES_PORT=5434
```

`DATABASE_URL` 负责让 FastAPI 和 Alembic 连接数据库。它的用户名、密码、端口和数据库名必须与上面四项保持一致。密码包含特殊字符时，需要在 URL 中进行百分号编码。

## 每天最常用的流程

启动数据库：

```bash
docker compose up -d --wait db
```

同步数据库迁移：

```bash
uv run alembic upgrade head
```

启动 FastAPI：

```bash
uv run fastapi dev
```

开发结束后停止数据库：

```bash
docker compose stop db
```

## Docker Compose 命令速查

### 启动和停止

```bash
# 第一次启动，或者容器被 docker compose down 移除后重新创建
docker compose up -d --wait db

# 停止数据库，但保留容器和数据
docker compose stop db

# 启动被 stop 的现有容器
docker compose start db

# 重启数据库
docker compose restart db

# 移除容器和 Compose 网络，但保留命名数据卷
docker compose down
```

区别：

- 执行 `stop` 后，用 `start` 恢复。
- 执行 `down` 后，容器已经被移除，需要用 `up -d --wait db` 重新创建。

### 状态、健康和日志

```bash
# 查看服务状态和健康状态
docker compose ps

# 检查 PostgreSQL 是否接受连接
docker compose exec db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

# 查看最后 100 行日志并持续跟踪
docker compose logs -f --tail=100 db

# 验证 compose.yaml 和 .env 是否能正确解析
docker compose config --quiet
```

按 `Ctrl+C` 退出日志跟踪不会停止数据库。

### 进入 PostgreSQL

```bash
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

进入 `psql` 后常用命令：

```text
\dt             列出数据表
\d posts        查看 posts 表结构
\l              列出数据库
\q              退出 psql
```

### 更新 PostgreSQL 16 镜像

```bash
docker compose pull db
docker compose up -d --wait db
```

镜像固定在 PostgreSQL 16 主版本，不会通过这里自动升级到 PostgreSQL 17。

## Alembic 命令速查

```bash
# 查看数据库当前 revision
uv run alembic current

# 升级到最新 revision
uv run alembic upgrade head

# 查看迁移历史
uv run alembic history

# 检查模型和数据库是否还有未生成的差异
uv run alembic check

# 根据模型改动生成新迁移；生成后必须人工检查迁移文件
uv run alembic revision --autogenerate -m "describe the change"
```

回退迁移会修改数据库数据或结构，不要把它当成普通日常命令。需要回退时先检查迁移内容和备份。

## 数据保存在哪里

Compose 使用命名 Docker volume：

```text
fastapi-blog_postgres_data
```

以下命令会保留数据：

```bash
docker compose stop db
docker compose down
```

不要运行下面的命令，除非你明确要删除本地数据库全部数据：

```text
docker compose down -v
```

## 从旧的手工容器迁移

旧的 `docker run` 容器和它的匿名 volume 不会自动变成 Compose 数据卷。当前旧容器还占用宿主机端口 `5434`，所以不能与新 Compose 数据库同时绑定这个端口。

如果旧数据不需要保留：

```bash
docker stop fastapi_blog
docker compose up -d --wait db
uv run alembic upgrade head
```

如果需要保留旧数据，先导出：

```bash
docker exec fastapi_blog pg_dump \
  -U postgres \
  -d blog \
  --format=custom \
  --no-owner \
  > /tmp/fastapi_blog.dump
```

然后停止旧容器，启动 Compose 数据库并恢复：

```bash
docker stop fastapi_blog
docker compose up -d --wait db

docker compose exec -T db pg_restore \
  -U postgres \
  -d blog \
  --no-owner \
  < /tmp/fastapi_blog.dump

uv run alembic current
uv run alembic upgrade head
```

确认数据和应用都正常以前，不要删除旧容器或旧 volume。停止旧容器不会删除它的数据，可以用下面的命令回退到旧容器：

```bash
docker compose stop db
docker start fastapi_blog
```

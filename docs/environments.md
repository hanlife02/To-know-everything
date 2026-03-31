# 环境与部署

## 目标

- 开发环境和生产环境都不需要改代码
- 后端从仓库根目录读取分层 `.env`
- 前端从 `apps/web` 目录读取 Vite 环境文件

## 后端环境文件

后端启动时会按以下顺序加载，后面的文件覆盖前面的文件；如果某个变量已经在系统环境变量里显式设置，则不会被文件覆盖：

1. `.env`
2. `.env.local`
3. `.env.<TKE_ENV>`
4. `.env.<TKE_ENV>.local`

`TKE_ENV` 未显式设置时：

- `cargo run` / debug 构建默认 `development`
- release 构建默认 `production`

推荐用法：

```text
.env
.env.development
.env.production
.env.local
.env.development.local
.env.production.local
```

示例：

```dotenv
# .env
TKE_APP_NAME="To Know Everything"
TKE_SESSION_COOKIE_NAME=tke_session
TKE_SESSION_TTL_HOURS=720
```

```dotenv
# .env.development
TKE_SERVER_ADDR=127.0.0.1:8787
TKE_DATABASE_PATH=./data/dev.db
TKE_WEB_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

```dotenv
# .env.production
TKE_ENV=production
TKE_SERVER_ADDR=0.0.0.0:8787
TKE_DATABASE_PATH=./data/prod.db
TKE_WEB_ORIGINS=https://admin.example.com
```

## 前端环境文件

Vite 原生支持：

```text
apps/web/.env
apps/web/.env.local
apps/web/.env.development
apps/web/.env.production
apps/web/.env.development.local
apps/web/.env.production.local
```

当前前端支持：

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8787
```

规则：

- 开发环境未配置时，默认请求 `http://127.0.0.1:8787`
- 生产环境未配置时，默认请求同源相对路径 `/api`
- 如果前后端分开部署，生产环境把 `VITE_API_BASE_URL` 设成完整后端地址

示例：

```dotenv
# apps/web/.env.development
VITE_API_BASE_URL=http://127.0.0.1:8787
```

```dotenv
# apps/web/.env.production
VITE_API_BASE_URL=https://api.example.com
```

如果生产环境是反向代理同域部署，可以不设置 `VITE_API_BASE_URL`。

## 开发环境启动

后端：

```powershell
cargo run -p tke-server
```

前端：

```powershell
cd apps/web
npm run dev
```

## 生产环境构建

后端：

```powershell
cargo build -p tke-server --release
```

前端：

```powershell
cd apps/web
npm run build
```

产物位置：

- 后端可执行文件：`target/release/tke-server.exe`
- 前端静态文件：`apps/web/dist`

## 典型部署方式

### 同域部署

- 反向代理把 `/api` 转到 `tke-server`
- 静态文件直接托管 `apps/web/dist`
- 前端可不配置 `VITE_API_BASE_URL`

### 分域部署

- 前端部署到 `https://admin.example.com`
- 后端部署到 `https://api.example.com`
- 前端生产环境设置 `VITE_API_BASE_URL=https://api.example.com`
- 后端 `TKE_WEB_ORIGINS` 允许前端域名

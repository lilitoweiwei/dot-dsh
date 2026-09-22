# ~/.dsh 配置仓库

本仓库管理 DeepSeek Harness（[github.com/deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness)）在本机上的运行期配置。已在 **v0.1.5-rc.2**（tag `fb2c4b9e69` + 本地 patch `7990e14ca8`）上验证可正常运行，其他版本未经测试。

## 仓库布局

```
~/.dsh/
├── .gitignore          # 排除密钥与运行时数据的规则
├── .gitmodules         # 插件 submodule 清单
├── plugins/            # 第三方插件（每个插件是一个 git submodule）
├── profiles/           # dsh profile 定义
├── .agent-presets/     # 自定义 agent preset
└── settings.yaml       # dsh 运行设置
```

## 管理插件

插件有两条接入路径，按插件是否以 npm 包发布来选。

### A. npm 包（以 npm 发布的客户端插件走这条）

`dsh plugin` 是 pnpm 转发器：把包装进 profile，并把包名追加到该 profile
`package.json` 的 `dsh.profile.bundles`（声明了 `dsh.bundle.patch` 的包才算一层）。

```bash
dsh plugin --profile web-plus add <包名>@<版本>
dsh plugin --profile web-plus remove <包名>
```

版本管理对象是 profile 的 `package.json` 与 `pnpm-lock.yaml`；装进
`profiles/<profile>/node_modules/` 的实体是构建产物，已 gitignore，恢复时用
`install` 重装（见末节）。

当前以这条路径接入：`dsh-web-mobile`（移动端布局，窄屏 + 粗指针下把三栏 shell
转成抽屉式布局，桌面细指针任何宽度保持原样）。

### B. 源码 submodule（本仓库原有做法）

1. `git submodule add <repo-url> plugins/<name>`，把插件源码纳入版本管理；
2. 在 profile 的 `cordis.patch.yml` 里用相对路径引用插件入口：

   ```yaml
   - insert:
       - id: <entry-id>
         name: "../../plugins/<name>/<入口>"
   ```

   相对路径以 profile 目录为基准，`../../` 上溯到 `~/.dsh` 再进入 `plugins/`。

当前以这条路径接入：

| 插件 | 做什么 |
|---|---|
| `dsh-web-search-tavily` | Tavily 后端的 `web_search` provider（密钥轮转） |
| `dsh-web-pwa` | DSH Web 的 PWA 安装元数据：自带光栅图标的 manifest + 让浏览器带凭据取 manifest 的 index tap（上游 manifest 用 `sizes:"any"` 的 SVG，Chrome 解析成 `0x0` 装不上；且取 manifest 时不带 cookie，鉴权反代后面只会拿到登录页）。取代了 2026-09-22 之前对 `apps/web/dist` 的手工补丁 |

### 升级插件

`git submodule update --remote` 拉取插件最新 commit（或手动 `checkout` 到目标 commit），随后在 `.dsh` 仓库提交 gitlink 变更。npm 包路径用 `dsh plugin --profile web-plus add <包名>@<新版本>` 升级。

> 注意：升级后请核对 patch 里的相对路径是否仍指向插件入口——插件仓库目录结构调整会使引用失效。

## 版本管理规则

**进版本管理**：配置类文件——`profiles/`、`.agent-presets/`、`settings.yaml`、`plugins/`（submodule）。

**不进版本管理**（见 `.gitignore`）：

| 路径 | 原因 |
|---|---|
| `.credentials.yaml`、`.anonymous-user-id` | 密钥与隐私，绝对红线 |
| `sessions/`、`storages/`、`attachments/`、`llm-deepseek/` | 运行时产生的瞬时数据 |
| `profiles/node_modules/` | dsh 启动时自动重建的模块 fallback，属构建产物 |
| `profiles/*/.dsh-module-fallback/` | 各 profile 内同类的 link 平面，同样由启动时重建 |

## 恢复环境

```bash
git clone git@github.com:lilitoweiwei/dot-dsh.git ~/.dsh
git -C ~/.dsh submodule update --init --recursive
# 安装 profile 的 npm 依赖：以 npm 包路径接入的插件实体不入版本管理
pnpm --dir ~/.dsh/profiles/web-plus install
```

随后按常规方式启动 dsh 服务即可，模块 fallback 会在启动时自动重建。
漏掉 `pnpm install` 时，profile 里以 npm 包接入的插件行解析不到包，启动会报
`plugin tree failed to load`。

## 已知上游 workaround

| 位置 | 问题 | 状态 |
|---|---|---|
| `profiles/web-plus/cordis.patch.yml` 末尾（`- id: modules` 段） | 组合里多出任何 `dsh.client` 行会踩中 `client-modules` 的启动竞态，首次启动可能报 `cannot get property "webServer" without inject` | 以行配置 `inject: [webServer]` 绕过（未改上游源码）；成因、依据与删除条件见该段注释 |

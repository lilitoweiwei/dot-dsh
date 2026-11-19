# ~/.dsh 配置仓库

本仓库管理 DeepSeek Harness（[github.com/deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness)）在本机上的运行期配置。当前针对 **v0.2.2-rc.2**（tag `ddac96760b`，分支 `upgrade/0.2.2-rc.2`，无本地 patch）验证，其他版本未经测试。
运行这个版本要求 **nodejs.org 的官方 Node 二进制**（不是 nixpkgs 构建的 Node），
原因与自检命令见 `~/ws/w/20260818-dsh/README.md` 注意事项 10。

## 仓库布局

```
~/.dsh/
├── .gitignore          # 排除密钥与运行时数据的规则
├── .gitmodules         # 插件 submodule 清单
├── CHANGELOG.md        # 配置层的变更记录
├── plugins/            # 插件（每个是 git submodule；多数自带 bundle 层）
└── profiles/           # dsh profile 定义
```

配置层的变更（profile patch 的语义变化、插件接入与升级、settings 迁移）记在
[`CHANGELOG.md`](CHANGELOG.md)；DSH 本身的版本升级流水见
`~/ws/w/20260818-dsh/CHANGELOG.md`。

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

当前以这条路径接入：

- `dsh-web-mobile` —— 移动端布局，窄屏 + 粗指针下把三栏 shell 转成抽屉式布局，桌面细指针任何宽度保持原样。
- `dsh-ctrl-enter-submit` —— 输入框回车语义：Enter 只换行、Ctrl/Cmd+Enter 发送。实现是在捕获阶段把
  Enter 事件改写成 Shift+Enter（宿主键位表对 `shiftKey === true` 直接放行给换行），`/`、`@` 菜单打开
  与输入法组合中不改写。插件本身没有设置项，停用即恢复原生行为。

### B. 本仓库自带的 bundle（submodule 源码 + `link:` 安装）

本仓库里的插件都是 **bundle**：包内有自己的 `cordis.patch.yml`，`package.json` 声明
`dsh.bundle.patch`。装进 profile 只需要一条命令 —— `dsh plugin` 记成 `link:` 依赖、把包名追加到
`dsh.profile.bundles`，然后包内的 patch 自己插那一行：

```bash
dsh plugin --profile web-plus add ~/.dsh/plugins/<name>
```

于是「一个插件的配置」跟着它自己的仓库走，profile 的 `cordis.patch.yml` 里不再有它们的行；
启停在 GUI 的 Plugins 页按 bundle 做（它是唯一能被单独关掉的粒度）。

当前以这条路径接入：

| 插件 | 做什么 | 它插的行 |
|---|---|---|
| `dsh-web-search-tavily` | Tavily 后端的 `web_search` provider（密钥轮转）；同时把 `web` 行的 `searchProvider` 钉成 `tavily` | `web-search-tavily` + 覆盖 `web` |
| `dsh-web-pwa` | DSH Web 的 PWA 安装元数据：自带光栅图标的 manifest + 让浏览器带凭据取 manifest 的 index tap（上游 manifest 用 `sizes:"any"` 的 SVG，Chrome 解析成 `0x0` 装不上；且取 manifest 时不带 cookie，鉴权反代后面只会拿到登录页） | `web-pwa`（`display: standalone`） |
| `dsh-wsjump` | DSH Web 侧栏的工作区面板：检索 / 新建 wsjump 工作区，编辑其标签与描述（元信息写入 `wsmeta.txt`） | `dsh-wsjump` |
| `dsh-editor` | 右侧栏文件编辑器（**fork**：[`lilitoweiwei/dsh-editor`](https://github.com/lilitoweiwei/dsh-editor)，上游 `dongasai/dsh_editor` v1.2.0）。官方文档预览只读，它把编辑器注册成文档渲染器（「打开方式」下拉里可逆切换），并补上「🗑 删除」按钮、可保存的编辑器页签与自带文件树的「文件编辑」面板；写盘走插件自己的六条 `/workspace-editor/*` Host 路由，带版本闸、工作区包含检查与沙箱策略 | `workspace-editor` |
| `dsh-webui-location` | 输入框 `+` 菜单里的「位置信息」：点一下把浏览器坐标写成一行文本插进光标处 | `webui-location` |
| `dsh-image-gen` | `image_gen` / `image_prompt_guide` 两个图像生成工具。**唯一的例外**：它插的是 host 平面的 `image-gen-gate` 服务，工具行反而挂在 preset 里（`pluszero` 与 `subone`），工具只在那个 preset 的会话里出现 | `image-gen-gate` |

> `tencent-map-mcp` 是个例外：它不是 npm 包，没有 `package.json`，由 `pluszero` preset 里的一行
> `mcp-client` 用 `uv run --project` 拉起（路径写死在那一行里）。它没有 bundle 形态。

### 升级插件

`git submodule update --remote` 拉取插件最新 commit（或手动 `checkout` 到目标 commit），随后在 `.dsh` 仓库提交 gitlink 变更；`link:` 依赖不需要重装。npm 包路径用 `dsh plugin --profile web-plus add <包名>@<新版本>` 升级。

> 注意两点：① 插件目录结构改了要同步它自己 `cordis.patch.yml` 里的入口；② `lib/` 类构建产物
> 不进版本管理，拉取后要重新 `npm run build`。

## 版本管理规则

**进版本管理**：配置类文件——`profiles/`（含 `profiles/web-plus/cordis.patch.yml`：preset 声明、默认模型、会话日志，以及设置页会回写的 UI 偏好行）、`plugins/`（submodule，每个插件的 bundle 层就在它自己的 `cordis.patch.yml` 里）。

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
漏掉 `pnpm install` 时，profile 里那些 `link:` 依赖不会出现在 `node_modules/`，对应插件的行会
解析不到包（preset 里引用 `dsh-image-gen` 的那一行同样会卡住），启动会报
`plugin tree failed to load`。

`lib/` 不进版本管理的插件（如 `dsh-wsjump`）还要在其目录执行一次
`npm install && npm run build`，否则 profile 里的入口解析不到文件。

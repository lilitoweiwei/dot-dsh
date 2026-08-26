# ~/.dsh 配置仓库

本仓库管理 DeepSeek Harness（[github.com/deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness)）在本机上的运行期配置。已在 **v0.1.1-rc.2** 上验证可正常运行，其他版本未经测试。

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

### 添加新插件

1. `git submodule add <repo-url> plugins/<name>`，把插件源码纳入版本管理；
2. 在 profile 的 `cordis.patch.yml` 里用相对路径引用插件入口：

   ```yaml
   - insert:
       - id: <entry-id>
         name: "../../plugins/<name>/<入口>"
   ```

   相对路径以 profile 目录为基准，`../../` 上溯到 `~/.dsh` 再进入 `plugins/`。

### 升级插件

`git submodule update --remote` 拉取插件最新 commit（或手动 `checkout` 到目标 commit），随后在 `.dsh` 仓库提交 gitlink 变更。

> 注意：升级后请核对 patch 里的相对路径是否仍指向插件入口——插件仓库目录结构调整会使引用失效。

## 版本管理规则

**进版本管理**：配置类文件——`profiles/`、`.agent-presets/`、`settings.yaml`、`plugins/`（submodule）。

**不进版本管理**（见 `.gitignore`）：

| 路径 | 原因 |
|---|---|
| `.credentials.yaml`、`.anonymous-user-id` | 密钥与隐私，绝对红线 |
| `sessions/`、`storages/`、`attachments/`、`llm-deepseek/` | 运行时产生的瞬时数据 |
| `profiles/node_modules/` | dsh 启动时自动重建的模块 fallback，属构建产物 |

## 恢复环境

```bash
git clone git@github.com:lilitoweiwei/dot-dsh.git ~/.dsh
git -C ~/.dsh submodule update --init --recursive
```

随后按常规方式启动 dsh 服务即可，模块 fallback 会在启动时自动重建。

# CHANGELOG

`~/.dsh` 配置仓库的变更记录：profile patch 的语义变化、插件接入与升级、settings 迁移、submodule 冻结点。

DSH 本身的版本升级流水（升到哪一版、回退点在哪）不在这里，见 `~/ws/w/20260818-dsh/CHANGELOG.md`。

## 0.2.2 时代

### 2026-11-19 — 插件 bundle 化：配置跟着插件仓库走

把「插件行写在 profile patch 里」改成「每个插件自己是一个 bundle」。profile 的
`cordis.patch.yml` 只剩必须压过所有 bundle 的行（preset 声明、默认模型、会话日志）与设置页会
回写的 UI 偏好行。五个插件补上 `dsh.bundle.patch` + 自己的 `cordis.patch.yml`，用
`dsh plugin --profile web-plus add ~/.dsh/plugins/<name>` 装成 `link:` 依赖并追加进
`dsh.profile.bundles`：

| bundle | 带来的行 |
|---|---|
| `@lilitoweiwei/dsh-web-search-tavily` | `web-search-tavily`（`searchDepth: basic`）+ 覆盖 `web`（`searchProvider: tavily` / `fetchProvider: http`） |
| `@lilitoweiwei/dsh-web-pwa` | `web-pwa`（`display: standalone`） |
| `dsh-wsjump` | `dsh-wsjump` |
| `@lilitoweiwei/dsh-editor` | `workspace-editor`（改用包自带的层，profile 里手写的 `dsh-editor` 行删掉） |
| `dsh-webui-location` | `webui-location` |
| `dsh-image-gen` | `image-gen-gate`（host 平面的**开关服务**，不提供工具） |

- **`dsh-image-gen` 的形态**：工具行仍然挂在 preset（`pluszero` / `subone`），但这包现在声明
  `dsh.bundle`，其补丁只插一个很薄的 host 服务 `imageGenGate`；`src/index.js` 的 `inject` 加了这个
  服务。于是「Plugins 页关掉这个 bundle」= 服务消失 = 两个工具从所有 preset 的会话里退出。bundle
  不能改别的 preset 的内部，这是它能拥有的全部杠杆。依赖关系同步简化：`dsh-my-agent-preset` 不再
  以 `link:` 依赖携带 `dsh-image-gen`，改由 profile 提供。
- **兼容声明**：`dsh-wsjump` / `dsh-webui-location` / `@lilitoweiwei/dsh-editor` / `dsh-image-gen`
  补了 `engines.dsh: ">=0.2.0 <0.3.0"`（此前一条也没声明，升级 DSH 时会被静默放过）。
  `dsh-web-pwa` / `dsh-web-search-tavily` 已有 `@deepseek-ai/dsh*` peer 范围，保持不动。
- **注释修正**：删掉 `session-log-deepseek` 那句「本行在 profile patch，设置页的开关不再能把它打开」
  —— 设置页写盘就是往 profile patch 的同一行写，那个结论站不住；只是我们没打算上锁，不需要额外说明。
- **代价（实测）**：bundle 的补丁文件**不在** HMR 的 watch 列表里（HMR 只 watch profile patch /
  home patch / profile manifest）。改 bundle 的 `cordis.patch.yml` 不会自己热生效，保存一次 profile
  patch 触发重组或重启即可。

### 2026-11-12 — 回车语义插件 + 工作区文件编辑器（fork）

- **新增 `dsh-ctrl-enter-submit@1.1.1`**（路径 A，npm）：Enter 只换行、Ctrl/Cmd+Enter 发送。做法是在
  `document` 捕获阶段把无修饰键的 Enter 改写成 `shiftKey: true`，让宿主键位表自己走
  `INSERT_LINE_BREAK` 分支；`/`、`@` 候选菜单可见、输入法组合中、带 Ctrl/Cmd/Alt 时一律放行。
  无设置项：停用插件即恢复原生「Enter 发送」。
- **新增 `dsh-editor`（fork）**：`lilitoweiwei/dsh-editor`，基线 `dongasai/dsh_editor` v1.2.0
  （`babd882`）。按 **路径 B** 接入（submodule + patch 行 `../../plugins/dsh-editor/index.js`），
  不再走 npm，也不在 `dsh.profile.bundles` 里选它；包名与客户端 id 改为 `@lilitoweiwei/dsh-editor`
  （`src/client.js` 的 `PACKAGE_NAME` 与派生 id 同步改名，`client.js` 由 `npm run build` 重新生成）。
- **为什么 fork**：后续要按本机习惯改造（编辑器形态、面板入口等），fork 保留上游 remote 便于合并；
  上游 npm 包名留在别人 scope 下，改了 id 才能与「路径 B」的挂载方式对齐。
- **生效方式**：两条都是热装载（HMR 重组 profile 组合），host 未重启；浏览器硬刷新一次。
  唯独改插件 `index.js` 的内容需要重启 `dsh-web`（`~/.dsh/plugins/` 不在 HMR 监视集内）。
- **fork 首个行为改动（fbc03bf）**：删掉 `dsh-editor` 预览头部的「✎ 编辑」按钮 —— 它把预览
  页签换成编辑器页签（`replaceTab`），而那个页签没有任何回预览的入口，只能关掉重开；官方
  预览的「打开方式」下拉本来就能在 Markdown/代码 与「编辑器」之间可逆切换，故编辑只留下拉
  这一条路径。「文件编辑」面板里点文件仍会开编辑器页签（已知的不可逆路径，本次未动）。

### 2026-11-12 — 启用 `subagent_fork`

- pluszero 加 `tool-subagent-fork`（`provider: fork`、`maxDepth: 1`）。上一批的「明确不开」清单里划掉 `subagent_fork`。
- 理由：长上下文里分工时，fork 子级继承父级已完成轮次，不必把前情重述进任务描述；`subagent` 仍是全新上下文的主力路径，两者并存。
- 代价与限制：fork 子级带走父级历史（请求前缀可复用，KV 命中率高）；上游刻意不给它模型选择参数，也不接受 `agent_preset`。

### 2026-11-12 — pluszero 扩充工具面

- 加 `time-context`：把"当前时间 / 时区 / 距上条模型可见事件多久"作为消息注入，默认 10 分钟最多一条。不配 `timeZone`（浏览器上报的时区优先，回落进程时区）。
- 加 `tool-todo`（`todo_write`）：`allowParallelInProgress: true`，允许同时推进多项（与上游 `standard` 一致），GUI 的「任务」面板显示进度。
- 加 `tool-schedule`：4 个工具，任务是 Host 级的、可投递到任意会话；Host 的 `schedule` 服务与 GUI 的 Schedule 页本来就在跑，这里只补工具。
- 加 `tool-office`：技能激活式（加载 `office`/`office-docx`/`office-xlsx`/`office-pptx` 之一后工具才出现），修好此前"技能在目录里、工具不存在"的死胡同。
- 明确不开：`ask_user_question`（用户习惯自己组织回答，不点选项）、`cordis_inspect_*`、`plan-mode`、`interrupt_agent`、`create_worktree`、terminal 六件套、session-search、plugin-manager/market、`subagent_fork`、workflow/ralph、cua/browser-use；forge bundle（变更请求与工作树）也没装，需要时从插件页一键开。

### 2026-11-12 — 配置刷新

- **搜索 provider 全部解禁**：删掉对 `web-search-deepseek` 的禁用，`deepseek-search-api`、`deepseek-official`、`tavily` 三项都回到「插件 → 内置插件配置 → 网页搜索与获取设置」的菜单里，可随时切换、立即生效（选择写回 `web` 行，持久化）。当前选择仍是 `tavily`。
- **`dsh-wsjump` 去掉硬编码绝对路径**：`wsjumpPath` 整块删除，插件按默认裸名从 `PATH` 解析（`~/ws/bin` 由 home-manager `sessionPath` 注入）。
- **patch 注释改成「为什么现在这样写」**：逐版本的改动记录从 `cordis.patch.yml` 迁进本文件。

### 2026-11-12 — 适配 dsh `0.2.2-rc.2`

- `webRuntime` → `webStartup`：`connection` 行的 `inject` 与 `trustedHosts` 表达式同步改名。不改的表现是这行等一个永不挂载的服务，Web UI 完全不启动。
- persona 去掉 `suffix`：`{{cwd}}` 变量已不存在，留着会让每个会话第一条请求抛 `unknown prompt variable`；工作目录那句改由 base 的 working-directory 服务注入。
- `tool-subagent` 删掉已废弃的 `backgroundMode`（新版本静默忽略），补 `interrupt: false` 与 base、三个自带 preset 对齐。
- `dsh-web-mobile` `3.0.3` → `3.3.5`。

### 2026-11-12 — 删掉不再需要的东西

- 删除随附的 `profiles/web`：CLI 首次 `--profile web` 按模板初始化出来的目录，唯一内容是早已被 `--trusted-host` 取代的静态 `trustedHosts` patch。
- 删除 `.agent-presets/`（0.1.7 起没有读取方，内容与 patch 里的声明已分叉）与 `settings.yaml.imported`。

### 2026-11-10 — flash 开 off 推理等级

`llm-pi-ai` 里给 `opencode-go/deepseek-v4.1-flash` 显式声明四级 effort：内置目录把 off 标成不支持，选择器里就没有 Off 档。

### 2026-11-05 — 接入 `dsh-wsjump`

侧栏工作区面板（检索 / 新建 wsjump 工作区、编辑标签与描述）以 submodule 方式接入，patch 里用相对路径引用其构建产物 `lib/index.js`。

### 2026-11-03 — 默认模型切到 `opencode-go/deepseek-v4.1-flash`

## 0.2.0 时代

### 2026-10-21 — 字号与欢迎提示版本；trustedHosts 跟到 dsha 域名

- 正文字号 15；欢迎提示的「最后确认版本」跟到 `2026-09-28.1`（该字段与源码常量精确相等才算已读，GUI 在你点掉公告时也会写它）。
- `trustedHosts` 补录的域名改成 `dsha.lan.supplient2026.lol`（机器改名后的真值）。

### 2026-10-10 — 适配 dsh `0.2.0-rc.2`

- **preset 由目录式改声明式**：旧的 `agent-presets` 行整条失效，换成 `agent-preset-registry`（选择 + 代际保留）与一行 `@deepseek-ai/dsh-agent-preset`（标识/元数据/子插件列表）。不改的后果是默认 preset 静默退回 `standard`、带 `agentPreset: pluszero` 的老会话拒绝恢复。
- **关闭会话日志上传**（`session-log-deepseek.enabled: false`）：0.2.0 把该默认值改成了 `true`，不关就会在每次官方 API 请求里附带 `dsh_session_log`（含未进模型的元数据事件，上游未脱敏）。
- 删掉 `modules` / `inject: [webServer]` 的启动竞态 workaround（上游已修），并补插件 peer 依赖。
- `dsh-web-mobile` `3.0.0` → `3.0.3`。
- 0.2.0 首次启动把 `settings.yaml` 一次性导入 patch（主题、字号、欢迎提示版本由此进入本文件）。

## 0.1.x 时代

### 2026-09-22 — 接入 `dsh-web-pwa`

自带光栅图标的 manifest + 让浏览器带凭据取 manifest 的 index tap，取代对 `apps/web/dist` 的手工补丁（每次 `pnpm run build:web` 都会丢）。`display: standalone` 替换上游的 `fullscreen`，保留系统状态栏与导航栏。

### 2026-09-21 — 接入 `dsh-web-mobile`

移动端布局以 npm 包路径接入（声明了 `dsh.bundle.patch`，因此必须写进 profile 的 bundle 名单 —— 这也是 `web-plus` 这个 profile 存在的唯一原因）。

### 2026-09-15 — Tavily `searchDepth` 降为 `basic`

插件默认 `advanced`（2 credits/请求），免费 key 反复撞额度上限；`basic` 是 1 credit/请求且延迟更低。

### 2026-09-12 — 适配 dsh `0.1.5-rc.2` / `0.1.2-rc.1`

- persona 拆成 `prefix` + `suffix`（0.1.2 那个版本还要求 `text`，先在中间版本上用 `text` 过渡）。
- 0.1.2 起 fetch provider 由 base 自带并在 `web` 行给出 `fetchProvider: http`；由于 patch 是整段替换 config，覆盖 `web` 行时必须把它一并重述，否则 `web_fetch` 失去显式 provider。
- 浏览器会话 cookie 有效期从默认 30 天提到 1 年（`cookieMaxAgeDays: 365`），减少"首次访问要从日志取启动令牌"的频率。
- pluszero 启用 `present`（文件交付卡片）、显式禁用 goal（`/goal` 命令与 goal 工具都归 preset 所有，不写就没有）。

### 2026-09-02 — 默认模型切到 `deepseek-official`；接入后移除 `dsh-better-sidebar`

### 2026-08-28 — connection 去掉静态 `trustedHosts`

信任回归 CLI `--trusted-host` 注入（`trustedHosts: !!js ctx.webStartup.trustedHosts`），profile 里不再写死域名。同一天 pluszero 启用技能（`skill-filesystem` 发现 + `skill` 工具），并把 `README.md` 加进 workspace 指令候选。

### 2026-08-27 — `trustedHosts` 补录 dshu 域名

### 2026-08-26 — 仓库初始化

开始跟踪 profile / preset / settings 配置；Tavily search provider 以 submodule 方式接入，profile 用相对路径引用插件源码。

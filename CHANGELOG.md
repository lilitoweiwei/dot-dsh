# CHANGELOG

配置仓库的变更记录：profile patch 的语义变化、插件接入与升级、settings 迁移、submodule 冻结点。
仓库根就是 DSH 的数据根（`$DSH_HOME`），本机自 2026-11-19 起在 `~/ws/w/20260818-dsh/dsh-home`（原 `~/.dsh`）。

DSH 本身的版本升级流水（升到哪一版、回退点在哪）不在这里，见 `~/ws/w/20260818-dsh/CHANGELOG.md`。

## 0.2.2 时代

### 2026-11-23 — 接入 PDF 阅读器 `dsh-pdf-bookmarks`（fork，含自动续读）

补齐右侧栏 PDF 预览的三件事：文档内嵌目录跳转、任意页码跳转、阅读进度。

- **fork 而不是从零写**：上游 `woody-dx/dsh-pdf-bookmarks` 0.1.2 已经用官方 `documentPreviews` 扩展点把
  PDF 渲染器整块替换掉（`priority: 'extension'`、完整字节、自带 vendored pdf.js 引擎 + `require.async` 懒加载），
  目录/书签/页码/连续滚动/缩放/文字选择都齐了，本机只需补「自动续读」。
- fork 仓库 `lilitoweiwei/dsh-pdf-bookmarks`，`0.1.3`：按文档内容 SHA-256 保存页码+页内位置，
  滚动停止 600ms / 页面隐藏 / 卸载时落盘，重开自动恢复并给出「已回到上次阅读位置」提示与「回到开头」；
  续读位置单独存 `dsh-pdf-bookmarks:progress:v1:`，旧书签数据零迁移；存储不可用时静默退化为不续读。
- **接入形态**：submodule `plugins/dsh-pdf-bookmarks`（指向 fork）+ `link:../../plugins/dsh-pdf-bookmarks`，
  profile 的 `dsh.profile.bundles` 追加 `dsh-pdf-bookmarks`；插件自带 `cordis.patch.yml`（含产物 SHA-256 的
  guard 行），profile patch 不需要额外条目。
- **验证**：插件 21 项 Node 测试全过；自带浏览器 harness 实测「滚到第 2 页 → 刷新 → 自动回到第 2 页并出提示」；
  线上组合 81 个客户端入口里出现 `dsh-pdf-bookmarks`，combo 与 6.8 MB 引擎 chunk 均可取（未重启，配置热重组生效）。
- **行为**：默认成为 `.pdf` 的阅读器；「打开方式」下拉仍可一键切回内置 PDF，两个预览互不影响。

### 2026-11-23 — PDF 阅读器 fork 升到 0.1.4：页面列表虚拟化

用户反馈在 926 页的 *Patternmaking for Fashion Design* 上「每页等很久、目录跳转卡很久、渲染时整个 WebUI 变卡」。
定位为上游实现的渲染结构问题（不是引擎），在 fork 内重写页面层，不动 vendored 引擎：

- **病因**：每页都挂成 DOM 节点（926 个页框 + 926 个 IntersectionObserver），每个滚动帧遍历全部页框量位置
  （~940 次 `getBoundingClientRect`）并重渲染整表；未渲染页用第 1 页尺寸占位，真实高度要等渲染完才知道，
  于是滚动位置会漂、目录跳转要等目标页渲染完才落定；「适应宽度」按第 1 页（252×327 pt 封面）定缩放，
  把 589.68×792 pt 的正文撑到侧栏外，每页多渲染约 5 倍像素。
- **改法**：打开时并行量出全部页面真实尺寸（926 页约 0.2 s）→ 绝对定位落到累计偏移；只挂载视口 ±1 屏的页框，
  可见范围用 `scrollTop` 二分查找（滚动期间不读 DOM）；单一路径的串行渲染泵按距离当前页排序、滚出窗口即取消，
  完成位图进小型 LRU；适应宽度改以出现最多的页宽为基准；当前页与续读位置取视口顶边所在页。
- **实测**（481 px 侧栏、DPR 2）：页框节点 926 → 4–5；每滚动帧 `getBoundingClientRect` ~940 → 2；
  连续滚动帧耗时 p95/最长 59/103 ms → 34/45 ms；目录跳转目标页出现 ~700 → ~120 ms，滚动停止 ~1100 → ~300 ms；
  单页渲染 100–720 ms → 12–210 ms；全流程主线程长任务 3100–3700 ms → 520–820 ms。
- **验证**：插件 23 项 Node 测试全过；926 页实机基准 + 16 项浏览器功能回归（跳转精度、续读、缩放锚点、书签、
  文字层、虚拟化、窄栏）全过；`lib/client.engine.js` 逐字节未变（pdf.js 与加载协议没动）。
- **部署**：submodule 指向 `b466c86` / tag `v0.1.4`；线上 bundle rev 由内容哈希决定（`2a01c7af7556` 之类），
  重新构建即换 URL，浏览器不会拿旧缓存，也不需要重启服务。

### 2026-11-23 — PDF 阅读器 fork 升到 0.1.6：导航展开时点正文即收起

用户觉得每次都回去点工具栏的 **☰** 太麻烦，希望「点一下 PDF 页面（导航以外的地方）」就收起。

- **改法**：在正文滚动区（`.dpb-scroll`）上挂 pointerdown + click；导航与工具栏是它的**兄弟节点**，
  所以点导航内部/工具栏不会误收。记下 pointerdown 的位置，抬起时位移 > 6px 就忽略 ——
  拖动选字与触摸滑动滚动不会被当成「点一下」。
- **实测**：新增 20 项浏览器检查（窄栏 481px / 宽栏 900px / 触摸 412px 各一组）全过，其中
  触摸滑动把内容滚了 511px 仍保持展开、收起前后 `scrollTop` 不变；原有 16 项功能回归与 25 项 Node 测试全过；
  `lib/client.engine.js` 与 0.1.5 逐字节相同。
- **部署**：submodule 指向 `1071219` / tag `v0.1.6`；线上 bundle rev 变为 `9e454e416f9c`，
  刷新页面即生效，不需要重启服务。

### 2026-11-23 — PDF 阅读器 fork 升到 0.1.5：http 域名下打不开（crypto.subtle）

用户报「手机能看、电脑上直接报 Cannot read properties of undefined (reading 'digest')」。定位为**插件缺陷**（与 PDF 无关）：

- **病因**：`crypto.subtle` 只在安全上下文（https / localhost / file）里存在。本机桌面走 `http://dshu:3080`
  （tailscale serve 只提供 http，`dshu` → 127.0.0.2），实测该源 `isSecureContext=false`、
  `crypto.subtle` 与 `crypto.randomUUID` 都是 `undefined`；手机走公网网关 `https://106.14.149.127:9093`，
  是安全上下文，所以只有电脑炸。文档内容键正是 `crypto.subtle.digest('SHA-256')`，于是打开阶段必抛。
- **改法**：新增 `src/sha256.js`（纯 JS 增量 SHA-256，输出与原生逐字节一致）作为降级实现，分片计算并用
  MessageChannel 让出主线程；`documentKey` 优先原生、缺失或抛错时降级；内容键与 PDF 解析/尺寸表并行；
  `newId()` 三级降级（randomUUID → getRandomValues → Math.random）。内容键不变 ⇒ 已有书签/续读零迁移。
- **实测**：真实 http 源（`http://insecure.test:58500`，Chromium 147，subtle 缺失）下 926 页 27 MB 文档
  正常渲染、加书签、滚动存进度、刷新续读到第 9 页全过，控制台零错误，算出的键与 `sha256sum` 一致；
  安全上下文 16 项功能回归全过；27 MB 纯 JS 哈希约 0.8 s，但切成短任务（最长任务 0 ms），
  http 源首次打开约多 0.8 s，https 源无此开销。
- **部署**：submodule 指向 `e1846b7` / tag `v0.1.5`；bundle rev 由内容哈希决定，刷新页面即生效。
- **残留选项**：若想连这 0.8 s 也去掉，可给 tailscale serve 开 https（`tailscale cert` + `serve https:`），
  桌面也进安全上下文，届时走原生 digest。

### 2026-11-19 — 数据根迁到工作区：`~/.dsh` → `~/ws/w/20260818-dsh/dsh-home`

把整个数据根（profile、插件 submodule、会话、附件、技能、凭据）搬进 DSH 工作区，让源码 checkout、
运维文档、配置仓库、运行数据集中在一处。

- **位置由环境变量决定**：nixos 的 `homes/dshu/default.nix` 显式声明
  `sessionVariables.DSH_HOME`（home-manager 会话变量，服务的 `bash -lc` 与交互 shell 都继承它）。
  以前全靠 `home-paths` 的默认值 `~/.dsh` 隐式约定。
- **顺带消掉配置里的绝对路径**（先改相对路径、再搬迁，避免搬迁时混合两类失败）：
  profile 的 7 条 `link:` 依赖改成 `link:../../plugins/<name>`（pnpm 相对 profile 目录解析，锁文件的
  specifier 同步重新生成）；`mcp-tencent-lbs` 行的 `uv run --project` 改成以 `$DSH_HOME` 为根、
  只在没有该变量时回退 `$HOME/.dsh`；`skills/mail-notify/SKILL.md` 里写死的脚本路径改用
  `${DSH_HOME:-$HOME/.dsh}`。
- **不在路径里的两处配套**：外层工作区 `.gitignore` 加 `/dsh-home/`（数据根本身是独立仓库
  `dot-dsh`）；`tencent-map-mcp` 的 `.venv` 里是绝对路径的 shebang 与 `.pth`，搬迁后删掉让
  `uv run` 重建。
- **为什么叫 `dsh-home` 而不是 `.dsh`**：`skill-filesystem` 会把 `<cwd 的 git 根>/.dsh/skills` 当项目
  技能根；若数据根叫 `<git 仓库>/.dsh`，它与全局根 `$DSH_HOME/skills` 就是同一目录，会以「项目技能」
  的身份重复扫描同一批文件。`dsh-home` 让两者永不重合。
- **验证**：搬迁后冷启动零告警（`--dump-config` exit 0 / stderr 0 行），会话、附件、技能、腾讯地图
  MCP、`image_gen`、Plugins 页 11 层 bundle 全部正常；旧会话可恢复（会话记录存的是工作区路径）。

### 2026-11-19 — 插件 bundle 化：配置跟着插件仓库走

把「插件行写在 profile patch 里」改成「每个插件自己是一个 bundle」。profile 的
`cordis.patch.yml` 只剩必须压过所有 bundle 的行（preset 声明、默认模型、会话日志）与设置页会
回写的 UI 偏好行。五个插件补上 `dsh.bundle.patch` + 自己的 `cordis.patch.yml`，用
`dsh plugin --profile web-plus add "$DSH_HOME/plugins/<name>"` 装成 `link:` 依赖并追加进
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
  唯独改插件 `index.js` 的内容需要重启 `dsh-web`（`$DSH_HOME/plugins/` 不在 HMR 监视集内）。
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

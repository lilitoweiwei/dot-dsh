# 本目录自 2026-10-10 起**不再被 dsh 读取**

dsh 0.1.7 起取消了「目录式 Agent preset」：`$DSH_HOME/.agent-presets/` 不再被扫描，
preset 必须由 profile / bundle patch 里的一行 `@deepseek-ai/dsh-agent-preset` 声明。

`pluszero` 的**活定义**现在在这里：

```
~/.dsh/profiles/web-plus/cordis.patch.yml
  ├─ - id: agent-preset-registry   name: '@deepseek-ai/dsh-agent-preset-registry'   # default: pluszero
  └─ - id: preset-pluszero         name: '@deepseek-ai/dsh-agent-preset'            # config.plugins = 原 agent.cordis.yml 的内容
```

要改 pluszero 的行为（挂哪些工具、persona、压缩、子代理深度等），**改那份文件**，
不要改本目录——改这里不会有任何效果。

本目录保留为历史参照：`agent.cordis.yml` 就是当初被逐字搬进 `preset-pluszero` 的那份
entry list；`preset.yml` 的 name / description / order 已并进声明的 `config`。
（背景：`~/ws/w/20260929-dsh-version-choice/notes/execution-20261010.md`）

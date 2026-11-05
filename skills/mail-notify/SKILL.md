---
name: mail-notify
description: 给用户发邮件（163 SMTP → 用户邮箱）。当内容超过一两行、需要配图/表格、或需要留档时用它，而不是只发一行通知。
---

# 发邮件

`mailme.py` 在本 skill 目录下，单文件、零依赖。凭据由 sops 渲染在
`~/.config/sops-nix/secrets/rendered/mail.env`，脚本自己读，不需要 source。

```bash
P=~/.dsh/skills/mail-notify/mailme.py
```

## 基本调用

```bash
# 纯文本：正文走 stdin
printf '正文第一行\n第二行\n' | python3 $P -s "主题" --to 437566830@qq.com

# HTML：正文在文件里
python3 $P -s "日报 2026-11-05" --to 437566830@qq.com --html --body page.html

# 带内嵌图和附件
python3 $P -s "周报" --to 437566830@qq.com --html --body page.html \
  --image chart.png --attach report.pdf
```

**收件人**：当前是 `437566830@qq.com`。用户的收件地址可能变，改这一处即可。

| 参数 | 说明 |
|---|---|
| `-s/--subject` | 必填 |
| `--to` | 必填，可逗号分隔；不能用默认值 |
| `--cc` / `--bcc` | 可选。`--bcc` 只进信封，不写进头部 |
| `--html` | 正文按 HTML 处理；不给则按纯文本 |
| `--body FILE` | 正文文件；不给则从 stdin 读 |
| `--from-name` | 覆盖发件人显示名（默认「AI 助手」） |
| `--image FILE` | 内嵌图片，可重复 |
| `--attach FILE` | 附件，可重复 |
| `--dry-run` | 只打印头部和 MIME 结构，不发 |
| `--save FILE` | 存一份 .eml |

## 内容：只封装发送，不封装格式

正文原样进邮件，不做 markdown 转换。纯文本模式下整块放在 `<pre>` 里（只转义）；
HTML 模式下原样发送，并自动去标签生成一份 `text/plain` 兜底。

**图片必须自己写 `cid:`**。`--image chart.png` 会得到 `cid:chart`（文件名主干，重名自动加
`-2`），HTML 里要写 `<img src="cid:chart">`。工具**不会**改写你的 `src`，写错了就是空白框。
外链图片在部分客户端默认不加载，本地图一律用 `--image` 内嵌。

## 邮件能渲染到什么程度

数据来自 caniemail.com 的实测。判断标准是最差的客户端（Windows Outlook 用 Word 渲染引擎）。

- **能用**：`<table>` 布局、内联 `style`、圆角（会退化）、GIF、`cid:` 图、系统字体。
- **不能用**：JS、flex、grid、`position`、`transform`、CSS 变量、`@font-face`、内嵌 SVG、
  `data:` base64 图片、`<video>`、`<iframe>`、表单提交。
- 布局只能用 table；单栏、宽度 600px 左右最稳。
- 视频只能放缩略图 + 链接，或剪成 GIF。

## 附带限制

- 单封总大小受收件方限制（QQ 邮箱 55MB，网易 50MB）；base64 会让附件膨胀约 1/3。
- HTML 正文别超过 100KB，Gmail 超过 102KB 会截断。
- 主题别用纯 emoji 或纯大写。

## 退出码

| 码 | 含义 |
|---|---|
| 0 | 成功（stdout 有一行摘要） |
| 2 | 参数错 |
| 4 | 认证失败（授权码失效） |
| 5 | 服务器拒绝（地址/内容） |
| 6 | 网络失败 |

同一内容不要重复发；不要在循环里逐条发——发件邮箱是免费个人邮箱，日发信量有上限
（几十封量级），撞上了会被临时限制。一天几封到十几封是安全的。

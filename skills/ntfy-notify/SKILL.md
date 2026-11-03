---
name: ntfy-notify
description: >-
  通过自建 ntfy 服务器把通知推送到用户手机。凭据由 sops 渲染成本机一个
  dotenv 文件，source 之后用 curl 发，不需要任何封装脚本。
whenToUse: 当需要给用户发送通知的时候。
---

# 给用户发通知

自建 ntfy 服务器，手机上是官方 Android app，长连接常驻。发一条通知就是一次
HTTP 请求：没有队列、没有模板、也没有送达确认。

## 环境

| 项 | 值 |
|---|---|
| 服务器 | `$NTFY_URL`（`https://106.14.149.127:9094`） |
| 凭据文件 | `~/.config/sops-nix/secrets/rendered/ntfy.env`（sops 渲染，内含 `NTFY_BOT_INFO_TOKEN`） |
| topic | `info` |

**每个 bash 调用都要先 source 这个文件。** DSH 在 spawn 子进程时会按变量名擦掉
含 `TOKEN`/`KEY`/`SECRET`/`PASSWORD` 的变量（`SENSITIVE_ENV_PATTERN`），所以
token **不会**被继承进来；但 `NTFY_URL` 会。source 之后两者都可用。

文件不存在时不要自己去翻密钥，直接告诉用户「凭据未渲染，需要 rebuild」。

## 发一条

```bash
. ~/.config/sops-nix/secrets/rendered/ntfy.env
curl -sS -X POST "$NTFY_URL/" \
  -H "Authorization: Bearer $NTFY_BOT_INFO_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"topic":"info","title":"构建完成","message":"3 个包，用时 42 秒","priority":3,"tags":["white_check_mark"]}'
```

成功时返回 200 和这条消息的 JSON（带服务端生成的 `id`）。

**用 JSON body，不要用 `Title:` / `Priority:` 这类 header**——header 是 latin-1，
中文标题和带引号的正文在 header 里都容易出错。

## 常用字段

| 字段 | 说明 |
|---|---|
| `title` | 标题 |
| `message` | 正文 |
| `priority` | `1` min / `2` low / `3` default / `4` high / `5` urgent |
| `tags` | 数组；命中 emoji 短码会显示图标，如 `warning`、`tada`、`white_check_mark` |
| `click` | 点通知后打开的 URL |

正文控制在 **4K 以内**（服务端硬上限）。

## 约定

- 主要是**写入**。除非用户明确要求，不要主动读取历史通知。
- 同一件事不要反复推送。

## 详细规范

https://docs.ntfy.sh/publish/

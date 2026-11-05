#!/usr/bin/env python3
"""mailme —— 通过 SMTP 发一封邮件。

设计约束：
  - 只封装「发送」，不碰内容。正文原样进邮件（--html 表示它是 HTML）。
  - 单文件、只用标准库（本机没有 pandoc，NixOS 不临时装包）。
  - 凭据读 sops 渲染出来的 dotenv；不依赖继承的环境变量（DSH 会擦掉含 PASS/TOKEN 的变量）。

退出码：
  0 成功 · 2 参数错 · 4 认证失败 · 5 服务器拒绝 · 6 网络失败
"""

import argparse
import email.policy
import html
import mimetypes
import os
import re
import smtplib
import ssl
import sys
import time
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from html.parser import HTMLParser
from pathlib import Path

CONNECT_TIMEOUT = 20
TOTAL_TIMEOUT = 45
RETRIES = 2

ENV_FILE = Path(
    os.environ.get(
        "MAILME_ENV", os.path.expanduser("~/.config/sops-nix/secrets/rendered/mail.env")
    )
)
EXIT_OK, EXIT_ARG, EXIT_AUTH, EXIT_REJECT, EXIT_NET = 0, 2, 4, 5, 6


class Fail(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code
        self.msg = msg


# ---------------------------------------------------------------- 配置


def load_env(path):
    if not path.is_file():
        raise Fail(
            EXIT_ARG,
            f"找不到凭据文件 {path}\n"
            "它应由 sops-nix 渲染（homes/dshu/mail.nix）。若未配置，先完成 sops + rebuild。",
        )
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        out[k.strip()] = v
    return out


# ---------------------------------------------------------------- 正文转换

_BLOCK = {
    "br",
    "p",
    "div",
    "tr",
    "li",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "table",
    "blockquote",
    "section",
    "article",
}
_SKIP = {"script", "style", "head", "title"}


class _ToText(HTMLParser):
    """HTML → 纯文本：只为 multipart/alternative 里的兜底副本，不求保真。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.buf = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP:
            self.skip += 1
        elif tag in _BLOCK:
            self.buf.append("\n")

    def handle_endtag(self, tag):
        if tag in _SKIP and self.skip:
            self.skip -= 1
        elif tag in _BLOCK:
            self.buf.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.buf.append(data)

    def text(self):
        s = "".join(self.buf)
        s = re.sub(r"[ \t\r\f\v]+", " ", s)
        s = re.sub(r"\n[ \t]+", "\n", s)
        s = re.sub(r"\n{3,}", "\n\n", s)
        return s.strip()


def html_to_text(s):
    p = _ToText()
    p.feed(s)
    p.close()
    out = p.text()
    return out or "（此邮件为 HTML 格式，请在支持 HTML 的客户端中查看）"


def text_to_html(s):
    """纯文本 → 极简 HTML。朴素：一整块 <pre>，只做转义，不解析结构。"""
    body = html.escape(s)
    return (
        "<!doctype html><html><body>"
        '<pre style="white-space:pre-wrap;word-wrap:break-word;'
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',"
        "'Microsoft YaHei',sans-serif;font-size:14px;line-height:1.6;margin:0;"
        f'color:#222">{body}</pre>'
        "</body></html>"
    )


# ---------------------------------------------------------------- 收件人 / 附件


_ADDR = re.compile(r"^[^@\s,;]+@[^@\s,;]+$")


def split_addrs(values, flag):
    out = []
    for v in values or []:
        for part in re.split(r"[,;]", v):
            part = part.strip()
            if not part:
                continue
            if not _ADDR.match(part):
                raise Fail(EXIT_ARG, f"{flag} 里的地址不像邮箱：{part!r}")
            out.append(part)
    return out


def cid_base(path):
    stem = Path(path).stem
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-")
    return stem or "image"


def guess_type(name, default="application/octet-stream"):
    return mimetypes.guess_type(name)[0] or default


def add_file_params(kw, name):
    kw["filename"] = name if name.isascii() else ("utf-8", "", name)


def new_part():
    return EmailMessage(policy=email.policy.SMTP)


def container(subtype, children):
    """显式装配一个 multipart 容器。

    email 库的 add_related/add_attachment 不能把 multipart/alternative 直接转成
    multipart/related（ValueError: Cannot convert alternative to related），所以
    这里自底向上自己搭：mixed( related( alternative(text, html), 图片 ) , 附件 )。
    """
    m = new_part()
    m["Content-Type"] = f"multipart/{subtype}"
    m.set_payload(children)
    return m


# ---------------------------------------------------------------- 构造消息


def build(args):
    env = {}
    to = split_addrs(args.to, "--to")
    cc = split_addrs(args.cc, "--cc")
    bcc = split_addrs(args.bcc, "--bcc")
    if not to:
        raise Fail(EXIT_ARG, "--to 不能为空")
    if not args.subject or not args.subject.strip():
        raise Fail(EXIT_ARG, "-s/--subject 不能为空")

    if args.body:
        raw = Path(args.body).read_text(encoding="utf-8")
    else:
        if sys.stdin.isatty():
            raise Fail(EXIT_ARG, "没有正文：用 --body FILE，或把正文从 stdin 管道进来。")
        raw = sys.stdin.read()
    if not raw.strip():
        raise Fail(EXIT_ARG, "正文是空的。")

    cfg = load_env(ENV_FILE)
    from_addr = cfg.get("MAIL_FROM", "").strip()
    if not from_addr:
        raise Fail(EXIT_ARG, f"{ENV_FILE} 里缺 MAIL_FROM")
    from_name = (args.from_name or cfg.get("MAIL_FROM_NAME", "") or "").strip()

    alt = new_part()
    if args.html:
        alt.set_content(html_to_text(raw), cte="base64")
        alt.add_alternative(raw, subtype="html", cte="base64")
    else:
        alt.set_content(raw, cte="base64")
        alt.add_alternative(text_to_html(raw), subtype="html", cte="base64")

    images, image_parts = [], []
    for spec in args.image or []:
        p = Path(spec)
        if not p.is_file():
            raise Fail(EXIT_ARG, f"--image 文件不存在：{p}")
        cid = cid_base(p)
        n, candidate = 1, cid
        while candidate in images:
            n += 1
            candidate = f"{cid}-{n}"
        mtype = guess_type(p.name, "image/png")
        maintype, _, subtype = mtype.partition("/")
        kw = {"cid": f"<{candidate}>", "disposition": "inline"}
        add_file_params(kw, p.name)
        part = new_part()
        part.set_content(p.read_bytes(), maintype=maintype, subtype=subtype, **kw)
        image_parts.append(part)
        images.append(candidate)

    body = container("related", [alt] + image_parts) if image_parts else alt

    attachments, attach_parts = [], []
    for spec in args.attach or []:
        p = Path(spec)
        if not p.is_file():
            raise Fail(EXIT_ARG, f"--attach 文件不存在：{p}")
        mtype = guess_type(p.name)
        maintype, _, subtype = mtype.partition("/")
        kw = {}
        add_file_params(kw, p.name)
        part = new_part()
        part.set_content(p.read_bytes(), maintype=maintype, subtype=subtype, **kw)
        attach_parts.append(part)
        attachments.append(p.name)

    msg = container("mixed", [body] + attach_parts) if attach_parts else body

    if "MIME-Version" not in msg:
        msg["MIME-Version"] = "1.0"
    msg["From"] = formataddr((from_name, from_addr)) if from_name else from_addr
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = args.subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=from_addr.rpartition("@")[2] or None)

    rcpts = to + cc + bcc  # Bcc 只进信封，不写进头部
    return msg, cfg, rcpts, from_addr, images, attachments


def describe(msg, depth=0):
    pad = "  " * depth
    lines = []
    if msg.is_multipart():
        lines.append(f"{pad}{msg.get_content_type()}")
        for sub in msg.get_payload():
            lines.append(describe(sub, depth + 1))
    else:
        parts = [msg.get_content_type(), f"{len(msg.get_payload(decode=True) or b'')}B"]
        if msg.get("Content-ID"):
            parts.append(f"cid={msg['Content-ID']}")
        if msg.get_filename():
            parts.append(f"file={msg.get_filename()}")
        lines.append(pad + " · ".join(parts))
    return "\n".join(lines)


# ---------------------------------------------------------------- 发送


def connect(cfg):
    host = cfg.get("SMTP_HOST", "smtp.163.com").strip()
    port = int(cfg.get("SMTP_PORT", "465"))
    sec = cfg.get("SMTP_SECURITY", "").strip().lower()
    if not sec:
        sec = "ssl" if port == 465 else ("starttls" if port == 587 else "plain")
    user = cfg.get("SMTP_USER", "").strip()
    pw = cfg.get("SMTP_PASS", "").strip()
    if not user or not pw:
        raise Fail(EXIT_ARG, f"{ENV_FILE} 里缺 SMTP_USER / SMTP_PASS")

    last = None
    for attempt in range(RETRIES + 1):
        try:
            if sec == "ssl":
                s = smtplib.SMTP_SSL(
                    host, port, timeout=CONNECT_TIMEOUT,
                    context=ssl.create_default_context(),
                )
            else:
                s = smtplib.SMTP(host, port, timeout=CONNECT_TIMEOUT)
                if sec == "starttls":
                    s.starttls(context=ssl.create_default_context())
            s.login(user, pw)
            return s
        except smtplib.SMTPAuthenticationError as e:
            raise Fail(
                EXIT_AUTH,
                f"认证失败（535）：{e}\n多数是授权码失效或被吊销——去邮箱网页端重新生成客户端授权码。",
            )
        except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError,
                smtplib.SMTPHeloError, OSError) as e:
            last = e
            if attempt < RETRIES:
                time.sleep(2 ** attempt)
                continue
    raise Fail(EXIT_NET, f"连不上 {host}:{port}（{sec}）：{last}")


def send(msg, cfg, rcpts, from_addr):
    s = connect(cfg)
    try:
        s.send_message(msg, from_addr=from_addr, to_addrs=rcpts)
    except smtplib.SMTPRecipientsRefused as e:
        raise Fail(EXIT_REJECT, f"收件人被拒：{e.recipients}")
    except smtplib.SMTPResponseException as e:
        code = e.smtp_code
        hint = {
            550: "收件人不存在或内容被拒",
            553: "发件人地址被拒",
            554: "内容被判为垃圾邮件",
            421: "服务器限流，稍后再试",
            450: "临时拒绝，稍后再试",
        }.get(code, "")
        raise Fail(EXIT_REJECT, f"服务器拒绝（{code}）{hint}：{e.smtp_error}")
    except smtplib.SMTPException as e:
        raise Fail(EXIT_NET, f"发送中断：{e}")
    finally:
        try:
            s.quit()
        except Exception:
            pass


# ---------------------------------------------------------------- main


def parse_args(argv):
    ap = argparse.ArgumentParser(
        prog="mailme", description="发一封邮件（正文原样，不做格式转换）"
    )
    ap.add_argument("-s", "--subject", required=True)
    ap.add_argument("--html", action="store_true", help="正文是 HTML（默认按纯文本处理）")
    ap.add_argument("--body", metavar="FILE", help="正文文件；不给则从 stdin 读")
    ap.add_argument("--to", action="append", metavar="ADDR", help="必填，可逗号分隔")
    ap.add_argument("--cc", action="append", metavar="ADDR")
    ap.add_argument("--bcc", action="append", metavar="ADDR")
    ap.add_argument("--from-name", metavar="NAME", help="覆盖发件人显示名")
    ap.add_argument("--image", action="append", metavar="FILE",
                    help="内嵌图片；cid 取文件名主干")
    ap.add_argument("--attach", action="append", metavar="FILE")
    ap.add_argument("--dry-run", action="store_true", help="只打印邮件结构，不发送")
    ap.add_argument("--save", metavar="FILE", help="把 .eml 存下来")
    return ap.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    msg, cfg, rcpts, from_addr, images, attachments = build(args)

    if args.save:
        Path(args.save).write_bytes(msg.as_bytes())
    if args.dry_run:
        print(f"From:    {msg['From']}")
        print(f"To:      {msg['To']}")
        if msg["Cc"]:
            print(f"Cc:      {msg['Cc']}")
        print(f"Subject: {msg['Subject']}")
        print(f"Rcpts:   {', '.join(rcpts)}")
        print(f"Size:    {len(msg.as_bytes()):,} bytes")
        if images:
            print("Images:  " + ", ".join(f"cid:{c}" for c in images))
        if attachments:
            print("Files:   " + ", ".join(attachments))
        print("\n结构：")
        print(describe(msg))
        print("\n（--dry-run：没有发送）")
        return EXIT_OK

    send(msg, cfg, rcpts, from_addr)
    bits = [f"{len(rcpts)} 收件人"]
    if images:
        bits.append(f"内嵌 {len(images)} 图")
    if attachments:
        bits.append(f"{len(attachments)} 附件")
    print(f"已发送 · {' · '.join(bits)} · {len(msg.as_bytes()):,} bytes · {msg['Message-ID']}")
    return EXIT_OK


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Fail as e:
        print(f"mailme: {e.msg}", file=sys.stderr)
        sys.exit(e.code)
    except BrokenPipeError:
        sys.exit(EXIT_NET)

"""CLI: workspace detect / split / pane / pipe / init."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .detect import detect
from .init import init_workspace
from .panes import (
    MuxError,
    close_pane,
    count_panes,
    focus_pane,
    list_panes,
    read_pane_content,
    resize_pane,
    send_keys_to_pane,
    send_text_to_pane,
    split_pane,
    swap_pane,
)
from .pipe import send as pipe_send, listen as pipe_listen


def _force_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workspace",
        description="检测 wt/herdr，同一窗口拆/换/调格，文件信箱传文本。",
    )
    parser.add_argument("--version", action="version", version=f"workspace {__version__}")
    sub = parser.add_subparsers(dest="command")

    init = sub.add_parser(
        "init",
        help="把 workspace skill 装到 .agents/skills 与 .claude/skills",
    )
    init.add_argument("dir", nargs="?", default=".", type=Path)
    init.add_argument("--force", action="store_true", help="覆盖已存在的 skill 目录")

    det = sub.add_parser("detect", help="当前是否在 wt（Windows）或 herdr（Linux）里")
    det.add_argument("--json", action="store_true")

    spl = sub.add_parser("split", help="同一窗口拆一格：right/down")
    _add_split_flags(spl)

    pane = sub.add_parser(
        "pane",
        help="同一窗口：split / swap / resize / count / read / text / keys / close",
    )
    pane_sub = pane.add_subparsers(dest="pane_command", required=True)
    psp = pane_sub.add_parser("split", help="同一窗口拆一格：right/down")
    _add_split_flags(psp)
    psw = pane_sub.add_parser("swap", help="与相邻格对调")
    psw.add_argument("direction")
    psw.add_argument("--json", action="store_true")
    prs = pane_sub.add_parser("resize", help="调整当前格大小")
    prs.add_argument("direction")
    prs.add_argument("--amount", type=float, default=None, help="herdr 比例；wt 为 Alt+Shift 次数")
    prs.add_argument("--json", action="store_true")
    pc = pane_sub.add_parser("count", help="当前窗口有几格")
    pc.add_argument("--json", action="store_true")
    pr = pane_sub.add_parser("read", help="读指定格的屏幕文本")
    pr.add_argument("id", help="序号或 pane_id / WT_SESSION 前缀")
    pr.add_argument("--json", action="store_true")
    ptxt = pane_sub.add_parser("text", help="向指定格打字（不带 Enter）")
    ptxt.add_argument("target")
    ptxt.add_argument("text", nargs="?", default=None)
    ptxt.add_argument("--json", action="store_true")
    pk = pane_sub.add_parser(
        "keys",
        help="向指定格发按键：up/down/left/right、enter、ctrl+c …",
    )
    pk.add_argument("target")
    pk.add_argument("keys", nargs="+", help="up down left right enter tab esc ctrl+c …")
    pk.add_argument("--json", action="store_true")
    pcl = pane_sub.add_parser("close", help="关掉指定格（不能关最后一格/自己）")
    pcl.add_argument("target")
    pcl.add_argument("--json", action="store_true")
    pl = pane_sub.add_parser("list")
    pl.add_argument("--json", action="store_true")
    pf = pane_sub.add_parser("focus")
    pf.add_argument("target")
    pf.add_argument("--json", action="store_true")

    pipe = sub.add_parser("pipe", help="项目级文件信箱 .workspace/inbox")
    pipe_sub = pipe.add_subparsers(dest="pipe_command", required=True)
    ps = pipe_sub.add_parser("send", help="写入一条文本消息")
    ps.add_argument("text", nargs="?", default=None)
    ps.add_argument("--root", type=Path, default=".")
    pln = pipe_sub.add_parser("listen", help="后台监听：打印后移到 seen/")
    pln.add_argument("--root", type=Path, default=".")
    pln.add_argument("--once", action="store_true", help="等到一条就退出")
    pln.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="秒；0 表示只清当前积压然后退出",
    )
    return parser


def _add_split_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("direction")
    parser.add_argument("--cwd", type=Path, default=None, help="默认当前 cwd")
    parser.add_argument("--title", default=None)
    parser.add_argument("--cmd", default=None, help="新窗格要跑的命令")
    parser.add_argument(
        "--agent",
        default=None,
        help="claude / codex / kimi / grok，或 PATH 上其它智能体（与 --cmd 互斥）",
    )
    parser.add_argument("--size", type=float, default=None, help="新窗格占比，如 0.4")
    parser.add_argument("--json", action="store_true")


def _print_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_init(args: argparse.Namespace) -> int:
    root = args.dir.resolve()
    try:
        actions = init_workspace(root, force=args.force)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for line in actions:
        print(line)
    return 0


def cmd_detect(args: argparse.Namespace) -> int:
    info = detect()
    if args.json:
        _print_json(info.to_dict())
    else:
        print(
            f"os={info.os} expected={info.expected} mux={info.mux or '-'} "
            f"inside={'true' if info.inside else 'false'}"
        )
        if info.session:
            print(f"session={info.session}")
        if info.pane:
            print(f"pane={info.pane}")
        if info.bin:
            print(f"bin={info.bin}")
        if info.evidence:
            print("evidence=" + ",".join(info.evidence))
    return 0 if info.inside else 1


def cmd_split(args: argparse.Namespace) -> int:
    try:
        data = split_pane(
            args.direction,
            cwd=args.cwd,
            title=args.title,
            cmd=args.cmd,
            agent=args.agent,
            size=args.size,
        )
    except MuxError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(data)
    else:
        extra = f" pane={data['pane']}" if data.get("pane") else ""
        agent = f" agent={data['agent']}" if data.get("agent") else ""
        print(f"split {data['mux']} {data['direction']} cwd={data['cwd']}{agent}{extra}")
    return 0


def cmd_pane(args: argparse.Namespace) -> int:
    if args.pane_command == "split":
        return cmd_split(args)
    try:
        if args.pane_command == "count":
            data = count_panes()
        elif args.pane_command == "read":
            data = read_pane_content(args.id)
        elif args.pane_command == "list":
            data = list_panes()
        elif args.pane_command == "focus":
            data = focus_pane(args.target)
        elif args.pane_command == "swap":
            data = swap_pane(args.direction)
        elif args.pane_command == "resize":
            data = resize_pane(args.direction, amount=args.amount)
        elif args.pane_command == "text":
            text = args.text
            if text is None:
                if sys.stdin.isatty():
                    print("error: 给出文本，或把内容通过 stdin 传入", file=sys.stderr)
                    return 1
                text = sys.stdin.read()
            text = text.rstrip("\n")
            if text == "":
                print("error: 空文本", file=sys.stderr)
                return 1
            data = send_text_to_pane(args.target, text)
        elif args.pane_command == "keys":
            data = send_keys_to_pane(args.target, args.keys)
        else:
            data = close_pane(args.target)
    except MuxError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    as_json = getattr(args, "json", False)
    if args.pane_command == "count" and not as_json:
        print(data.get("count", 0))
        return 0
    if args.pane_command == "read" and not as_json:
        print(data.get("text") or "")
        return 0
    if as_json or args.pane_command in {"list", "count", "read", "close"}:
        _print_json(data)
        return 0
    print(" ".join(f"{k}={v}" for k, v in data.items()))
    return 0


def cmd_pipe(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    if args.pipe_command == "send":
        text = args.text
        if text is None:
            if sys.stdin.isatty():
                print("error: 给出文本，或把内容通过 stdin 传入", file=sys.stderr)
                return 1
            text = sys.stdin.read()
        if text == "":
            print("error: 空消息", file=sys.stderr)
            return 1
        path = pipe_send(root, text)
        print(path.relative_to(root).as_posix())
        return 0
    try:
        pipe_listen(root, timeout=args.timeout, once=args.once)
    except KeyboardInterrupt:
        return 0
    return 0


def main(argv: list[str] | None = None) -> int:
    _force_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "init":
        return cmd_init(args)
    if args.command == "detect":
        return cmd_detect(args)
    if args.command == "split":
        return cmd_split(args)
    if args.command == "pane":
        return cmd_pane(args)
    if args.command == "pipe":
        return cmd_pipe(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())

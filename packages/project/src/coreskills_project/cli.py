"""CLI: project check / project hooks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .docs import check_docs
from .hooks import hook_status, install_hooks, run_pre_push
from .init import init_project
from .problems import ERR, Problem
from .structure import check_structure
from .sync import check_code_doc_sync


def _force_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="project",
        description=(
            "结构与文档健康度检查。"
            "推送时扫描关键文档是否随代码一起更新（git pre-push）。"
        ),
    )
    parser.add_argument("--version", action="version", version=f"project {__version__}")
    sub = parser.add_subparsers(dest="command")

    init = sub.add_parser(
        "init",
        help="把 project skill 装到项目级 .agents/skills 与 .claude/skills",
    )
    init.add_argument("dir", nargs="?", default=".", type=Path)
    init.add_argument("--force", action="store_true", help="覆盖已存在的 SKILL.md")

    check = sub.add_parser("check", help="检查项目结构与文档健康度")
    check.add_argument("dir", nargs="?", default=".", type=Path)
    check.add_argument("--structure", action="store_true")
    check.add_argument("--docs", action="store_true")
    check.add_argument(
        "--sync",
        action="store_true",
        help="扫描相对上游的代码变更是否同步了关键文档（与 pre-push 相同）",
    )
    check.add_argument("--json", action="store_true")
    check.add_argument("--strict", action="store_true", help="warning 也非零退出")

    hooks = sub.add_parser("hooks", help="部署 git pre-push 文档同步扫描")
    hooks_sub = hooks.add_subparsers(dest="hooks_command", required=True)

    install = hooks_sub.add_parser("install", help="写入 .githooks/pre-push")
    install.add_argument("dir", nargs="?", default=".", type=Path)

    status = hooks_sub.add_parser("status")
    status.add_argument("dir", nargs="?", default=".", type=Path)

    run = hooks_sub.add_parser("run", help="由 git pre-push 调用")
    run.add_argument("event", choices=["pre-push"])
    run.add_argument("--file", action="append", default=[], help="覆盖变更文件列表（测试用）")
    run.add_argument("--dir", type=Path, default=".")
    return parser


def _run_checks(
    root: Path, *, do_structure: bool, do_docs: bool, do_sync: bool
) -> list[Problem]:
    problems: list[Problem] = []
    if do_structure:
        problems.extend(check_structure(root))
    if do_docs:
        problems.extend(check_docs(root))
    if do_sync:
        from .hooks import files_vs_upstream

        problems.extend(check_code_doc_sync(files_vs_upstream(root)))
    return problems


def _print_problems(root: Path, problems: list[Problem], as_json: bool) -> None:
    if as_json:
        print(
            json.dumps(
                {
                    "root": str(root),
                    "problems": [
                        {"level": p.level, "check": p.check, "msg": p.msg}
                        for p in problems
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    if not problems:
        print(f"OK: {root} 结构与文档状态通过")
        return
    for p in problems:
        tag = "[error]" if p.level == ERR else "[warn ]"
        print(f"  {tag} [{p.check}] {p.msg}")
    n_err = sum(1 for p in problems if p.level == ERR)
    print(f"Summary: {n_err} error, {len(problems) - n_err} warning")


def cmd_init(args: argparse.Namespace) -> int:
    root = args.dir.resolve()
    try:
        actions = init_project(root, force=args.force)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for line in actions:
        print(line)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    root = args.dir.resolve()
    both = not args.structure and not args.docs and not args.sync
    problems = _run_checks(
        root,
        do_structure=both or args.structure,
        do_docs=both or args.docs,
        do_sync=args.sync,
    )
    _print_problems(root, problems, args.json)
    n_err = sum(1 for p in problems if p.level == ERR)
    if n_err:
        return 1
    if args.strict and problems:
        return 1
    return 0


def cmd_hooks_install(args: argparse.Namespace) -> int:
    root = args.dir.resolve()
    try:
        actions = install_hooks(root)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for line in actions:
        print(line)
    return 0


def cmd_hooks_status(args: argparse.Namespace) -> int:
    info = hook_status(args.dir.resolve())
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0 if info.get("installed") else 1


def cmd_hooks_run(args: argparse.Namespace) -> int:
    root = args.dir.resolve()
    stdin = ""
    if not args.file and not sys.stdin.isatty():
        stdin = sys.stdin.read()
    problems = run_pre_push(root, files=list(args.file) or None, stdin=stdin)
    if not problems:
        return 0
    for p in problems:
        print(f"[提醒] {p.msg}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    _force_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "init":
        return cmd_init(args)
    if args.command == "check":
        return cmd_check(args)
    if args.command == "hooks":
        if args.hooks_command == "install":
            return cmd_hooks_install(args)
        if args.hooks_command == "status":
            return cmd_hooks_status(args)
        if args.hooks_command == "run":
            return cmd_hooks_run(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())

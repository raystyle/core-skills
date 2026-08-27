"""Code vs key-doc sync: used on git push."""

from __future__ import annotations

from .mapping import KEY_DOC_ROOT, is_key_doc, is_source
from .problems import Problem, warning

KEY_DOC_HINT = "、".join(KEY_DOC_ROOT) + "，或 docs/sdlc/changes/<名>/{intent,spec,plan}.md"


def check_code_doc_sync(changed: list[str]) -> list[Problem]:
    files = [c.replace("\\", "/").lstrip("./") for c in changed if c.strip()]
    sources = [c for c in files if is_source(c)]
    docs = [c for c in files if is_key_doc(c)]
    if not sources or docs:
        return []
    shown = ", ".join(sources[:6])
    if len(sources) > 6:
        shown += ", …"
    return [
        warning(
            "sync",
            f"代码已改（{shown}）但关键文档未同步更新。请更新：{KEY_DOC_HINT}",
        )
    ]

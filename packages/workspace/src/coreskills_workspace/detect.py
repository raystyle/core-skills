"""Detect whether this process is inside Windows Terminal (wt) or Herdr."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass, field


def platform_name(plat: str | None = None) -> str:
    p = plat if plat is not None else sys.platform
    if p == "win32":
        return "windows"
    if p.startswith("linux"):
        return "linux"
    if p == "darwin":
        return "darwin"
    return p


def expected_mux(os_name: str) -> str:
    return "wt" if os_name == "windows" else "herdr"


@dataclass
class DetectResult:
    os: str
    expected: str
    mux: str | None
    inside: bool
    session: str | None = None
    pane: str | None = None
    bin: str | None = None
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "os": self.os,
            "expected": self.expected,
            "mux": self.mux,
            "inside": self.inside,
            "session": self.session,
            "pane": self.pane,
            "bin": self.bin,
            "evidence": list(self.evidence),
        }


def _which_wt() -> str | None:
    return shutil.which("wt") or shutil.which("wt.exe")


def _which_herdr() -> str | None:
    return shutil.which("herdr")


def detect(*, environ: dict[str, str] | None = None, plat: str | None = None) -> DetectResult:
    env = os.environ if environ is None else environ
    os_name = platform_name(plat)
    expected = expected_mux(os_name)
    evidence: list[str] = []

    wt_session = (env.get("WT_SESSION") or "").strip() or None
    wt_profile = (env.get("WT_PROFILE_ID") or "").strip() or None
    herdr_env = (env.get("HERDR_ENV") or "").strip()
    herdr_pane = (env.get("HERDR_PANE_ID") or "").strip() or None
    herdr_sock = (env.get("HERDR_SOCKET_PATH") or "").strip() or None

    inside_wt = bool(wt_session or wt_profile)
    inside_herdr = herdr_env in {"1", "true", "TRUE"} or bool(herdr_pane or herdr_sock)

    if wt_session:
        evidence.append("WT_SESSION")
    if wt_profile:
        evidence.append("WT_PROFILE_ID")
    if herdr_env in {"1", "true", "TRUE"}:
        evidence.append("HERDR_ENV")
    if herdr_pane:
        evidence.append("HERDR_PANE_ID")
    if herdr_sock:
        evidence.append("HERDR_SOCKET_PATH")

    mux: str | None = None
    if expected == "wt" and inside_wt:
        mux = "wt"
    elif expected == "herdr" and inside_herdr:
        mux = "herdr"
    elif inside_herdr:
        mux = "herdr"
    elif inside_wt:
        mux = "wt"

    bin_path: str | None = None
    if mux == "wt":
        bin_path = _which_wt()
    elif mux == "herdr":
        bin_path = _which_herdr()
    else:
        bin_path = _which_wt() if expected == "wt" else _which_herdr()

    return DetectResult(
        os=os_name,
        expected=expected,
        mux=mux,
        inside=mux is not None,
        session=wt_session if mux == "wt" else herdr_sock,
        pane=herdr_pane if mux == "herdr" else None,
        bin=bin_path,
        evidence=evidence,
    )

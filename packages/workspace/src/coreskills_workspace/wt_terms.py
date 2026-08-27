"""Current Cascadia window: count / read / close TermControls."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

EXITED_RE = (
    r"进程已退出|Process exited|0x00000001|Ctrl\+D to close|按 Ctrl\+D 关闭"
)

_PS_INSPECT = r"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$src = @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class WtTerms {
  public delegate bool Cb(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(Cb lp, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern uint GetCurrentThreadId();
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool attach);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  public static void ForceForeground(IntPtr h) {
    if (GetForegroundWindow() == h) return;
    uint pid;
    uint fore = GetWindowThreadProcessId(GetForegroundWindow(), out pid);
    uint self = GetCurrentThreadId();
    if (fore != self) AttachThreadInput(fore, self, true);
    if (IsIconic(h)) ShowWindow(h, 9);
    BringWindowToTop(h);
    SetForegroundWindow(h);
    if (fore != self) AttachThreadInput(fore, self, false);
  }
  [DllImport("user32.dll", SetLastError=true)]
  public static extern uint SendInput(uint n, INPUT[] p, int cb);
  [StructLayout(LayoutKind.Explicit, Size=40)]
  public struct INPUT {
    [FieldOffset(0)] public int type;
    [FieldOffset(8)] public ushort wVk;
    [FieldOffset(10)] public ushort wScan;
    [FieldOffset(12)] public uint dwFlags;
    [FieldOffset(16)] public uint time;
    [FieldOffset(24)] public UIntPtr dwExtraInfo;
  }
  public static void Vk(ushort vk, bool up) {
    INPUT i = new INPUT();
    i.type = 1;
    i.wVk = vk;
    i.dwFlags = up ? 0x0002u : 0;
    SendInput(1, new INPUT[]{ i }, 40);
  }
  public static void Chord(byte[] keys) {
    foreach (var k in keys) Vk(k, false);
    for (int i = keys.Length - 1; i >= 0; i--) Vk(keys[i], true);
  }
  public static void TypeChar(char ch) {
    INPUT d = new INPUT();
    d.type = 1;
    d.wScan = ch;
    d.dwFlags = 0x0004;
    INPUT u = d;
    u.dwFlags = 0x0004 | 0x0002;
    SendInput(2, new INPUT[]{ d, u }, 40);
  }
}
'@
Add-Type -TypeDefinition $src

$wtPid = [uint32]$env:WT_PROBE_PID
$cwdName = $env:WT_PANE_CWD
$wantFull = $env:WT_PANE_FULL -eq '1'
$op = $env:WT_PANE_OP
$targetId = 0
[void][int]::TryParse($env:WT_PANE_ID, [ref]$targetId)
$resizeDir = $env:WT_PANE_RESIZE
$resizeSteps = 5
[void][int]::TryParse($env:WT_PANE_STEPS, [ref]$resizeSteps)
if ($resizeSteps -lt 1) { $resizeSteps = 1 }
$restoreId = -1
[void][int]::TryParse($env:WT_PANE_RESTORE, [ref]$restoreId)
$textFile = $env:WT_PANE_TEXT_FILE
$chordSpec = $env:WT_PANE_CHORDS
$selfId = -1
[void][int]::TryParse($env:WT_PANE_SELF_ID, [ref]$selfId)

$wins = [System.Collections.Generic.List[object]]::new()
$cb = [WtTerms+Cb]{
  param($h, $l)
  $p = 0
  [void][WtTerms]::GetWindowThreadProcessId($h, [ref]$p)
  if ($p -ne $wtPid -or -not [WtTerms]::IsWindowVisible($h)) { return $true }
  $c = New-Object System.Text.StringBuilder 256
  [void][WtTerms]::GetClassName($h, $c, 256)
  if ($c.ToString() -ne 'CASCADIA_HOSTING_WINDOW_CLASS') { return $true }
  $t = New-Object System.Text.StringBuilder 512
  [void][WtTerms]::GetWindowText($h, $t, 512)
  $wins.Add([pscustomobject]@{ hwnd = $h; title = $t.ToString() })
  return $true
}
[void][WtTerms]::EnumWindows($cb, [IntPtr]::Zero)

$wantHwnd = [int64]0
[void][int64]::TryParse($env:WT_PANE_HWND, [ref]$wantHwnd)
$chosen = $null
if ($wantHwnd -ne 0) {
  $hits = @($wins | Where-Object { [int64]$_.hwnd -eq $wantHwnd })
  if ($hits.Count -eq 1) { $chosen = $hits[0] }
}
if (-not $chosen -and $cwdName) {
  $hits = @($wins | Where-Object { $_.title -like "*$cwdName*" })
  if ($hits.Count -eq 1) { $chosen = $hits[0] }
}
if (-not $chosen) {
  $multi = @($wins | Where-Object {
    $el = [System.Windows.Automation.AutomationElement]::FromHandle($_.hwnd)
    $n = 0
    foreach ($x in $el.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)) {
      if ($x.Current.ClassName -eq 'TermControl') { $n++ }
    }
    $n -gt 1
  })
  if ($multi.Count -eq 1) { $chosen = $multi[0] }
}
if (-not $chosen) { $chosen = $wins | Select-Object -First 1 }
if (-not $chosen) { '{ "error": "no Cascadia window" }'; exit 1 }

function Get-Panes([IntPtr]$hwnd) {
  $el = [System.Windows.Automation.AutomationElement]::FromHandle($hwnd)
  $all = $el.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
  $i = 0
  $out = @()
  foreach ($x in $all) {
    if ($x.Current.ClassName -ne 'TermControl') { continue }
    $doc = ''
    try {
      $doc = $x.GetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern).DocumentRange.GetText(12000)
    } catch {}
    $flat = ($doc -replace '\s+', ' ').Trim()
    $preview = if ($flat.Length -gt 240) { $flat.Substring(0, 240) } else { $flat }
    $item = [ordered]@{
      id = $i
      focus = [bool]$x.Current.HasKeyboardFocus
      exited = [bool]($flat -match '进程已退出|Process exited|0x00000001|Ctrl\+D to close|按 Ctrl\+D 关闭')
      preview = $preview
    }
    if ($wantFull) { $item.text = $doc }
    $out += $item
    $i++
  }
  return $out
}

$panes = @(Get-Panes $chosen.hwnd)
$result = [ordered]@{
  hwnd = [int64]$chosen.hwnd
  title = $chosen.title
  count = $panes.Count
  panes = $panes
}

if ($op -eq 'close') {
  if ($targetId -lt 0 -or $targetId -ge $panes.Count) {
    $result.error = "no pane $targetId"
    $result | ConvertTo-Json -Compress -Depth 8
    exit 1
  }
  if ($panes.Count -le 1) {
    $result.error = "last pane"
    $result | ConvertTo-Json -Compress -Depth 8
    exit 1
  }
  if ($selfId -ge 0 -and $targetId -eq $selfId) {
    $result.error = "refused self"
    $result | ConvertTo-Json -Compress -Depth 8
    exit 1
  }
  $hostEl = [System.Windows.Automation.AutomationElement]::FromHandle($chosen.hwnd)
  $allEl = $hostEl.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
  $terms = @()
  foreach ($x in $allEl) {
    if ($x.Current.ClassName -eq 'TermControl') { $terms += $x }
  }
  if ($targetId -ge $terms.Count) {
    $result.error = "no pane $targetId"
    $result | ConvertTo-Json -Compress -Depth 8
    exit 1
  }
  [WtTerms]::ForceForeground($chosen.hwnd)
  Start-Sleep -Milliseconds 200
  [void]$terms[$targetId].SetFocus()
  Start-Sleep -Milliseconds 400
  if (-not $terms[$targetId].Current.HasKeyboardFocus) {
    $result.error = "focus missed; refused close"
    $result | ConvertTo-Json -Compress -Depth 8
    exit 1
  }
  $panes2 = @(Get-Panes $chosen.hwnd)
  $hint = $env:WT_PANE_SELF
  $targetPreview = ''
  if ($targetId -lt $panes2.Count) {
    $targetPreview = [string]$panes2[$targetId].text
    if (-not $targetPreview) { $targetPreview = [string]$panes2[$targetId].preview }
  }
  if ($hint -and $targetPreview -like "*$hint*") {
    $result.error = "refused self"
    $result.panes = $panes2
    $result.count = $panes2.Count
    $result | ConvertTo-Json -Compress -Depth 8
    exit 1
  }
  $exited = $false
  if ($targetId -lt $panes2.Count) { $exited = [bool]$panes2[$targetId].exited }
  if ($exited) {
    [WtTerms]::Chord([byte[]](0x11, 0x44))
    $result.keys = 'ctrl+d'
  } else {
    [WtTerms]::Chord([byte[]](0x11, 0x10, 0x57))
    $result.keys = 'ctrl+shift+w'
  }
  Start-Sleep -Milliseconds 800
  $panes3 = @(Get-Panes $chosen.hwnd)
  $result.panes = $panes3
  $result.count = $panes3.Count
  $result.closed = $targetId
  if ($panes3.Count -ge $panes.Count) {
    $result.error = "close did not remove pane"
    $result | ConvertTo-Json -Compress -Depth 8
    exit 1
  }
}

if ($op -eq 'resize') {
  $vk = @{ left = 0x25; up = 0x26; right = 0x27; down = 0x28 }[$resizeDir]
  if ($null -eq $vk) {
    $result.error = "bad resize direction"
    $result | ConvertTo-Json -Compress -Depth 8
    exit 1
  }
  $hostEl = [System.Windows.Automation.AutomationElement]::FromHandle($chosen.hwnd)
  $allEl = $hostEl.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
  $terms = @()
  foreach ($x in $allEl) {
    if ($x.Current.ClassName -eq 'TermControl') { $terms += $x }
  }
  [WtTerms]::ForceForeground($chosen.hwnd)
  Start-Sleep -Milliseconds 200
  if ($targetId -ge 0 -and $targetId -lt $terms.Count) {
    [void]$terms[$targetId].SetFocus()
    Start-Sleep -Milliseconds 350
    if (-not $terms[$targetId].Current.HasKeyboardFocus) {
      $result.error = "focus missed; refused resize"
      $result | ConvertTo-Json -Compress -Depth 8
      exit 1
    }
  }
  for ($n = 0; $n -lt $resizeSteps; $n++) {
    [WtTerms]::Chord([byte[]](0x12, 0x10, $vk))
    Start-Sleep -Milliseconds 40
  }
  $result.keys = "alt+shift+$resizeDir"
  $result.steps = $resizeSteps
}

if ($op -eq 'send') {
  if ($targetId -lt 0 -or $targetId -ge $panes.Count) {
    $result.error = "no pane $targetId"
    $result | ConvertTo-Json -Compress -Depth 8
    exit 1
  }
  $hostEl = [System.Windows.Automation.AutomationElement]::FromHandle($chosen.hwnd)
  $allEl = $hostEl.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
  $terms = @()
  foreach ($x in $allEl) {
    if ($x.Current.ClassName -eq 'TermControl') { $terms += $x }
  }
  [WtTerms]::ForceForeground($chosen.hwnd)
  Start-Sleep -Milliseconds 200
  [void]$terms[$targetId].SetFocus()
  Start-Sleep -Milliseconds 350
  if (-not $terms[$targetId].Current.HasKeyboardFocus) {
    $result.error = "focus missed; refused send"
    $result | ConvertTo-Json -Compress -Depth 8
    exit 1
  }
  $sentText = 0
  if ($textFile -and (Test-Path -LiteralPath $textFile)) {
    $s = [System.IO.File]::ReadAllText($textFile, [System.Text.Encoding]::UTF8)
    foreach ($ch in $s.ToCharArray()) {
      if ($ch -eq "`r") { continue }
      if ($ch -eq "`n") { [WtTerms]::Chord([byte[]](0x0D)) }
      else { [WtTerms]::TypeChar($ch) }
      Start-Sleep -Milliseconds 8
      $sentText++
    }
  }
  $sentKeys = @()
  if ($chordSpec) {
    foreach ($group in ($chordSpec -split ';')) {
      if (-not $group) { continue }
      $bytes = @($group.Split(',') | ForEach-Object { [byte]$_ })
      [WtTerms]::Chord($bytes)
      $sentKeys += $group
      Start-Sleep -Milliseconds 50
    }
  }
  if ($restoreId -ge 0 -and $restoreId -ne $targetId -and $restoreId -lt $terms.Count) {
    Start-Sleep -Milliseconds 200
    [void]$terms[$restoreId].SetFocus()
  }
  $result.sent_chars = $sentText
  $result.sent_chords = $sentKeys
  $result.id = $targetId
}

$result | ConvertTo-Json -Compress -Depth 8
"""


def _run_inspect(
    *,
    op: str,
    pane_id: int | None = None,
    full: bool = False,
    resize_dir: str | None = None,
    steps: int | None = None,
    text_file: str | None = None,
    chords: str | None = None,
    restore: int | None = None,
    self_id: int | None = None,
    timeout: float = 45,
) -> dict:
    env = os.environ.copy()
    env["WT_PANE_OP"] = op
    env["WT_PANE_CWD"] = Path.cwd().name
    env["WT_PANE_SELF"] = "workspace pane"
    if pane_id is not None:
        env["WT_PANE_ID"] = str(pane_id)
    if full:
        env["WT_PANE_FULL"] = "1"
    if resize_dir:
        env["WT_PANE_RESIZE"] = resize_dir
    if steps is not None:
        env["WT_PANE_STEPS"] = str(steps)
    if text_file:
        env["WT_PANE_TEXT_FILE"] = text_file
    if chords:
        env["WT_PANE_CHORDS"] = chords
    if restore is not None:
        env["WT_PANE_RESTORE"] = str(restore)
    if self_id is not None:
        env["WT_PANE_SELF_ID"] = str(self_id)
    from .wt_window import list_host_windows, pick_current_window, snapshot_processes, terminal_pid

    rows = snapshot_processes()
    tid = terminal_pid(rows, os.getpid())
    if tid:
        env["WT_PROBE_PID"] = str(tid)
        chosen = pick_current_window(list_host_windows(tid), cwd=str(Path.cwd()))
        if chosen and chosen.get("hwnd"):
            env["WT_PANE_HWND"] = str(int(chosen["hwnd"]))
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", _PS_INSPECT],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
    )
    raw = (proc.stdout or "").strip()
    if not raw:
        raise RuntimeError((proc.stderr or "uia inspect empty").strip())
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"uia inspect json: {raw[:400]}") from exc
    if not isinstance(data, dict):
        raise RuntimeError("uia inspect: expected object")
    panes = data.get("panes")
    if isinstance(panes, dict):
        data["panes"] = [panes]
    return data


def inspect_panes(*, full: bool = False) -> dict:
    return _run_inspect(op="list", full=full)


def read_pane(pane_id: int) -> dict:
    data = _run_inspect(op="list", full=True)
    panes = data.get("panes") or []
    if pane_id < 0 or pane_id >= len(panes):
        raise RuntimeError(f"本窗口没有窗格 {pane_id}（共 {len(panes)} 格）")
    one = panes[pane_id]
    return {
        "hwnd": data.get("hwnd"),
        "title": data.get("title"),
        "count": data.get("count"),
        "id": pane_id,
        "focus": one.get("focus"),
        "exited": one.get("exited"),
        "text": one.get("text") or one.get("preview") or "",
    }


def close_term(pane_id: int, *, self_id: int | None = None) -> dict:
    data = _run_inspect(op="close", pane_id=pane_id, self_id=self_id, full=True)
    if data.get("error"):
        raise RuntimeError(str(data["error"]))
    return data


def resize_term(direction: str, steps: int = 5, pane_id: int | None = None) -> dict:
    data = _run_inspect(
        op="resize", resize_dir=direction, steps=steps, pane_id=pane_id
    )
    if data.get("error"):
        raise RuntimeError(str(data["error"]))
    return data


def send_term(
    pane_id: int,
    *,
    text: str | None = None,
    chords: list[list[int]] | None = None,
    restore: int | None = None,
) -> dict:
    import tempfile

    path = None
    try:
        if text:
            handle = tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", suffix=".txt", delete=False
            )
            with handle as fh:
                fh.write(text)
            path = handle.name
        encoded = ";".join(
            ",".join(str(int(v)) for v in chord) for chord in (chords or []) if chord
        )
        data = _run_inspect(
            op="send",
            pane_id=pane_id,
            text_file=path,
            chords=encoded or None,
            restore=restore,
            timeout=60,
        )
    finally:
        if path:
            try:
                Path(path).unlink()
            except OSError:
                pass
    if data.get("error"):
        raise RuntimeError(str(data["error"]))
    return data

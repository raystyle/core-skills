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
  [DllImport("user32.dll")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr extra);
  public static void Chord(byte[] keys) {
    foreach (var k in keys) { keybd_event(k, 0, 0, UIntPtr.Zero); }
    for (int i = keys.Length - 1; i >= 0; i--) { keybd_event(keys[i], 0, 2, UIntPtr.Zero); }
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

$chosen = $null
if ($cwdName) {
  $hits = @($wins | Where-Object { $_.title -like "*$cwdName*" })
  if ($hits.Count -eq 1) { $chosen = $hits[0] }
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
  [void][WtTerms]::SetForegroundWindow($chosen.hwnd)
  Start-Sleep -Milliseconds 200
  wt -w 0 focus-pane -t $targetId | Out-Null
  Start-Sleep -Milliseconds 400
  $panes2 = @(Get-Panes $chosen.hwnd)
  $focused = $panes2 | Where-Object { $_.focus } | Select-Object -First 1
  $hint = $env:WT_PANE_SELF
  $isSelf = $false
  if ($hint -and $focused -and ($focused.preview -like "*$hint*")) { $isSelf = $true }
  if ($isSelf) {
    $result.error = "refused self"
    $result.panes = $panes2
    $result.count = $panes2.Count
    $result | ConvertTo-Json -Compress -Depth 8
    exit 1
  }
  if ($focused -and $focused.exited) {
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
}

$result | ConvertTo-Json -Compress -Depth 8
"""


def _run_inspect(*, op: str, pane_id: int | None = None, full: bool = False) -> dict:
    env = os.environ.copy()
    env["WT_PANE_OP"] = op
    env["WT_PANE_CWD"] = Path.cwd().name
    env["WT_PANE_SELF"] = "workspace pane"
    if pane_id is not None:
        env["WT_PANE_ID"] = str(pane_id)
    if full:
        env["WT_PANE_FULL"] = "1"
    from .wt_window import snapshot_processes, terminal_pid

    rows = snapshot_processes()
    tid = terminal_pid(rows, os.getpid())
    if tid:
        env["WT_PROBE_PID"] = str(tid)
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", _PS_INSPECT],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=45,
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


def close_term(pane_id: int) -> dict:
    data = _run_inspect(op="close", pane_id=pane_id, full=False)
    if data.get("error"):
        raise RuntimeError(str(data["error"]))
    return data

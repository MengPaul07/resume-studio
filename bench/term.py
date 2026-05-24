"""Terminal interaction helpers — ANSI colors, prompts, progress (zero dependencies)."""
from __future__ import annotations

import sys
import os
import re
import shutil
from typing import Any, Callable, List, Optional, Sequence

# Enable ANSI on Windows Terminal
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

# ── ANSI codes ──────────────────────────────────────────────────────────────

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"

def _rgb(r: int, g: int, b: int, bg: bool = False) -> str:
    return f"\033[{48 if bg else 38};2;{r};{g};{b}m"

GREEN = _rgb(70, 200, 70)
RED = _rgb(255, 90, 90)
YELLOW = _rgb(240, 200, 50)
CYAN = _rgb(80, 200, 200)
BLUE = _rgb(100, 160, 255)
GRAY = _rgb(140, 140, 140)
WHITE = _rgb(240, 240, 240)

PASS = f"{GREEN}✓{_RESET}"
FAIL = f"{RED}✗{_RESET}"
WARN = f"{YELLOW}⚠{_RESET}"
INFO = f"{CYAN}→{_RESET}"
ARROW = f"{BLUE}>{_RESET}"


def bold(s: str) -> str: return f"{_BOLD}{s}{_RESET}"
def dim(s: str) -> str: return f"{_DIM}{s}{_RESET}"
def green(s: str) -> str: return f"{GREEN}{s}{_RESET}"
def red(s: str) -> str: return f"{RED}{s}{_RESET}"
def yellow(s: str) -> str: return f"{YELLOW}{s}{_RESET}"
def cyan(s: str) -> str: return f"{CYAN}{s}{_RESET}"
def blue(s: str) -> str: return f"{BLUE}{s}{_RESET}"
def gray(s: str) -> str: return f"{GRAY}{s}{_RESET}"
def white(s: str) -> str: return f"{WHITE}{s}{_RESET}"

def tag(label: str, color_fn: Callable = blue) -> str:
    return f"{color_fn(f'[{label}]')}"

def header(title: str) -> str:
    w = shutil.get_terminal_size().columns
    return f"\n{_BOLD}{'─'*3} {title} {'─'*(max(0, w - len(title) - 6))}{_RESET}"

def divider(char: str = "─") -> str:
    w = shutil.get_terminal_size().columns
    return dim(char * w)

# ── Prompts ──────────────────────────────────────────────────────────────────

def confirm(question: str, default: bool = True) -> bool:
    """Y/n confirm prompt."""
    yn = "Y/n" if default else "y/N"
    while True:
        try:
            ans = input(f"\n{cyan('?')} {question} {dim(f'[{yn}]')} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if not ans:
            return default
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print(f"  {dim('Please answer y or n')}")


def select(question: str, choices: List[str], default: int = 0) -> int:
    """Single-select from a numbered list. Returns index."""
    print(f"\n{cyan('?')} {bold(question)}")
    for i, c in enumerate(choices):
        print(f"  {dim(f'[{i+1}]')} {c}")
    while True:
        try:
            ans = input(f"  {blue('>')} {dim(f'[1-{len(choices)}]')} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if not ans and default >= 0:
            return default
        try:
            idx = int(ans) - 1
            if 0 <= idx < len(choices):
                return idx
        except ValueError:
            pass
        print(f"  {red(f'Enter 1-{len(choices)}')}")


def multi_select(question: str, choices: List[str], default_indices: List[int] | None = None) -> List[int]:
    """Multi-select from a numbered list. Space-separated input. Returns indices."""
    if default_indices is None:
        default_indices = list(range(len(choices)))
    print(f"\n{cyan('?')} {bold(question)}")
    for i, c in enumerate(choices):
        mark = green("◆") if i in default_indices else dim("◇")
        print(f"  {mark} {dim(f'[{i+1}]')} {c}")
    print(f"  {dim('Enter numbers (e.g. 1 3 5) or press Enter for all')}")
    while True:
        try:
            ans = input(f"  {blue('>')} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if not ans:
            return default_indices
        try:
            indices = [int(x.strip()) - 1 for x in re.split(r'[\s,]+', ans) if x.strip()]
            indices = [i for i in indices if 0 <= i < len(choices)]
            if indices:
                return indices
        except ValueError:
            pass
        print(f"  {red(f'Enter numbers 1-{len(choices)} (space or comma separated)')}")


def input_text(question: str, default: str = "", validate: Callable[[str], str | None] | None = None) -> str:
    """Free-text input with optional validation."""
    hint = dim(f"[{default}]") if default else ""
    while True:
        try:
            ans = input(f"\n{cyan('?')} {question} {hint} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if not ans:
            ans = default
        if validate:
            err = validate(ans)
            if err:
                print(f"  {red(err)}")
                continue
        return ans


# ── Progress ─────────────────────────────────────────────────────────────────

class LiveCounter:
    """Compact live counter for concurrent eval runs."""

    def __init__(self, total: int, label: str = ""):
        self.total = total
        self.label = label
        self.passed = 0
        self.failed = 0
        self.errors = 0
        self.done = 0
        self._started = False

    def _render(self):
        pct = self.done / max(1, self.total) * 100
        bar_w = 20
        filled = int(bar_w * self.done / max(1, self.total))
        bar = green("█" * filled) + dim("░" * (bar_w - filled))
        status = (
            f"  {bar}  {self.done}/{self.total} ({pct:.0f}%)"
            f"  {PASS} {green(str(self.passed))}"
            f"  {FAIL} {red(str(self.failed))}"
        )
        if self.errors:
            status += f"  {WARN} {yellow(str(self.errors))}"
        if self.label:
            status = f" {cyan(f'[{self.label}]')}{status}"
        # Clear line and print
        sys.stderr.write(f"\r\033[K{status}")
        sys.stderr.flush()

    def start(self):
        self._started = True
        self._render()

    def update(self, passed: bool = False, error: bool = False):
        self.done += 1
        if error:
            self.errors += 1
        elif passed:
            self.passed += 1
        else:
            self.failed += 1
        self._render()

    def done_line(self):
        sys.stderr.write("\n")
        sys.stderr.flush()


# ── Panels / boxes ───────────────────────────────────────────────────────────

def box(lines: List[str], title: str = "") -> str:
    """Simple bordered box."""
    w = max(len(strip_ansi(l)) for l in lines) + 4
    top = f"┌{'─'*w}┐"
    bot = f"└{'─'*w}┘"
    if title:
        top = f"┌─ {bold(title)} {'─'*(max(0, w - len(title) - 5))}┐"
    out = [dim(top)]
    for l in lines:
        pad = w - len(strip_ansi(l))
        out.append(f"{dim('│')} {l}{' '*pad} {dim('│')}")
    out.append(dim(bot))
    return "\n".join(out)


def strip_ansi(s: str) -> str:
    return re.sub(r"\033\[[0-9;]*m", "", s)


# ── Table ────────────────────────────────────────────────────────────────────

def table(headers: List[str], rows: List[List[str]], col_widths: List[int] | None = None) -> str:
    """Align table with ANSI-aware column widths."""
    if not rows:
        return ""
    if col_widths is None:
        col_widths = [0] * len(headers)
        for i, h in enumerate(headers):
            col_widths[i] = max(col_widths[i], len(strip_ansi(h)))
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(strip_ansi(str(cell))))
    out = []
    # Header
    hdr = "  ".join(f"{bold(h):<{col_widths[i]}}" for i, h in enumerate(headers))
    out.append(hdr)
    out.append(dim("─" * len(strip_ansi(hdr))))
    # Rows
    for row in rows:
        r = "  ".join(f"{str(row[i]):<{col_widths[i]}}" if i < len(row) else ""
                      for i in range(len(col_widths)))
        out.append(r)
    return "\n".join(out)

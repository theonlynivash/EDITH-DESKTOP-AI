"""
Edith — AI Desktop Assistant
Futuristic Sci-fi UI with chat bubbles
Requires: Python 3.10+ (tkinter bundled, no pip needed)
"""

from __future__ import annotations
import atexit
import os
import re
import subprocess
import threading
import tkinter as tk
from tkinter import font as tkfont
from typing import Optional
import time

from ai_handler import ask_openai
from commands import handle_offline_command
from utils import has_internet


# ── SAPI voice via PowerShell ─────────────────────────────────────────────────
_SAPI_SCRIPT = r"""
Add-Type -AssemblyName System.Speech
$rec = New-Object System.Speech.Recognition.SpeechRecognitionEngine
$rec.SetInputToDefaultAudioDevice()
$grammar = New-Object System.Speech.Recognition.DictationGrammar
$rec.LoadGrammar($grammar)
$result = $rec.Recognize([TimeSpan]::FromSeconds(6))
if ($result) { Write-Output $result.Text } else { Write-Output "" }
"""

def listen_from_microphone() -> tuple[Optional[str], str]:
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", _SAPI_SCRIPT],
            capture_output=True, text=True, timeout=12,
        )
        transcript = result.stdout.strip()
        return (transcript, "OK") if transcript else (None, "No speech detected")
    except FileNotFoundError:
        return None, "PowerShell not found"
    except subprocess.TimeoutExpired:
        return None, "Listening timed out"
    except Exception as e:
        return None, f"Voice error: {e}"


def process_command(user_input: str) -> str:
    user_input = user_input.strip()
    if not user_input:
        return "Please say something."
    handled, message = handle_offline_command(user_input)
    if handled:
        return message
    ai_response = ask_openai(user_input)
    if ai_response:
        return ai_response
    if not has_internet():
        return "No internet. Try: time, date, lock system, play <song>, open <app>."
    return "I'm not sure about that. Try rephrasing?"


# ── Colour palette ────────────────────────────────────────────────────────────
BG          = "#050d1a"
PANEL       = "#0a1628"
BUBBLE_USER = "#003566"
BUBBLE_BOT  = "#0d1f3c"
ACCENT      = "#00d4ff"
ACCENT2     = "#7b2fff"
TEXT        = "#e0f0ff"
TEXT_DIM    = "#4a7a9b"
BORDER      = "#0d3b5e"
GLOW        = "#00d4ff"


def GlowButton(parent, text, command, color=ACCENT, btn_width=80):
    """Neon-styled tkinter Button — no Canvas needed."""
    btn = tk.Button(
        parent, text=text, command=command,
        bg=PANEL, fg=color,
        font=("Courier", 9, "bold"),
        relief="flat", bd=0,
        padx=10, pady=6,
        cursor="hand2",
        activebackground="#0a1e3d",
        activeforeground=color,
        highlightthickness=1,
        highlightbackground=color,
        highlightcolor=color,
    )
    btn.bind("<Enter>", lambda e: btn.config(bg="#0a1e3d"))
    btn.bind("<Leave>", lambda e: btn.config(bg=PANEL))
    return btn


class BubbleFrame(tk.Frame):
    """A single chat bubble (user or bot)."""
    def __init__(self, parent, text, is_user, **kw):
        super().__init__(parent, bg=BG, **kw)

        bubble_color = BUBBLE_USER if is_user else BUBBLE_BOT
        anchor = "e" if is_user else "w"
        side   = tk.RIGHT if is_user else tk.LEFT
        label_color = ACCENT if is_user else ACCENT2

        # sender label
        sender = "YOU" if is_user else "EDITH"
        tk.Label(self, text=sender, fg=label_color, bg=BG,
                 font=("Courier", 7, "bold")).pack(anchor=anchor, padx=18, pady=(4,0))

        # bubble
        outer = tk.Frame(self, bg=label_color, padx=1, pady=1)
        outer.pack(anchor=anchor, padx=12, pady=(0,6))

        inner = tk.Frame(outer, bg=bubble_color, padx=14, pady=10)
        inner.pack()

        tk.Label(inner, text=text, fg=TEXT, bg=bubble_color,
                 font=("Courier", 10), wraplength=480,
                 justify=tk.LEFT).pack(anchor="w")


class EdithAssistant(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("EDITH — Neural Interface v2.0")
        self.geometry("860x720")
        self.minsize(600, 500)
        self.configure(bg=BG)

        self.is_running  = True
        self.is_listening = False
        self.listen_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._dot_job = None

        atexit.register(self._cleanup)
        self._build_ui()
        self._animate_scanline()

        from ai_handler import _get_api_key, _CONFIG_FILE
        key_ok = bool(_get_api_key())
        status = "NEURAL LINK ACTIVE" if key_ok else f"NO API KEY — add to {_CONFIG_FILE.name}"
        self._add_bubble(
            f"SYSTEM BOOT COMPLETE\n"
            f"Status : {status}\n\n"
            f"Commands: 'lock system' · 'what time is it'\n"
            f"          'play <song>' · 'open <app>' · 'shutdown'\n"
            f"Voice   : click MIC or enable ALWAYS LISTEN",
            is_user=False
        )

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # ── top header bar ────────────────────────────────────────────────────
        header = tk.Frame(self, bg=PANEL, height=52)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        # animated dots (left)
        self._dot_canvas = tk.Canvas(header, width=60, height=52,
                                     bg=PANEL, highlightthickness=0)
        self._dot_canvas.pack(side=tk.LEFT, padx=12)

        tk.Label(header, text="◈  E D I T H", fg=ACCENT,
                 bg=PANEL, font=("Courier", 16, "bold")).pack(side=tk.LEFT)
        tk.Label(header, text="Neural Desktop Interface", fg=TEXT_DIM,
                 bg=PANEL, font=("Courier", 8)).pack(side=tk.LEFT, padx=12)

        # live clock (right)
        self._clock_var = tk.StringVar()
        tk.Label(header, textvariable=self._clock_var, fg=ACCENT2,
                 bg=PANEL, font=("Courier", 10, "bold")).pack(side=tk.RIGHT, padx=16)
        self._tick_clock()

        # thin neon separator
        sep = tk.Canvas(self, height=2, bg=BG, highlightthickness=0)
        sep.pack(fill=tk.X)
        sep.create_line(0, 1, 3000, 1, fill=ACCENT, width=1)

        # ── scrollable chat area ──────────────────────────────────────────────
        chat_frame = tk.Frame(self, bg=BG)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self._canvas = tk.Canvas(chat_frame, bg=BG, highlightthickness=0,
                                  bd=0)
        self._scrollbar = tk.Scrollbar(chat_frame, orient="vertical",
                                        command=self._canvas.yview,
                                        bg=PANEL, troughcolor=BG,
                                        activebackground=ACCENT)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._bubble_frame = tk.Frame(self._canvas, bg=BG)
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._bubble_frame, anchor="nw"
        )

        self._bubble_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>",       self._on_canvas_configure)
        self._canvas.bind("<MouseWheel>",      self._on_mousewheel)

        # ── scanline overlay ──────────────────────────────────────────────────
        self._scan_canvas = tk.Canvas(self, height=2, bg=BG,
                                       highlightthickness=0)
        # (decorative — placed via place() after pack to overlay)

        # ── status / typing indicator ─────────────────────────────────────────
        self._status_var = tk.StringVar(value="READY")
        status_bar = tk.Frame(self, bg=PANEL, height=24)
        status_bar.pack(fill=tk.X)
        status_bar.pack_propagate(False)
        tk.Label(status_bar, textvariable=self._status_var,
                 fg=TEXT_DIM, bg=PANEL,
                 font=("Courier", 8)).pack(side=tk.LEFT, padx=10)

        # ── input bar ─────────────────────────────────────────────────────────
        input_bg = tk.Frame(self, bg=PANEL, height=64)
        input_bg.pack(fill=tk.X)
        input_bg.pack_propagate(False)

        # glowing border around entry
        entry_border = tk.Frame(input_bg, bg=ACCENT, padx=1, pady=1)
        entry_border.pack(side=tk.LEFT, fill=tk.Y, padx=(12,6), pady=10, expand=True)

        self.entry = tk.Entry(
            entry_border, font=("Courier", 12), bg="#020c1b",
            fg=ACCENT, insertbackground=ACCENT,
            relief="flat", bd=4,
        )
        self.entry.pack(fill=tk.BOTH, expand=True)
        self.entry.bind("<Return>", self._on_send)
        self.entry.focus_set()

        # buttons
        btn_frame = tk.Frame(input_bg, bg=PANEL)
        btn_frame.pack(side=tk.RIGHT, padx=10, pady=10)

        GlowButton(btn_frame, "SEND",  self._on_send,  color=ACCENT).pack(side=tk.LEFT, padx=3)
        GlowButton(btn_frame, "🎤 MIC", self._on_voice, color=ACCENT2).pack(side=tk.LEFT, padx=3)

        self._listen_var = tk.BooleanVar(value=False)
        chk = tk.Checkbutton(
            btn_frame, text="ALWAYS\nLISTEN",
            variable=self._listen_var, command=self._toggle_always,
            bg=PANEL, fg=TEXT_DIM, selectcolor=PANEL,
            activebackground=PANEL, font=("Courier", 7),
            relief="flat",
        )
        chk.pack(side=tk.LEFT, padx=6)

    # ── bubble helpers ────────────────────────────────────────────────────────

    def _add_bubble(self, text: str, is_user: bool):
        def _do():
            b = BubbleFrame(self._bubble_frame, text, is_user)
            b.pack(fill=tk.X, pady=2)
            self.update_idletasks()
            self._canvas.yview_moveto(1.0)
        self.after(0, _do)

    def _on_frame_configure(self, _e=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, e):
        self._canvas.itemconfig(self._canvas_window, width=e.width)

    def _on_mousewheel(self, e):
        self._canvas.yview_scroll(int(-1*(e.delta/120)), "units")

    # ── clock & animations ────────────────────────────────────────────────────

    def _tick_clock(self):
        import datetime
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self._clock_var.set(f"[ {now} ]")
        self.after(1000, self._tick_clock)

    def _animate_scanline(self):
        """Pulse the three dots in the header."""
        colors = [ACCENT, ACCENT2, TEXT_DIM]
        dots = self._dot_canvas
        dots.delete("all")
        t = int(time.time() * 3) % 3
        for i, c in enumerate(colors):
            col = c if i == t else TEXT_DIM
            dots.create_oval(8 + i*18, 20, 20 + i*18, 32, fill=col, outline="")
        self.after(333, self._animate_scanline)

    def _set_status(self, msg: str):
        self.after(0, lambda: self._status_var.set(msg))

    # ── event handlers ────────────────────────────────────────────────────────

    def _on_send(self, _e=None):
        text = self.entry.get().strip()
        if not text:
            return
        self._add_bubble(text, is_user=True)
        self.entry.delete(0, tk.END)
        self._set_status("PROCESSING...")
        threading.Thread(target=self._respond, args=(text,), daemon=True).start()

    def _respond(self, text: str):
        response = process_command(text)
        self._add_bubble(response, is_user=False)
        self._set_status("READY")

    def _on_voice(self):
        self._set_status("🎤 LISTENING...")
        self._add_bubble("[ Listening… ]", is_user=False)
        def _do():
            transcript, msg = listen_from_microphone()
            if transcript:
                self._add_bubble(transcript, is_user=True)
                self._set_status("PROCESSING...")
                self._respond(transcript)
            else:
                self._add_bubble(msg, is_user=False)
                self._set_status("READY")
        threading.Thread(target=_do, daemon=True).start()

    def _toggle_always(self):
        with self._lock:
            self.is_listening = self._listen_var.get()
        if self.is_listening:
            self.listen_thread = threading.Thread(
                target=self._always_listen, daemon=True)
            self.listen_thread.start()
            self._set_status("🔴 LISTENING FOR 'EDITH'...")
        else:
            self._set_status("READY")

    def _always_listen(self):
        while self.is_running and self.is_listening:
            transcript, _ = listen_from_microphone()
            if transcript and "edith" in transcript.lower():
                self._add_bubble(transcript, is_user=True)
                command = re.sub(r"(?i)\b(hey\s*)?edith\b", "", transcript, count=1).strip()
                self._set_status("PROCESSING...")
                self._respond(command or "hello")
                self.after(0, self.lift)

    def _cleanup(self):
        self.is_running = False
        self.is_listening = False

    def run(self):
        self.mainloop()


if __name__ == "__main__":
    print("🚀 Booting EDITH Neural Interface...")
    EdithAssistant().run()
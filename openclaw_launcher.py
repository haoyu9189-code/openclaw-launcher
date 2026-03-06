"""
OpenClaw Launcher — Refined dark UI with customtkinter.
"""
import sys
import os
from pathlib import Path as _P

# Early crash handler for --windowed mode
def _setup_crash_handler():
    _log = _P.home() / ".openclaw" / "launcher-crash.log"
    _log.parent.mkdir(parents=True, exist_ok=True)
    sys.stderr = open(str(_log), "w")

if getattr(sys, 'frozen', False):
    _setup_crash_handler()

import base64
import io
import json
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
import tkinter as tk
import urllib.request
import webbrowser
import zipfile
from pathlib import Path

import customtkinter as ctk
from PIL import Image


# ── Embedded icon (openclaw-icon-128.png base64) ──
ICON_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAACC0lEQVR4nO3dPYoUURhA0SoxccA1mA"
    "6mZk6gBsaCmLsCY9dg7ArMRTA2cAyczFRMXYMwhu0K7Bc0zavue05aQ/UwfXnwvqmfZQEAAAAAAAAA"
    "zs06+xd4fHF/t4Td3P6Z+h3cmfnhzCeAOAHECSBOAHECiBNA3Dp7nz/aB+9ePD3pOcH6+Xo95t/n"
    "UFaAOAHECSBOAHECiBNAnADi1lPf599+/Lr3+MWrZ8uWz79OnhNYAeIEECeAOAHECSBOAHECiBvu"
    "IUf70O9vXu4/wa/fyzHd+/Zz7/G/Tx5u+vxDlw/2Hr56/2k5ZE5gBYgTQJwA4gQQJ4A4AcQJIG44"
    "B9i9fX3YdflHngOcvcv9c4CR9d0HcwD+TwBxAogTQJwA4gQQJ4C4u6MfGP2/eXg9AEc1+n5GrABx"
    "AogTQJwA4gQQJ4A4AcSd/PMBTt3q+QDMJIA4AcQJIE4AcQKIE0Cc9wWc+T5/xAoQJ4A4AcQJIE4A"
    "cQKIE0Dc1HfXb2EfXGcFiBNAnADiBBAngDgBxAkgbvN77NGcYOtuNj7HsALECSBOAHECiBNAnADi"
    "BBA3fY86fC/h80fLKbv68mPTcwIrQJwA4gQQJ4A4AcQJIE4AcZt/PsDI7OcHrIP7/7d+X4QVIE4A"
    "cQKIE0CcAOIEECeAuOnXA4y4L+C4rABxAogTQJwA4gQQJ4A4AQAAAABE/AN5PnNDTvbUSQAAAABJ"
    "RU5ErkJggg=="
)

# ══════════════════════════════════════════════════
#  Color System
# ══════════════════════════════════════════════════
C_BG         = "#0d1117"
C_SURFACE    = "#161b22"
C_SURFACE_2  = "#1c2128"
C_SURFACE_3  = "#272d36"
C_BORDER     = "#30363d"
C_BORDER_HL  = "#3d444d"
C_TEXT       = "#e6edf3"
C_TEXT_2     = "#9198a1"
C_TEXT_3     = "#656d76"
C_ACCENT     = "#58a6ff"
C_ACCENT_2   = "#79c0ff"
C_GREEN      = "#3fb950"
C_GREEN_2    = "#2ea043"
C_RED        = "#f85149"
C_AMBER      = "#d29922"
C_AMBER_2    = "#bb8009"
C_INPUT_BG   = "#0d1117"
C_LOG_BG     = "#010409"

# ── Config constants ──
APP_NAME = "OpenClaw"
OPENCLAW_DIR = Path.home() / ".openclaw"
CONFIG_FILE = OPENCLAW_DIR / "openclaw.json"
NODE_CONFIG = OPENCLAW_DIR / "node.json"
GATEWAY_PORT = 18789
NODE_VERSION = "v22.14.0"
NODE_DOWNLOAD_URL = f"https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-win-x64.zip"
PORTABLE_NODE_DIR = OPENCLAW_DIR / "runtime" / "node"

# ── Font helper (0.8x scale) ──
def _f(size=12, weight="normal"):
    s = max(7, int(size * 0.8))
    if weight == "normal":
        return ("Segoe UI", s)
    return ("Segoe UI", s, weight)


# ══════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════

def load_icon_image(size=32):
    data = base64.b64decode(ICON_B64)
    img = Image.open(io.BytesIO(data))
    return img.resize((size, size), Image.LANCZOS)


def load_ctk_image(size=32):
    return ctk.CTkImage(light_image=load_icon_image(size),
                        dark_image=load_icon_image(size),
                        size=(size, size))


def _find_ico():
    cached = OPENCLAW_DIR / "openclaw.ico"
    if not cached.exists():
        sources = []
        if getattr(sys, 'frozen', False):
            sources.append(Path(sys.executable).parent / "openclaw.ico")
        else:
            sources.append(Path(__file__).parent.parent / "openclaw.ico")
        for src in sources:
            if src.exists():
                try:
                    OPENCLAW_DIR.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(src), str(cached))
                except Exception:
                    pass
                break
    if cached.exists():
        return str(cached)
    if getattr(sys, 'frozen', False):
        beside_exe = Path(sys.executable).parent / "openclaw.ico"
        if beside_exe.exists():
            return str(beside_exe)
    return None


def set_window_icon(window):
    def _apply():
        ico = _find_ico()
        if ico:
            try:
                window.iconbitmap(ico)
            except Exception:
                pass
        try:
            img = load_icon_image(64)
            from PIL import ImageTk
            photo = ImageTk.PhotoImage(img)
            window.iconphoto(True, photo)
            window._icon_ref = photo
        except Exception:
            pass
    # Apply immediately and also after a delay to override CustomTkinter's
    # default feather icon which it sets via after() callbacks.
    _apply()
    window.after(50, _apply)
    window.after(200, _apply)


def force_center(window, w, h):
    def _do():
        window.update_idletasks()
        sw = window.winfo_screenwidth()
        sh = window.winfo_screenheight()
        x = (sw - w) // 2
        y = max(0, (sh - h) // 2 - 30)
        window.geometry(f"{w}x{h}+{x}+{y}")
        window.lift()
        window.focus_force()
    window.after(100, _do)


def find_node():
    portable = PORTABLE_NODE_DIR / "node.exe"
    if portable.exists():
        return str(portable)
    return shutil.which("node")


def find_npm():
    portable = PORTABLE_NODE_DIR / "npm.cmd"
    if portable.exists():
        return str(portable)
    return shutil.which("npm")


def find_openclaw(node_path):
    if node_path is None:
        return None
    npm = find_npm()
    if npm is None:
        return None
    try:
        result = subprocess.run(
            [npm, "list", "-g", "openclaw", "--depth=0"],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if "openclaw" in result.stdout:
            npm_root = subprocess.run(
                [npm, "root", "-g"],
                capture_output=True, text=True, timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            index_js = Path(npm_root.stdout.strip()) / "openclaw" / "dist" / "index.js"
            if index_js.exists():
                return str(index_js)
    except Exception:
        pass
    return None


def generate_token():
    return secrets.token_hex(24)


# Known provider base URLs (providers not listed here use OpenClaw built-in routing)
PROVIDER_BASE_URLS = {
    "deepseek":  "https://api.deepseek.com",
    "qwen":      "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "minimax":   "https://api.minimax.chat/v1",
    "moonshot":  "https://api.moonshot.cn/v1",
    "meta":      "https://openrouter.ai/api/v1",
}

# Providers natively supported by OpenClaw (no custom baseUrl needed)
NATIVE_PROVIDERS = {"anthropic", "openai", "google", "mistral"}


def _get_provider_slug(model):
    """Extract provider slug from model id like 'deepseek/deepseek-chat'."""
    return model.split("/")[0] if "/" in model else "anthropic"


def _get_model_id(model):
    """Extract model id from full model string like 'deepseek/deepseek-chat'."""
    return model.split("/", 1)[1] if "/" in model else model


def _build_provider_entry(provider_slug, model):
    """Build models.providers entry for non-native providers."""
    base_url = PROVIDER_BASE_URLS.get(provider_slug)
    if not base_url:
        return None
    model_id = _get_model_id(model)
    return {
        "baseUrl": base_url,
        "api": "openai-completions",
        "models": [
            {"id": model_id, "name": model_id, "reasoning": False,
             "input": ["text"], "contextWindow": 128000, "maxTokens": 8192},
        ],
    }


def _build_all_provider_models(provider_slug):
    """Build models list from PROVIDERS dict for a given provider slug."""
    models = []
    for prov_info in PROVIDERS.values():
        for label, full_id in prov_info.get("models", {}).items():
            if full_id.startswith(provider_slug + "/"):
                mid = _get_model_id(full_id)
                reasoning = "reason" in label.lower()
                models.append({"id": mid, "name": mid, "reasoning": reasoning,
                               "input": ["text"], "contextWindow": 128000, "maxTokens": 8192})
    return models


def _read_previous_settings():
    """Read previous settings from config files for pre-filling the setup form."""
    prev = {}
    try:
        if NODE_CONFIG.exists():
            with open(NODE_CONFIG, "r", encoding="utf-8") as f:
                node = json.load(f)
            prev["name"] = node.get("displayName", "")
    except Exception:
        pass
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            prev["model"] = cfg.get("agents", {}).get("defaults", {}).get(
                "model", {}).get("primary", "")
            # Read channel settings
            channels_cfg = cfg.get("channels", {})
            prev["channels"] = [ch for ch, v in channels_cfg.items()
                                if isinstance(v, dict) and v.get("enabled")]
            ch_tokens = {}
            for ch, v in channels_cfg.items():
                if not isinstance(v, dict):
                    continue
                tokens = {}
                for k, val in v.items():
                    if k in ("enabled", "dmPolicy", "groups", "mode",
                             "groupPolicy", "groupAllowFrom"):
                        continue
                    if isinstance(val, str) and val:
                        tokens[k] = val
                if tokens:
                    ch_tokens[ch] = tokens
            prev["channel_tokens"] = ch_tokens
    except Exception:
        pass
    # Read API key from auth-profiles
    try:
        auth_pf = OPENCLAW_DIR / "agents" / "main" / "agent" / "auth-profiles.json"
        if auth_pf.exists():
            with open(auth_pf, "r", encoding="utf-8") as f:
                ap = json.load(f)
            profiles = ap.get("profiles", {})
            if profiles:
                first_profile = next(iter(profiles.values()))
                prev["api_key"] = first_profile.get("token", "")
    except Exception:
        pass
    return prev


def _build_channels_config(channels, channel_tokens):
    """Build the channels config section for openclaw.json."""
    if not channels:
        return {}
    channel_tokens = channel_tokens or {}
    result = {}
    for ch in channels:
        ch_cfg = {"enabled": True}
        if ch in channel_tokens:
            ch_cfg.update(channel_tokens[ch])
        # Set sensible defaults per channel
        if ch == "whatsapp":
            ch_cfg.setdefault("dmPolicy", "pairing")
        elif ch == "telegram":
            ch_cfg.setdefault("dmPolicy", "pairing")
            ch_cfg.setdefault("groups", {"*": {"requireMention": True}})
        elif ch == "discord":
            pass
        elif ch == "slack":
            ch_cfg.setdefault("mode", "socket")
        result[ch] = ch_cfg
    return result


def create_config(api_key, display_name, model="anthropic/claude-haiku-4-5", channels=None, channel_tokens=None):
    OPENCLAW_DIR.mkdir(parents=True, exist_ok=True)
    for subdir in ["agents", "credentials", "logs", "plugins", "memory",
                    "identity", "media", "extensions", "subagents",
                    "delivery-queue", "devices", "cron", "telegram"]:
        (OPENCLAW_DIR / subdir).mkdir(exist_ok=True)

    gateway_token = generate_token()

    provider_slug = _get_provider_slug(model)
    # For meta/llama models routed through openrouter
    auth_provider = "openrouter" if provider_slug == "meta" else provider_slug
    profile_key = f"{auth_provider}:default"
    cred_filename = f"{auth_provider}-default.json"

    config = {
        "meta": {"lastTouchedVersion": "2026.2.24"},
        "auth": {
            "profiles": {
                profile_key: {"provider": auth_provider, "mode": "token"}
            }
        },
        "agents": {
            "defaults": {
                "model": {"primary": model},
                "workspace": str(Path.home() / "clawd"),
                "compaction": {"mode": "safeguard"},
                "maxConcurrent": 4
            }
        },
        "channels": _build_channels_config(channels, channel_tokens),
        "gateway": {
            "port": GATEWAY_PORT,
            "mode": "local",
            "bind": "loopback",
            "auth": {"mode": "token", "token": gateway_token}
        },
        "plugins": {"entries": {}},
        "skills": {"install": {"nodeManager": "npm"}}
    }

    # Add custom provider config for non-native providers
    if provider_slug not in NATIVE_PROVIDERS:
        provider_entry = _build_provider_entry(provider_slug, model)
        if provider_entry:
            # Include all models for this provider, not just the selected one
            all_models = _build_all_provider_models(provider_slug)
            if all_models:
                provider_entry["models"] = all_models
            config["models"] = {
                "mode": "merge",
                "providers": {provider_slug: provider_entry}
            }

    node_config = {
        "version": 1,
        "nodeId": secrets.token_hex(16),
        "displayName": display_name,
        "gateway": {"host": "127.0.0.1", "port": GATEWAY_PORT, "tls": False}
    }

    # Write main config files
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    with open(NODE_CONFIG, "w", encoding="utf-8") as f:
        json.dump(node_config, f, indent=2, ensure_ascii=False)

    # Write credential file
    cred_file = OPENCLAW_DIR / "credentials" / cred_filename
    with open(cred_file, "w", encoding="utf-8") as f:
        json.dump({"apiKey": api_key}, f, indent=2)

    # Write auth-profiles.json (where the agent actually reads API keys)
    agent_dir = OPENCLAW_DIR / "agents" / "main" / "agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    auth_profiles_file = agent_dir / "auth-profiles.json"
    if auth_profiles_file.exists():
        with open(auth_profiles_file, "r", encoding="utf-8") as f:
            auth_profiles = json.load(f)
    else:
        auth_profiles = {"version": 1, "profiles": {}, "lastGood": {}, "usageStats": {}}
    auth_profiles["profiles"][profile_key] = {
        "type": "token", "provider": auth_provider, "token": api_key
    }
    auth_profiles.setdefault("lastGood", {})[auth_provider] = profile_key
    with open(auth_profiles_file, "w", encoding="utf-8") as f:
        json.dump(auth_profiles, f, indent=2, ensure_ascii=False)

    (Path.home() / "clawd").mkdir(exist_ok=True)
    create_desktop_shortcut()
    return gateway_token


def create_desktop_shortcut():
    try:
        if not getattr(sys, 'frozen', False):
            return
        exe_path = sys.executable
        desktop = Path.home() / "Desktop"
        shortcut_path = desktop / "OpenClaw.lnk"
        if shortcut_path.exists():
            return
        ico_path = OPENCLAW_DIR / "openclaw.ico"
        src_ico = Path(exe_path).parent / "openclaw.ico"
        if src_ico.exists() and not ico_path.exists():
            shutil.copy2(src_ico, ico_path)
        icon_line = f"$sc.IconLocation = '{ico_path}'" if ico_path.exists() else ""
        exe_dir = str(Path(exe_path).parent)
        ps_script = (
            "$ws = New-Object -ComObject WScript.Shell; "
            f"$sc = $ws.CreateShortcut('{shortcut_path}'); "
            f"$sc.TargetPath = '{exe_path}'; "
            f"$sc.WorkingDirectory = '{exe_dir}'; "
            f"$sc.Description = 'OpenClaw AI Assistant'; "
            f"{icon_line}; "
            "$sc.Save()"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════
#  Providers & models
# ══════════════════════════════════════════════════

PROVIDERS = {
    "Anthropic (Claude)": {
        "models": {
            "Claude Haiku 4.5 — Fast & Cheap": "anthropic/claude-haiku-4-5",
            "Claude Sonnet 4.6 — Balanced": "anthropic/claude-sonnet-4-6",
            "Claude Opus 4.6 — Most Capable": "anthropic/claude-opus-4-6",
        },
        "default": "Claude Haiku 4.5 — Fast & Cheap",
    },
    "OpenAI": {
        "models": {
            "GPT-4o — Fast & Smart": "openai/gpt-4o",
            "GPT-4o Mini — Budget": "openai/gpt-4o-mini",
            "GPT-4.1 — Latest": "openai/gpt-4.1",
            "GPT-4.1 Mini — Fast": "openai/gpt-4.1-mini",
            "GPT-4.1 Nano — Cheapest": "openai/gpt-4.1-nano",
            "o3 — Reasoning": "openai/o3",
            "o4 Mini — Fast Reasoning": "openai/o4-mini",
        },
        "default": "GPT-4o — Fast & Smart",
    },
    "DeepSeek": {
        "models": {
            "DeepSeek Chat — Budget": "deepseek/deepseek-chat",
            "DeepSeek Reasoner — Reasoning": "deepseek/deepseek-reasoner",
        },
        "default": "DeepSeek Chat — Budget",
    },
    "Google (Gemini)": {
        "models": {
            "Gemini 2.5 Pro — Most Capable": "google/gemini-2.5-pro",
            "Gemini 2.5 Flash — Fast": "google/gemini-2.5-flash",
            "Gemini 2.0 Flash — Budget": "google/gemini-2.0-flash",
        },
        "default": "Gemini 2.5 Flash — Fast",
    },
    "Meta (Llama)": {
        "models": {
            "Llama 4 Maverick — Latest": "meta/llama-4-maverick",
            "Llama 4 Scout — Fast": "meta/llama-4-scout",
            "Llama 3.3 70B — Balanced": "meta/llama-3.3-70b",
        },
        "default": "Llama 3.3 70B — Balanced",
    },
    "Mistral": {
        "models": {
            "Mistral Large — Most Capable": "mistral/mistral-large-latest",
            "Mistral Medium — Balanced": "mistral/mistral-medium-latest",
            "Mistral Small — Budget": "mistral/mistral-small-latest",
            "Codestral — Coding": "mistral/codestral-latest",
        },
        "default": "Mistral Small — Budget",
    },
    "Alibaba (Qwen)": {
        "models": {
            "Qwen Max — Most Capable": "qwen/qwen-max",
            "Qwen Plus — Balanced": "qwen/qwen-plus",
            "Qwen Turbo — Fast": "qwen/qwen-turbo",
        },
        "default": "Qwen Plus — Balanced",
    },
    "xAI (Grok)": {
        "models": {
            "Grok 3 — Most Capable": "xai/grok-3",
            "Grok 3 Mini — Fast": "xai/grok-3-mini",
        },
        "default": "Grok 3 Mini — Fast",
    },
    "MiniMax": {
        "models": {
            "MiniMax-Text-01 — Latest": "minimax/minimax-text-01",
            "abab6.5s — Fast": "minimax/abab6.5s-chat",
        },
        "default": "MiniMax-Text-01 — Latest",
    },
    "ByteDance (Doubao)": {
        "models": {
            "Doubao Pro 256K — Most Capable": "doubao/doubao-pro-256k",
            "Doubao Lite 128K — Fast": "doubao/doubao-lite-128k",
        },
        "default": "Doubao Pro 256K — Most Capable",
    },
}

DEFAULT_MODEL = "anthropic/claude-haiku-4-5"

CHANNELS_LIST = [
    ("whatsapp",  "WhatsApp — QR pairing at startup", []),
    ("telegram",  "Telegram — Bot messaging", [("botToken", "Telegram Bot Token (from @BotFather)")]),
    ("discord",   "Discord — Bot channel", [("token", "Discord Bot Token")]),
    ("slack",     "Slack — Workspace channel", [
        ("appToken", "Slack App Token (xapp-...)"),
        ("botToken", "Slack Bot Token (xoxb-...)"),
    ]),
]

SKILLS_LIST = [
    ("@openclaw/voice-call",                "Voice Call — Make and receive voice calls"),
    ("@openclaw/feishu",                    "Feishu / Lark — Channel integration"),
    ("@canghe/openclaw-wechat",             "WeChat — Messaging channel"),
    ("@supermemory/openclaw-supermemory",    "Supermemory — Persistent memory"),
    ("@mem0/openclaw-mem0",                 "Mem0 — Long-term memory for agents"),
    ("@browserbasehq/openclaw-browserbase", "Browser — Cloud browser automation"),
    ("@composio/openclaw-plugin",           "Composio — 500+ app integrations"),
    ("@agentsandbox/openclaw-agentsandbox", "Sandbox — Run Python/Bash safely"),
]


# ══════════════════════════════════════════════════
#  Setup Dialog
# ══════════════════════════════════════════════════

class SetupDialog(ctk.CTk):
    def __init__(self, prev=None):
        super().__init__()
        self._prev = prev or {}
        self.title(APP_NAME)
        self._win_w, self._win_h = 1240, 880
        self.geometry(f"{self._win_w}x{self._win_h}")
        self.minsize(800, 600)
        self.resizable(True, True)
        self.configure(fg_color=C_BG)
        self.result = None
        self._base_w = self._win_w
        self._last_ratio = 1.0
        set_window_icon(self)
        self._build()
        if self._prev:
            self._prefill()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.bind("<Configure>", self._on_resize)
        force_center(self, self._win_w, self._win_h)

    def _on_resize(self, event):
        if event.widget is not self:
            return
        ratio = self.winfo_width() / self._base_w
        if abs(ratio - self._last_ratio) < 0.05:
            return
        self._last_ratio = ratio
        ctk.set_widget_scaling(ratio)

    def _build(self):
        body = ctk.CTkFrame(self, fg_color=C_BG)
        body.pack(fill="both", expand=True)

        px = 20

        # ── Header ──
        hdr = ctk.CTkFrame(body, fg_color="transparent")
        hdr.pack(fill="x", padx=px, pady=(4, 0))
        icon_img = load_ctk_image(28)
        ctk.CTkLabel(hdr, image=icon_img, text="").pack(side="left", padx=(0, 8))
        ctk.CTkLabel(hdr, text="OpenClaw Setup", font=_f(16, "bold"),
                     text_color=C_TEXT).pack(side="left")
        ctk.CTkButton(
            hdr, text="Launch OpenClaw", height=28, width=150,
            corner_radius=8, fg_color="#7c3aed", hover_color="#6d28d9",
            text_color="#ffffff", font=_f(12, "bold"),
            command=self._on_submit
        ).pack(side="right")

        # Subtitle + GitHub link
        sub_row = ctk.CTkFrame(body, fg_color="transparent")
        sub_row.pack(fill="x", padx=px, pady=0)
        ctk.CTkLabel(sub_row, text="Configure your AI assistant to get started.",
                     font=_f(11), text_color=C_TEXT_3
                     ).pack(side="left")
        ctk.CTkButton(
            sub_row, text="GitHub", anchor="w", fg_color="transparent",
            hover_color=C_SURFACE_2, text_color=C_ACCENT,
            font=_f(10), height=20, width=50, corner_radius=4,
            command=lambda: webbrowser.open("https://github.com/openclaw/openclaw")
        ).pack(side="left", padx=(6, 0))

        # ══ Row 1: Info card + Links card (side by side) ══
        row1 = ctk.CTkFrame(body, fg_color="transparent")
        row1.pack(fill="x", padx=px, pady=(0, 2))
        row1.columnconfigure(0, weight=1)
        row1.columnconfigure(1, weight=1)

        # Info card (left)
        info = ctk.CTkFrame(row1, fg_color=C_SURFACE, corner_radius=8,
                             border_width=1, border_color=C_BORDER)
        info.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        ctk.CTkLabel(info, text="What is an API Key?", font=_f(11, "bold"),
                     text_color=C_ACCENT, anchor="w"
                     ).pack(fill="x", padx=10, pady=(2, 0))
        ctk.CTkLabel(info,
                     text=("An API Key is your personal access token for AI services.\n"
                           "OpenClaw uses it to call models (Claude, DeepSeek, etc.)\n"
                           "on your behalf.\n\n"
                           "AI models run on GPU servers — you pay per usage,\n"
                           "typically ~$0.01 per message."),
                     font=_f(10), text_color=C_TEXT_3, justify="left", anchor="w",
                     ).pack(fill="x", padx=10, pady=(0, 0))
        ctk.CTkLabel(info, text="How to begin?", font=_f(11, "bold"),
                     text_color=C_ACCENT, anchor="w"
                     ).pack(fill="x", padx=10, pady=(2, 0))
        ctk.CTkLabel(info,
                     text="Fill your Name and API Key → Launch!",
                     font=_f(10), text_color=C_TEXT_3, anchor="w",
                     ).pack(fill="x", padx=10, pady=(0, 2))

        # Links card (right) — compact, no scroll
        links = ctk.CTkFrame(row1, fg_color=C_SURFACE, corner_radius=8,
                              border_width=1, border_color=C_BORDER)
        links.grid(row=0, column=1, sticky="new", padx=(4, 0))

        ctk.CTkLabel(links, text="Get your API Key", font=_f(10, "bold"),
                     text_color=C_GREEN, anchor="w", height=14
                     ).pack(fill="x", padx=10, pady=(2, 0))

        for name, url in [
            ("Anthropic (Claude)",  "https://console.anthropic.com/settings/keys"),
            ("OpenAI (ChatGPT)",    "https://platform.openai.com/api-keys"),
            ("Google (Gemini)",     "https://aistudio.google.com/apikey"),
            ("DeepSeek",            "https://platform.deepseek.com/api_keys"),
            ("Mistral",             "https://console.mistral.ai/api-keys"),
            ("Alibaba (Qwen)",      "https://dashscope.console.aliyun.com/apikey"),
            ("Meta (Llama)",        "https://ai.meta.com/llama/"),
            ("xAI (Grok)",          "https://console.x.ai/"),
            ("MiniMax",             "https://platform.minimaxi.com/"),
            ("ByteDance (Doubao)",  "https://console.volcengine.com/ark"),
        ]:
            lrow = ctk.CTkFrame(links, fg_color="transparent")
            lrow.pack(fill="x", padx=6, pady=0)
            ctk.CTkLabel(lrow, text=name, width=110, anchor="w",
                         font=_f(9), text_color=C_TEXT_2, height=5).pack(side="left")
            ctk.CTkButton(
                lrow, text=url, anchor="w", fg_color="transparent",
                hover_color=C_SURFACE_2, text_color=C_ACCENT,
                font=_f(9), height=5, corner_radius=2,
                command=lambda u=url: webbrowser.open(u)
            ).pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(links, text="Register, add credit, then create a key.",
                     font=_f(8), text_color=C_TEXT_3, height=10
                     ).pack(padx=10, pady=(0, 2), anchor="w")

        # ══ Main two-column layout: Left (Name/Key/Model) | Right (Channels & Skills) ══
        main_row = ctk.CTkFrame(body, fg_color="transparent")
        main_row.pack(fill="both", expand=True, padx=px, pady=0)
        main_row.columnconfigure(0, weight=1)
        main_row.columnconfigure(1, weight=1)
        main_row.rowconfigure(0, weight=1)

        # ── Left column: Name, API Key, Model ──
        left_col = ctk.CTkFrame(main_row, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        # Display Name
        ctk.CTkLabel(left_col, text="Display Name", font=_f(10, "bold"),
                     text_color=C_TEXT_2).pack(anchor="w", pady=0)
        self.name_entry = ctk.CTkEntry(
            left_col, height=26, corner_radius=6,
            fg_color=C_INPUT_BG, border_color=C_BORDER, border_width=1,
            text_color=C_TEXT, placeholder_text="Your name",
            placeholder_text_color=C_TEXT_3, font=_f(11))
        self.name_entry.pack(fill="x", pady=(0, 2))

        # API Key
        ctk.CTkLabel(left_col, text="API Key", font=_f(10, "bold"),
                     text_color=C_TEXT_2).pack(anchor="w", pady=0)
        key_row = ctk.CTkFrame(left_col, fg_color="transparent")
        key_row.pack(fill="x", pady=(0, 2))
        self.key_entry = ctk.CTkEntry(
            key_row, height=26, corner_radius=6,
            fg_color=C_INPUT_BG, border_color=C_BORDER, border_width=1,
            text_color=C_TEXT, show="*",
            placeholder_text="sk-ant-... or sk-...",
            placeholder_text_color=C_TEXT_3, font=_f(11))
        self.key_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._show_key = False
        self.eye_btn = ctk.CTkButton(
            key_row, text="Show", width=40, height=26,
            corner_radius=6, fg_color=C_SURFACE_2, hover_color=C_SURFACE_3,
            border_width=1, border_color=C_BORDER,
            text_color=C_TEXT_3, font=_f(9),
            command=self._toggle_key)
        self.eye_btn.pack(side="right")

        # Model
        ctk.CTkLabel(left_col, text="Model", font=_f(10, "bold"),
                     text_color=C_TEXT_2).pack(anchor="w", pady=0)

        prov_row = ctk.CTkFrame(left_col, fg_color="transparent")
        prov_row.pack(fill="x", pady=(0, 1))
        ctk.CTkLabel(prov_row, text="Provider", width=55, anchor="w",
                     font=_f(10), text_color=C_TEXT_2).pack(side="left")
        self.provider_var = ctk.StringVar(value=list(PROVIDERS.keys())[0])
        self.provider_menu = ctk.CTkOptionMenu(
            prov_row, variable=self.provider_var,
            values=list(PROVIDERS.keys()),
            height=26, corner_radius=6,
            fg_color=C_SURFACE_2, button_color=C_SURFACE_3,
            button_hover_color=C_BORDER_HL,
            dropdown_fg_color=C_SURFACE, dropdown_hover_color=C_SURFACE_3,
            dropdown_text_color=C_TEXT, text_color=C_TEXT,
            font=_f(10), dropdown_font=_f(10),
            command=self._on_provider_change)
        self.provider_menu.pack(side="left", fill="x", expand=True)

        mod_row = ctk.CTkFrame(left_col, fg_color="transparent")
        mod_row.pack(fill="x", pady=0)
        ctk.CTkLabel(mod_row, text="Model", width=55, anchor="w",
                     font=_f(10), text_color=C_TEXT_2).pack(side="left")
        first_prov = list(PROVIDERS.keys())[0]
        first_models = list(PROVIDERS[first_prov]["models"].keys())
        first_default = PROVIDERS[first_prov]["default"]
        self.model_var = ctk.StringVar(value=first_default)
        self.model_menu = ctk.CTkOptionMenu(
            mod_row, variable=self.model_var,
            values=first_models,
            height=26, corner_radius=6,
            fg_color=C_SURFACE_2, button_color=C_SURFACE_3,
            button_hover_color=C_BORDER_HL,
            dropdown_fg_color=C_SURFACE, dropdown_hover_color=C_SURFACE_3,
            dropdown_text_color=C_TEXT, text_color=C_TEXT,
            font=_f(10), dropdown_font=_f(10))
        self.model_menu.pack(side="left", fill="x", expand=True)

        # ── Right column: Channels & Skills (scrollable) ──
        right_col = ctk.CTkFrame(main_row, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="new", padx=(4, 0))

        ctk.CTkLabel(right_col, text="Channels & Skills", font=_f(10, "bold"),
                     text_color=C_TEXT_2).pack(anchor="w", pady=0)

        addons_wrapper = ctk.CTkFrame(right_col, fg_color="transparent", height=170)
        addons_wrapper.pack(fill="x")
        addons_wrapper.pack_propagate(False)

        self.addons_frame = ctk.CTkScrollableFrame(
            addons_wrapper, fg_color=C_SURFACE, corner_radius=6,
            border_width=1, border_color=C_BORDER,
            scrollbar_button_color=C_SURFACE_3,
            scrollbar_button_hover_color=C_BORDER_HL)
        self.addons_frame.pack(fill="both", expand=True)

        # Channels (built-in)
        ctk.CTkLabel(self.addons_frame, text="Channels", font=_f(8, "bold"),
                     text_color=C_TEXT_2).pack(anchor="w", padx=6, pady=(2, 0))
        self.channel_vars = {}
        self.channel_token_entries = {}
        self._channel_token_frames = {}
        self._channel_checkboxes = {}
        for ch_id, desc, token_fields in CHANNELS_LIST:
            var = ctk.BooleanVar(value=(ch_id == "telegram"))
            self.channel_vars[ch_id] = var
            cb = ctk.CTkCheckBox(
                self.addons_frame, text=desc, variable=var,
                font=_f(8), text_color=C_TEXT_3,
                fg_color=C_ACCENT, hover_color=C_ACCENT_2,
                border_color=C_BORDER, checkmark_color="#ffffff",
                height=15, checkbox_width=14, checkbox_height=14,
                corner_radius=3,
                command=lambda cid=ch_id: self._toggle_channel_tokens(cid),
            )
            cb.pack(anchor="w", padx=6, pady=0)
            self._channel_checkboxes[ch_id] = cb
            if token_fields:
                tf = ctk.CTkFrame(self.addons_frame, fg_color="transparent")
                entries = {}
                for field_key, placeholder in token_fields:
                    e = ctk.CTkEntry(
                        tf, height=18, corner_radius=3,
                        fg_color=C_INPUT_BG, border_color=C_BORDER, border_width=1,
                        text_color=C_TEXT, placeholder_text=placeholder,
                        placeholder_text_color=C_TEXT_3, font=_f(8))
                    e.pack(fill="x", padx=(18, 0), pady=0)
                    entries[field_key] = e
                self.channel_token_entries[ch_id] = entries
                self._channel_token_frames[ch_id] = tf
                if ch_id == "telegram":
                    tf.pack(fill="x", padx=6, pady=0, after=cb)

        # Skills (npm packages)
        ctk.CTkLabel(self.addons_frame, text="Skills", font=_f(8, "bold"),
                     text_color=C_TEXT_2).pack(anchor="w", padx=6, pady=(2, 0))
        self.skill_vars = {}
        for pkg, desc in SKILLS_LIST:
            var = ctk.BooleanVar(value=False)
            self.skill_vars[pkg] = var
            ctk.CTkCheckBox(
                self.addons_frame, text=desc, variable=var,
                font=_f(8), text_color=C_TEXT_3,
                fg_color=C_GREEN, hover_color=C_GREEN_2,
                border_color=C_BORDER, checkmark_color="#ffffff",
                height=15, checkbox_width=14, checkbox_height=14,
                corner_radius=3,
            ).pack(anchor="w", padx=6, pady=0)


    # ── Handlers ──

    def _toggle_key(self):
        self._show_key = not self._show_key
        self.key_entry.configure(show="" if self._show_key else "*")
        self.eye_btn.configure(text="Hide" if self._show_key else "Show")

    def _prefill(self):
        """Pre-fill form fields from previous settings."""
        p = self._prev
        if p.get("name"):
            self.name_entry.insert(0, p["name"])
        if p.get("api_key"):
            self.key_entry.insert(0, p["api_key"])
        # Set provider and model from previous model ID (e.g. "deepseek/deepseek-chat")
        prev_model = p.get("model", "")
        if prev_model:
            for prov_name, prov_info in PROVIDERS.items():
                for label, mid in prov_info["models"].items():
                    if mid == prev_model:
                        self.provider_var.set(prov_name)
                        self._on_provider_change(prov_name)
                        self.model_var.set(label)
                        break
        # Pre-check channels and fill tokens
        prev_channels = p.get("channels", [])
        prev_ch_tokens = p.get("channel_tokens", {})
        if prev_channels:
            # Uncheck defaults first, then set previous selections
            for ch_id in self.channel_vars:
                self.channel_vars[ch_id].set(ch_id in prev_channels)
                self._toggle_channel_tokens(ch_id)
            for ch_id in prev_channels:
                if ch_id in prev_ch_tokens and ch_id in self.channel_token_entries:
                    for field_key, val in prev_ch_tokens[ch_id].items():
                        if field_key in self.channel_token_entries[ch_id]:
                            self.channel_token_entries[ch_id][field_key].insert(0, val)

    def _toggle_channel_tokens(self, ch_id):
        if ch_id not in self._channel_token_frames:
            return
        frame = self._channel_token_frames[ch_id]
        if self.channel_vars[ch_id].get():
            cb = self._channel_checkboxes[ch_id]
            frame.pack(fill="x", padx=6, pady=0, after=cb)
        else:
            frame.pack_forget()

    def _on_provider_change(self, provider_name):
        info = PROVIDERS.get(provider_name, {})
        models = list(info.get("models", {}).keys())
        default = info.get("default", models[0] if models else "")
        self.model_menu.configure(values=models)
        self.model_var.set(default)

    def _on_submit(self):
        name = self.name_entry.get().strip()
        key = self.key_entry.get().strip()
        if not name:
            self._flash_error("Please enter a display name.")
            return
        if not key or len(key) < 10:
            self._flash_error(
                "Please enter a valid API key.\n"
                "Claude: starts with 'sk-ant-'\n"
                "DeepSeek: starts with 'sk-'"
            )
            return
        provider_name = self.provider_var.get()
        model_label = self.model_var.get()
        model_id = PROVIDERS.get(provider_name, {}).get("models", {}).get(
            model_label, DEFAULT_MODEL)
        selected_skills = [pkg for pkg, var in self.skill_vars.items() if var.get()]
        selected_channels = [ch for ch, var in self.channel_vars.items() if var.get()]
        # Collect channel tokens
        channel_tokens = {}
        for ch_id in selected_channels:
            if ch_id in self.channel_token_entries:
                tokens = {}
                for field_key, entry in self.channel_token_entries[ch_id].items():
                    val = entry.get().strip()
                    if val:
                        tokens[field_key] = val
                if tokens:
                    channel_tokens[ch_id] = tokens
        self.result = {"name": name, "api_key": key, "model": model_id,
                       "skills": selected_skills, "channels": selected_channels,
                       "channel_tokens": channel_tokens}
        self.quit()

    def _on_cancel(self):
        self.result = None
        self.quit()

    def _flash_error(self, msg):
        err = ctk.CTkToplevel(self)
        err.title("Error")
        ew, eh = 340, 160
        err.geometry(f"{ew}x{eh}")
        err.resizable(False, False)
        err.configure(fg_color=C_BG)
        set_window_icon(err)
        err.grab_set()
        force_center(err, ew, eh)
        ctk.CTkLabel(err, text=msg, font=_f(11),
                     text_color=C_RED, wraplength=300, justify="left"
                     ).pack(padx=20, pady=(20, 10))
        ctk.CTkButton(err, text="OK", width=70, height=28,
                      fg_color=C_SURFACE_2, hover_color=C_SURFACE_3,
                      text_color=C_TEXT, corner_radius=6, font=_f(10),
                      command=lambda: (err.grab_release(), err.destroy())
                      ).pack(pady=(0, 14))


# ══════════════════════════════════════════════════
#  Progress / Running Window
# ══════════════════════════════════════════════════

class ProgressWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self._win_w, self._win_h = 520, 380
        self.geometry(f"{self._win_w}x{self._win_h}")
        self.minsize(380, 280)
        self.resizable(True, True)
        self.configure(fg_color=C_BG)
        set_window_icon(self)
        self._processes = []
        self._running = True
        self._reset_requested = False
        self._base_w = self._win_w
        self._last_ratio = 1.0
        self.protocol("WM_DELETE_WINDOW", self._on_stop)
        self._build()
        self.bind("<Configure>", self._on_resize)
        force_center(self, self._win_w, self._win_h)

    def _on_resize(self, event):
        if event.widget is not self:
            return
        ratio = self.winfo_width() / self._base_w
        if abs(ratio - self._last_ratio) < 0.05:
            return
        self._last_ratio = ratio
        ctk.set_widget_scaling(ratio)
        try:
            new_sz = max(7, int(9 * ratio))
            self.log_text.configure(font=("Cascadia Code", new_sz))
        except Exception:
            pass

    def _build(self):
        # ── Header bar ──
        header = ctk.CTkFrame(self, fg_color=C_SURFACE, height=40, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        icon_img = load_ctk_image(18)
        ctk.CTkLabel(header, image=icon_img, text="").pack(side="left", padx=(12, 6))
        ctk.CTkLabel(header, text="OpenClaw", font=_f(12, "bold"),
                     text_color=C_TEXT).pack(side="left")

        self.status_label = ctk.CTkLabel(
            header, text="Initializing...", font=_f(10), text_color=C_TEXT_3)
        self.status_label.pack(side="right", padx=12)

        self.status_dot = ctk.CTkFrame(header, width=7, height=7,
                                        corner_radius=4, fg_color=C_AMBER)
        self.status_dot.pack(side="right")

        # ── Accent line ──
        ctk.CTkFrame(self, fg_color=C_ACCENT, height=2, corner_radius=0).pack(fill="x")

        # ── Progress bar ──
        self.progress = ctk.CTkProgressBar(
            self, height=3, corner_radius=2,
            fg_color=C_SURFACE_2, progress_color=C_ACCENT)
        self.progress.pack(fill="x", padx=16, pady=(10, 4))
        self.progress.set(0)
        self._progress_anim = True
        self._animate_progress()

        # ── Bottom bar ──
        bottom = ctk.CTkFrame(self, fg_color=C_SURFACE, height=44, corner_radius=0)
        bottom.pack(side="bottom", fill="x")
        bottom.pack_propagate(False)

        self.console_btn = ctk.CTkButton(
            bottom, text="Open Console", height=28,
            corner_radius=6, fg_color=C_ACCENT, hover_color=C_ACCENT_2,
            text_color="#ffffff", font=_f(11, "bold"),
            state="disabled",
            command=lambda: webbrowser.open(f"http://127.0.0.1:{GATEWAY_PORT}"))
        self.console_btn.pack(side="left", padx=(12, 0), pady=8)

        ctk.CTkButton(
            bottom, text="Reset", height=28,
            corner_radius=6, fg_color=C_SURFACE_3, hover_color=C_AMBER_2,
            text_color=C_TEXT_2, font=_f(10),
            command=self._on_reset
        ).pack(side="right", padx=(0, 12), pady=8)

        # ── Log area ──
        log_frame = ctk.CTkFrame(self, fg_color=C_SURFACE, corner_radius=8,
                                  border_width=1, border_color=C_BORDER)
        log_frame.pack(fill="both", expand=True, padx=12, pady=(6, 6))

        self.log_text = tk.Text(
            log_frame, font=("Cascadia Code", 9), wrap="word",
            bg=C_LOG_BG, fg=C_TEXT_3, insertbackground=C_TEXT,
            selectbackground=C_ACCENT, selectforeground="#ffffff",
            bd=0, padx=10, pady=8, state="disabled",
            highlightthickness=0, relief="flat")
        self.log_text.pack(fill="both", expand=True, padx=2, pady=2)

        self.log_text.tag_configure("error",   foreground=C_RED)
        self.log_text.tag_configure("success", foreground=C_GREEN)
        self.log_text.tag_configure("warn",    foreground=C_AMBER)
        self.log_text.tag_configure("accent",  foreground=C_ACCENT)

    def _animate_progress(self):
        if not self._progress_anim:
            return
        cur = self.progress.get()
        nxt = cur + 0.008
        if nxt > 0.92:
            nxt = 0.0
        self.progress.set(nxt)
        self.after(60, self._animate_progress)

    def set_status(self, text):
        self.after(0, lambda: self.status_label.configure(text=text))

    def log(self, text, tag=None):
        def _do():
            self.log_text.configure(state="normal")
            if tag:
                self.log_text.insert("end", text + "\n", tag)
            else:
                auto_tag = None
                lower = text.lower()
                if "error" in lower or "failed" in lower:
                    auto_tag = "error"
                elif "warning" in lower:
                    auto_tag = "warn"
                elif "success" in lower or "running" in lower:
                    auto_tag = "success"
                elif "using" in lower or "console" in lower:
                    auto_tag = "accent"
                if auto_tag:
                    self.log_text.insert("end", text + "\n", auto_tag)
                else:
                    self.log_text.insert("end", text + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.after(0, _do)

    def set_done(self):
        def _do():
            self._progress_anim = False
            self.progress.set(1.0)
            self.progress.configure(progress_color=C_GREEN)
            self.status_dot.configure(fg_color=C_GREEN)
            self.console_btn.configure(state="normal")
        self.after(0, _do)

    def _stop_processes(self):
        self._running = False
        for p in self._processes:
            try:
                p.terminate()
            except Exception:
                pass

    def _on_stop(self):
        self._stop_processes()
        self.quit()

    def _on_reset(self):
        self._stop_processes()
        # Save previous settings before deleting config files
        self._previous_settings = _read_previous_settings()
        for f in [CONFIG_FILE, NODE_CONFIG]:
            try:
                f.unlink(missing_ok=True)
            except Exception:
                pass
        cred_dir = OPENCLAW_DIR / "credentials"
        for f in cred_dir.glob("*-default.json"):
            try:
                f.unlink(missing_ok=True)
            except Exception:
                pass
        auth_pf = OPENCLAW_DIR / "agents" / "main" / "agent" / "auth-profiles.json"
        try:
            auth_pf.unlink(missing_ok=True)
        except Exception:
            pass
        self._reset_requested = True
        self.quit()


# ══════════════════════════════════════════════════
#  Service management
# ══════════════════════════════════════════════════

def download_node(progress):
    progress.set_status("Downloading Node.js...")
    progress.log(f"Downloading {NODE_DOWNLOAD_URL}")
    runtime_dir = OPENCLAW_DIR / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        def reporthook(block_num, block_size, total_size):
            if total_size > 0:
                pct = min(100, block_num * block_size * 100 // total_size)
                progress.set_status(f"Downloading Node.js... {pct}%")
        urllib.request.urlretrieve(NODE_DOWNLOAD_URL, tmp_path, reporthook)
        progress.log("Download complete. Extracting...")
        progress.set_status("Extracting Node.js...")
        with zipfile.ZipFile(tmp_path, 'r') as zf:
            zf.extractall(runtime_dir)
        extracted = runtime_dir / f"node-{NODE_VERSION}-win-x64"
        if extracted.exists():
            if PORTABLE_NODE_DIR.exists():
                shutil.rmtree(PORTABLE_NODE_DIR)
            extracted.rename(PORTABLE_NODE_DIR)
        progress.log(f"Node.js installed to {PORTABLE_NODE_DIR}", "success")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def install_openclaw(progress):
    npm = find_npm()
    if npm is None:
        raise RuntimeError("npm not found")
    progress.set_status("Installing OpenClaw...")
    progress.log("Running: npm install -g openclaw")
    env = os.environ.copy()
    env["PATH"] = str(PORTABLE_NODE_DIR) + os.pathsep + env.get("PATH", "")
    proc = subprocess.Popen(
        [npm, "install", "-g", "openclaw"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, env=env,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    for line in proc.stdout:
        line = line.strip()
        if line:
            progress.log(line)
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("Failed to install openclaw")
    progress.log("OpenClaw installed successfully.", "success")


def install_skills(progress, skills):
    if not skills:
        return
    npm = find_npm()
    if npm is None:
        progress.log("npm not found, skipping skills install.", "warn")
        return
    env = os.environ.copy()
    env["PATH"] = str(PORTABLE_NODE_DIR) + os.pathsep + env.get("PATH", "")
    plugins_dir = OPENCLAW_DIR / "plugins"
    plugins_dir.mkdir(exist_ok=True)
    pkg_json = plugins_dir / "package.json"
    if not pkg_json.exists():
        with open(pkg_json, "w") as f:
            json.dump({"name": "plugins", "version": "1.0.0", "dependencies": {}}, f)
    for pkg in skills:
        progress.set_status(f"Installing {pkg}...")
        progress.log(f"Installing skill: {pkg}")
        proc = subprocess.Popen(
            [npm, "install", pkg],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, env=env, cwd=str(plugins_dir),
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        for line in proc.stdout:
            line = line.strip()
            if line:
                progress.log(line)
        proc.wait()
        if proc.returncode == 0:
            progress.log(f"Installed {pkg}", "success")
        else:
            progress.log(f"Failed to install {pkg}", "warn")


def start_services(progress, gateway_token):
    node_path = find_node()
    openclaw_js = find_openclaw(node_path)
    if not openclaw_js:
        raise RuntimeError("OpenClaw not found after installation")
    env = os.environ.copy()
    env["PATH"] = str(PORTABLE_NODE_DIR) + os.pathsep + env.get("PATH", "")
    env["HOME"] = str(Path.home())
    env["OPENCLAW_GATEWAY_PORT"] = str(GATEWAY_PORT)
    env["OPENCLAW_GATEWAY_TOKEN"] = gateway_token
    env["OPENCLAW_SERVICE_MARKER"] = "openclaw"

    progress.set_status("Starting Gateway...")
    progress.log(f"Starting gateway on port {GATEWAY_PORT}")

    gateway_proc = subprocess.Popen(
        [node_path, openclaw_js, "gateway", "--port", str(GATEWAY_PORT)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, env=env, creationflags=subprocess.CREATE_NO_WINDOW
    )
    progress._processes.append(gateway_proc)

    progress.set_status("Waiting for Gateway...")
    gateway_ready = False
    for _ in range(60):
        time.sleep(0.5)
        try:
            req = urllib.request.urlopen(
                f"http://127.0.0.1:{GATEWAY_PORT}", timeout=2)
            req.close()
            gateway_ready = True
            break
        except Exception:
            if gateway_proc.poll() is not None:
                raise RuntimeError("Gateway process exited unexpectedly")

    if not gateway_ready:
        progress.log("Gateway not responding yet, continuing anyway...", "warn")

    progress.set_status("Starting Node...")
    progress.log("Starting node host")

    node_proc = subprocess.Popen(
        [node_path, openclaw_js, "node", "run",
         "--host", "127.0.0.1", "--port", str(GATEWAY_PORT)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, env=env.copy(), creationflags=subprocess.CREATE_NO_WINDOW
    )
    progress._processes.append(node_proc)

    progress.set_done()
    progress.set_status("Running")
    console_url = f"http://127.0.0.1:{GATEWAY_PORT}?token={gateway_token}"
    progress.log(f"Gateway and Node are running. Console: http://127.0.0.1:{GATEWAY_PORT}", "success")
    progress.log("Close this window to stop all services.")
    webbrowser.open(console_url)

    def monitor():
        while progress._running:
            if gateway_proc.poll() is not None:
                progress.log("[WARNING] Gateway process exited", "warn")
                break
            if node_proc.poll() is not None:
                progress.log("[WARNING] Node process exited", "warn")
                break
            time.sleep(2)

    threading.Thread(target=monitor, daemon=True).start()


# ══════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════

def show_setup(prev=None):
    ctk.set_widget_scaling(1.0)
    dialog = SetupDialog(prev=prev)
    dialog.mainloop()
    result = dialog.result
    try:
        dialog.destroy()
    except Exception:
        pass
    return result


def show_progress(gateway_token, pending_skills):
    ctk.set_widget_scaling(1.0)
    progress = ProgressWindow()

    def background_task():
        try:
            node_path = find_node()
            if node_path is None:
                progress.log("Node.js not found. Downloading...", "warn")
                download_node(progress)
                node_path = find_node()
                if node_path is None:
                    raise RuntimeError("Failed to install Node.js")
            progress.log(f"Using Node.js: {node_path}", "accent")
            openclaw_js = find_openclaw(node_path)
            if openclaw_js is None:
                install_openclaw(progress)
                openclaw_js = find_openclaw(node_path)
            if openclaw_js is None:
                raise RuntimeError("Failed to find openclaw after install")
            progress.log(f"Using OpenClaw: {openclaw_js}", "accent")
            if pending_skills:
                install_skills(progress, pending_skills)
            start_services(progress, gateway_token)
        except Exception as e:
            progress.set_status("Error")
            progress.log(f"ERROR: {e}", "error")

    threading.Thread(target=background_task, daemon=True).start()
    progress.mainloop()
    reset = progress._reset_requested
    prev_settings = getattr(progress, '_previous_settings', None) if reset else None
    try:
        progress.destroy()
    except Exception:
        pass
    return reset, prev_settings


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    prev_settings = None
    while True:
        already_configured = CONFIG_FILE.exists() and NODE_CONFIG.exists()
        has_creds = any(
            f.name.endswith("-default.json")
            for f in (OPENCLAW_DIR / "credentials").glob("*-default.json")
        ) if (OPENCLAW_DIR / "credentials").exists() else False

        if not already_configured or not has_creds:
            result = show_setup(prev=prev_settings)
            prev_settings = None
            if result is None:
                sys.exit(0)
            gateway_token = create_config(
                result["api_key"], result["name"],
                result.get("model", DEFAULT_MODEL),
                result.get("channels", []),
                result.get("channel_tokens", {}))
            pending_skills = result.get("skills", [])
        else:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            gateway_token = cfg.get("gateway", {}).get("auth", {}).get(
                "token", generate_token())
            pending_skills = []

        reset, prev_settings = show_progress(gateway_token, pending_skills)
        if reset:
            continue
        else:
            break


if __name__ == "__main__":
    import traceback as _tb
    _log = Path.home() / ".openclaw" / "launcher-crash.log"
    try:
        _log.parent.mkdir(parents=True, exist_ok=True)
        main()
    except Exception:
        with open(_log, "w") as _f:
            _tb.print_exc(file=_f)
        raise

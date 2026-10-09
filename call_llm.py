"""LLM 调用：支持云端 Maas 与本地 vLLM（OpenAI 兼容 /v1）。

切换：config.yaml 里 llm.provider = maas | local
     或环境变量 LLM_PROVIDER=maas|local
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional

import yaml
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM
from langchain_core.outputs import GenerationChunk

ROOT = Path(__file__).resolve().parent

DEFAULT_MODEL = "qwen3.8-27b"
DEFAULT_CHAT_BASE_URL = (
    "https://llm-272z7g522or0uqy1.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
)
DEFAULT_LOCAL_BASE_URL = "http://10.0.113.3:8800/v1"
DEFAULT_LOCAL_MODEL = "/model"

_clients: dict[tuple[str, str], Any] = {}
_warmed_modes: set[str] = set()

# Qwen3 思考块：<think>...</think>
_THINK_BLOCK_RE = re.compile(r"<think>[\s\S]*?</think>", re.I)


@dataclass
class LLMResult:
    text: str
    ttft_s: float | None  # 流式：首条 content token；非流式：None
    total_s: float
    ttft_from_origin_s: float | None = None
    thinking_s: float | None = None  # 保留字段兼容；思考模式已关闭


def load_config(config_path: str | Path | None = None) -> dict:
    path = Path(config_path) if config_path else ROOT / "config.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _llm_provider(cfg: dict) -> str:
    env = (os.environ.get("LLM_PROVIDER") or "").strip().lower()
    if env in ("maas", "cloud", "api"):
        return "maas"
    if env == "local":
        return "local"
    raw = str((cfg.get("llm") or {}).get("provider") or "maas").strip().lower()
    if raw in ("local", "vllm"):
        return "local"
    return "maas"


def _normalize_openai_base(url: str) -> str:
    """requests 常用 .../v1/chat/completions；OpenAI SDK 只需 .../v1。"""
    u = (url or "").strip().rstrip("/")
    if u.endswith("/chat/completions"):
        u = u[: -len("/chat/completions")]
    return u


def _llm_settings(cfg: dict) -> dict:
    llm = cfg.get("llm", {}) or {}
    provider = _llm_provider(cfg)

    if provider == "local":
        local = llm.get("local") or {}
        base_url = _normalize_openai_base(
            os.environ.get("LOCAL_LLM_URL")
            or local.get("base_url")
            or local.get("url")
            or DEFAULT_LOCAL_BASE_URL
        )
        temperature = local.get("temperature", 0)
        if os.environ.get("LOCAL_LLM_TEMPERATURE") is not None:
            temperature = float(os.environ["LOCAL_LLM_TEMPERATURE"])
        return {
            "provider": "local",
            "api_key": (
                os.environ.get("LOCAL_LLM_API_KEY")
                or local.get("api_key")
                or "EMPTY"
            ),
            "chat_base_url": base_url,
            "model": (
                os.environ.get("LOCAL_LLM_MODEL")
                or local.get("model")
                or DEFAULT_LOCAL_MODEL
            ),
            "temperature": float(temperature),
            "timeout": float(
                os.environ.get("LOCAL_LLM_TIMEOUT")
                or local.get("timeout", 620)
            ),
            "enable_thinking": bool(local.get("enable_thinking", False)),
            "top_p": float(os.environ.get("LOCAL_LLM_TOP_P", local.get("top_p", 0.8))),
            "top_k": int(os.environ.get("LOCAL_LLM_TOP_K", local.get("top_k", 20))),
            "presence_penalty": float(
                os.environ.get(
                    "LOCAL_LLM_PRESENCE_PENALTY",
                    local.get("presence_penalty", 1.5),
                )
            ),
        }

    api_key = llm.get("api_key") or os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        raise RuntimeError("请在 config.yaml 配置 llm.api_key 或设置环境变量 DASHSCOPE_API_KEY")
    chat_base_url = llm.get("stream_base_url") or llm.get("base_url") or DEFAULT_CHAT_BASE_URL
    return {
        "provider": "maas",
        "api_key": api_key,
        "chat_base_url": chat_base_url,
        "model": llm.get("model", DEFAULT_MODEL),
        "temperature": llm.get("temperature", 0),
        "timeout": llm.get("timeout", 120),
        "enable_thinking": bool(llm.get("enable_thinking", False)),
        "top_p": None,
        "top_k": None,
        "presence_penalty": None,
    }


def _strict_openai_body() -> bool:
    """transformers serve 会 422 拒收非标准字段（enable_thinking / top_k 等）。"""
    server = (os.environ.get("LLM_SERVER") or "").strip().lower()
    return server in {"transformers", "hf"}


def _chat_extra_body(
    settings: dict,
    kwargs: dict[str, Any],
    *,
    enable_thinking: bool = False,
) -> dict[str, Any]:
    """组装 extra_body；默认关闭思考。关思考时不传 enable_thinking，避免网关误开。"""
    extra = dict(kwargs.pop("extra_body", {}) or {})
    if _strict_openai_body():
        # 只保留调用方显式传入的其它键；去掉 vLLM/Qwen 扩展字段
        for k in ("enable_thinking", "top_k", "chat_template_kwargs"):
            extra.pop(k, None)
        return extra
    enable = bool(enable_thinking)
    if settings.get("provider") == "local":
        # vLLM Qwen：chat_template_kwargs；部分网关也认顶层 enable_thinking
        ctk = dict(extra.get("chat_template_kwargs") or {})
        ctk["enable_thinking"] = enable
        extra["chat_template_kwargs"] = ctk
        if settings.get("top_k") is not None and "top_k" not in extra:
            extra["top_k"] = settings["top_k"]
        extra["enable_thinking"] = enable
        return extra
    # maas：仅在显式开启时写入；关闭则剔除，保持兼容模式干净
    if enable:
        extra["enable_thinking"] = True
    else:
        extra.pop("enable_thinking", None)
        ctk = dict(extra.get("chat_template_kwargs") or {})
        ctk.pop("enable_thinking", None)
        if ctk:
            extra["chat_template_kwargs"] = ctk
        else:
            extra.pop("chat_template_kwargs", None)
    return extra


def _apply_sampling(req: dict[str, Any], settings: dict) -> None:
    if settings.get("provider") != "local":
        return
    if settings.get("top_p") is not None and "top_p" not in req:
        req["top_p"] = settings["top_p"]
    if settings.get("presence_penalty") is not None and "presence_penalty" not in req:
        req["presence_penalty"] = settings["presence_penalty"]


def _strip_thinking(text: str) -> str:
    if not text:
        return text
    text = _THINK_BLOCK_RE.sub("", text)
    # 流式未凑齐完整块时：只保留最后一个结束标记之后
    end = "</think>"
    if end in text:
        text = text.split(end)[-1]
    return text.strip()


def _build_messages(system: str, prompt: str, *, json_mode: bool = False) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if system:
        content = system
        if json_mode:
            content += "\n只输出合法 JSON，不要 markdown。"
        messages.append({"role": "system", "content": content})
    elif json_mode:
        messages.append({"role": "system", "content": "只输出合法 JSON，不要 markdown。"})
    messages.append({"role": "user", "content": prompt})
    return messages


def _extract_message_text(message: Any) -> str:
    content = getattr(message, "content", None) or ""
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text") or block.get("content")
            else:
                text = getattr(block, "text", None) or getattr(block, "content", None)
            if text:
                parts.append(str(text))
        return _strip_thinking("\n".join(parts).strip())
    return _strip_thinking(str(content).strip())


def _get_client(base_url: str, api_key: str, timeout: float):
    key = (base_url, api_key)
    if key not in _clients:
        from openai import OpenAI

        _clients[key] = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)
    return _clients[key]


def _make_client(base_url: str, api_key: str, timeout: float):
    return _get_client(base_url, api_key, timeout)


def warmup_llm(
    cfg: dict | None = None,
    *,
    sync: bool = True,
    stream: bool = True,
    force: bool = False,
) -> dict[str, float]:
    """批量评测前预热模型，避免首条请求冷启动拉高耗时。"""
    cfg = cfg or load_config()
    report: dict[str, float] = {}
    provider = _llm_provider(cfg)
    # provider 变化时允许重新预热
    mode_prefix = f"{provider}:"

    if sync and (force or f"{mode_prefix}sync" not in _warmed_modes):
        t0 = time.perf_counter()
        responses_chat(
            "用户问题：空调什么牌子好？",
            cfg,
            system='你是品类分类器。只输出 JSON：{"category":"air_conditioner"}',
            json_mode=True,
        )
        report["sync_warmup_s"] = time.perf_counter() - t0
        _warmed_modes.add(f"{mode_prefix}sync")

    if stream and (force or f"{mode_prefix}stream" not in _warmed_modes):
        t0 = time.perf_counter()
        stream_chat(
            [{"role": "user", "content": "回复一个字：好"}],
            cfg,
        )
        report["stream_warmup_s"] = time.perf_counter() - t0
        _warmed_modes.add(f"{mode_prefix}stream")

    return report


def responses_chat_messages(
    messages: list[dict[str, Any]],
    cfg: dict | None = None,
    *,
    enable_thinking: bool = False,
    **kwargs: Any,
) -> LLMResult:
    """非流式；messages 可为多模态 content 列表。"""
    cfg = cfg or load_config()
    settings = _llm_settings(cfg)

    client = _make_client(settings["chat_base_url"], settings["api_key"], settings["timeout"])

    req: dict[str, Any] = {
        "model": settings["model"],
        "messages": messages,
        "temperature": settings["temperature"],
        "extra_body": _chat_extra_body(settings, kwargs, enable_thinking=enable_thinking),
    }
    _apply_sampling(req, settings)
    req.update(kwargs)

    t_start = time.perf_counter()
    response = client.chat.completions.create(**req)
    total_s = time.perf_counter() - t_start
    message = response.choices[0].message
    return LLMResult(text=_extract_message_text(message), ttft_s=None, total_s=total_s)


def responses_chat(
    prompt: str,
    cfg: dict | None = None,
    system: str = "",
    *,
    json_mode: bool = False,
    enable_thinking: bool = False,
    **kwargs: Any,
) -> LLMResult:
    """非流式：chat.completions.create（选表 / linking / JSON / 修复等）。"""
    messages = _build_messages(system, prompt, json_mode=json_mode)
    return responses_chat_messages(
        messages,
        cfg,
        enable_thinking=enable_thinking,
        **kwargs,
    )


def stream_chat(
    messages: list[dict[str, str]],
    cfg: dict | None = None,
    *,
    latency_origin: float | None = None,
    enable_thinking: bool = False,
    **kwargs: Any,
) -> LLMResult:
    """流式：chat.completions.create(stream=True)，首字时延只计 content。"""
    cfg = cfg or load_config()
    settings = _llm_settings(cfg)

    client = _make_client(settings["chat_base_url"], settings["api_key"], settings["timeout"])

    req: dict[str, Any] = {
        "model": settings["model"],
        "messages": messages,
        "temperature": settings["temperature"],
        "stream": True,
        "extra_body": _chat_extra_body(settings, kwargs, enable_thinking=enable_thinking),
    }
    _apply_sampling(req, settings)
    req.update(kwargs)

    t_start = time.perf_counter()
    ttft_s: float | None = None
    ttft_from_origin_s: float | None = None
    full_content = ""

    stream = client.chat.completions.create(**req)
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta

        if getattr(delta, "reasoning_content", None):
            continue

        content = getattr(delta, "content", None) or ""
        if not content:
            continue

        now = time.perf_counter()
        if ttft_s is None:
            ttft_s = now - t_start
            if latency_origin is not None:
                ttft_from_origin_s = now - latency_origin
        full_content += content

    total_s = time.perf_counter() - t_start
    return LLMResult(
        text=_strip_thinking(full_content),
        ttft_s=ttft_s,
        total_s=total_s,
        ttft_from_origin_s=ttft_from_origin_s,
    )


def call_llm(
    prompt: str,
    cfg: dict | None = None,
    system: str = "",
    json_mode: bool = False,
    *,
    stream: bool = False,
    latency_origin: float | None = None,
    enable_thinking: bool = False,
    **kwargs: Any,
) -> LLMResult:
    """统一入口：默认非流式；stream=True 时走 chat 流式（SQL 生成）。

    enable_thinking 默认 False（选表/linking/修复等保持关）。
    仅 Step6 SQL 生成按 config 显式传入。
    """
    kwargs.pop("enable_thinking", None)
    if stream:
        messages = _build_messages(system, prompt, json_mode=json_mode)
        return stream_chat(
            messages,
            cfg,
            latency_origin=latency_origin,
            enable_thinking=enable_thinking,
            **kwargs,
        )
    return responses_chat(
        prompt,
        cfg,
        system=system,
        json_mode=json_mode,
        enable_thinking=enable_thinking,
        **kwargs,
    )


def call_llm_json(
    prompt: str,
    cfg: dict | None = None,
    system: str = "",
    *,
    latency_origin: float | None = None,
) -> dict:
    result = call_llm(
        prompt,
        cfg,
        system=system,
        json_mode=True,
        stream=False,
        latency_origin=latency_origin,
    )
    raw = result.text
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            return json.loads(m.group())
        raise


class CustomLLM(LLM):
    """LangChain 封装（随 config provider 走 maas 或 local）。"""

    cfg: dict | None = None

    def __init__(self, verbose: bool = False, config_path: str | Path | None = None, **kwargs):
        super().__init__(verbose=verbose, **kwargs)
        object.__setattr__(self, "cfg", load_config(config_path))

    def generate_text_stream(
        self,
        messages: list[dict[str, str]],
        model_name: str | None = None,
        tools: list | None = None,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        cfg = dict(self.cfg or load_config())
        if model_name:
            provider = _llm_provider(cfg)
            if provider == "local":
                llm = {**(cfg.get("llm") or {}), "local": {**((cfg.get("llm") or {}).get("local") or {}), "model": model_name}}
                cfg = {**cfg, "llm": llm}
            else:
                cfg = {**cfg, "llm": {**cfg.get("llm", {}), "model": model_name}}
        extra = dict(kwargs)
        if tools is not None:
            extra["tools"] = tools
        if tool_choice is not None and tool_choice != "auto":
            extra["tool_choice"] = tool_choice
        result = stream_chat(messages, cfg, **extra)
        return {"content": result.text, "tool_calls": [], "timing": result}

    def complete(self, prompt: str) -> str:
        """单轮补全（与自建 CustomLLM.complete 同语义）。"""
        return call_llm(prompt, self.cfg, stream=False).text

    def _call(
        self,
        prompt: str,
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        return call_llm(prompt, self.cfg, stream=False, **kwargs).text

    def _stream(
        self,
        prompt: str,
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[GenerationChunk]:
        messages = _build_messages("", prompt)
        cfg = self.cfg or load_config()
        settings = _llm_settings(cfg)
        client = _make_client(settings["chat_base_url"], settings["api_key"], settings["timeout"])
        req: dict[str, Any] = {
            "model": settings["model"],
            "messages": messages,
            "temperature": settings["temperature"],
            "stream": True,
            "extra_body": _chat_extra_body(settings, dict(kwargs)),
        }
        _apply_sampling(req, settings)
        stream = client.chat.completions.create(**req)
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if getattr(delta, "reasoning_content", None):
                continue
            text = getattr(delta, "content", None) or ""
            if not text:
                continue
            gen = GenerationChunk(text=text)
            if run_manager:
                run_manager.on_llm_new_token(text, chunk=gen)
            yield gen

    @property
    def _identifying_params(self) -> dict[str, Any]:
        cfg = self.cfg or load_config()
        settings = _llm_settings(cfg)
        return {
            "provider": settings["provider"],
            "model_name": settings["model"],
            "base_url": settings["chat_base_url"],
        }

    @property
    def _llm_type(self) -> str:
        cfg = self.cfg or load_config()
        return f"{_llm_provider(cfg)}_compatible"


if __name__ == "__main__":
    cfg = load_config()
    settings = _llm_settings(cfg)
    print(f"provider={settings['provider']} model={settings['model']} url={settings['chat_base_url']}")

    sync = call_llm("9.9和9.11哪个大？", cfg=cfg)
    print(f"[sync] total={sync.total_s:.2f}s  {sync.text[:80]}")

    stream = call_llm("用一句话介绍广州", cfg=cfg, stream=True)
    ttft = stream.ttft_s if stream.ttft_s is not None else -1.0
    print(f"[stream] ttft={ttft:.2f}s total={stream.total_s:.2f}s  {stream.text[:80]}")

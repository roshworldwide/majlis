"""LLM adapter (Y.3172 M node): Ollama or deterministic templates.

* temperature 0, fixed seed, JSON-mode output validated against a pydantic
  schema; one repair retry; then the deterministic template fallback.
* Prompt-hash cache in ``cache/llm/``. ``replay=True`` (DEMO_MODE) reads only
  from the cache — instant, deterministic, offline. A cache miss in replay
  mode uses the template fallback and is logged as such.
* ``reasoning_trace`` fields are the model's explicit, structured rationale.
  MAJLIS never claims access to hidden chain-of-thought.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Callable, Type

import httpx
from pydantic import BaseModel, ValidationError

from majlis import config


class LLM:
    def __init__(self, provider: str = config.LLM_PROVIDER, model: str = config.LLM_MODEL, replay: bool = False,
                 base_url: str = config.OLLAMA_BASE_URL, num_ctx: int = 6144, num_predict: int = 700):
        self.provider = provider
        self.model = model
        self.replay = replay
        self.base_url = base_url.rstrip("/")
        self.num_ctx = num_ctx
        self.num_predict = num_predict
        self.stats = {"calls": 0, "cache_hits": 0, "live_calls": 0, "repairs": 0, "fallbacks": 0, "seconds": 0.0}
        config.LLM_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.model}" if self.provider != "none" else "none (deterministic templates)"

    def _key(self, system: str, prompt: str, schema: str) -> str:
        return hashlib.sha256(json.dumps([self.model, system, prompt, schema], ensure_ascii=False).encode()).hexdigest()

    def generate(self, system: str, prompt: str, schema: Type[BaseModel], fallback: Callable[[], dict[str, Any]],
                 tag: str = "") -> tuple[BaseModel, dict[str, Any]]:
        """Return (validated object, call metadata for the audit log)."""
        self.stats["calls"] += 1
        key = self._key(system, prompt, schema.__name__)
        meta: dict[str, Any] = {"model": self.label, "prompt_hash": key[:16], "tag": tag, "cache_hit": False,
                                "source": "", "repair": False}
        if self.provider == "none":
            meta["source"] = "template"
            self.stats["fallbacks"] += 1
            return schema.model_validate(fallback()), meta
        path = config.LLM_CACHE_DIR / f"{key}.json"
        if path.exists():
            cached = json.loads(path.read_text(encoding="utf-8"))
            meta.update(cache_hit=True, source=cached.get("source", "llm"), repair=cached.get("repair", False))
            self.stats["cache_hits"] += 1
            try:
                return schema.model_validate(cached["output"]), meta
            except ValidationError:
                pass
        if self.replay:
            meta["source"] = "template (replay cache miss)"
            self.stats["fallbacks"] += 1
            return schema.model_validate(fallback()), meta
        t0 = time.time()
        out, source, repaired = self._live(system, prompt, schema, fallback)
        self.stats["seconds"] += time.time() - t0
        meta.update(source=source, repair=repaired)
        path.write_text(json.dumps({"model": self.model, "tag": tag, "source": source, "repair": repaired,
                                    "output": out.model_dump()}, ensure_ascii=False, indent=1), encoding="utf-8")
        return out, meta

    def _live(self, system: str, prompt: str, schema: Type[BaseModel], fallback: Callable[[], dict[str, Any]]):
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        for attempt in range(2):
            try:
                raw = self._chat(messages)
                self.stats["live_calls"] += 1
                obj = schema.model_validate(json.loads(raw))
                return obj, "llm", attempt == 1
            except (ValidationError, json.JSONDecodeError) as exc:
                if attempt == 0:
                    self.stats["repairs"] += 1
                    messages = messages + [
                        {"role": "assistant", "content": raw if 'raw' in locals() else ""},
                        {"role": "user", "content": f"That output was invalid: {str(exc)[:400]}. Return ONLY a JSON object "
                                                    f"with exactly these keys: {list(schema.model_fields)}."},
                    ]
                    continue
            except Exception:
                break
        self.stats["fallbacks"] += 1
        return schema.model_validate(fallback()), "template (llm failed validation)", True

    def _chat(self, messages: list[dict[str, str]]) -> str:
        r = httpx.post(
            f"{self.base_url}/api/chat",
            json={"model": self.model, "messages": messages, "stream": False, "format": "json",
                  "options": {"temperature": 0, "seed": config.LLM_SEED, "num_ctx": self.num_ctx,
                              "num_predict": self.num_predict}},
            timeout=300,
        )
        r.raise_for_status()
        return r.json()["message"]["content"]

    def available(self) -> bool:
        if self.provider == "none":
            return True
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=3)
            return any(m.get("name", "").startswith(self.model.split(":")[0]) for m in r.json().get("models", []))
        except Exception:
            return False

"""
╔══════════════════════════════════════════════════════════════════════╗
║         TRISHULA LEDGER TRACE  —  TrishulaLedgerTrace               ║
║         Sovereign Wrapper: langfuse (self-hosted)                   ║
║         Doctrine: Rule 1 Micro-Receipt | Zero Cloud Egress          ║
║         Provides: @trace decorator for every ai_core module         ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import functools
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

# ── Doctrine Ledger path (Rule 1 — Primary) ───────────────────────────
LEDGER_PATH = Path(r"D:\Trishula-Infra\Swarm-Core\Ledger\trishula_ledger.jsonl")
TRACE_LOG   = Path(r"D:\Trishula-Infra\Swarm-Core\Ledger\trace_log.jsonl")
LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Langfuse self-hosted config ───────────────────────────────────────
LANGFUSE_HOST       = "http://localhost:3000"   # Self-hosted Docker instance
LANGFUSE_PUBLIC_KEY = "pk-lf-trishula-local"
LANGFUSE_SECRET_KEY = "sk-lf-trishula-local"


def _get_langfuse_client():
    """Return langfuse Langfuse client pointed at local instance."""
    try:
        from langfuse import Langfuse
        return Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST,
        )
    except Exception:
        return None  # Graceful degradation if langfuse server not running


def _write_local_trace(
    trace_id: str,
    module: str,
    function: str,
    input_preview: str,
    output_preview: str,
    latency_ms: float,
    status: str,
    token_estimate: int = 0,
) -> None:
    """
    Local JSONL trace log (Rule 1 secondary receipt).
    Fires regardless of whether the Langfuse server is running.
    """
    entry = {
        "trace_id": trace_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "module": module,
        "function": function,
        "input_preview": input_preview[:200],
        "output_preview": output_preview[:200],
        "latency_ms": round(latency_ms, 2),
        "status": status,
        "token_estimate": token_estimate,
        "doctrine": "Rule1:MicroReceipt|ZeroCloudEgress"
    }
    with open(TRACE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


class TrishulaLedgerTrace:
    """
    Sovereign observability and tracing layer.

    Provides:
    - @trace decorator for synchronous functions
    - @atrace decorator for async functions
    - Direct span creation for manual instrumentation
    - Local JSONL trace log (always fires, Rule 1 compliant)
    - Langfuse push (fires only if self-hosted server is running)
    - Zero cloud egress — all data stays on D:\\

    Usage:
        tracer = TrishulaLedgerTrace(module_name="TrishulaEVEngine")

        @tracer.trace
        def analyze(data):
            return result

        @tracer.atrace
        async def async_analyze(data):
            return result
    """

    def __init__(self, module_name: str = "TrishulaSwarm"):
        self.module_name = module_name
        self._lf = _get_langfuse_client()
        self._trace_count = 0

        if self._lf:
            print(f"[TrishulaLedgerTrace] ✅ Langfuse connected: {LANGFUSE_HOST}")
        else:
            print(f"[TrishulaLedgerTrace] ⚠  Langfuse offline — local trace only")

    def trace(self, func: Callable) -> Callable:
        """Decorator for synchronous functions."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            trace_id = str(uuid.uuid4())[:8]
            self._trace_count += 1
            t_start = time.perf_counter()
            status = "OK"
            result = None

            # Build input preview
            input_preview = str(args[:2])[:200] if args else str(kwargs)[:200]

            try:
                result = func(*args, **kwargs)
                output_preview = str(result)[:200] if result else ""
            except Exception as e:
                status = f"ERROR: {e}"
                output_preview = str(e)[:200]
                raise
            finally:
                latency_ms = (time.perf_counter() - t_start) * 1000

                # Local trace (always)
                _write_local_trace(
                    trace_id=trace_id,
                    module=self.module_name,
                    function=func.__name__,
                    input_preview=input_preview,
                    output_preview=output_preview,
                    latency_ms=latency_ms,
                    status=status,
                )

                # Langfuse push (if online)
                if self._lf:
                    try:
                        lf_trace = self._lf.trace(
                            name=f"{self.module_name}.{func.__name__}",
                            input=input_preview,
                            output=output_preview,
                            metadata={"trace_id": trace_id, "doctrine": "Rule1"},
                        )
                        self._lf.flush()
                    except Exception:
                        pass  # Never let trace failures break the main path

            return result
        return wrapper

    def atrace(self, func: Callable) -> Callable:
        """Decorator for async functions."""
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import asyncio
            trace_id = str(uuid.uuid4())[:8]
            self._trace_count += 1
            t_start = time.perf_counter()
            status = "OK"
            result = None
            input_preview = str(args[:2])[:200] if args else str(kwargs)[:200]

            try:
                result = await func(*args, **kwargs)
                output_preview = str(result)[:200] if result else ""
            except Exception as e:
                status = f"ERROR: {e}"
                output_preview = str(e)[:200]
                raise
            finally:
                latency_ms = (time.perf_counter() - t_start) * 1000
                _write_local_trace(
                    trace_id=trace_id,
                    module=self.module_name,
                    function=func.__name__,
                    input_preview=input_preview,
                    output_preview=output_preview,
                    latency_ms=latency_ms,
                    status=status,
                )
                if self._lf:
                    try:
                        self._lf.trace(
                            name=f"{self.module_name}.{func.__name__}",
                            input=input_preview,
                            output=output_preview,
                            metadata={"trace_id": trace_id, "async": True},
                        )
                        self._lf.flush()
                    except Exception:
                        pass

            return result
        return wrapper

    def span(
        self,
        name: str,
        input_data: Any = None,
        output_data: Any = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """Manual span creation for instrumentation inside functions."""
        trace_id = str(uuid.uuid4())[:8]
        _write_local_trace(
            trace_id=trace_id,
            module=self.module_name,
            function=name,
            input_preview=str(input_data)[:200] if input_data else "",
            output_preview=str(output_data)[:200] if output_data else "",
            latency_ms=0.0,
            status="SPAN",
        )
        return trace_id

    def stats(self) -> dict:
        """Return session trace statistics."""
        return {
            "module": self.module_name,
            "traces_this_session": self._trace_count,
            "trace_log": str(TRACE_LOG),
            "langfuse_online": self._lf is not None,
        }


# ── Module-level convenience tracer (import and use directly) ─────────
swarm_tracer = TrishulaLedgerTrace(module_name="TrishulaSwarm")


# ── Standalone test ───────────────────────────────────────────────────
if __name__ == "__main__":
    tracer = TrishulaLedgerTrace(module_name="TestModule")

    @tracer.trace
    def sample_function(x: int, y: int) -> int:
        time.sleep(0.05)
        return x + y

    result = sample_function(42, 58)
    print(f"Result: {result}")
    print(f"Stats: {tracer.stats()}")
    print(f"Trace log: {TRACE_LOG}")

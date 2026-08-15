# 🔱 Trishula-LedgerTrace

**Sovereign LLM Observability and Causal Tracing Layer**

Trishula-LedgerTrace is a zero-cloud observability wrapper built on [Langfuse](https://github.com/langfuse/langfuse). It provides `@trace` and `@atrace` decorators that wrap every AI module function — capturing token costs, latency, inputs, outputs, and causal chains locally — with optional push to a self-hosted Langfuse server.

**All data stays on your machine. Zero cloud egress by design.**

## Features

- 🎯 **`@trace` / `@atrace` decorators** — wrap any sync or async function instantly
- 📋 **Local JSONL micro-receipts** — always fires, regardless of Langfuse server status
- 🔗 **Langfuse integration** — push to self-hosted server when running (port 3000)
- ⚡ **Zero-overhead fallback** — trace failures never break the main execution path
- 📊 **Manual span creation** — instrument specific code blocks with `.span()`
- 🏠 **Zero cloud egress** — all trace data written to local filesystem only

## Quick Start

```bash
pip install trishula-ledgertrace
pip install langfuse
```

```python
from trishula_trace import TrishulaLedgerTrace

tracer = TrishulaLedgerTrace(module_name="MyAIEngine")

@tracer.trace
def analyze_pick(game_data: dict) -> dict:
    # Your AI logic here
    return {"prediction": "Chiefs -3.5", "confidence": 0.78}

@tracer.atrace
async def async_fetch(url: str) -> str:
    # Async function — also traced
    return "data"

# Every call is now traced automatically
result = analyze_pick({"home": "Chiefs", "away": "Bills"})
print(tracer.stats())
```

## Trace Output

Every traced call writes to `D:/Trishula-Infra/Swarm-Core/Ledger/trace_log.jsonl`:

```json
{
  "trace_id": "a3f9c1b2",
  "timestamp": "2026-08-15T03:00:00Z",
  "module": "MyAIEngine",
  "function": "analyze_pick",
  "input_preview": "{'home': 'Chiefs', 'away': 'Bills'}",
  "output_preview": "{'prediction': 'Chiefs -3.5', 'confidence': 0.78}",
  "latency_ms": 247.3,
  "status": "OK"
}
```

## Self-Hosted Langfuse

```bash
docker run -p 3000:3000 langfuse/langfuse
```

TrishulaLedgerTrace auto-detects Langfuse at `localhost:3000` on init.

## Requirements

- Python 3.10+
- `pip install langfuse` (optional for server push)

## License

MIT — see [LICENSE](LICENSE)

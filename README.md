# Symbolica 🧩

Deterministic, auditable **rule-engine** that converts YAML rules into a compact, hot-reloadable `rulepack.rpack` and evaluates them in milliseconds. Perfect for plugging deterministic decision logic into LLM-agent workflows (LangGraph, OpenAI function calling, etc.).

---

## ✨ Features

* 🚀 **Fast** – memory-mapped rulepack; sub-millisecond inference for typical packs.
* 🧮 **Deterministic & transparent** – every run returns a JSON trace (`compact`, `verbose`, or `debug`).
* 🛠 **CLI tooling** – lint, compile, run, infer, test, trace.
* 🔌 **Embeddable** – call from Python *or* spin up a tiny FastAPI micro-service.
* 🔄 **Hot-reload** – the runtime notices when `rulepack.rpack` changes and reloads in-place.

---

## 📦 Installation

```bash
pip install symbolica
```

Optional REST service:

```bash
pip install "symbolica[rest]"   # installs fastapi & uvicorn
```

---

## 🚀 Quick Start

```bash
# 1. Create a rule
mkdir symbolica_rules
cat > symbolica_rules/fraud.yaml <<'YAML'
rule:
  id: txn.high_amount
  if: "transaction_amount > 1000"
  then:
    set:
      decision_status: FRAUD_SUSPECTED
      reason: high_amount
YAML

# 2. Compile → rulepack.rpack
symbolica compile --rules symbolica_rules

# 3. Run local REST server
symbolica run --port 8080 &

# 4. Fire an inference request
curl -X POST localhost:8080/infer -d '{
  "facts":  {"transaction_amount": 1500},
  "agent":  "Default",
  "trace_level": "verbose"
}' | jq
```

Example **response** (truncated):

```json
{
  "verdict": {
    "decision_status": "FRAUD_SUSPECTED",
    "reason": "high_amount"
  },
  "trace": {
    "run_id": "6e9c…",
    "level": "verbose",
    "fired": [
      {
        "id": "txn.high_amount",
        "cond": "transaction_amount > 1000",
        "set": {
          "decision_status": "FRAUD_SUSPECTED",
          "reason": "high_amount"
        }
      }
    ]
  }
}
```

---

## 🔧 CLI Commands

| Command              | Description                               |
|----------------------|-------------------------------------------|
| `symbolica lint`     | Static schema & tab check for YAML rules. |
| `symbolica compile`  | YAML → `rulepack.rpack`.                  |
| `symbolica run`      | FastAPI server exposing `/infer`.         |
| `symbolica infer`    | One-shot inference on a JSON file.        |
| `symbolica test`     | Regression run on a dataset. *(stub)*     |
| `symbolica trace`    | Pretty-print stored trace files.          |

---

## 📁 Project Layout

```text
symbolica/             ← Python package
 ├─ compiler/          ← parse • lint • optimise • pack
 ├─ runtime/           ← loader • evaluator • trace • REST API
 ├─ cli/               ← Typer entry-points
 └─ registry/          ← agent rule-filters
symbolica_rules/       ← Your YAML rules
agent_registries/      ← Per-agent *.reg.yml
```

---

## 📈 Status & Roadmap

* Predicate-index & multi-level traces implemented.
* Next up: aggregates, temporal rules, Rete event mode, UI playground.

---

## 🛡 License

Licensed under the terms of the **Apache 2.0 License** – see `LICENSE` for details.
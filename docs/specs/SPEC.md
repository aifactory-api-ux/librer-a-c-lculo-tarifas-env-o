# SPEC.md

## 0. SCOPE CONSTRAINTS AND DOCUMENTED ASSUMPTIONS

This project is a **small, dependency-free Python library** that computes parcel shipping charges. There is **no web service, no HTTP API, no database, no message queue, no frontend, no container, and no cloud infrastructure**. The code generator MUST NOT create FastAPI/Flask apps, Dockerfiles, docker-compose files, Alembic migrations, ORMs, or `.tsx` files.

### 0.1 Truncation of the source requirement (READ CAREFULLY)

The authoritative user request provided in the project context is **truncated mid-token** at the end of the third bullet:

> `- shipping_c`

The complete text of that bullet was not supplied. The following facts are **explicit and unambiguous** in the supplied text and are therefore binding requirements:

1. The library lives at the path `src/shipping.py`.
2. It exposes `volumetric_weight(length_cm, width_cm, height_cm) -> Decimal`, computed as `length_cm * width_cm * height_cm / 5000`, rounded to 2 decimals with `ROUND_HALF_UP`; the worked example `30x20x10 -> Decimal("1.20")` is normative.
3. It exposes `billable_weight(actual_kg, length_cm, width_cm, height_cm) -> Decimal`, returning the greater of actual and volumetric weight, rounded **up** to the next multiple of `0.5` kg; examples `2.0 -> 2.0` and `2.01 -> 2.5` are normative; exceeding `30` kg raises `ValueError`.

The following assumption is made **solely to close the truncated bullet** and is recorded here so the generator implements exactly one interpretation:

**ASSUMPTION A-1 — third public function is `shipping_cost`.** The truncated name `shipping_c` is resolved to the function `shipping_cost`. Its signature is:

```python
shipping_cost(actual_kg, length_cm, width_cm, height_cm, *, base_fee, rate_per_kg) -> Decimal
```

- It computes `billable = billable_weight(actual_kg, length_cm, width_cm, height_cm)` and returns `base_fee + rate_per_kg * billable`, quantized to two decimal places with `ROUND_HALF_UP`.
- `base_fee` and `rate_per_kg` are **required keyword arguments with no default values**. No tariff constants, currency, taxes, surcharges, discounts, or zone tables are invented, because the source request specifies none. Callers supply the pricing parameters.
- `shipping_cost` propagates `ValueError` from `billable_weight` unchanged.

If the operator supplies the untruncated bullet later, only `shipping_cost` in `src/shipping.py` and the corresponding test cases in `tests/test_shipping.py` need to change; nothing else in this spec depends on it.

### 0.2 Explicit non-requirements (do NOT implement)

- No input validation for negative or zero dimensions or weights (the request specifies exactly one error condition: weight above 30 kg).
- No currency handling, rounding to minor units of a specific currency, taxes, fuel surcharges, insurance, or carrier-specific rate cards.
- No persistence, logging framework, retries, caching, or configuration loading.
- No `Decimal` context/precision mutation via `getcontext()`; use the default decimal context and per-call `quantize`.

---

## 1. TECHNOLOGY STACK

| Layer | Technology | Version constraint |
|---|---|---|
| Language | Python | `>= 3.9` (uses `from __future__ import annotations`, `Decimal` type hints) |
| Runtime dependencies | **None** (standard library only: `decimal`) | — |
| Decimal arithmetic | `decimal.Decimal`, `decimal.ROUND_HALF_UP`, `decimal.ROUND_CEILING` | stdlib |
| Test framework | `pytest` | `>= 7.0` |
| Test-path config | `[tool.pytest.ini_options] pythonpath = ["src"]` in `pyproject.toml` | pytest >= 7 |
| Build backend | `setuptools` via `pyproject.toml` (`py-modules = ["shipping"]`) | `setuptools >= 61` |
| Packaging | PEP 621 `pyproject.toml`, src layout | — |
| Lint/format | **Not required by the request** — do not add ruff/black/mypy config | — |

No third-party runtime package may be added to `dependencies`. `pytest` lives only under `[project.optional-dependencies] dev`.

---

## 2. DATA CONTRACTS

This is a pure-function library. There are no ORM entities, no tables, and no Pydantic models. The data contracts are the **function signatures, numeric types, and module-level constants**. Every numeric input and output is `decimal.Decimal` (except that inputs may also be `int`, `float`, or `str`, which are coerced — see §2.3).

### 2.1 Module-level constants (exact names, exact values)

```python
# src/shipping.py
from __future__ import annotations

from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

VOLUMETRIC_DIVISOR: Decimal = Decimal("5000")   # cm^3 per kg
WEIGHT_STEP_KG: Decimal = Decimal("0.5")        # billable rounding step
MAX_WEIGHT_KG: Decimal = Decimal("30")          # hard upper limit
VOLUME_QUANTUM: Decimal = Decimal("0.01")       # 2 dp for volumetric weight
WEIGHT_QUANTUM: Decimal = Decimal("0.1")        # 1 dp, matches "2.0" / "2.5" examples
MONEY_QUANTUM: Decimal = Decimal("0.01")        # 2 dp for shipping cost
```

### 2.2 Public functions — exact signatures and return types

```python
def volumetric_weight(length_cm, width_cm, height_cm) -> Decimal: ...
def billable_weight(actual_kg, length_cm, width_cm, height_cm) -> Decimal: ...
def shipping_cost(actual_kg, length_cm, width_cm, height_cm, *,
                  base_fee, rate_per_kg) -> Decimal: ...
```

All three have **positional** parameters in exactly the order shown. `shipping_cost` has two **keyword-only** parameters (`base_fee`, `rate_per_kg`) — enforced by the bare `*`.

### 2.3 Input coercion contract

A module-private helper `_to_decimal(value, name: str) -> Decimal` MUST be used for every numeric input:

- If `isinstance(value, Decimal)` → returned unchanged (never re-quantized, never cast through `float`).
- Otherwise → `Decimal(str(value))`. This guarantees `2.01` (a `float`) becomes `Decimal("2.01")`, not `Decimal("2.0100000000000000088817841970012523233890533447265625")`. **Casting through `float()` before `Decimal` is forbidden.**
- If `Decimal(str(value))` raises `decimal.InvalidOperation`, `TypeError`, or `ValueError`, re-raise as `ValueError(f"{name} must be a number, got {value!r}")`.

### 2.4 Output contracts

| Function | Return type | Quantum applied | Rounding mode |
|---|---|---|---|
| `volumetric_weight` | `Decimal` | `Decimal("0.01")` | `ROUND_HALF_UP` |
| `billable_weight` | `Decimal` | `Decimal("0.1")` | exact multiple of `0.5` via `ROUND_CEILING` (see §2.5) |
| `shipping_cost` | `Decimal` | `Decimal("0.01")` | `ROUND_HALF_UP` |

Functions MUST return `Decimal`, never `float`, never `int`, never `str`. Example: `volumetric_weight(30, 20, 10)` returns `Decimal("1.20")` (two decimal places, trailing zero preserved by `quantize`).

### 2.5 Exact algorithms (normative)

**`volumetric_weight`**

```python
length = _to_decimal(length_cm, "length_cm")
width  = _to_decimal(width_cm, "width_cm")
height = _to_decimal(height_cm, "height_cm")
volume = length * width * height                    # Decimal
raw = volume / VOLUMETRIC_DIVISOR                    # Decimal division
return raw.quantize(VOLUME_QUANTUM, rounding=ROUND_HALF_UP)
```

Worked example: `30 * 20 * 10 = 6000`; `6000 / 5000 = 1.2`; `.quantize(Decimal("0.01"), ROUND_HALF_UP)` → `Decimal("1.20")`. ✔
Half-up example: `15 * 15 * 15 = 3375`; `3375 / 5000 = 0.675`; → `Decimal("0.68")`.

**`billable_weight`** — ordered steps, each MUST happen in this order:

1. `actual = _to_decimal(actual_kg, "actual_kg")`
2. If `actual > MAX_WEIGHT_KG`: `raise ValueError(f"actual weight {actual} kg exceeds the maximum allowed weight of 30 kg")`
3. `volumetric = volumetric_weight(length_cm, width_cm, height_cm)` (already 2 dp)
4. `raw = actual if actual > volumetric else volumetric` — i.e. `max(actual, volumetric)`; **no** pre-rounding of `actual`
5. Round **up** to the next multiple of `WEIGHT_STEP_KG`:
   ```python
   steps = (raw / WEIGHT_STEP_KG).to_integral_value(rounding=ROUND_CEILING)
   rounded = (steps * WEIGHT_STEP_KG).quantize(WEIGHT_QUANTUM, rounding=ROUND_HALF_UP)
   ```
   `ROUND_CEILING` (toward +∞) is what makes `2.01 → 2.5` and keeps an exact multiple unchanged: `2.0 / 0.5 = 4` → `to_integral_value(ROUND_CEILING) = 4` → `4 * 0.5 = 2.0` → `Decimal("2.0")`. ✔
   **`ROUND_HALF_UP` must NOT be used for this step** — it would map `2.01` to `2.0` and violate the requirement.
6. If `rounded > MAX_WEIGHT_KG`: `raise ValueError(f"billable weight {rounded} kg exceeds the maximum allowed weight of 30 kg")` (this triggers when the *volumetric* weight is the offending value, e.g. actual `1.0` with a volumetric weight of `31.00`).
7. `return rounded`

Boundary: `actual_kg == Decimal("30")` with small dimensions → step 2 passes (not `>`), result `Decimal("30.0")` — allowed. `actual_kg == Decimal("30.1")` → `ValueError`.

**`shipping_cost`** (Assumption A-1)

```python
billable = billable_weight(actual_kg, length_cm, width_cm, height_cm)   # may raise ValueError
fee  = _to_decimal(base_fee, "base_fee")
rate = _to_decimal(rate_per_kg, "rate_per_kg")
total = fee + (rate * billable)
return total.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
```

`billable_weight` is called exactly once. The `ValueError` from it propagates unchanged (no wrapping, no re-raise with a different message).

### 2.6 `__all__`

```python
__all__ = [
    "VOLUMETRIC_DIVISOR",
    "WEIGHT_STEP_KG",
    "MAX_WEIGHT_KG",
    "VOLUME_QUANTUM",
    "WEIGHT_QUANTUM",
    "MONEY_QUANTUM",
    "volumetric_weight",
    "billable_weight",
    "shipping_cost",
]
```

Module docstring (one line, Spanish or English — pick English): `"""Parcel shipping rate calculation helpers."""`

---

## 3. API ENDPOINTS

**None.** This is an in-process Python library consumed via `import shipping`. There are no HTTP, gRPC, GraphQL, CLI, or webhook surfaces, no route handlers, no request/response schemas, no `/metrics`, and no `/health` endpoint. Creating any of these would violate scope traceability. The only callable surface is the Python API defined in §2 and §6.

---

## 4. FILE STRUCTURE

```
.
├── pyproject.toml            # PEP 621 metadata, zero runtime deps, pytest pythonpath=["src"]
├── README.md                 # short usage example for the three functions
├── .gitignore                # __pycache__/, *.pyc, .pytest_cache/, .venv/, dist/, build/, *.egg-info/
├── src/
│   └── shipping.py           # the entire library: constants, _to_decimal, 3 public functions
└── tests/
    └── test_shipping.py      # pytest suite covering every normative example and boundary
```

No `src/__init__.py` is required: `src` is used only as a `pythonpath` root (`pythonpath = ["src"]`), making `import shipping` resolve to `src/shipping.py`. Do **not** create `src/__init__.py`.

### 4.1 FILE: `pyproject.toml` (content contract)

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "shipping"
version = "0.1.0"
description = "Small Python library to compute parcel shipping rates."
requires-python = ">=3.9"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=7.0"]

[tool.setuptools]
package-dir = {"" = "src"}
py-modules = ["shipping"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

### 4.2 FILE: `tests/test_shipping.py` (required cases)

The test file imports `from decimal import Decimal` and `import pytest`, and `from shipping import volumetric_weight, billable_weight, shipping_cost`. It MUST contain at least these tests, each asserting `isinstance(result, Decimal)` **and** value equality:

| Test name | Inputs | Expected |
|---|---|---|
| `test_volumetric_weight_worked_example` | `(30, 20, 10)` | `Decimal("1.20")` |
| `test_volumetric_weight_returns_decimal_with_two_places` | `(30, 20, 10)` | `str(result) == "1.20"` |
| `test_volumetric_weight_rounds_half_up` | `(15, 15, 15)` → `0.675` | `Decimal("0.68")` |
| `test_volumetric_weight_accepts_decimal_and_str_inputs` | `(Decimal("30"), "20", Decimal("10.0"))` | `Decimal("1.20")` |
| `test_billable_weight_exact_multiple_unchanged` | `(2.0, 10, 10, 10)` | `Decimal("2.0")` |
| `test_billable_weight_rounds_up_to_next_half_kilo` | `(2.01, 10, 10, 10)` | `Decimal("2.5")` |
| `test_billable_weight_uses_volumetric_when_larger` | `(1.0, 30, 20, 10)` | `Decimal("1.5")` |
| `test_billable_weight_just_below_half_step_rounds_up` | `(2.49, 10, 10, 10)` | `Decimal("2.5")` |
| `test_billable_weight_allows_exactly_30_kg` | `(30, 10, 10, 10)` | `Decimal("30.0")` |
| `test_billable_weight_raises_when_actual_weight_exceeds_max` | `(30.1, 10, 10, 10)` | `pytest.raises(ValueError)` |
| `test_billable_weight_raises_when_volumetric_exceeds_max` | `(1.0, 50, 60, 55)` → volum `33.00` | `pytest.raises(ValueError)` |
| `test_shipping_cost_applies_base_fee_and_rate` | `(2.0, 10, 10, 10, base_fee=Decimal("5.00"), rate_per_kg=Decimal("1.50"))` | `Decimal("8.00")` |
| `test_shipping_cost_uses_billable_weight` | `(2.01, 10, 10, 10, base_fee=Decimal("5.00"), rate_per_kg=Decimal("2.00"))` | `Decimal("10.00")` (billable `2.5`) |
| `test_shipping_cost_propagates_value_error` | `(31, 10, 10, 10, base_fee=..., rate_per_kg=...)` | `pytest.raises(ValueError)` |

`ValueError` assertions use `pytest.raises(ValueError)` only — do **not** pin the message text, so wording changes never break the suite.

### 4.3 PORT TABLE

**Not applicable.** No service listens on any port; there are no Dockerfiles and no `EXPOSE`/`CMD` directives.

### 4.4 SHARED MODULES

**Not applicable.** Single module `src/shipping.py`, imported directly via `pythonpath = ["src"]`.

---

## 5. ENVIRONMENT VARIABLES

**None.** The library reads no environment variables, configuration files, dotenv files, or secrets; it has no network calls. Do **not** create `.env.example`.

Documented explicitly to prevent generation of config plumbing:

| Variable | Type | Description | Example |
|---|---|---|---|
| — | — | No environment variables are defined or read. | — |

Test invocation requires no env vars: `python -m pytest` from the repository root.

---

## 6. IMPORT CONTRACTS

### 6.1 `src/shipping.py` exports

```python
from shipping import (
    volumetric_weight,   # (length_cm, width_cm, height_cm) -> Decimal
    billable_weight,     # (actual_kg, length_cm, width_cm, height_cm) -> Decimal
    shipping_cost,       # (actual_kg, length_cm, width_cm, height_cm, *, base_fee, rate_per_kg) -> Decimal
    VOLUMETRIC_DIVISOR,  # Decimal("5000")
    WEIGHT_STEP_KG,      # Decimal("0.5")
    MAX_WEIGHT_KG,       # Decimal("30")
    VOLUME_QUANTUM,      # Decimal("0.01")
    WEIGHT_QUANTUM,      # Decimal("0.1")
    MONEY_QUANTUM,       # Decimal("0.01")
)
```

### 6.2 Internal (private, not exported)

```python
from shipping import _to_decimal   # only used inside shipping.py; NOT in __all__
```

`_to_decimal` is an implementation detail. Tests MUST NOT import it; they exercise behaviour through the three public functions.

### 6.3 Consumer contract

Any consumer (including `tests/test_shipping.py`) imports with `import shipping` or `from shipping import <name>` and depends on: return type `decimal.Decimal`; `ValueError` for weights above 30 kg; keyword-only `base_fee`/`rate_per_kg` on `shipping_cost`. Consumers MUST NOT pass `base_fee` or `rate_per_kg` positionally — doing so raises `TypeError` by design.

---

## 7. FRONTEND STATE & COMPONENT CONTRACTS

**Not applicable.** There is no frontend, no React/Vue/Angular/Svelte code, no hooks, no components, and no shared UI state. No `.jsx`, `.tsx`, `.vue`, `.svelte`, `index.html`, or `package.json` file may be generated.

---

## 8. FILE EXTENSION CONVENTION

- **Project language:** Python only.
- **File extensions:** `.py` for all source and test files; `.toml` for `pyproject.toml`; `.md` for `README.md`.
- **No `.jsx` / `.tsx` / `.js` / `.ts` files exist in this project.** There is no JavaScript or TypeScript anywhere.
- **Entry point:** there is no application entry point and no `index.html`. The library entry module is `src/shipping.py`, imported as `shipping` because `pyproject.toml` sets `[tool.pytest.ini_options] pythonpath = ["src"]` (and, when installed, `py-modules = ["shipping"]` with `package-dir = {"" = "src"}`).
- **Test execution:** `python -m pytest` from the repository root.

---

## 9. DESIGN TOKENS

**Not applicable.** No UI/UX Design Implementation Contract was supplied and no user interface exists in scope; there is no `frontend/src/styles/tokens.ts` and no visual styling of any kind.

---

## 10. FUNCTIONAL REQUIREMENTS COVERAGE

| # | Requirement (from the request) | Implementation | Files |
|---|---|---|---|
| 1 | Small Python shipping-rate library | Single module, ~60 lines, stdlib only | `src/shipping.py` |
| 2 | Library lives at `src/shipping.py` | File path fixed; `pythonpath = ["src"]` makes `import shipping` resolve to it | `src/shipping.py`, `pyproject.toml` |
| 3 | `volumetric_weight(length_cm, width_cm, height_cm) -> Decimal` | Public function, exact name/parameter order, returns `Decimal` | `src/shipping.py` |
| 4 | Volumetric formula `length * width * height / 5000` | `(l * w * h) / VOLUMETRIC_DIVISOR` with `VOLUMETRIC_DIVISOR = Decimal("5000")` | `src/shipping.py` |
| 5 | Round volumetric to 2 decimals with `ROUND_HALF_UP` | `.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` | `src/shipping.py` |
| 6 | `30x20x10 -> Decimal("1.20")` | `6000/5000 = 1.2` → quantized `"1.20"`; asserted in test | `src/shipping.py`, `tests/test_shipping.py` |
| 7 | `billable_weight(actual_kg, length_cm, width_cm, height_cm) -> Decimal` | Public function, exact name/parameter order | `src/shipping.py` |
| 8 | Billable = greater of actual and volumetric | `max`-style ternary on raw `actual` vs `volumetric_weight(...)` result | `src/shipping.py` |
| 9 | Round billable **up** to next multiple of 0.5 kg | `(raw / WEIGHT_STEP_KG).to_integral_value(ROUND_CEILING) * WEIGHT_STEP_KG`, quantized to `0.1` | `src/shipping.py` |
| 10 | `2.0 -> 2.0` (no change for exact multiples) | Ceiling on an exact quotient is a no-op; asserted in test | `src/shipping.py`, `tests/test_shipping.py` |
| 11 | `2.01 -> 2.5` (round up, not half-up) | `ROUND_CEILING` step; `ROUND_HALF_UP` explicitly excluded from this step | `src/shipping.py`, `tests/test_shipping.py` |
| 12 | Weight above 30 kg raises `ValueError` | Guard on `actual_kg > MAX_WEIGHT_KG` **and** on the rounded result (volumetric-driven overflow) | `src/shipping.py` |
| 13 | `shipping_cost(...)` (bullets 1–2 verbatim; bullet 3 truncated → Assumption A-1) | `base_fee + rate_per_kg * billable_weight(...)`, keyword-only pricing args, 2 dp `ROUND_HALF_UP`, `ValueError` propagated | `src/shipping.py`, `tests/test_shipping.py` |
| 14 | Decimal-precise arithmetic (no binary-float drift) | All math in `decimal.Decimal`; inputs coerced via `Decimal(str(value))` | `src/shipping.py` |
| 15 | Behavioural tests for the stated examples and boundaries | 14-case pytest suite (§4.2) | `tests/test_shipping.py` |
| 16 | Zero third-party runtime dependencies | `dependencies = []`; only `decimal` imported | `pyproject.toml`, `src/shipping.py` |
| 17 | Installable/importable package metadata | PEP 621 `pyproject.toml` with `py-modules = ["shipping"]`, `package-dir = {"" = "src"}` | `pyproject.toml` |
| 18 | Usage documentation | `README.md` with one runnable example per function showing `Decimal` output for `30x20x10` | `README.md` |

### 10.1 Explicit exclusions (traceability guard)

No requirement in the supplied context mentions, and therefore the generator MUST NOT create: HTTP endpoints, servers, databases, ORMs, caches, tracing, metrics, dashboards, containers, CI pipelines, frontends, CLI argument parsers, logging configuration, i18n, retries, or carrier API integrations. Requirement 12 is the **only** specified error condition; do not add validation errors for negative or zero values. Requirement 13 is implemented strictly per Assumption A-1; if the untruncated bullet becomes available and contradicts it, that single function and its tests are revised — nothing else changes.
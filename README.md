# Nozle Python SDK

Backend-only Python SDK for Nozle billing, exact-decimal credits, Entity lifecycle,
ledger usage, margin intelligence, and LLM usage capture. Version 0.4.1 mirrors the
backend contract exposed by `@nozle-js/node` 0.4.1.

## Install

```bash
pip install nozle-sdk
```

Python 3.9 through 3.13 are supported. The package is typed and includes `py.typed`.

## Authentication

- `pk_` publishable keys may call only `plans()`.
- `sk_` secret keys are required for every customer read, mutation, event, credit,
  Entity, usage, and margin operation.
- Protected operations reject `pk_` locally before network I/O.

Keep secret keys on a trusted backend. This package is not a browser SDK.
When a request originates in a browser, authenticate it in your backend and derive the
Nozle `customer_id` from that authenticated user, team, or organization. Do not treat a
browser-supplied customer ID as authoritative.

```python
from nozle import Nozle

nozle = Nozle(
    api_key="sk_backend_...",
    base_url="https://api.nozle.ai",
    events_url="https://core.nozle.ai",
    timeout=15,
)
```

## Public namespaces

The client exposes `customers`, `credit_systems`, `credits`, `entities`, `usage`, and
`margin`.

### Plans and checkout

```python
plans = nozle.plans()

checkout = nozle.checkout(
    "customer-123",
    "pro",
    return_url="https://merchant.example/billing/complete",
)
```

Checkout can return any production transition shape:

- `{"type": "stripe", "client_secret": "..."}`
- `{"type": "stripe", "url": "https://..."}`
- `{"type": "completed", "status": "..."}`
- `{"type": "scheduled", "status": "..."}`

The deprecated `success_url=` argument remains an alias for `return_url=`. The SDK
never sends both fields and rejects conflicting values.

Backend subscription creation remains available with `nozle.subscribe(customer_id,
plan_code)`. Both checkout and subscription creation require an `sk_` key.

Cancellation is also backend-only. It defaults to end-of-period behavior, preserving
access until Nozle's authoritative billing boundary:

```python
result = nozle.cancel_subscription("customer-123", "subscription-123")
# result["subscription"]["status"] == "active"
# result["subscription"]["ending_at"] contains the scheduled boundary
```

Immediate termination must be explicit:

```python
nozle.cancel_subscription("customer-123", "subscription-123", policy="immediate")
```

### Customers and Credit Systems

```python
customer = nozle.customers.upsert(
    "customer-123",
    name="Acme",
    email="billing@example.com",
)

# Follows every active Core page and returns one normalized list.
systems = nozle.credit_systems.list()
```

### Customer and Entity credits

```python
balance = nozle.credits.get_balance("customer-123", "ai_credits")
balances = nozle.credits.list_balances("customer-123")
operations = nozle.credits.list_operations(
    "customer-123",
    credit_system_code="ai_credits",
    limit=50,
    cursor=None,
)

entity_balance = nozle.credits.get_entity_balance(
    "customer-123", "user-42", "ai_credits"
)
entity_balances = nozle.credits.list_entity_balances("customer-123", "user-42")
entity_operations = nozle.credits.list_entity_operations(
    "customer-123", "user-42", limit=50
)

allocation = nozle.credits.allocate(
    "customer-123",
    "user-42",
    credit_system_code="ai_credits",
    amount="100.000000000001",
    idempotency_key="allocation-user-42-v1",
)
```

Every credit amount is returned as a string and is never converted to `float`.
Allocation and deallocation amounts must be positive decimal strings with at most 12
decimal places. Mutation idempotency keys are mandatory and must fit within 255 UTF-8
bytes.

### Entities

```python
entity = nozle.entities.get("customer-123", "user-42")
page = nozle.entities.list("customer-123", status="active", limit=50)

result = nozle.entities.upsert(
    "customer-123",
    "user-42",
    status="active",
    name="Asha",
    metadata={"team": "support"},
    idempotency_key="entity-user-42-v1",
)

nozle.entities.suspend(
    "customer-123", "user-42", idempotency_key="suspend-user-42-v1"
)
nozle.entities.activate(
    "customer-123", "user-42", idempotency_key="activate-user-42-v1"
)

nozle.entities.bulk_upsert(
    "customer-123",
    [
        {"external_id": "user-42", "status": "active"},
        {"external_id": "user-43", "status": "suspended"},
    ],
    idempotency_key="entity-import-v1",
)
```

Entity IDs use UTF-8 byte limits, list limits are 1–100, and bulk upserts accept 1–500
unique Entity IDs.

### Ledger usage

`usage.check()` is advisory and does not mutate a balance. `usage.track()` atomically
records consumption and requires an idempotency key.

```python
preview = nozle.usage.check(
    "customer-123",
    "agent_execution",
    entity_id="user-42",
    credit_system_code="ai_credits",
    properties={"model": "gpt-5"},
    occurred_at="2026-07-20T12:00:00.750Z",
)

consumption = nozle.usage.track(
    "customer-123",
    "agent_execution",
    entity_id="user-42",
    properties={"model": "gpt-5"},
    timestamp="2026-07-20T12:00:00.750Z",
    idempotency_key="execution-123",
)
```

The SDK does not automatically retry mutation requests. Retry only with the same
idempotency key after deciding the failure is safe to retry.

## Existing operations

```python
nozle.track(
    "customer-123",
    "api_call",
    metadata={"tokens": 100},
    subscription_id="subscription-123",
)

entitlement = nozle.can("customer-123", "code_completion")
deduction = nozle.check_and_deduct("customer-123", "code_completion", credits=5)
health = nozle.ping()

summary = nozle.margin.summary()
by_customer = nozle.margin.by_customer()
trend = nozle.margin.trend(granularity="week")
```

If `track()` is called without `subscription_id`, the SDK resolves and caches the
customer's single active subscription through Core.

## OpenAI and Anthropic wrappers

Install an optional provider dependency:

```bash
pip install "nozle-sdk[openai]"
pip install "nozle-sdk[anthropic]"
```

```python
from openai import OpenAI
from nozle import Nozle, wrap_openai

nozle = Nozle("sk_backend_...")
openai = wrap_openai(
    OpenAI(),
    nozle,
    customer_id="customer-123",
    metric_code="llm_tokens",
    feature="assistant",
)

response = openai.chat.completions.create(
    model="gpt-5",
    messages=[{"role": "user", "content": "Hello"}],
)
```

Synchronous clients, asynchronous clients, synchronous streams, and asynchronous
streams are supported for OpenAI and Anthropic. The wrappers emit these event
properties:

- `model`
- `input_tokens`
- `output_tokens`
- `latency_ms`
- optional `feature`

Provider failures are propagated. If the provider succeeds but Nozle tracking fails,
the successful provider response or completed stream is preserved and a
`NozleTrackingWarning` is emitted without credential-bearing error details.

## Errors

`NozleAPIError` exposes `operation`, `status_code`, and credential-safe
`response_details`. Local contract failures use `NozleValidationError` or
`NozleAuthenticationError`; transport failures use `NozleTransportError`. Exception
messages redact API keys and secret-shaped response fields.

## License

AGPL-3.0-or-later

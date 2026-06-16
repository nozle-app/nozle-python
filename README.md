# Nozle

Python SDK for usage tracking, entitlement checks, margin intelligence, LLM cost capture, and billing management.

## Install

```bash
pip install nozle-sdk
```

## Quick Start

```python
from nozle import Nozle

client = Nozle(
    api_key="sk_live_...",
    base_url="https://api.nozle.ai",      # Default: http://localhost:8080
    events_url="https://lago.nozle.ai",    # Default: http://localhost:3000
    timeout=15,                             # Default: 10 (seconds)
)

# Track usage events
client.track("cust_123", "api_call", metadata={"model": "gpt-4o", "tokens": 1500})

# Check feature entitlements
result = client.can("cust_123", "advanced_analytics")

# Margin intelligence
summary = client.margin.summary()
```

## LLM Auto-Capture

Automatically extract model name, token counts, and latency from LLM API responses. No manual tracking needed — the SDK intercepts completions and calls `nozle.track()` for you.

Cost calculation happens server-side via the Go engine's cost model system.

### OpenAI

```bash
pip install nozle-sdk[openai]  # installs openai>=1.0
```

```python
from openai import OpenAI
from nozle import Nozle, wrap_openai

nozle = Nozle(api_key="sk_live_...")
openai = wrap_openai(
    OpenAI(),
    nozle,
    customer_id="cust_123",
    feature="code_completion",   # optional: tag for entitlement tracking
    metric_code="llm_tokens",    # optional: defaults to "llm_tokens"
)

# Use OpenAI normally — tracking happens automatically
response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}],
)

# Streaming works too
stream = openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}],
    stream=True,
)
for chunk in stream:
    pass  # usage is captured from the final chunk
```

### Anthropic

```bash
pip install nozle-sdk[anthropic]  # installs anthropic>=0.30.0
```

```python
from anthropic import Anthropic
from nozle import Nozle, wrap_anthropic

nozle = Nozle(api_key="sk_live_...")
anthropic = wrap_anthropic(
    Anthropic(),
    nozle,
    customer_id="cust_123",
    feature="code_completion",
)

# Use Anthropic normally
message = anthropic.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}],
)
```

Each tracked event sends `{ model, input_tokens, output_tokens, latency_ms, feature }` to the engine. The Go cost model system calculates `cost_cents` server-side.

## Usage Tracking

```python
# Basic tracking (auto-resolves subscription)
client.track("cust_123", "api_call", metadata={"tokens": 100})

# With explicit subscription
client.track("cust_123", "api_call", metadata={"tokens": 100}, subscription_id="sub_abc")

# With custom transaction ID and timestamp
client.track("cust_123", "api_call", metadata={"tokens": 100},
             transaction_id="tx_custom_123",
             timestamp="2025-01-15T10:30:00Z")
```

Subscription auto-resolution: if no `subscription_id` is provided, the SDK looks up the customer's active subscription and caches it for subsequent calls.

## Entitlement Checks

```python
result = client.can("cust_123", "code_completion")

if result["allowed"]:
    print(f"{result['remaining']} uses remaining")
else:
    print(f"Blocked: {result['reason']}")
```

Response includes cost intelligence:

```python
result["cost_per_use_cents"]    # Your cost per unit
result["revenue_per_use_cents"] # What you charge per unit
result["margin_per_use_cents"]  # Revenue minus cost
result["min_margin_percent"]    # Configured margin floor (if set)
```

## Credit Check & Deduct

Atomically check wallet balance and deduct credits in a single transaction. Uses row-level locking to prevent race conditions.

```python
result = client.check_and_deduct("cust_123", "code_completion", credits=5)

if result["allowed"]:
    print(f"Deducted. Remaining: {result['remaining']}")
else:
    print(f"Insufficient credits. Balance: {result['remaining']}")
```

## Customer Management

```python
# Create or update a customer
customer = client.customers.upsert("cust_123", name="Acme Corp", email="billing@acme.com")
```

## Health Check

```python
status = client.ping()
# {"ok": True, "engine": "ok"}
```

## Margin Intelligence

Requires a secret key (`sk_` prefix).

```python
client.margin.summary()                        # overall margin summary
client.margin.by_customer()                    # margin broken down by customer
client.margin.by_metric()                      # margin broken down by billable metric
client.margin.by_plan()                        # margin broken down by plan
client.margin.by_model()                       # margin broken down by AI model
client.margin.trend(granularity="day")         # margin trend over time
```

## Plans & Checkout

```python
# List available plans
plans = client.plans()

# Create checkout session (returns Stripe client_secret)
result = client.checkout("cust_123", "pro")
# {"client_secret": "...", "invoice_id": "...", "amount_cents": 2900, "currency": "USD"}

# With success URL
result = client.checkout("cust_123", "pro", success_url="https://example.com/done")

# Create subscription after payment
result = client.subscribe("cust_123", "pro")
# {"subscription_id": "...", "status": "active"}
```

## License

AGPL-3.0-or-later

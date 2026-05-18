# Nozle

Python SDK for usage tracking, margin intelligence, and entitlement checks.

## Install

```bash
pip install nozle-sdk
```

## Quick Start

```python
from nozle import Nozle

client = Nozle(
    api_key="your-api-key",
    base_url="https://api.your-domain.com",
    events_url="https://events.your-domain.com",
)

# Track usage events
client.track("customer_123", "api_call", metadata={"model": "gpt-4", "tokens": 1500})

# Check feature entitlements
result = client.can("customer_123", "advanced_analytics")

# Margin intelligence
summary = client.margin.summary()
by_customer = client.margin.by_customer()
by_model = client.margin.by_model()
trend = client.margin.trend(granularity="day")
```

## Margin Intelligence

The `margin` client exposes several views into your cost and revenue data:

```python
client.margin.summary()                        # overall margin summary
client.margin.by_customer()                    # margin broken down by customer
client.margin.by_metric()                      # margin broken down by billable metric
client.margin.by_plan()                        # margin broken down by plan
client.margin.by_model()                       # margin broken down by AI model
client.margin.trend(granularity="day")         # margin trend over time
```

## Optional: OpenAI Integration

```bash
pip install nozle-sdk-sdk[openai]
```

## License

AGPL-3.0-or-later

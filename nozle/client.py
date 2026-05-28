import requests

from nozle.can import can as _can
from nozle.margin import MarginClient
from nozle.track import track as _track


class Nozle:
    def __init__(self, api_key, base_url="http://localhost:8080", events_url="http://localhost:3000"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.events_url = events_url.rstrip("/")
        self.margin = MarginClient(self.base_url, self.api_key)
        self._sub_cache = {}

    def track(self, customer_id, event, metadata=None,
              subscription_id=None, transaction_id=None, timestamp=None):
        if not subscription_id:
            subscription_id = self._resolve_subscription(customer_id)
        _track(self.events_url, self.api_key, customer_id, event, metadata,
               subscription_id, transaction_id, timestamp)

    def can(self, customer_id, feature):
        return _can(self.base_url, self.api_key, customer_id, feature)

    def plans(self):
        res = requests.get(
            f"{self.base_url}/v1/plans",
            headers=self._headers(),
            timeout=10,
        )
        res.raise_for_status()
        return res.json().get("plans", [])

    def checkout(self, customer_id, plan_code, success_url=None):
        body = {
            "plan_code": plan_code,
            "customer_id": customer_id,
        }
        if success_url:
            body["success_url"] = success_url
        res = requests.post(
            f"{self.base_url}/v1/checkout",
            headers=self._headers(),
            json=body,
            timeout=10,
        )
        res.raise_for_status()
        return res.json()

    def subscribe(self, customer_id, plan_code):
        res = requests.post(
            f"{self.base_url}/v1/subscribe",
            headers=self._headers(),
            json={
                "plan_code": plan_code,
                "customer_id": customer_id,
            },
            timeout=10,
        )
        res.raise_for_status()
        return res.json()

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}"}

    def _resolve_subscription(self, customer_id):
        if customer_id in self._sub_cache:
            return self._sub_cache[customer_id]

        resp = requests.get(
            f"{self.events_url}/api/v1/subscriptions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            params={"external_customer_id": customer_id, "status[]": "active"},
            timeout=10,
        )
        resp.raise_for_status()
        subs = resp.json().get("subscriptions", [])

        if len(subs) == 0:
            raise ValueError(f"No active subscription for customer '{customer_id}'")
        if len(subs) > 1:
            raise ValueError(
                f"Customer '{customer_id}' has {len(subs)} active subscriptions — "
                f"specify subscription_id"
            )

        ext_id = subs[0]["external_id"]
        self._sub_cache[customer_id] = ext_id
        return ext_id

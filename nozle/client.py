import requests

from nozle.can import can as _can
from nozle.margin import MarginClient
from nozle.track import track as _track


class _CustomersNamespace:
    def __init__(self, base_url, api_key, timeout=10):
        self._base_url = base_url
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._timeout = timeout

    def upsert(self, external_id, name=None, email=None):
        body = {"external_id": external_id}
        if name is not None:
            body["name"] = name
        if email is not None:
            body["email"] = email
        res = requests.post(
            f"{self._base_url}/api/v1/customers",
            headers=self._headers,
            json=body,
            timeout=self._timeout,
        )
        res.raise_for_status()
        return res.json()


class Nozle:
    def __init__(self, api_key, base_url="http://localhost:8080", events_url="http://localhost:3000", timeout=10):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.events_url = events_url.rstrip("/")
        self.timeout = timeout
        self.margin = MarginClient(self.base_url, self.api_key, timeout=self.timeout)
        self.customers = _CustomersNamespace(self.base_url, self.api_key, timeout=self.timeout)
        self._sub_cache = {}

    def track(self, customer_id, event, metadata=None,
              subscription_id=None, transaction_id=None, timestamp=None):
        if not subscription_id:
            subscription_id = self._resolve_subscription(customer_id)
        _track(self.events_url, self.api_key, customer_id, event, metadata,
               subscription_id, transaction_id, timestamp, timeout=self.timeout)

    def can(self, customer_id, feature):
        return _can(self.base_url, self.api_key, customer_id, feature, timeout=self.timeout)

    def plans(self):
        res = requests.get(
            f"{self.base_url}/api/v1/plans",
            headers=self._headers(),
            timeout=self.timeout,
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
            f"{self.base_url}/api/v1/checkout",
            headers=self._headers(),
            json=body,
            timeout=self.timeout,
        )
        res.raise_for_status()
        return res.json()

    def subscribe(self, customer_id, plan_code):
        res = requests.post(
            f"{self.base_url}/api/v1/subscribe",
            headers=self._headers(),
            json={
                "plan_code": plan_code,
                "customer_id": customer_id,
            },
            timeout=self.timeout,
        )
        res.raise_for_status()
        return res.json()

    def ping(self):
        res = requests.get(
            f"{self.base_url}/api/v1/ping",
            headers=self._headers(),
            timeout=self.timeout,
        )
        res.raise_for_status()
        return res.json()

    def check_and_deduct(self, customer_id, feature, credits):
        res = requests.post(
            f"{self.base_url}/api/v1/check-and-deduct",
            headers=self._headers(),
            json={
                "customer_id": customer_id,
                "feature": feature,
                "credits": credits,
            },
            timeout=self.timeout,
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
            timeout=self.timeout,
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

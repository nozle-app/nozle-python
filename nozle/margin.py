import requests


class MarginClient:
    def __init__(self, basera_url, api_key):
        self._base = f"{basera_url}/v1/margin"
        self._headers = {"Authorization": f"Bearer {api_key}"}

    def _get(self, path, **params):
        resp = requests.get(
            f"{self._base}{path}",
            headers=self._headers,
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def summary(self, **params):
        return self._get("/summary", **params)

    def by_customer(self, **params):
        return self._get("/customers", **params)

    def by_metric(self, **params):
        return self._get("/metrics", **params)

    def by_plan(self, **params):
        return self._get("/plans", **params)

    def by_model(self, **params):
        return self._get("/models", **params)

    def trend(self, granularity="day", **params):
        return self._get("/trend", granularity=granularity, **params)

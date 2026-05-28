from unittest.mock import MagicMock, patch

from nozle import Nozle, __version__


def test_version():
    assert __version__ == "0.2.0"


def test_client_init():
    client = Nozle("test-key")
    assert client.api_key == "test-key"
    assert client.base_url == "http://localhost:8080"
    assert client.events_url == "http://localhost:3000"


def test_client_strips_trailing_slashes():
    client = Nozle("key", base_url="https://api.example.com/", events_url="https://events.example.com/")
    assert client.base_url == "https://api.example.com"
    assert client.events_url == "https://events.example.com"


@patch("nozle.track.requests.post")
def test_track_with_subscription(mock_post):
    client = Nozle("key")
    client.track("cust_1", "api_call", metadata={"tokens": 100}, subscription_id="sub_1")
    mock_post.assert_called_once()
    body = mock_post.call_args.kwargs["json"]["event"]
    assert body["external_customer_id"] == "cust_1"
    assert body["code"] == "api_call"
    assert body["external_subscription_id"] == "sub_1"
    assert body["properties"] == {"tokens": 100}


@patch("nozle.track.requests.post")
def test_track_generates_transaction_id(mock_post):
    client = Nozle("key")
    client.track("cust_1", "api_call", subscription_id="sub_1")
    body = mock_post.call_args.kwargs["json"]["event"]
    assert len(body["transaction_id"]) == 36


@patch("nozle.can.requests.get")
def test_can(mock_get):
    mock_get.return_value = MagicMock(json=lambda: {"allowed": True})
    client = Nozle("key")
    result = client.can("cust_1", "feature_x")
    assert result == {"allowed": True}
    mock_get.assert_called_once()


@patch("nozle.margin.requests.get")
def test_margin_summary(mock_get):
    mock_get.return_value = MagicMock(json=lambda: {"margin": 0.42})
    client = Nozle("key")
    result = client.margin.summary()
    assert result == {"margin": 0.42}


@patch("nozle.margin.requests.get")
def test_margin_by_customer(mock_get):
    mock_get.return_value = MagicMock(json=lambda: [{"customer": "c1", "margin": 0.5}])
    client = Nozle("key")
    result = client.margin.by_customer()
    assert result[0]["customer"] == "c1"


@patch("nozle.margin.requests.get")
def test_margin_trend(mock_get):
    mock_get.return_value = MagicMock(json=lambda: {"points": []})
    client = Nozle("key")
    client.margin.trend(granularity="week")
    _, kwargs = mock_get.call_args
    assert kwargs["params"]["granularity"] == "week"


@patch("nozle.client.requests.get")
def test_plans(mock_get):
    mock_get.return_value = MagicMock(
        json=lambda: {"plans": [{"code": "pro", "name": "Pro", "amount_cents": 2900}]}
    )
    client = Nozle("key")
    plans = client.plans()
    assert len(plans) == 1
    assert plans[0]["code"] == "pro"
    mock_get.assert_called_once_with(
        "http://localhost:8080/v1/plans",
        headers={"Authorization": "Bearer key"},
        timeout=10,
    )


@patch("nozle.client.requests.post")
def test_checkout(mock_post):
    mock_post.return_value = MagicMock(
        json=lambda: {
            "client_secret": "cs_test_123",
            "invoice_id": "inv_123",
            "amount_cents": 2900,
            "currency": "USD",
        }
    )
    client = Nozle("key")
    result = client.checkout("cust_1", "pro")
    assert result["client_secret"] == "cs_test_123"
    assert result["invoice_id"] == "inv_123"
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["json"]["customer_id"] == "cust_1"
    assert call_kwargs["json"]["plan_code"] == "pro"
    assert "success_url" not in call_kwargs["json"]


@patch("nozle.client.requests.post")
def test_checkout_with_success_url(mock_post):
    mock_post.return_value = MagicMock(json=lambda: {"client_secret": "cs_test_123"})
    client = Nozle("key")
    client.checkout("cust_1", "pro", success_url="https://example.com/done")
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["json"]["success_url"] == "https://example.com/done"


@patch("nozle.client.requests.post")
def test_subscribe(mock_post):
    mock_post.return_value = MagicMock(
        json=lambda: {"subscription_id": "sub_123", "status": "active"}
    )
    client = Nozle("key")
    result = client.subscribe("cust_1", "pro")
    assert result["subscription_id"] == "sub_123"
    assert result["status"] == "active"
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["json"]["customer_id"] == "cust_1"
    assert call_kwargs["json"]["plan_code"] == "pro"

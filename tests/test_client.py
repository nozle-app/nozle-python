from unittest.mock import MagicMock, patch

from nozle import Nozle, __version__


def test_version():
    assert __version__ == "0.1.0"


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

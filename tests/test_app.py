import pytest
from app import app, is_valid_ip


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_valid_ipv4():
    assert is_valid_ip("8.8.8.8") is True


def test_valid_ipv6():
    assert is_valid_ip("::1") is True


def test_invalid_ip_string():
    assert is_valid_ip("not-an-ip") is False


def test_invalid_ip_out_of_range():
    assert is_valid_ip("999.999.999.999") is False


def test_index(client):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "version" in data


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_valid_public_ip(client):
    resp = client.get("/ip/8.8.8.8")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ip"] == "8.8.8.8"
    assert data["version"] == "IPv4"
    assert data["is_private"] is False


def test_private_ip(client):
    resp = client.get("/ip/192.168.1.1")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["is_private"] is True


def test_loopback_ip(client):
    resp = client.get("/ip/127.0.0.1")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["is_loopback"] is True


def test_invalid_ip_route(client):
    resp = client.get("/ip/banana")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_ipv6_loopback(client):
    resp = client.get("/ip/::1")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["version"] == "IPv6"
    assert data["is_loopback"] is True

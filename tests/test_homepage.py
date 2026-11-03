def test_homepage_toont_prijzen(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "€375" in resp.text
    assert "€675" in resp.text
    assert "Automatisering" in resp.text

def test_create_user_and_duplicate_email(client):
    r = client.post("/users", json={"name": "  Anna  ", "email": "anna@example.com"})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Anna"  # пробелы по краям обрезаны
    assert body["id"] and body["created_at"]

    # тот же email -> 409, в том числе в другом регистре
    for email in ("anna@example.com", "ANNA@example.com"):
        dup = client.post("/users", json={"name": "Other", "email": email})
        assert dup.status_code == 409

    assert len(client.get("/users").json()) == 1


def test_user_validation(client):
    assert client.post("/users", json={"name": "   ", "email": "a@example.com"}).status_code == 422
    assert client.post("/users", json={"name": "A", "email": "not-an-email"}).status_code == 422


def test_get_user(client, make_user):
    user = make_user()
    assert client.get(f"/users/{user['id']}").json()["email"] == "ivan@example.com"
    assert client.get("/users/9999").status_code == 404

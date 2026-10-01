def test_delete_project_deletes_its_tasks(client, make_project, make_task):
    doomed, kept = make_project("Doomed"), make_project("Kept")
    doomed_tasks = [make_task(doomed["id"], f"t{i}") for i in range(3)]
    kept_task = make_task(kept["id"], "stay")

    r = client.delete(f"/projects/{doomed['id']}")
    assert r.status_code == 204
    assert r.content == b""

    assert client.get(f"/projects/{doomed['id']}").status_code == 404
    for t in doomed_tasks:
        assert client.get(f"/tasks/{t['id']}").status_code == 404
    assert client.get("/tasks", params={"project_id": doomed["id"]}).json()["total"] == 0

    # задачи другого проекта не пострадали
    assert client.get(f"/tasks/{kept_task['id']}").status_code == 200
    assert client.get("/tasks").json()["total"] == 1
    assert client.delete(f"/projects/{doomed['id']}").status_code == 404


def test_update_project(client, make_project):
    p = make_project("Old", "desc")
    r = client.patch(f"/projects/{p['id']}", json={"name": "New"})
    assert r.status_code == 200
    assert r.json()["name"] == "New" and r.json()["description"] == "desc"

    r = client.patch(f"/projects/{p['id']}", json={"description": None})
    assert r.json()["description"] is None

    assert client.patch(f"/projects/{p['id']}", json={"name": "  "}).status_code == 422
    assert client.patch(f"/projects/{p['id']}", json={"name": None}).status_code == 422


def test_project_validation_and_404(client):
    assert client.post("/projects", json={"name": "  "}).status_code == 422
    assert client.get("/projects/9999").status_code == 404

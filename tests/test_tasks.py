from sqlalchemy import text


def test_create_task_and_get_by_id(client, make_project):
    project = make_project()
    r = client.post("/tasks", json={"title": "  Write tests ", "project_id": project["id"]})
    assert r.status_code == 201
    task = r.json()
    assert task["title"] == "Write tests"
    assert task["status"] == "todo"  # значение по умолчанию
    assert task["assignee_id"] is None

    got = client.get(f"/tasks/{task['id']}")
    assert got.status_code == 200
    assert got.json() == task
    assert client.get("/tasks/9999").status_code == 404


def test_create_task_with_missing_project_or_assignee(client, make_project):
    r = client.post("/tasks", json={"title": "T", "project_id": 9999})
    assert r.status_code == 404

    project = make_project()
    r = client.post("/tasks", json={"title": "T", "project_id": project["id"], "assignee_id": 9999})
    assert r.status_code == 404
    # ничего не сохранилось
    assert client.get("/tasks").json()["total"] == 0


def test_task_validation(client, make_project):
    pid = make_project()["id"]
    assert client.post("/tasks", json={"title": "   ", "project_id": pid}).status_code == 422
    assert client.post("/tasks", json={"title": "T", "project_id": pid, "status": "wrong"}).status_code == 422


def test_filters_and_pagination_work_together(client, make_project, make_user, make_task):
    p1, p2 = make_project("P1"), make_project("P2")
    u1, u2 = make_user("U1", "u1@example.com"), make_user("U2", "u2@example.com")

    # P1: 5 задач todo у u1, 2 done у u1, 1 todo у u2. P2: 3 todo у u1.
    p1_todo_u1 = [make_task(p1["id"], f"a{i}", assignee_id=u1["id"]) for i in range(5)]
    for i in range(2):
        make_task(p1["id"], f"d{i}", status="done", assignee_id=u1["id"])
    make_task(p1["id"], "other", assignee_id=u2["id"])
    for i in range(3):
        make_task(p2["id"], f"b{i}", assignee_id=u1["id"])

    params = {"project_id": p1["id"], "status": "todo", "assignee_id": u1["id"]}
    page1 = client.get("/tasks", params={**params, "limit": 2, "offset": 0}).json()
    page2 = client.get("/tasks", params={**params, "limit": 2, "offset": 2}).json()
    page3 = client.get("/tasks", params={**params, "limit": 2, "offset": 4}).json()

    # total считается по фильтрам, до пагинации
    assert page1["total"] == page2["total"] == page3["total"] == 5
    assert (page1["limit"], page1["offset"]) == (2, 0)
    assert [len(p["items"]) for p in (page1, page2, page3)] == [2, 2, 1]

    # от новых к старым
    got_ids = [t["id"] for p in (page1, page2, page3) for t in p["items"]]
    assert got_ids == sorted((t["id"] for t in p1_todo_u1), reverse=True)

    # каждый фильтр по отдельности
    assert client.get("/tasks", params={"project_id": p2["id"]}).json()["total"] == 3
    assert client.get("/tasks", params={"status": "done"}).json()["total"] == 2
    assert client.get("/tasks", params={"assignee_id": u2["id"]}).json()["total"] == 1

    # значения по умолчанию и границы limit
    assert client.get("/tasks").json()["limit"] == 20
    assert client.get("/tasks", params={"limit": 101}).status_code == 422
    assert client.get("/tasks", params={"limit": 0}).status_code == 422
    assert client.get("/tasks", params={"offset": -1}).status_code == 422


def test_stable_order_when_created_at_equal(client, engine, make_project):
    pid = make_project()["id"]
    # Один INSERT -> у всех строк одинаковый created_at (now() = время начала транзакции)
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO tasks (title, project_id) VALUES ('a', :p), ('b', :p), ('c', :p)"),
            {"p": pid},
        )
    ids = [t["id"] for t in client.get("/tasks").json()["items"]]
    assert ids == sorted(ids, reverse=True)
    second = client.get("/tasks", params={"limit": 1, "offset": 1}).json()["items"][0]["id"]
    assert second == ids[1]


def test_partial_update_and_unassign(client, make_project, make_user, make_task):
    project, user = make_project(), make_user()
    task = make_task(
        project["id"], "Old", description="desc", assignee_id=user["id"],
        deadline="2030-01-01T10:00:00+00:00",
    )

    # меняем только статус; остальное не трогаем
    r = client.patch(f"/tasks/{task['id']}", json={"status": "in_progress"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "in_progress"
    assert body["title"] == "Old" and body["description"] == "desc"
    assert body["assignee_id"] == user["id"]
    assert body["updated_at"] >= task["updated_at"]

    # снимаем исполнителя и очищаем необязательные поля
    r = client.patch(f"/tasks/{task['id']}", json={"assignee_id": None, "deadline": None, "description": None})
    assert r.status_code == 200
    body = r.json()
    assert body["assignee_id"] is None and body["deadline"] is None and body["description"] is None
    assert body["status"] == "in_progress"  # не затронут

    # ошибки
    tid = task["id"]
    assert client.patch(f"/tasks/{tid}", json={"assignee_id": 9999}).status_code == 404
    assert client.patch(f"/tasks/{tid}", json={"title": None}).status_code == 422
    assert client.patch(f"/tasks/{tid}", json={"title": "  "}).status_code == 422
    assert client.patch(f"/tasks/{tid}", json={"status": "nope"}).status_code == 422
    assert client.patch("/tasks/9999", json={"title": "x"}).status_code == 404


def test_delete_task(client, make_project, make_task):
    task = make_task(make_project()["id"])
    assert client.delete(f"/tasks/{task['id']}").status_code == 204
    assert client.get(f"/tasks/{task['id']}").status_code == 404
    assert client.delete(f"/tasks/{task['id']}").status_code == 404

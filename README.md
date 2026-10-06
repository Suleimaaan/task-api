Task Manager API

REST API для управления пользователями, проектами и задачами.
**Стек:** Python 3.12, FastAPI, SQLAlchemy 2.x (sync), PostgreSQL 16, Alembic, pytest.

 Запуск

```bash
docker compose up -d db                
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                    
alembic upgrade head                    # миграции
uvicorn app.main:app --reload
```

Тесты
Нужна отдельная БД, имя которой заканчивается на `_test` (`TEST_DATABASE_URL`).
```bash
pytest
```
Перед тестами схема пересоздаётся **миграциями Alembic** (заодно проверяются сами миграции),
перед каждым тестом таблицы очищаются `TRUNCATE`. Если `TEST_DATABASE_URL` совпадает с рабочим
или не оканчивается на `_test`, pytest откажется стартовать — рабочие данные защищены.

Модель данных
| Таблица | Связи и ограничения |
|---|---|
| `users` | `email` UNIQUE |
| `projects` | — |
| `tasks` | `project_id` NOT NULL → `projects.id` **ON DELETE CASCADE**; `assignee_id` NULL → `users.id` ON DELETE SET NULL; `status` CHECK (`todo`/`in_progress`/`done`), по умолчанию `todo` |

`created_at`/`updated_at` заполняются в БД (`server_default now()`, `updated_at` обновляется при UPDATE через `onupdate`).
Идентификаторы — `integer` с автоинкрементом (проще и компактнее UUID; для тестового сервиса без внешней
репликации этого достаточно).

Индексы
- `users.email` — уникальный индекс: гарантирует уникальность и быстрый поиск.
- `tasks (project_id, status)` — основной сценарий «задачи проекта (со статусом)»; левый префикс покрывает и фильтр только по проекту, а также ускоряет каскадное удаление.
- `tasks (assignee_id)` — фильтр по исполнителю и операции с FK.
- `tasks (created_at DESC, id DESC)` — совпадает с сортировкой списка, ускоряет выдачу без фильтров.

Примеры запросов
```bash
curl -X POST localhost:8000/users    -H 'Content-Type: application/json' -d '{"name":"Anna","email":"anna@example.com"}'
curl -X POST localhost:8000/projects -H 'Content-Type: application/json' -d '{"name":"Website","description":"Redesign"}'
curl -X POST localhost:8000/tasks    -H 'Content-Type: application/json' -d '{"title":"Layout","project_id":1,"assignee_id":1,"deadline":"2026-12-01T12:00:00Z"}'

# фильтры + пагинация
curl 'localhost:8000/tasks?project_id=1&status=todo&assignee_id=1&limit=10&offset=0'

# частичное обновление: сменить статус и снять исполнителя
curl -X PATCH localhost:8000/tasks/1 -H 'Content-Type: application/json' -d '{"status":"done","assignee_id":null}'

curl -X DELETE localhost:8000/projects/1    # 204, задачи проекта удалены
```
Ответ `GET /tasks`: `{"items": [...], "total": 42, "limit": 10, "offset": 0}`.

Принятые решения
- **Синхронный SQLAlchemy.** Нагрузка — простые CRUD-запросы; синхронный код проще читать и тестировать. FastAPI выполняет sync-эндпоинты в пуле потоков, поэтому event loop не блокируется.
- **Сессия на запрос** (`get_db`): `commit()` вызывается явно в конце операции; при любой ошибке сессия закрывается и транзакция откатывается — частично сохранённых данных нет.
- **Гонки.** Уникальность email и внешние ключи гарантирует сама БД; `IntegrityError` при commit превращается в 409/404 с откатом.
- **PATCH** использует `model_dump(exclude_unset=True)`: отсутствующее поле не меняется, явный `null` очищает (`description`, `assignee_id`, `deadline`). Для `title`, `status`, `project_id`, `name` явный `null` → 422.
- **Стабильная сортировка:** `ORDER BY created_at DESC, id DESC`. `now()` в PostgreSQL — время начала транзакции, поэтому даты могут совпадать, а `id` делает порядок детерминированным (есть тест).
- `deadline` должен содержать часовой пояс (иначе 422); колонки — `timestamptz`.
- Email приводится к нижнему регистру.
- Статус хранится как `VARCHAR + CHECK`, а не нативный enum PostgreSQL — проще менять набор значений миграциями.

## Ограничения
- Нет авторизации, удаления/редактирования пользователей (не требовались).
- Пагинация `offset/limit` на больших смещениях медленнее keyset-пагинации.
- Списки пользователей и проектов ограничены `limit` (по умолчанию 100).

## Затраченное время
Примерно 10 часов: БД и миграции 2 ч, API 3 ч, тесты 3 ч, README и Docker 2 ч.



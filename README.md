# Sigma Intelligence

Прототип системы для автоматического обнаружения опасных событий в видео на основе VLM/LLM без специализированного обучения.

Поддерживаемые домены: **дорожные инциденты**, **производственные нарушения**, **драки и агрессивное поведение**.

---

## Быстрый старт

```bash
docker compose up --build
```

API: `http://localhost:8080`
Docs: `http://localhost:8080/docs`

---

## Стек

| Слой | Технологии |
|---|---|
| Backend | FastAPI, SQLAlchemy (async), Pydantic v2 |
| База данных | PostgreSQL (Docker) / SQLite (local) |
| VLM/LLM | self-hosted vLLM inference service |
| Контейнеризация | Docker, Docker Compose |

---

## Архитектура

```
Клиент
  │
  ├── POST /incidents/upload        загрузка видео
  │         │
  │         ├── сохранение файла на диск
  │         ├── создание записи в БД (status=SAVED)
  │         └── запуск фонового анализа → LLM
  │
  ├── GET  /incidents/{id}/status/stream   SSE: отслеживание статуса
  │         └── SAVED → PROCESSING → DONE
  │
  └── GET  /events/?incident_iid={id}      результаты с таймкодами
```

Анализ видео запускается сразу после сохранения файла без ручного старта.
LLM определяет домен сама, если он не был указан явно.

---

## Анализ

1. Видео отправляется в сервис (`POST /analyze_video`)
2. VLM нарезает видео на временные окна, описывает их
3. Определяет наличие событий, их тип, таймкоды, описание
4. Сервер сохраняет результат по таблицам в БД:
   - `incidents` — метаданные видео + статус
   - `timelines` — раскадровка по окнам
   - `events` — обнаруженные инциденты с таймкодами

---

## Основные эндпоинты

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/api/v1/incidents/upload` | Загрузить видео |
| `GET` | `/api/v1/incidents/{id}/status/stream` | SSE статус анализа |
| `GET` | `/api/v1/incidents/{id}` | Результат по инциденту |
| `GET` | `/api/v1/events/?incident_iid={id}` | События с таймкодами |
| `GET` | `/api/v1/timelines/?incident_iid={id}` | Раскадровка по окнам |
| `GET` | `/api/v1/incidents/{id}/media` | Стриминг видео (Range support) |
| `POST` | `/api/v1/incidents/{id}/search?prompt=...` | Текстовый поиск по таймлайну |
| `GET` | `/api/v1/incidents/{id}/report` | Скачать DOCX-отчёт |

---

## Формат ответа анализа

```json
{
  "has_event": true,
  "inferred_domain": "traffic",
  "events": [
    {
      "event_type": "NEAR_CRASH",
      "start_time": 7.36,
      "end_time": 8.86,
      "description": "Столкновение экскаватора и внедорожника на перекрёстке",
      "highlight": "7.36-8.86"
    }
  ]
}
```

---

## Устойчивость к пропускам

Короткие хайлайты могут занимать менее секунды, а при большом окне анализа llm усредняет их и может не заметить инцидент в исходном видео.

Если первый проход не нашел событий, бэкенд повторяет анализ с более агрессивными параметрами.

Если retry тоже не нашёл событий, запускается третий прогон: извлекает кадры из видео через OpenCV и отправляет их в `/generate`.

Все три прохода запускаются только при пустом результате предыдущего. Параметры настраиваются через `.env`:

```
LLM_WINDOW_SEC=1.5
LLM_TARGET_FPS=10
LLM_FRAMES_PER_WINDOW=5
LLM_MAX_HIGHLIGHTS=10
```

---

## Логирование

Каждый запуск анализа фиксирует в таблице `logs`:
- версию модели `model_version`
- версию промптов `prompt_version`
- временную метку каждого шага обработки

Полный JSON ответ LLM сохраняется в `incidents.analysis_json` — отчёт можно перегенерировать без повторного анализа.

---

## Локальный запуск без Docker

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

База SQLite создается автоматически при первом запуске (`sigma.db`).

ENV (`.env`):

```
DB_URL=sqlite+aiosqlite:///./sigma.db
```

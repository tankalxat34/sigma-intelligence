# Frontend Integration

URL: `http://localhost:8080/api/v1`

---

## Upload

### 1. Upload video

```
POST /incidents/upload
Content-Type: multipart/form-data

file: <binary>
domain: traffic | production | violence | other  (optional, omit for auto-detect)
```

Response:
```json
{
  "status": "OK",
  "data": {
    "incident_iid": 1,
    "status": "SAVED",
    "stream_url": "/api/v1/incidents/1/status/stream"
  }
}
```

incident_iid нужен для всех последующих запросов к этому инциденту, его хранить.

---

### 2. Следить за статусом

Открыть стрим после получения id `incident_iid`, что-то типа такого:

```js
const es = new EventSource(`/api/v1/incidents/${incidentId}/status/stream`)

es.onmessage = (e) => {
    const data = JSON.parse(e.data)
    // data.status: SAVED | PROCESSING | DONE | ERROR
    // при PROCESSING дополнительно: data.stage (1|2|3), data.stage_name

    if (data.status === 'PROCESSING' && data.stage) {
        // "Первичный анализ" / "Повторный анализ (мелкие окна)" / "Покадровый анализ"
        showProgress(`[${data.stage}/3] ${data.stage_name}`)
    }
    if (data.status === 'DONE') {
        es.close()
        // когда DONE можно запрашивать результаты
    }
    if (data.event === 'close') {
        es.close()
    }
}
```

Или закроется автоматически при `DONE` или `ERROR`.

**Стадии PROCESSING:**

| stage | stage_name | когда |
|-------|-----------|-------|
| 1 | Первичный анализ | всегда, первый запрос к LLM |
| 2 | Повторный анализ (мелкие окна) | если стадия 1 не нашла события — повтор с меньшими окнами |
| 3 | Покадровый анализ | если стадия 2 тоже не нашла — параллельный покадровый анализ |

Если событие найдено на стадии 1 или 2 — стадия 3 не запускается, сразу `DONE`.

---

### 3. результаты по инциденту

После `DONE`:

```
GET /incidents/{incident_iid}
```
```json
{
  "iid": 1,
  "has_event": true,
  "inferred_domain": "violence",
  "duration_sec": 16.3,
  "num_frames": 409,
  "num_windows": 12,
  "status": "DONE"
}
```

**Ивенты с таймкодами:**
```
GET /events/?incident_iid={incident_iid}
```
```json
[
  {
    "iid": 1,
    "event_type": "NEAR_CRASH",
    "start_time": 7.36,
    "end_time": 8.86,
    "confidence": 1.0,
    "description": "На перекрестке произошло столкновение ...",
    "highlight": "7.36-8.86"
  }
]
```

**Раскадровка по окнам для таймлайна:**
```
GET /timelines/?incident_iid={incident_iid}
```
```json
[
  {
    "window_idx": 0,
    "timestamp_sec": 0.08,
    "interval_end_sec": 6.5,
    "label": "SAFE_TRAFFIC",
    "has_event": false,
    "caption": "На перекрестке движутся автомобили...",
    "risk_score": 0.0,
    "event_type": "safe"
  }
]
```

---

### 4. Видео плеер

перемотка тоже должна работать:

```
GET /incidents/{incident_iid}/media
```

То есть можно как src в `<video>` или плеере.

Таймкоды для плеера из `GET /events/`:
- `start_time` и `end_time` - в секундах

---

### 5. Текстовый поиск

```
POST /incidents/{incident_iid}/search?prompt=столкновение
```

Вернет окна таймлайна, в описании которых есть слова из промпта:
```json
{
  "prompt": "столкновение",
  "total_windows": 12,
  "matches": 2,
  "results": [
    {
      "window_idx": 4,
      "timestamp_sec": 7.36,
      "interval_end_sec": 8.86,
      "caption": "...",
      "risk_score": 0.5,
      "event_type": "risk"
    }
  ]
}
```

---

### 6. Скачать отчет DOCX

200 только после `DONE`:

```
GET /incidents/{incident_iid}/report
```

Возвращает бинарник `.docx`. скачает как `report_1.docx`.

---

## Статусы инцидента

`PENDING` создан, ожидает
`UPLOADING` файл принимается
`SAVED` файл сохранился, анализ llm запускается
`PROCESSING` llm анализирует видео
`DONE` готово, результаты доступны
`ERROR` error

---

## Swagger

```
http://localhost:8080/docs
```

# NL-API Agent — минимальный AI-агент-обёртка над API (LangChain)

Клонирование: `git clone https://github.com/SID-mobile-dev/langchain-nl-api-agent.git`
(далее все команды выполняются из корня репозитория)

Прототип «natural-language SDK» для сервиса **Task tracker**: агент принимает запрос на
естественном языке, интерпретирует намерение, вызывает нужные API-методы через tool
и возвращает структурированный результат со статусом выполнения.

- **LLM**: Xiaomi MiMo, OpenAI-совместимый API (модель по умолчанию `xiaomi/mimo-v2.6-flash`).
- **API**: mock-сервис Task tracker (FastAPI) в этом же репозитории — 4 операции + статистика.
- **Tool**: один LangChain tool `api_tool` с параметром `operation`, внутри — реальный HTTP-вызов к API.

## Структура

```
LangChain/
├── main.py            # CLI-запуск агента: python main.py "<запрос>"
├── agent.py           # сборка агента (LangChain create_agent)
├── tools/
│   └── api_tool.py    # LangChain tool: операции API + HTTP-вызов + логирование
├── prompts/
│   └── system.md      # системный промпт (роль, границы, правила вызова tool)
├── mock_api/
│   └── server.py      # mock API Task tracker (FastAPI)
├── requirements.txt   # зафиксированные зависимости
├── .env.example       # шаблон конфигурации (секреты — только в .env)
└── runs/              # логи проверочных запусков
```

## Настройка (LLM)

Скопируйте шаблон конфигурации и заполните ключом провайдера:

```bash
cd langchain-nl-api-agent  # каталог, куда склонирован репозиторий
# если .env ещё нет — создайте из шаблона и впишите ключ:
cp .env.example .env
# вписать MIMO_API_KEY=<ваш ключ> (и при необходимости MIMO_MODEL / MIMO_BASE_URL)
# если .env УЖЕ существует — НЕ перезаписывайте его командой cp, иначе ключ затрётся
```

Переменные окружения (см. `.env.example`):

| Переменная | Назначение | Пример |
|---|---|---|
| `MIMO_API_KEY` | ключ LLM-провайдера (секрет, только в `.env`) | `sk-...` |
| `MIMO_BASE_URL` | базовый URL OpenAI-совместимого эндпоинта | `https://token-plan-sgp.xiaomimimo.com/v1` |
| `MIMO_MODEL` | модель | `xiaomi/mimo-v2.6-flash` |
| `API_BASE_URL` | адрес mock API | `http://127.0.0.1:8000` |

Секреты не коммитятся: `.env` добавлен в `.gitignore`, в репозитории только `.env.example`.

## Запуск

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 1) поднять mock API (отдельный терминал)
.venv/bin/uvicorn mock_api.server:app --port 8000

# 2) запустить агента с запросом на естественном языке
.venv/bin/python main.py "создай задачу 'купить хлеб'"
```

## Ручная проверка

**0. Подготовка** (если ещё не сделано):
```bash
cd langchain-nl-api-agent  # каталог, куда склонирован репозиторий
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# .env: если файла нет — cp .env.example .env и вписать MIMO_API_KEY=<ключ>;
# если .env уже есть — НЕ перезаписывайте его (ключ затрётся!)
```

**1. Терминал A — поднять mock API:**
```bash
.venv/bin/uvicorn mock_api.server:app --port 8000
```
Если порт занят (`[Errno 48] address already in use`) — сервер уже запущен, либо остановите старый процесс.
Проверка, что живой: `curl http://127.0.0.1:8000/health` → `{"status":"ok"}`.

**2. Терминал B — запросы к агенту** (по одному):

| # | Запрос | Ожидаемый вызов tool | Ожидаемый ответ |
|---|---|---|---|
| Q1 | `сколько задач в системе?` | `stats` | `Status: success` + статистика |
| Q2 | `создай задачу 'подготовить презентацию' с описанием 'к дедлайну в пятницу'` | `create_task` | `Status: success` + созданная задача |
| Q3 | `покажи задачу с id 2` | `get_task` | `Status: success` + задача |
| Q4 | `отметь задачу номер 2 как выполненную` | `update_task_status` | `Status: success` + `status: done` |
| Q5 | `покажи все незавершённые задачи` | `list_tasks` (фильтры) | `Status: success` + список |
| Q6 | `какая сейчас погода в Москве?` | НЕ вызывается | `Status: error`, запрос вне домена |
| Q7 | `удали все задачи` | НЕ вызывается | `Status: error`, операции нет |
| Q8 | `покажи задачу с id 999` | `get_task` | `Status: error`, `Errors: HTTP 404 ...` |

**3. На что смотреть:**
- строки `[api_tool] INFO -> ...` / `[api_tool] INFO <- ...` в консоли — реальные HTTP-вызовы к API (метод, URL, payload, код ответа); для Q6/Q7 их быть не должно;
- ответ агента — ровно 4 поля `Status:` / `Action:` / `Data:` / `Errors:` без лишнего текста;
- итоговое состояние API: `curl http://127.0.0.1:8000/stats` — цифры должны совпадать с ответами агента.

**4. Опционально — API и tool без LLM:**
```bash
curl -X POST http://127.0.0.1:8000/tasks -H 'Content-Type: application/json' -d '{"title":"тест"}'
curl http://127.0.0.1:8000/tasks/1
```

На свежем запущенном сервере id задач начинаются с 1, содержимое `Data` в ответах будет соответствующим — порядок операций тот же.

## Операции API (Task tracker)

| operation | Что делает | HTTP |
|---|---|---|
| `create_task` | создать задачу (title, описание) | `POST /tasks` |
| `get_task` | получить задачу по id | `GET /tasks/{id}` |
| `update_task_status` | обновить статус задачи | `PATCH /tasks/{id}` |
| `list_tasks` | список задач (фильтр по статусу) | `GET /tasks` |
| `stats` | статистика по задачам | `GET /stats` |

## Контракт ответа

Агент **всегда** отвечает фиксированным форматом (4 поля, в этом порядке):

```
Status: success | error
Action: <описание действия>
Data: <результат API>
Errors: <если есть, иначе пусто>
```

Правила контракта:

1. `Status` — только `success` или `error`.
2. `Action` — что именно сделано (например, `create_task`), человеческим языком.
3. `Data` — только реальные данные из ответа API-tool; выдумывать данные запрещено.
4. Если операция не выполнена — `Status: error`, в `Errors` причина.
5. Запросы вне границ ответственности (не про задачи Task tracker) агент отклоняет
   без вызова API, с `Status: error`.

# routes-reconcile

Скрипт синхронизирует маршруты на MikroTik для списка доменов (OpenAI/ChatGPT):
- резолвит `A`-записи доменов;
- добавляет отсутствующие `/32` маршруты через заданный gateway/interface;
- удаляет только свои устаревшие маршруты (по префиксу комментария `openai:`).

В Docker используется `supercronic`, запуск по cron: каждые 30 минут.
Базовый образ: `python:3.12-alpine`.

## Файлы

- `main.py` — основная логика синхронизации.
- `requirements.txt` — Python-зависимости.
- `Dockerfile` — образ приложения + `supercronic` + `dig`.
- `crontab` — расписание (`*/30 * * * *`).
- `compose.yml` — запуск через Docker Compose.
- `.env.example` — пример переменных окружения.

## Переменные окружения

Обязательные:
- `MT_HOST` — адрес MikroTik.
- `MT_USER` — пользователь API.
- `MT_PASS` — пароль API.

Опциональные:
- `MT_USE_SSL` — `true|false` (по умолчанию `true`).
- `MT_SSL_VERIFY` — `true|false` (по умолчанию `false`).
- `MT_PORT` — порт API (обычно `8729` для SSL, `8728` без SSL).
- `MT_WG_GW` — gateway/interface для маршрутов (по умолчанию `wg0`).
- `MT_DOMAINS` — домены через запятую.
- `MT_DRY_RUN` — `true|false` (если `true`, изменения не применяются).

Пример (`.env`):

```env
MT_HOST=192.168.88.1
MT_USER=routebot
MT_PASS=CHANGE_ME_LONG
MT_USE_SSL=true
MT_SSL_VERIFY=false
MT_PORT=8729
MT_WG_GW=wg0
MT_DOMAINS=api.openai.com,chat.openai.com,auth.openai.com,platform.openai.com,chatgpt.com,ios.chat.openai.com
MT_DRY_RUN=true
```

## Локальный запуск (разработка)

```bash
cd /Users/golovinps/PycharmProjects/routes-reconcile
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

`python-dotenv` подхватит `.env` автоматически, если файл существует.

## Запуск в Docker Compose

1. Подготовить переменные окружения в shell или через `.env` для Docker Compose.
2. Запустить:

```bash
docker compose -f compose.yml up -d --build
```

Логи:

```bash
docker compose -f compose.yml logs -f route-reconcile
```

Остановка:

```bash
docker compose -f compose.yml down
```

## Публикация образа в GHCR

Добавлен workflow: `/Users/golovinps/PycharmProjects/routes-reconcile/.github/workflows/docker-publish.yml`.

Он собирает и пушит multi-arch образ в GHCR:
- `linux/amd64`
- `linux/arm64`

Триггеры:
- push в `main`;
- push тега `v*` (например, `v1.0.0`);
- ручной запуск (`workflow_dispatch`).

Теги образа:
- `latest` (только для default branch);
- `sha-<commit>`;
- тег git-релиза (например, `v1.0.0`).

## Как работает cron

В контейнере стартует `supercronic` и читает `crontab`:

```cron
*/30 * * * * python /app/main.py
```

То есть синхронизация выполняется каждые 30 минут.

## Dry-run

Для безопасной проверки:

```env
MT_DRY_RUN=true
```

В логах будет план (`add/delete`) без реальных изменений на MikroTik.

## Troubleshooting

### `[Errno 61] Connection refused`

Обычно это сеть/порт:
- проверить `MT_HOST` и `MT_PORT`;
- убедиться, что API/API-SSL включены на MikroTik;
- проверить доступность порта с хоста, где запущен контейнер.

### `sslv3 alert handshake failure` на `8729`

Обычно проблема в `api-ssl`/сертификате на MikroTik.
Варианты:
- временно переключиться на обычный API: `MT_USE_SSL=false`, `MT_PORT=8728`;
- настроить сертификат для `api-ssl` и вернуть `8729`.

### Повторные добавления маршрутов

Скрипт сверяет `dst-address` со всеми текущими маршрутами и не должен дублировать существующие. 
Если видите повторные `add`, приложите логи со строками `all_routes`/`managed_routes`.

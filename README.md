# routes-reconcile

[![Docker Publish](https://github.com/31337Ghost/routes-reconcile/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/31337Ghost/routes-reconcile/actions/workflows/docker-publish.yml)
[![GHCR](https://img.shields.io/badge/GHCR-packages-blue)](https://github.com/31337Ghost/routes-reconcile/pkgs/container/routes-reconcile)
[![Platforms](https://img.shields.io/badge/platform-amd64%20%7C%20arm64-informational)](https://github.com/31337Ghost/routes-reconcile/actions/workflows/docker-publish.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)

Сервис синхронизирует маршруты на MikroTik для доменов OpenAI/ChatGPT.

Что делает:
- резолвит `A`-записи доменов;
- добавляет отсутствующие `/32` маршруты через заданный gateway/interface;
- удаляет только свои устаревшие маршруты (по комментарию `openai:*`);
- запускается по cron каждые 30 минут через `supercronic`.

База образа: `python:3.12-alpine`.

## Quick Start

1. Скопировать пример:

```bash
cp .env.example .env
```

2. Заполнить `MT_HOST`, `MT_USER`, `MT_PASS` в `.env`.

3. Запустить:

```bash
docker compose -f compose.yml up -d --build
```

4. Проверить логи:

```bash
docker compose -f compose.yml logs -f route-reconcile
```

## Репозиторий и образ

- Репозиторий: [github.com/31337Ghost/routes-reconcile](https://github.com/31337Ghost/routes-reconcile)
- GHCR package: [ghcr.io/31337ghost/routes-reconcile](https://github.com/31337Ghost/routes-reconcile/pkgs/container/routes-reconcile)

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

## Локальная разработка

```bash
cd /Users/golovinps/PycharmProjects/routes-reconcile
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

`python-dotenv` подхватывает `.env`, если файл существует.

## Docker Compose

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

## Cron

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

## Файлы проекта

- `main.py` — логика синхронизации.
- `requirements.txt` — Python-зависимости.
- `Dockerfile` — образ + `supercronic` + `dig`.
- `crontab` — расписание (`*/30 * * * *`).
- `compose.yml` — запуск через Docker Compose.
- `.env.example` — пример переменных окружения.

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

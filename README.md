# Платформа партнерских интеграций 

Это Backend-платформа для контроля партнерских интеграций в Мегамаркете с AI-помощником на GigaChat

![Python](https://img.shields.io/badge/Python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)
![Docker](https://img.shields.io/badge/Docker-ready-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## О проекте 

Платформа помогает отслеживать, как партнеры передают данные во внутренние системы компании: статусы загрузок,
обработка ошибок, история обмена, результаты проверок и технические сбои.

**Основаня задача:** снизить количество ручных сверок с партнерами и ускорить разбор проблемных интеграций 

### Кому помогает

- Менеджерам - видят все операции партнеров в одном месте
- Техподдержке - быстро разбирают ошибки без участия разработчиков 
- Техническим специалистам - получают полную историю и диагностику 

---

### Прием и обработка данных
- REST API для приема данных от партнеров 
- Двухуровневая валидация (Pydantic + кастомные проверки)
- Фоновая проверка через Celery + RabbitMQ
- Автоматический retry с экспоненциальной задержкой 
- Ручной retry с перепроверкой валидации 

### Работа с ошибками 
- Детализация ошибок по строкам и полям
- Стандартизированные коды ошибок
- AI-помощник на GigaChat - генерирует понятные объяснения для партнеров
- Кеширование LLM-ответов (24 часа)

### Управление и мониторинг
- Аутентификация через JWT с ролями (partner/manager/admin)
- Список операций с фильтрацией и пагинацией 
- Полная история статусов каждой операции 
- Кеширование статусов в Redis
- Мониторинг задач Celery через Flower
- Swagger/OpenAPI документация 

---

## Архитектура 

┌─────────────────────────────────────────────────────┐
│ Клиент │
│ (Партнёры, Менеджеры) │
└──────────────────────┬──────────────────────────────┘
↓
┌─────────────────────────────────────────────────────┐
│ Nginx │
│ (Reverse Proxy + Rate Limiting) │
└──────────────────────┬──────────────────────────────┘
↓
┌─────────────────────────────────────────────────────┐
│ FastAPI │
│ (REST API + JWT Auth) │
└────┬────────────────────────────────────┬───────────┘
↓ ↓
┌─────────────┐ ┌─────────────────┐
│ PostgreSQL │ │ Redis │
│ (основные │ │ (кеш статусов │
│ данные) │ │ + кеш LLM) │
└─────────────┘ └─────────────────┘
↓
┌─────────────────────────────────────────────────────┐
│ RabbitMQ │
│ (Очередь задач) │
└──────────────────────┬──────────────────────────────┘
↓
┌─────────────────────────────────────────────────────┐
│ Celery Worker │
│ (Фоновая обработка операций) │
└──────────────────────┬──────────────────────────────┘
↓
┌─────────────────────────────────────────────────────┐
│ GigaChat │
│ (AI-объяснения ошибок) │
└─────────────────────────────────────────────────────┘

---

## Стек технологий 

| Категория | Технологии |
|-----------|------------|
| **Язык** | Python 3.13 |
| **Web Framework** | FastAPI, Uvicorn |
| **Валидация** | Pydantic v2 |
| **ORM** | SQLAlchemy 2.0 (async) |
| **БД** | PostgreSQL 15 |
| **Миграции** | Alembic |
| **Кеш** | Redis 7 |
| **Очереди** | Celery, RabbitMQ 3 |
| **Аутентификация** | JWT (python-jose), passlib |
| **AI** | GigaChat (Sber) |
| **Мониторинг** | Flower |
| **Reverse Proxy** | Nginx |
| **Контейнеризация** | Docker, Docker Compose |
| **Логирование** | Loguru |

---

## 🚀 Быстрый старт

### Требования

- Docker Desktop (Windows/Mac) или Docker Engine (Linux)
- Git

### Установка и запуск

```bash
# 1. Клонировать проект
git clone https://github.com/kuzyahockey88/partner-integration-platform.git
cd partner-integration-platform

# 2. Создать .env файл
cp .env.example .env  # или создать вручную (см. ниже)

# 3. Запустить всё через Docker Compose
docker-compose up -d --build

# 4. Применить миграции
docker exec -it integration_api alembic upgrade head

# 5. Создать первого пользователя
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","email":"admin@example.com","password":"admin123","role":"admin"}'

Структура проекта 

partner-integration-platform/
├── services/
│   └── api/
│       └── app/
│           ├── api/v1/endpoints/   # REST-эндпоинты
│           ├── core/               # Config, Database
│           ├── models/             # SQLAlchemy модели
│           ├── schemas/            # Pydantic схемы
│           ├── services/           # Бизнес-логика
│           ├── validators/         # Валидаторы данных
│           ├── worker/             # Celery задачи
│           └── main.py             # Точка входа
├── alembic/                        # Миграции
├── nginx/                          # Конфигурация Nginx
├── scripts/                        # Скрипты запуска
├── tests/                          # Тесты
├── docker-compose.yml              # Оркестрация
├── Dockerfile                      # Сборка образа
└── requirements/                   # Зависимости

Ключевые технические решения:

Async everywhere: FastAPI + SQLAlchemy 2.0 + asyncpg для высокой производительности

Идемпотентность: external_request_id защищает от дублей

Optimistic Lock: поле version в модели защищает от гонок

Retry с backoff: экспоненциальная задержка (60с → 180с → ...)

Кеширование: 2 уровня — статусы (5 мин) + LLM-ответы (24 часа)

AI-friendly: fallback, если GigaChat недоступен

Мониторинг: structured logs + Flower + health checks

Автор
Илья Кузнецов 

GitHub: https://github.com/kuzyahockey88

Email: kuzyahockey88@mail.ru
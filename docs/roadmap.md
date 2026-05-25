# Дорожная карта (Roadmap)

Проект рассчитан на последовательное прохождение фаз. **Не переходите к следующей, пока не заработает текущая.**

---

## Критерии перехода между фазами

| Фаза | Критерий перехода |
|------|-------------------|
| 0 → 1 | Нарисована схема БД, написаны контракты API |
| 1 → 2 | MVP работает, размещены первые ордера, есть тесты |
| 2 → 3 | Все микросервисы в Docker, интеграционные тесты проходят |
| 3 → 4 | CI/CD зеленый, метрики собираются, нагрузка пройдена |

---

## Фаза 0: Подготовка и проектирование (1-2 дня)

**Цель:** понять предметную область и спроектировать контракты.

### Задачи
- [ ] Изучить базовые концепции: стакан, типы ордеров, матчинг.
- [ ] Изучить биржевую торговлю (не бинарные опционы): посмотреть стакан заявок на [Binance Spot](https://www.binance.com/ru/trade/BTC_USDT) или [TradingView](https://ru.tradingview.com/chart/), разобрать лимитные/рыночные ордера.
- [ ] Выбрать структуру репозитория (монорепо).
- [ ] Написать контракты (REST API, Protobuf, форматы событий Kafka) на бумаге.
- [ ] Нарисовать ER-диаграмму (User, Asset, Order, Trade, Portfolio).

### Теория для собеседований
- **REST API design:** ресурсы vs действия, idempotency, статусы HTTP.
- **API Versioning:** как версионировать (URL, headers).
- **Protobuf basics:** зачем бинарные протоколы, сравнение с JSON/REST.
- **Domain-Driven Design (DDD):** Entities, Value Objects, Aggregates. Order Book как aggregate.

### Архитектурные паттерны
- **Event Storming** (на бумаге): какие события происходят в системе (OrderPlaced, OrderMatched, TradeExecuted).
- **CQRS** (чтение vs запись): отдельные модели для торговли и аналитики.

### Вопросы с собеседований
- «Что такое идемпотентность? Где она нужна в торговой системе?»
- «Почему для матчинга лучше gRPC, а для клиента — REST/WebSocket?»
- «Объясните Price-Time Priority.»

---

## Фаза 1: MVP «Монолит» (2-3 недели)

**Цель:** работающий прототип в одном FastAPI-процессе. Включает авторизацию, котировки, платежи, Celery.

### Задачи

#### 1. Инфраструктура
- [ ] Инициализация проекта: `poetry`, структура каталогов.
- [ ] Docker Compose: PostgreSQL, Redis, RabbitMQ.
- [ ] Конфигурация: `pydantic-settings`, `.env`.

#### 2. Аутентификация и авторизация (JWT + Сессии)
- [ ] Регистрация пользователей (`POST /auth/register`).
- [ ] Логин через JWT (access + refresh tokens, RS256).
- [ ] **Бонус:** логин через сессии (cookie-based) для изучения обоих подходов.
- [ ] Эндпоинт `GET /users/me` (профиль, баланс).
- [ ] Middleware для проверки JWT на защищенных роутах.

**Почему оба подхода:**
- JWT — stateless, масштабируется горизонтально (проверка подписи без БД).
- Сессии — stateful, проще отозвать (хранятся в Redis), меньше attack surface.
- На собеседовании спросят разницу — нужно знать оба.

#### 3. Работа с котировками (REST API + WebSocket)
- [ ] Интеграция с внешним API котировок (Yahoo Finance, Alpha Vantage, Finnhub — выбрать один).
- [ ] Эндпоинт `GET /assets/{symbol}/quote` (текущая цена).
- [ ] Фоновая задача Celery: периодическое обновление цен (каждые 5 секунд).
- [ ] Кеширование в Redis (TTL 10 секунд).
- [ ] **Бонус:** WebSocket `/ws/quotes` для real-time стриминга цен.

**Почему REST + WebSocket:**
- REST — для запроса текущей цены (просто, кешируется).
- WebSocket — для real-time обновлений (пуши на клиент).
- На собеседовании: «Когда polling, когда WebSocket?»

#### 4. Платежная система (заглушка)
- [ ] Сервис `payment` (отдельный модуль в монолите).
- [ ] Эндпоинт `POST /deposits` (пополнение баланса).
- [ ] Эндпоинт `POST /withdrawals` (вывод средств).
- [ ] Интеграция с внешней платежной системой — **заглушка** (mock).
- [ ] Транзакционность: обновление баланса + запись в историю платежей.
- [ ] Идемпотентность: `Idempotency-Key` header.

**Почему заглушка:**
- Реальные платежи требуют договоров, PCI DSS, тестовые карты.
- Заглушка позволяет изучить паттерны (идемпотентность, транзакции, retry) без внешних зависимостей.
- На собеседовании: «Как бы вы интегрировали Stripe?» — обсуждаете webhooks, idempotency, retry.

#### 5. Order Service (торговля)
- [ ] Модели SQLAlchemy: `Asset`, `Order`, `Trade`, `Portfolio`.
- [ ] Миграции через Alembic.
- [ ] Эндпоинты:
  - `POST /orders/` — создание лимитного/рыночного ордера.
  - `GET /orders/` — история ордеров.
  - `GET /orders/{id}` — детали ордера.
- [ ] Валидация: проверка баланса перед созданием ордера.
- [ ] Простейший матчинг-движок в памяти (словари для стаканов, `asyncio.Lock`).

#### 6. WebSocket портфеля
- [ ] `/ws/portfolio` — real-time обновления портфеля.
- [ ] Подписка на Redis Pub/Sub.
- [ ] Рассылка обновлений при исполнении сделки.

#### 7. Celery + RabbitMQ
- [ ] Настройка Celery с брокером RabbitMQ.
- [ ] Задачи:
  - Обновление котировок (periodic task, каждые 5 сек).
  - Отправка email при исполнении ордера (mock).
  - Генерация дневного отчета (mock).
- [ ] Retry policy: 3 попытки с exponential backoff.
- [ ] Dead Letter Queue (DLQ) для ошибок.

**Почему RabbitMQ в монолите:**
- Для изучения. В реальном монолите можно обойтись asyncio tasks.
- Но RabbitMQ + Celery — стандартный стек для production. Нужно знать.
- На собеседовании: «Почему Celery, а не asyncio background tasks?»

#### 8. Фронтенд-заглушка
- [ ] Простой HTML с кнопками «Купить», «Продать».
- [ ] Таблица портфеля.
- [ ] Отображение стакана (mock данные).

### Best Practices (Фаза 1)
- **SQLAlchemy 2.0** с async (`async_session`, `select()`).
- **Pydantic v2** для валидации: `BaseModel`, `Field`, `validator`.
- **Dependency Injection:** `Depends()` в FastAPI для сервисов.
- **Repository Pattern:** отдельный класс `OrderRepository`, не пишите SQL в эндпоинтах.
- **Unit of Work:** транзакция охватывает создание ордера + обновление баланса.
- **Structlog** сразу: JSON-логи с `request_id`.
- **Configuration:** `pydantic-settings` + `.env`, никаких хардкод-конфигов.
- **Mypy** и `ruff` с первого дня.

### Теория для собеседований (Фаза 1)
- **ACID:** как обеспечить атомарность создания ордера и списания средств?
- **Индексы PostgreSQL:** какие индексы нужны для `SELECT * FROM orders WHERE user_id = ? AND status = ?`?
- **Asyncio:** event loop, coroutines, `asyncio.Lock` vs `asyncio.Semaphore`.
- **Redis data structures:** когда использовать Pub/Sub, Streams, Sorted Sets (ZSET для стакана!).
- **WebSocket протокол:** handshake, фреймы, почему не HTTP polling.
- **JWT vs Sessions:** stateless vs stateful, отзыв токенов, хранение refresh.
- **Celery:** acks_late, retry, DLQ, Flower.

### Вопросы с собеседований
- «Как обеспечить консистентность при создании ордера и списании денег?»
- «Почему WebSocket, а не SSE (Server-Sent Events)?»
- «Как работает asyncio.Lock? Чем отличается от threading.Lock?»
- «Нарисуйте схему БД для ордеров и сделок.»
- «Чем JWT отличается от сессий? Когда что использовать?»
- «Как работает идемпотентность в платежах?»
- «Зачем RabbitMQ, если можно asyncio.create_task?»

### Что писать в резюме после Фазы 1
- «Спроектировал доменную модель торговой системы (SQLAlchemy 2.0, Alembic).»
- «Реализовал in-memory matching engine с Price-Time Priority.»
- «Настроил real-time обновления через WebSocket + Redis Pub/Sub.»
- «Внедрил JWT (RS256) и сессионную авторизацию.»
- «Интегрировал внешнее API котировок с кешированием Redis.»
- «Реализовал заглушку платежной системы с идемпотентностью.»
- «Настроил Celery + RabbitMQ для фоновых задач с retry и DLQ.»

---

## Фаза 2: Микросервисы и настоящие данные (4-6 недель)

**Цель:** разбить монолит, подключить внешние котировки, внедрить gRPC и брокер.

### Задачи

#### 1. Выделить Account Service (Django)
- [ ] Настроить Django, DRF, JWT (RS256).
- [ ] Перенести модель `User` и эндпоинты `/auth/`, `/register/`.
- [ ] Сессионная авторизация (опционально, для изучения).
- [ ] Эндпоинт для проверки баланса (внутренний, для Order Service).

#### 2. Market Data Service (aiohttp)
- [ ] Подключиться к Binance WebSocket (real-time котировки).
- [ ] Сохранять цену в Redis.
- [ ] Публиковать тики в Kafka/Redis Streams.
- [ ] REST API для исторических данных.

#### 3. Выделить Matching Engine (gRPC)
- [ ] Описать `.proto` контракт.
- [ ] Реализовать сервер с полноценным движком (price-time priority).
- [ ] Подписать движок на тики из Kafka для активации рыночных ордеров.
- [ ] Гарантировать идемпотентность и конкурентный доступ (`asyncio.Lock`).

#### 4. Модифицировать Order Service (FastAPI)
- [ ] Заменить внутренний движок на gRPC-клиент.
- [ ] Реализовать Outbox-паттерн для гарантированной доставки.
- [ ] Интегрировать проверку JWT и баланса через Account Service.
- [ ] WebSocket `/ws/portfolio` для real-time обновлений.

#### 5. History & Analytics Service (FastAPI + GraphQL)
- [ ] Потребитель событий `TradeExecuted` из Kafka.
- [ ] Strawberry GraphQL эндпоинт `/graphql` для запросов истории.
- [ ] Агрегация данных (свечи, объемы).

#### 6. Notification Worker (Celery)
- [ ] Слушает события из Kafka (исполнение ордера).
- [ ] Отправка email (заглушка) при исполнении ордера.
- [ ] Push-уведомления (опционально).

#### 7. Payment Service (заглушка)
- [ ] Выделить в отдельный сервис.
- [ ] gRPC/REST API для пополнения/вывода.
- [ ] Интеграция с внешней системой — mock.
- [ ] События `PaymentProcessed` в Kafka.

### Best Practices (Фаза 2)
- **Outbox Pattern:** пишете событие в таблицу `outbox` в той же транзакции, что и ордер.
- **Saga Pattern** (упомянуть): компенсирующие транзакции.
- **Circuit Breaker:** при недоступности Matching Engine возвращать 503.
- **Idempotency Key:** клиент генерирует ключ, сервер проверяет.
- **JWT best practices:** RS256, короткий access token, refresh token в httpOnly cookie.
- **gRPC streaming:** server-side streaming для стакана.
- **Kafka:** topics (`orders.placed`, `trades.executed`), partitions по `asset_id`.

### Теория для собеседований (Фаза 2)
- **Микросервисы vs Монолит:** когда дробить, межсервисное взаимодействие.
- **CAP теорема:** что выбираете для матчинга (CP) и для аналитики (AP)?
- **Event-Driven Architecture:** eventual consistency, at-least-once delivery.
- **gRPC vs REST:** HTTP/2, multiplexing, protobuf, streaming.
- **Kafka fundamentals:** topics, partitions, consumer groups, offset, retention.
- **Celery:** acks_late, retry policy, dead letter queue.
- **GraphQL vs REST:** N+1 problem, DataLoader.

### Вопросы с собеседований
- «Как обеспечить надежность при отправке события в Kafka? (Outbox)»
- «Что будет, если Matching Engine упадет после списания денег? (Saga)»
- «Как масштабировать Matching Engine? (Шардирование по asset_id)»
- «Почему Kafka, а не RabbitMQ?»
- «Как работает JWT? Чем access отличается от refresh?»
- «Что такое Eventual Consistency? Где она в вашей системе?»

### Что писать в резюме после Фазы 2
- «Разделил монолит на микросервисы (Django, FastAPI, aiohttp).»
- «Внедрил gRPC для межсервисного взаимодействия с streaming.»
- «Настроил Event-Driven Architecture на Kafka с Outbox-паттерном.»
- «Реализовал авторизацию JWT (RS256) + интеграцию сервисов.»

---

## Фаза 3: Продакшен-инфраструктура (2-3 недели)

**Цель:** проект можно развернуть одной командой и наблюдать за ним.

### Задачи

#### 1. Docker
- [ ] Dockerfile для каждого сервиса (multi-stage build).
- [ ] `docker-compose.yml` с PostgreSQL, Redis, Kafka, RabbitMQ, Nginx, сервисами.
- [ ] Health checks для каждого сервиса (`/health`, `/ready`).

#### 2. CI/CD (GitHub Actions)
- [ ] Запуск линтеров (ruff, mypy) и тестов при пуше.
- [ ] Сборка и пуш Docker образов.
- [ ] Security scan (Trivy/Snyk).
- [ ] Matrix builds (Python 3.11, 3.12).

#### 3. Мониторинг
- [ ] Prometheus для сбора метрик.
- [ ] FastAPI instrumentator, кастомные метрики движка.
- [ ] Grafana дашборд: latency матчинга, количество ордеров в секунду.
- [ ] Alerting: latency > 100ms, ошибки > 1%.

#### 4. Логирование
- [ ] Structlog, JSON-логи.
- [ ] Grafana Loki для агрегации.
- [ ] Correlation ID (request_id) через все сервисы.

#### 5. Трейсинг
- [ ] OpenTelemetry автоинструментация FastAPI, gRPC.
- [ ] Jaeger для визуализации трейсов.
- [ ] Context propagation через сервисы.

#### 6. Нагрузочное тестирование
- [ ] Сценарий Locust: создание шквала лимитных ордеров.
- [ ] Замер latency матчинга (p50, p95, p99).
- [ ] Поиск bottleneck.

### Best Practices (Фаза 3)
- **Docker multi-stage:** builder stage → runtime stage (slim).
- **Health checks:** liveness (`/health`) и readiness (`/ready`).
- **Graceful shutdown:** обработка SIGTERM, закрытие соединений.
- **GitHub Actions:** кеширование `pip`/`poetry`, security scan.
- **Prometheus метрики:** counters, histograms, gauges.
- **Rate Limiting:** ограничение количества ордеров от одного пользователя.

### Теория для собеседований (Фаза 3)
- **Docker:** слои, кеширование, multi-stage, CMD vs ENTRYPOINT.
- **CI/CD:** blue-green deployment, feature flags, trunk-based development.
- **Observability:** метрики vs логи vs трейсы (three pillars).
- **Prometheus:** pull модель, типы метрик.
- **OpenTelemetry:** span, trace, context propagation.
- **Нагрузочное тестирование:** RPS, latency (p50, p95, p99), throughput.

### Вопросы с собеседований
- «Какие метрики вы мониторите в торговой системе?»
- «Что делать, если latency матчинга вырос в 10 раз?»
- «Как найти bottleneck в микросервисной архитектуре?»
- «Как обеспечить zero-downtime deployment?»
- «Что такое graceful shutdown и почему он важен?»

### Что писать в резюме после Фазы 3
- «Настроил CI/CD pipeline (GitHub Actions, Docker multi-stage).»
- «Внедрил observability: Prometheus + Grafana + Loki + Jaeger.»
- «Провел нагрузочное тестирование матчинга (Locust, 10k RPS).»
- «Обеспечил graceful shutdown и health checks для всех сервисов.»

---

## Фаза 4: Расширения (по желанию)

- [ ] Темная/светлая тема фронтенда.
- [ ] Алгоритмическая торговля (пользователь пишет Python-скрипт на сайте).
- [ ] Чат трейдеров.
- [ ] Мобильное приложение (React Native) с тем же API.

### Теория для собеседований (Фаза 4)
- **WebSocket scaling:** как масштабировать на несколько инстансов.
- **Rate limiting algorithms:** token bucket, leaky bucket, sliding window.
- **Security:** XSS, CSRF, SQL injection, rate limiting.

---

## Чек-лист перед собеседованием

- [ ] Я могу нарисовать архитектуру на доске за 2 минуты.
- [ ] Я могу объяснить, зачем каждый сервис существует.
- [ ] Я знаю, где в моем коде используется ACID, а где — eventual consistency.
- [ ] Я могу объяснить Outbox, Saga, Circuit Breaker на примере моей системы.
- [ ] Я знаю, как масштабировать Matching Engine (шардирование).
- [ ] Я провел нагрузочное тестирование и знаю bottleneck.
- [ ] У меня есть метрики (графики) и я могу показать их.
- [ ] Я могу объяснить разницу между p50, p95, p99 latency.
- [ ] Я знаю, как работает JWT и почему выбрал RS256.
- [ ] Я могу рассказать про observability (метрики, логи, трейсы).
- [ ] Я знаю разницу между JWT и сессиями.
- [ ] Я могу объяснить идемпотентность на примере платежей.
- [ ] Я знаю, зачем RabbitMQ + Celery, а не просто asyncio tasks.

---

## Советы по мотивации

- **Не пытайтесь сделать идеально с первого раза.** MVP должен быть грязным, но работающим.
- **Делайте коммиты каждый день.** Даже если это 10 строк.
- **Пишите тесты параллельно с кодом.** Это сложно, но на собеседованиях спрашивают TDD.
- **Если застряли — сделайте проще.** Лучше простой матчинг, чем никакого.
- **Покажите проект друзьям/ментору.** Обратная связь важнее перфекционизма.

---

**Главное правило:** не пишите код вслепую, а понимайте, почему вы делаете именно так.

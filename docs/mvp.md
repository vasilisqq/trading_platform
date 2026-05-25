# MVP: Детальный план монолита

**Цель:** работающий прототип в одном FastAPI-процессе за 2-3 недели.

**Включает:** авторизацию (JWT + сессии), котировки через REST API, заглушку платежей, RabbitMQ + Celery, matching engine в памяти.

---

## Архитектура MVP

```
┌─────────────┐
│   Клиент    │
│  (Браузер)  │
└──────┬──────┘
       │ HTTP/WS
┌──────▼──────┐
│  FastAPI    │
│   (монолит) │
│             │
│ ┌─────────┐ │
│ │  Auth   │ │  JWT + Sessions
│ │ (JWT)   │ │
│ └────┬────┘ │
│ ┌────▼────┐ │
│ │  Order  │ │  Matching Engine (in-memory)
│ │ Service │ │
│ └────┬────┘ │
│ ┌────▼────┐ │
│ │ Payment │ │  Заглушка платежей
│ │ Service │ │
│ └────┬────┘ │
│ ┌────▼────┐ │
│ │ Market  │ │  REST API котировок
│ │  Data   │ │
│ └────┬────┘ │
│ ┌────▼────┐ │
│ │ Celery  │ │  Фоновые задачи
│ │ Worker  │ │
│ └─────────┘ │
└──────┬──────┘
       │
┌──────┼──────┐
│      │      │
┌▼─────▼┐ ┌──▼───┐
│PostgreSQL│ │ Redis│
│         │ │Rabbit│
└─────────┘ └──────┘
```

---

## 1. Инфраструктура и настройка

### Структура проекта
```
services/
└── monolith/
    ├── src/
    │   ├── __init__.py
    │   ├── main.py              # Точка входа FastAPI
    │   ├── config.py            # Pydantic Settings
    │   ├── auth/                # Аутентификация
    │   │   ├── __init__.py
    │   │   ├── jwt_handler.py   # JWT encode/decode
    │   │   ├── session_handler.py # Session management
    │   │   ├── models.py        # User SQLAlchemy
    │   │   ├── schemas.py       # Pydantic схемы
    │   │   ├── router.py        # /auth/register, /auth/login
    │   │   └── dependencies.py  # get_current_user (JWT + Session)
    │   ├── orders/              # Торговля
    │   │   ├── __init__.py
    │   │   ├── models.py        # Order, Trade, Asset, Portfolio
    │   │   ├── schemas.py
    │   │   ├── router.py        # /orders/
    │   │   ├── repository.py    # Repository Pattern
    │   │   ├── matching_engine.py # In-memory matching
    │   │   └── service.py       # Бизнес-логика
    │   ├── market_data/         # Котировки
    │   │   ├── __init__.py
    │   │   ├── client.py        # HTTP клиент для API
    │   │   ├── service.py       # Кеширование, обновление
    │   │   └── router.py        # /quotes/
    │   ├── payments/            # Платежи (заглушка)
    │   │   ├── __init__.py
    │   │   ├── models.py        # Deposit, Withdrawal
    │   │   ├── schemas.py
    │   │   ├── router.py        # /deposits/, /withdrawals/
    │   │   └── service.py       # Идемпотентность, mock
    │   ├── websocket/           # WebSocket handlers
    │   │   ├── __init__.py
    │   │   ├── portfolio.py     # /ws/portfolio
    │   │   └── quotes.py        # /ws/quotes
    │   └── tasks/               # Celery задачи
    │       ├── __init__.py
    │       ├── quotes.py        # Периодическое обновление цен
    │       └── notifications.py # Email при исполнении ордера
    ├── alembic/                 # Миграции
    ├── tests/
    ├── Dockerfile
    ├── pyproject.toml
    └── .env.example
```

### Docker Compose
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: tradesim
      POSTGRES_USER: tradesim
      POSTGRES_PASSWORD: tradesim
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"

  app:
    build: ./services/monolith
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
      - rabbitmq
    env_file:
      - .env

volumes:
  postgres_data:
```

---

## 2. Аутентификация и авторизация

### Почему JWT + Сессии?

**JWT (JSON Web Token):**
- **Плюсы:** stateless, масштабируется горизонтально (проверка подписи без обращения к БД), подходит для микросервисов.
- **Минусы:** нельзя отозвать токен мгновенно (нужен blacklist), токен большой, хранит много данных.
- **Где используем:** API endpoints, микросервисы.

**Sessions (cookie-based):**
- **Плюсы:** можно отозвать мгновенно (удалить из Redis), меньше attack surface, проще с CSRF.
- **Минусы:** stateful, требует хранилища сессий (Redis), сложнее масштабировать.
- **Где используем:** веб-интерфейс, админка.

**Почему оба:**
- На собеседовании спросят разницу. Нужно знать оба подхода из практики.
- JWT — для API (мобильное приложение, сторонние клиенты).
- Сессии — для браузера (админка, веб-интерфейс).

### Реализация JWT

```python
# src/auth/jwt_handler.py
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# RS256 — асимметричное шифрование
# Публичный ключ проверяет токен (можно раздать сервисам)
# Приватный ключ подписывает (хранится только на Account Service)
PRIVATE_KEY = open("private.pem").read()
PUBLIC_KEY = open("public.pem").read()

def create_tokens(user_id: int) -> dict:
    access_payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=15),
        "iat": datetime.utcnow(),
    }
    refresh_payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=7),
        "iat": datetime.utcnow(),
    }
    return {
        "access_token": jwt.encode(access_payload, PRIVATE_KEY, algorithm="RS256"),
        "refresh_token": jwt.encode(refresh_payload, PRIVATE_KEY, algorithm="RS256"),
    }

def verify_token(token: str) -> dict:
    return jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
```

**Почему RS256, а не HS256:**
- HS256 — симметричный (один ключ на подпись и проверку). Если скомпрометирован — все сломано.
- RS256 — асимметричный. Публичный ключ можно безопасно раздать другим сервисам для проверки.
- Приватный ключ хранится только на сервере аутентификации.

### Реализация Сессий

```python
# src/auth/session_handler.py
import redis
import uuid

redis_client = redis.Redis(host='redis', port=6379, db=1)

def create_session(user_id: int) -> str:
    session_id = str(uuid.uuid4())
    redis_client.setex(
        f"session:{session_id}",
        timedelta(hours=24),
        str(user_id)
    )
    return session_id

def get_user_by_session(session_id: str) -> int | None:
    user_id = redis_client.get(f"session:{session_id}")
    return int(user_id) if user_id else None

def delete_session(session_id: str):
    redis_client.delete(f"session:{session_id}")
```

### Dependency для FastAPI

```python
# src/auth/dependencies.py
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    # Пробуем JWT
    try:
        payload = verify_token(credentials.credentials)
        if payload["type"] != "access":
            raise HTTPException(401, "Invalid token type")
        return await get_user_by_id(int(payload["sub"]))
    except:
        pass
    
    # Пробуем Session (из cookie)
    session_id = request.cookies.get("session_id")
    if session_id:
        user_id = get_user_by_session(session_id)
        if user_id:
            return await get_user_by_id(user_id)
    
    raise HTTPException(401, "Not authenticated")
```

### Endpoints

```python
# src/auth/router.py
from fastapi import APIRouter, Response

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
async def register(data: RegisterSchema) -> UserSchema:
    """Регистрация нового пользователя."""
    # Проверка уникальности email
    # Хеширование пароля (bcrypt)
    # Создание пользователя в БД
    # Возврат JWT токенов
    pass

@router.post("/login")
async def login(data: LoginSchema, response: Response) -> TokenSchema:
    """Логин через JWT (access + refresh) или сессию (cookie)."""
    # Проверка пароля
    # Создание JWT токенов
    # Создание сессии (для cookie-based auth)
    # Set-Cookie: session_id=...
    pass

@router.post("/refresh")
async def refresh(token: RefreshSchema) -> TokenSchema:
    """Обновление access token по refresh token."""
    # Проверка refresh token
    # Создание новой пары токенов
    pass

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user)
):
    """Выход: удаление сессии из Redis, добавление JWT в blacklist (опционально)."""
    session_id = request.cookies.get("session_id")
    if session_id:
        delete_session(session_id)
    response.delete_cookie("session_id")
    return {"message": "Logged out"}
```

---

## 3. Работа с котировками (REST API + WebSocket)

### Почему внешнее API?

**Варианты:**
1. **Yahoo Finance** (yfinance) — бесплатно, но неофициальное API, может блокировать.
2. **Alpha Vantage** — официальное, 25 запросов/день бесплатно.
3. **Finnhub** — 60 запросов/минута бесплатно, WebSocket для real-time.
4. **Twelve Data** — 8 запросов/минута, хорошая документация.

**Выбор для MVP:** Finnhub или Alpha Vantage (REST для истории, WebSocket для real-time).

**Почему не Binance в MVP:**
- Binance — криптовалюты. Для акций нужен другой источник.
- В MVP важно изучить интеграцию с внешним API, а не конкретную биржу.

### Реализация REST API

```python
# src/market_data/client.py
import httpx
from typing import Optional

class QuotesClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://finnhub.io/api/v1"
        self.client = httpx.AsyncClient()
    
    async def get_quote(self, symbol: str) -> dict:
        """Получить текущую цену акции."""
        response = await self.client.get(
            f"{self.base_url}/quote",
            params={"symbol": symbol, "token": self.api_key}
        )
        return response.json()
    
    async def get_company_profile(self, symbol: str) -> dict:
        """Информация о компании."""
        response = await self.client.get(
            f"{self.base_url}/stock/profile2",
            params={"symbol": symbol, "token": self.api_key}
        )
        return response.json()

# src/market_data/service.py
import redis
from datetime import timedelta

redis_client = redis.Redis(host='redis', port=6379, db=0)

class MarketDataService:
    def __init__(self, client: QuotesClient):
        self.client = client
    
    async def get_cached_quote(self, symbol: str) -> dict:
        """Получить цену с кешированием (TTL 10 сек)."""
        cache_key = f"quote:{symbol}"
        
        # Пробуем кеш
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Запрос к API
        quote = await self.client.get_quote(symbol)
        
        # Сохраняем в кеш
        redis_client.setex(cache_key, timedelta(seconds=10), json.dumps(quote))
        
        return quote

# src/market_data/router.py
from fastapi import APIRouter

router = APIRouter(prefix="/quotes", tags=["quotes"])

@router.get("/{symbol}")
async def get_quote(symbol: str) -> QuoteSchema:
    """Текущая цена акции (с кешем Redis)."""
    return await market_data_service.get_cached_quote(symbol)

@router.get("/{symbol}/history")
async def get_history(symbol: str, period: str = "1m") -> list[CandleSchema]:
    """Исторические данные (свечи)."""
    pass
```

### WebSocket для real-time котировок

```python
# src/websocket/quotes.py
from fastapi import WebSocket
import asyncio

class QuotesWebSocketManager:
    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, symbol: str):
        await websocket.accept()
        if symbol not in self.connections:
            self.connections[symbol] = []
        self.connections[symbol].append(websocket)
    
    async def disconnect(self, websocket: WebSocket, symbol: str):
        self.connections[symbol].remove(websocket)
    
    async def broadcast(self, symbol: str, data: dict):
        for conn in self.connections.get(symbol, []):
            await conn.send_json(data)

quotes_manager = QuotesWebSocketManager()

# Фоновая задача (asyncio, не Celery — для real-time)
async def quotes_streamer():
    """Периодически опрашивает API и рассылает обновления."""
    while True:
        for symbol in quotes_manager.connections.keys():
            quote = await market_data_service.get_cached_quote(symbol)
            await quotes_manager.broadcast(symbol, quote)
        await asyncio.sleep(5)  # 5 секунд

# Endpoint
@app.websocket("/ws/quotes/{symbol}")
async def quotes_websocket(websocket: WebSocket, symbol: str):
    await quotes_manager.connect(websocket, symbol)
    try:
        while True:
            # Ждем сообщения от клиента (подписка/отписка)
            data = await websocket.receive_json()
    except:
        await quotes_manager.disconnect(websocket, symbol)
```

**Почему asyncio, а не Celery для стриминга:**
- Celery — для фоновых задач (email, отчеты). Периодичность — секунды/минуты.
- Real-time стриминг требует постоянного соединения — asyncio.create_task.
- На собеседовании: «Когда Celery, когда asyncio?»

---

## 4. Платежная система (заглушка)

### Почему заглушка?

**Реальные платежи требуют:**
- Договор с платежной системой (Stripe, PayPal, ЮKassa).
- PCI DSS compliance (если принимаете карты).
- Тестовые карты, sandbox окружение.
- Вебхуки (webhooks) для подтверждения платежей.

**Что изучаем на заглушке:**
- Идемпотентность (`Idempotency-Key`).
- Транзакционность (баланс + история).
- Асинхронная обработка (Celery).
- Retry и обработка ошибок.
- Состояния платежа (pending → processing → completed/failed).

### Модели

```python
# src/payments/models.py
from enum import Enum
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Enum as SQLEnum

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class PaymentType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    type = Column(SQLEnum(PaymentType))
    amount = Column(Numeric(15, 2))
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    idempotency_key = Column(String(64), unique=True, index=True)
    external_id = Column(String(128))  # ID во внешней системе
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Сервис

```python
# src/payments/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_deposit(
        self,
        user_id: int,
        amount: Decimal,
        idempotency_key: str
    ) -> Payment:
        """Создать депозит с идемпотентностью."""
        
        # Проверяем, не обработан ли уже этот ключ
        existing = await self.db.execute(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(409, "Payment already processed")
        
        # Создаем платеж
        payment = Payment(
            user_id=user_id,
            type=PaymentType.DEPOSIT,
            amount=amount,
            idempotency_key=idempotency_key,
            status=PaymentStatus.PENDING
        )
        self.db.add(payment)
        await self.db.commit()
        
        # Отправляем в Celery для обработки
        process_payment.delay(payment.id)
        
        return payment
    
    async def process_payment_mock(self, payment_id: int):
        """Заглушка обработки платежа."""
        payment = await self.db.get(Payment, payment_id)
        
        # Имитируем вызов внешнего API
        await asyncio.sleep(2)  # Имитация задержки
        
        # 90% успех, 10% ошибка (для тестирования retry)
        if random.random() < 0.9:
            payment.status = PaymentStatus.COMPLETED
            payment.external_id = f"mock_{uuid.uuid4()}"
            
            # Обновляем баланс пользователя (в транзакции!)
            user = await self.db.get(User, payment.user_id)
            user.balance += payment.amount
        else:
            payment.status = PaymentStatus.FAILED
        
        await self.db.commit()
```

### Celery задача

```python
# src/tasks/payments.py
from celery import Celery
from celery.exceptions import MaxRetriesExceededError

app = Celery('payments', broker='amqp://guest:guest@rabbitmq:5672//')

@app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_payment(self, payment_id: int):
    """Обработка платежа с retry."""
    try:
        # Здесь вызов process_payment_mock
        # В реальности — интеграция с Stripe/PayPal
        asyncio.run(payment_service.process_payment_mock(payment_id))
    except Exception as exc:
        # Retry с exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

### Endpoints

```python
# src/payments/router.py
from fastapi import APIRouter, Header

router = APIRouter(prefix="/payments", tags=["payments"])

@router.post("/deposits")
async def create_deposit(
    data: DepositSchema,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    user: User = Depends(get_current_user)
) -> PaymentSchema:
    """Создать депозит. Идемпотентность через заголовок."""
    return await payment_service.create_deposit(
        user_id=user.id,
        amount=data.amount,
        idempotency_key=idempotency_key
    )

@router.post("/withdrawals")
async def create_withdrawal(
    data: WithdrawalSchema,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    user: User = Depends(get_current_user)
) -> PaymentSchema:
    """Создать вывод средств."""
    # Проверка баланса
    if user.balance < data.amount:
        raise HTTPException(400, "Insufficient funds")
    
    return await payment_service.create_withdrawal(
        user_id=user.id,
        amount=data.amount,
        idempotency_key=idempotency_key
    )

@router.get("/history")
async def get_payment_history(
    user: User = Depends(get_current_user)
) -> list[PaymentSchema]:
    """История платежей пользователя."""
    pass
```

---

## 5. Order Service (торговля)

### Модели

```python
# src/orders/models.py
from enum import Enum

class OrderType(str, Enum):
    LIMIT = "limit"
    MARKET = "market"

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(str, Enum):
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), index=True)
    type = Column(SQLEnum(OrderType))
    side = Column(SQLEnum(OrderSide))
    price = Column(Numeric(15, 2), nullable=True)  # NULL для market
    quantity = Column(Numeric(15, 8))
    filled_quantity = Column(Numeric(15, 8), default=0)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True)
    buy_order_id = Column(Integer, ForeignKey("orders.id"))
    sell_order_id = Column(Integer, ForeignKey("orders.id"))
    price = Column(Numeric(15, 2))
    quantity = Column(Numeric(15, 8))
    created_at = Column(DateTime, default=datetime.utcnow)

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), index=True)
    quantity = Column(Numeric(15, 8), default=0)
    avg_price = Column(Numeric(15, 2), default=0)
```

### Matching Engine (in-memory)

```python
# src/orders/matching_engine.py
import asyncio
from collections import defaultdict
from decimal import Decimal

class OrderBook:
    """Стакан заявок для одного актива."""
    
    def __init__(self):
        # Bid: цена → список ордеров (отсортированы по времени)
        # Sorted по убыванию цены
        self.bids: dict[Decimal, list[Order]] = defaultdict(list)
        
        # Ask: цена → список ордеров (отсортированы по времени)
        # Sorted по возрастанию цены
        self.asks: dict[Decimal, list[Order]] = defaultdict(list)
        
        self.lock = asyncio.Lock()
    
    async def add_order(self, order: Order) -> list[Trade]:
        """Добавить ордер и выполнить матчинг."""
        async with self.lock:
            trades = []
            
            if order.side == OrderSide.BUY:
                trades = await self._match_buy(order)
            else:
                trades = await self._match_sell(order)
            
            # Если ордер не полностью исполнен — добавляем в стакан
            if order.filled_quantity < order.quantity:
                if order.side == OrderSide.BUY:
                    self.bids[order.price].append(order)
                else:
                    self.asks[order.price].append(order)
            
            return trades
    
    async def _match_buy(self, order: Order) -> list[Trade]:
        """Матчинг покупки. Ищем лучшие ask (самые низкие цены)."""
        trades = []
        remaining = order.quantity - order.filled_quantity
        
        # Сортируем ask по возрастанию цены
        sorted_asks = sorted(self.asks.items(), key=lambda x: x[0])
        
        for price, orders in sorted_asks:
            if price > order.price and order.type == OrderType.LIMIT:
                break  # Лимитный ордер — цена не подходит
            
            for ask_order in orders[:]:
                if remaining <= 0:
                    break
                
                trade_qty = min(remaining, ask_order.quantity - ask_order.filled_quantity)
                
                trade = Trade(
                    buy_order_id=order.id,
                    sell_order_id=ask_order.id,
                    price=price,
                    quantity=trade_qty
                )
                trades.append(trade)
                
                # Обновляем количества
                order.filled_quantity += trade_qty
                ask_order.filled_quantity += trade_qty
                remaining -= trade_qty
                
                # Удаляем полностью исполненные ордера
                if ask_order.filled_quantity >= ask_order.quantity:
                    orders.remove(ask_order)
            
            if not orders:
                del self.asks[price]
        
        return trades
```

### Repository Pattern

```python
# src/orders/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class OrderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, order: Order) -> Order:
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        return order
    
    async def get_by_id(self, order_id: int) -> Order | None:
        return await self.db.get(Order, order_id)
    
    async def get_by_user(self, user_id: int, status: OrderStatus | None = None) -> list[Order]:
        query = select(Order).where(Order.user_id == user_id)
        if status:
            query = query.where(Order.status == status)
        result = await self.db.execute(query)
        return result.scalars().all()
```

### Endpoints

```python
# src/orders/router.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/")
async def create_order(
    data: OrderCreateSchema,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> OrderSchema:
    """Создать ордер (лимитный или рыночный)."""
    
    # Валидация баланса
    if data.side == OrderSide.BUY:
        required = data.price * data.quantity if data.type == OrderType.LIMIT else data.quantity * await get_market_price(data.asset_id)
        if user.balance < required:
            raise HTTPException(400, "Insufficient funds")
    
    # Создание ордера
    order = Order(
        user_id=user.id,
        asset_id=data.asset_id,
        type=data.type,
        side=data.side,
        price=data.price,
        quantity=data.quantity
    )
    
    # Матчинг
    trades = await matching_engine.add_order(order)
    
    # Сохранение в БД (в транзакции!)
    async with db.begin():
        db.add(order)
        for trade in trades:
            db.add(trade)
            # Обновление портфеля
            await update_portfolio(trade)
    
    # Уведомление через WebSocket
    await notify_portfolio_update(user.id)
    
    return order

@router.get("/")
async def get_orders(
    status: OrderStatus | None = None,
    user: User = Depends(get_current_user)
) -> list[OrderSchema]:
    """История ордеров пользователя."""
    return await order_repository.get_by_user(user.id, status)

@router.get("/book/{asset_id}")
async def get_order_book(asset_id: int) -> OrderBookSchema:
    """Текущий стакан заявок для актива."""
    return matching_engine.get_book(asset_id)
```

---

## 6. Celery + RabbitMQ

### Почему RabbitMQ, а не Redis?

**RabbitMQ:**
- **Плюсы:** надежная доставка (acknowledgments), routing keys, DLQ из коробки, приоритеты.
- **Минусы:** сложнее настраивать, требует больше ресурсов.
- **Где:** production задачи (платежи, email, отчеты).

**Redis (как брокер):**
- **Плюсы:** проще, уже используется для кеша.
- **Минусы:** не сохраняет сообщения при перезапуске (можно потерять), нет DLQ.
- **Где:** development, периодические задачи.

**В MVP используем RabbitMQ** для изучения production стека.

### Настройка Celery

```python
# src/tasks/celery_app.py
from celery import Celery
from celery.signals import task_failure

app = Celery(
    'tradesim',
    broker='amqp://guest:guest@rabbitmq:5672//',
    backend='redis://redis:6379/0',
    include=['src.tasks.quotes', 'src.tasks.notifications', 'src.tasks.payments']
)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 минут на задачу
    worker_prefetch_multiplier=1,  # Fair scheduling
)

# Обработка ошибок
@task_failure.connect
def handle_task_failure(sender, task_id, exception, args, kwargs, traceback, einfo, **extra):
    """Логирование ошибок, отправка алертов."""
    logger.error(f"Task {sender.name} failed: {exception}", extra={
        "task_id": task_id,
        "args": args,
        "kwargs": kwargs
    })
```

### Задачи

```python
# src/tasks/quotes.py
from celery import shared_task
from celery.schedules import crontab

@shared_task(bind=True, max_retries=3)
def update_quotes(self):
    """Периодическое обновление котировок."""
    try:
        symbols = get_active_symbols()
        for symbol in symbols:
            quote = fetch_quote_from_api(symbol)
            cache_quote(symbol, quote)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

# Периодическая задача
app.conf.beat_schedule = {
    'update-quotes-every-5-seconds': {
        'task': 'src.tasks.quotes.update_quotes',
        'schedule': 5.0,
    },
}

# src/tasks/notifications.py
@shared_task
def send_order_notification(user_id: int, order_id: int, status: str):
    """Отправка email при изменении статуса ордера."""
    # Заглушка — просто логируем
    # В реальности — интеграция с SendGrid/AWS SES
    logger.info(f"Notification: Order {order_id} for user {user_id} is {status}")
```

### Dead Letter Queue (DLQ)

```python
# Настройка DLQ в Celery
from kombu import Queue, Exchange

app.conf.task_queues = (
    Queue('default', Exchange('default'), routing_key='default'),
    Queue('failed', Exchange('failed'), routing_key='failed'),  # DLQ
)

app.conf.task_routes = {
    'src.tasks.payments.*': {'queue': 'payments'},
    'src.tasks.notifications.*': {'queue': 'default'},
}

# При превышении retry — отправляем в DLQ
@app.task(bind=True, max_retries=3)
def process_with_dlq(self, ...):
    try:
        ...
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            # Отправляем в DLQ
            self.apply_async(args=self.request.args, queue='failed')
            raise Ignore()
        raise self.retry(exc=exc)
```

---

## 7. WebSocket портфеля

```python
# src/websocket/portfolio.py
from fastapi import WebSocket

class PortfolioWebSocketManager:
    def __init__(self):
        self.connections: dict[int, WebSocket] = {}
    
    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.connections[user_id] = websocket
    
    async def disconnect(self, user_id: int):
        del self.connections[user_id]
    
    async def send_update(self, user_id: int, portfolio: dict):
        if user_id in self.connections:
            await self.connections[user_id].send_json(portfolio)

portfolio_manager = PortfolioWebSocketManager()

@app.websocket("/ws/portfolio")
async def portfolio_websocket(websocket: WebSocket, token: str):
    # Проверка JWT из query param
    user = await verify_websocket_token(token)
    await portfolio_manager.connect(user.id, websocket)
    
    try:
        while True:
            # Ждем сообщений от клиента
            data = await websocket.receive_json()
            # Обработка (например, подписка на активы)
    except:
        await portfolio_manager.disconnect(user.id)

# Отправка обновлений при исполнении сделки
async def notify_portfolio_update(user_id: int):
    portfolio = await get_portfolio(user_id)
    await portfolio_manager.send_update(user_id, portfolio)
```

---

## 8. Тестирование MVP

### Unit тесты (Pytest)

```python
# tests/test_matching_engine.py
import pytest
from decimal import Decimal

@pytest.mark.asyncio
async def test_limit_buy_matches_with_ask():
    engine = MatchingEngine()
    
    # Создаем ask (продажа) по цене 100
    ask = Order(side=OrderSide.SELL, price=Decimal("100"), quantity=Decimal("1"))
    await engine.add_order(ask)
    
    # Создаем bid (покупка) по цене 100
    bid = Order(side=OrderSide.BUY, price=Decimal("100"), quantity=Decimal("1"))
    trades = await engine.add_order(bid)
    
    assert len(trades) == 1
    assert trades[0].price == Decimal("100")
    assert trades[0].quantity == Decimal("1")

@pytest.mark.asyncio
async def test_market_order_matches_best_price():
    engine = MatchingEngine()
    
    # Два ask: 100 и 101
    await engine.add_order(Order(side=OrderSide.SELL, price=Decimal("101"), quantity=Decimal("1")))
    await engine.add_order(Order(side=OrderSide.SELL, price=Decimal("100"), quantity=Decimal("1")))
    
    # Market buy — должен купить по 100
    bid = Order(side=OrderSide.BUY, type=OrderType.MARKET, quantity=Decimal("1"))
    trades = await engine.add_order(bid)
    
    assert trades[0].price == Decimal("100")
```

### Интеграционные тесты (Testcontainers)

```python
# tests/integration/test_orders.py
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

@pytest.fixture
async def db():
    with PostgresContainer("postgres:16") as postgres:
        # Создаем таблицы
        yield async_session

@pytest.fixture
async def redis():
    with RedisContainer("redis:7") as redis:
        yield redis.get_client()

@pytest.mark.asyncio
async def test_create_order_flow(db, redis):
    # Создаем пользователя с балансом
    user = await create_user(balance=1000)
    
    # Создаем ордер
    order = await create_order(user_id=user.id, price=100, quantity=1)
    
    # Проверяем баланс
    assert user.balance == 900
    
    # Проверяем, что ордер в БД
    db_order = await get_order_by_id(order.id)
    assert db_order.status == OrderStatus.PENDING
```

---

## 9. Чек-лист готовности MVP

- [ ] Регистрация и логин работают (JWT + сессии).
- [ ] Можно создать лимитный и рыночный ордер.
- [ ] Матчинг исполняет ордера (в памяти).
- [ ] Баланс обновляется при сделке.
- [ ] WebSocket портфеля обновляется в real-time.
- [ ] Котировки приходят из внешнего API (REST + кеш).
- [ ] Можно пополнить баланс через заглушку платежей.
- [ ] Идемпотентность работает (повторный запрос с тем же ключом — 409).
- [ ] Celery обрабатывает фоновые задачи (email, обновление цен).
- [ ] RabbitMQ виден в management UI (localhost:15672).
- [ ] Тесты проходят (pytest).
- [ ] Линтеры не ругаются (ruff, mypy).

---

## 10. Что изучили к концу MVP

| Технология | Что изучили |
|------------|-------------|
| **FastAPI** | DI, валидация, WebSocket, middleware |
| **SQLAlchemy 2.0** | Async ORM, миграции (Alembic), транзакции |
| **JWT** | RS256, access/refresh, verification |
| **Sessions** | Cookie-based, Redis storage, отзыв |
| **Redis** | Кеш (TTL), Pub/Sub, сессии |
| **Celery** | Tasks, retry, DLQ, periodic tasks |
| **RabbitMQ** | Broker, management UI, queues |
| **Matching Engine** | Price-Time Priority, asyncio.Lock |
| **Repository Pattern** | Абстракция над БД, тестируемость |
| **Testcontainers** | Интеграционные тесты с реальными БД |

---

## Вопросы с собеседований (MVP)

- «Как работает JWT? Чем access отличается от refresh?»
- «Почему RS256, а не HS256?»
- «Чем сессии отличаются от JWT? Когда что использовать?»
- «Как обеспечить идемпотентность в платежах?»
- «Почему RabbitMQ, а не Redis как брокер?»
- «Как работает Price-Time Priority?»
- «Что такое Repository Pattern и зачем он?»
- «Как тестировать асинхронный код?»
- «Как работает asyncio.Lock?»

---

**Следующий шаг:** Фаза 2 — разделение на микросервисы, gRPC, Kafka.

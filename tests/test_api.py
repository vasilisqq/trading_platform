import pytest


class TestAuth:
    """Тесты аутентификации"""

    @pytest.mark.asyncio(loop_scope="session")
    async def test_register_user_success(self, client, mock_resend, mock_redis):
        """
        Тест успешной регистрации.
        Проверяем, что endpoint возвращает 200 и отправляет email.
        """
        response = await client.post(
            "/auth/register",
            json={
                "email": "new@example.com",
                "username": "newuser",
                "password": "StrongPass123!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["Register"] == "Email was sent"

        # Проверяем, что email был отправлен
        mock_resend.assert_called_once()

    @pytest.mark.asyncio(loop_scope="session")
    async def test_register_user_duplicate(self, client, mock_resend, mock_redis):
        """
        Тест регистрации с дублирующимся email.
        Первый запрос создаёт пользователя, второй возвращает 409.
        """
        payload = {
            "email": "dup@example.com",
            "username": "dupuser",
            "password": "StrongPass123!",
        }

        # Первый раз — успех
        r1 = await client.post("/auth/register", json=payload)
        assert r1.status_code == 200

        # Второй раз — конфликт (409)
        r2 = await client.post("/auth/register", json=payload)
        assert r2.status_code == 409
        assert "already exists" in r2.json()["detail"]

    @pytest.mark.asyncio(loop_scope="session")
    async def test_login_unverified_email(self, client, mock_resend, mock_redis):
        """
        Тест логина с неподтверждённым email.
        Сначала регистрируем, потом логинимся — получаем 403.
        """
        # Регистрация
        await client.post(
            "/auth/register",
            json={
                "email": "login@test.com",
                "username": "loginuser",
                "password": "StrongPass123!",
            },
        )

        # Логин
        response = await client.post(
            "/auth/login",
            json={"email": "login@test.com", "password": "StrongPass123!"},
        )

        # 403, потому что email не верифицирован
        assert response.status_code == 403
        assert "Check your email" in response.json()["detail"]

    @pytest.mark.asyncio(loop_scope="session")
    async def test_google_auth_url(self, client, mock_google_oauth):
        """
        Тест получения URL для Google OAuth.
        Проверяем, что endpoint возвращает auth_url.
        """
        response = await client.get("/auth/google")

        assert response.status_code == 200
        data = response.json()
        assert "auth_url" in data
        assert "google.com" in data["auth_url"]

        # Проверяем, что мок был вызван
        mock_google_oauth.get_auth_url.assert_called_once()

    @pytest.mark.asyncio(loop_scope="session")
    async def test_google_callback(self, client, mock_google_http, mock_redis):
        """
        Тест Google OAuth callback.
        Мокаем HTTP запросы к Google и Redis.
        """
        # Настраиваем мок Redis для oauth state
        mock_redis.get.return_value = "pending"

        response = await client.get(
            "/auth/google/callback",
            params={"code": "fake-code", "state": "test-state"},
            cookies={"oauth_state": "test-state"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

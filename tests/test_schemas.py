import pytest
from src.schemas.user import CreateUser


class TestUser:

    valid_email = "email@mail.com"
    valid_username = "username"
    valid_password = "wfhsfiuUIWHUIW1813616!@#^(!*)"

    def test_weak_password(self):
        with pytest.raises(ValueError):
            user = CreateUser(
                email=self.valid_email,
                username=self.valid_username,
                password="12345678")
        user = CreateUser(
                email=self.valid_email,
                username=self.valid_username,
                password=self.valid_password)
        assert user is not None


    def test_short_login(self):
        with pytest.raises(ValueError):
            user = CreateUser(
                email=self.valid_email,
                username="w",
                password=self.valid_password)
        
    def test_long_login(self):
        with pytest.raises(ValueError):
            user = CreateUser(
                email=self.valid_email,
                username="w"*200,
                password=self.valid_password)

    def test_long_password(self):
        with pytest.raises(ValueError):
            user = CreateUser(
                email=self.valid_email,
                username=self.valid_username,
                password=self.valid_password*20)

    def test_invalide_email(self):
        with pytest.raises(ValueError):
            user = CreateUser(
                email="email",
                username=self.valid_username,
                password=self.valid_password)


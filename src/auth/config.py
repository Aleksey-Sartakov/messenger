from fastapi_users.authentication import JWTStrategy, CookieTransport, AuthenticationBackend

from src.config import settings


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.SECRET_KEY_FOR_JWT, lifetime_seconds=None)


cookie_transport = CookieTransport(cookie_name="messanger_auth")
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

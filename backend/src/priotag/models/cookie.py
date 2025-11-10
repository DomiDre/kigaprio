# Cookie config
import os

ENVIRONMENT = os.getenv("ENV", "development")
IS_PRODUCTION = ENVIRONMENT != "development"

COOKIE_DOMAIN = "priotag.de" if IS_PRODUCTION else None
COOKIE_PATH = "/"
COOKIE_SECURE = IS_PRODUCTION
COOKIE_AUTH_TOKEN = "auth_token"
COOKIE_DEK = "dek"

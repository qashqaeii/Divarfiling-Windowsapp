"""اطلاعات برند و سازنده — اپ استخراج."""

SITE_DISPLAY_NAME = "فایلینگ دیوار"
SITE_URL = "https://divarfiling.ir"
SITE_URL_DISPLAY = "divarfiling.ir"

CREATOR_NAME = "حسین قشقایی"
CREATOR_PHONE = "09357930033"
CREATOR_PHONE_DISPLAY = "۰۹۳۵۷۹۳۰۰۳۳"

CREATOR_TELEGRAM = "@hosseinQashqaeii"
CREATOR_TELEGRAM_URL = "https://t.me/hosseinQashqaeii"

SUPPORT_EMAIL = "info@divarfiling.ir"

LOGO_ASSET = "assets/logo.png"
ICON_ASSET = "assets/icon.png"
ICON_ICO_ASSET = "assets/icon.ico"


def get_logo_path() -> str:
    from app.paths import get_resource_path

    return get_resource_path(LOGO_ASSET)

DEFAULT_LICENSE_API_URL = SITE_URL
DEFAULT_PLATFORM_UPLOAD_URL = f"{SITE_URL}/workspace/import/"
DEFAULT_BUY_LICENSE_URL = f"{SITE_URL}/products/divar-extraction-bot/"

# باید با LICENSE_BOT_API_KEY در .env سرور Django یکسان باشد
LICENSE_BOT_API_KEY = "jim-HWqegAp3ePJ4iJu0uoDpSc8KYJFlXJsfHOgCUMQWOzw4HCpHsjVidsYPUYdi"

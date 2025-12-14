import os

from datametronome_podium.core.config import Settings


def main():
    os.environ["DATAMETRONOME_ALLOWED_ORIGINS"] = "*"

    print("Testing Settings instantiation...")
    try:
        settings = Settings()
    except Exception as exc:
        print(f"❌ Failed to instantiate Settings: {exc}")
        raise

    print("✅ Settings instantiated successfully")
    print(f"Allowed origins: {settings.allowed_origins}")


if __name__ == "__main__":
    main()

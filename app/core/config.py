from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Samostalni Reklamacije/QMS app — vlastiti SQLite. Za Postgres postavi DATABASE_URL u .env.
    database_url: str = "sqlite:///./reklamacije.db"

    # Naziv tvrtke za zaglavlja dokumenata (PDF). Pravi naziv postavi u .env (FIRMA_NAZIV).
    firma_naziv: str = "DEMO TISAK d.o.o."

    # Prijava / sesija. secret_key potpisuje cookie; admin_password je lozinka
    # početnog admina (oboje se generira u .env pri prvom pokretanju run.bat).
    secret_key: str = "promijeni-me-tajni-kljuc-reklamacije"
    admin_password: str = "admin"

    # Email notifikacije (SMTP). notif_enabled=false -> ništa se ne šalje (dry-run).
    # Sve postaviti u .env; bez toga sustav radi normalno, samo bez slanja.
    notif_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_tls: bool = True
    notif_from: str = "qms@localhost"
    notif_default: str = ""          # fallback primatelj (npr. voditelj kvalitete)


settings = Settings()

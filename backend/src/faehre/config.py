"""Einstellungen und Projektpfade. Werte kommen aus der .env im Projektwurzelverzeichnis."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJEKT_WURZEL: Path = Path(__file__).resolve().parents[3]


class Einstellungen(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FAEHRE_",
        env_file=PROJEKT_WURZEL / ".env",
        extra="ignore",
    )

    backend_port: int = 8490
    frontend_port: int = 5490
    # Einträge je Seite, die der Dienst beim Auflisten eines Ordners schickt.
    seitengroesse: int = 200
    # Blockgröße beim Streamen von Dateiinhalten.
    blockgroesse: int = 1024 * 1024
    # Startordner der Mac-Seite; leer bedeutet Benutzerordner.
    mac_start: str = ""
    # Startordner auf dem Telefon.
    android_start: str = "/sdcard"


einstellungen = Einstellungen()

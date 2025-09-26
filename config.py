from dataclasses import dataclass
from typing import Optional
import os
from dotenv import load_dotenv


@dataclass
class DatabaseConfig:
    """Configuración de base de datos"""
    name: str = "monevo.db"
    backup_enabled: bool = True
    backup_interval_hours: int = 24


@dataclass
class TelegramConfig:
    """Configuración de Telegram"""
    token: str
    webhook_url: Optional[str] = None
    max_message_length: int = 4096


@dataclass
class AppConfig:
    """Configuración general de la aplicación"""
    debug_mode: bool = False
    log_level: str = "INFO"
    timezone: str = "America/Bogota"
    max_presupuestos_por_usuario: int = 50
    max_movimientos_historial: int = 1000


class ConfigManager:
    """Gestor de configuración (Singleton Pattern)"""
    
    _instance = None
    _config_loaded = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._config_loaded:
            self._load_config()
            self._config_loaded = True
    
    def _load_config(self):
        """Carga la configuración desde variables de entorno"""
        load_dotenv()
        
        # Configuración de Telegram
        telegram_token = os.getenv("MONEVO_API_KEY_TELEGRAM")
        if not telegram_token:
            raise ValueError(
                "Token de Telegram requerido. "
                "Define MONEVO_API_KEY_TELEGRAM en el archivo .env"
            )
        
        self.telegram = TelegramConfig(
            token=telegram_token,
            webhook_url=os.getenv("TELEGRAM_WEBHOOK_URL")
        )
        
        # Configuración de base de datos
        self.database = DatabaseConfig(
            name=os.getenv("DATABASE_NAME", "monevo.db"),
            backup_enabled=os.getenv("DATABASE_BACKUP_ENABLED", "true").lower() == "true"
        )
        
        # Configuración general
        self.app = AppConfig(
            debug_mode=os.getenv("DEBUG_MODE", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            timezone=os.getenv("TIMEZONE", "America/Bogota")
        )
    
    def validate(self):
        """Valida que la configuración sea correcta"""
        errors = []
        
        # Validar token de Telegram
        if not self.telegram.token:
            errors.append("Token de Telegram es requerido")
        
        # Validar configuración de logs
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.app.log_level not in valid_log_levels:
            errors.append(f"Log level debe ser uno de: {valid_log_levels}")
        
        if errors:
            raise ValueError(f"Errores de configuración: {', '.join(errors)}")
        
        return True


# Instancia global del gestor de configuración
config = ConfigManager()
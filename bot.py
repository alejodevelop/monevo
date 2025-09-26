from telegram.ext import Application, MessageHandler, filters, CommandHandler
from telegram.ext import CallbackQueryHandler
from dotenv import load_dotenv
import os
import logging

# Importar módulos refactorizados
from database import SQLiteRepository
from services import MonevoFacade
from telegram_handlers import TelegramHandlers


class MonevoBot:
    """Clase principal del bot (Single Responsibility)"""
    
    def __init__(self, token: str, db_name: str = "monevo.db"):
        self.token = token
        
        # Dependency Injection
        self.repository = SQLiteRepository(db_name)
        self.monevo_service = MonevoFacade(self.repository)
        self.handlers = TelegramHandlers(self.monevo_service)
        
        # Configurar aplicación de Telegram
        self.app = Application.builder().token(token).build()
        self._register_handlers()
    
    def _register_handlers(self):
        """Registra todos los handlers del bot"""
        # Handler para mensajes de texto (no comandos)
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_message)
        )
        
        # Handlers para comandos
        self.app.add_handler(CommandHandler("start", self.handlers.handle_start))
        self.app.add_handler(CommandHandler("crear", self.handlers.handle_crear))
        self.app.add_handler(CommandHandler("actualizar", self.handlers.handle_actualizar))
        self.app.add_handler(CommandHandler("eliminar", self.handlers.handle_eliminar))
        self.app.add_handler(CommandHandler("historial", self.handlers.handle_historial))
        self.app.add_handler(CommandHandler("resumen", self.handlers.handle_resumen))
        self.app.add_handler(CallbackQueryHandler(self.handlers.handle_callback))

    
    def run(self):
        """Inicia el bot"""
        print("🤖 Monevo Bot iniciado...")
        print(f"📊 Base de datos: {self.repository.db_name}")
        print("⚡ Listo para recibir mensajes!")
        
        self.app.run_polling()


def setup_logging():
    """Configurar logging"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )


def load_environment():
    """Cargar variables de entorno"""
    load_dotenv()
    token = os.getenv("MONEVO_API_KEY_TELEGRAM")
    
    if not token:
        raise ValueError(
            "Token de Telegram no encontrado. "
            "Asegúrate de definir MONEVO_API_KEY_TELEGRAM en tu archivo .env"
        )
    
    return token


def main():
    """Función principal"""
    try:
        # Configuración inicial
        setup_logging()
        token = load_environment()
        
        # Crear y ejecutar el bot
        bot = MonevoBot(token)
        bot.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Bot detenido por el usuario")
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        logging.error(f"Error fatal: {e}", exc_info=True)


if __name__ == "__main__":
    main()
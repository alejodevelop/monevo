"""
Excepciones personalizadas para Monevo Bot
Facilita el manejo de errores específicos del dominio
"""


class MonevoException(Exception):
    """Excepción base para errores de Monevo"""
    
    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class PresupuestoException(MonevoException):
    """Excepciones relacionadas con presupuestos"""
    pass


class PresupuestoNotFoundError(PresupuestoException):
    """Error cuando no se encuentra un presupuesto"""
    
    def __init__(self, categoria: str):
        message = f"No existe presupuesto para la categoría '{categoria}'"
        super().__init__(message, "PRESUPUESTO_NOT_FOUND")
        self.categoria = categoria


class PresupuestoAlreadyExistsError(PresupuestoException):
    """Error cuando se intenta crear un presupuesto que ya existe"""
    
    def __init__(self, categoria: str):
        message = f"Ya existe un presupuesto para la categoría '{categoria}'"
        super().__init__(message, "PRESUPUESTO_ALREADY_EXISTS")
        self.categoria = categoria


class InvalidAmountError(MonevoException):
    """Error cuando el monto es inválido"""
    
    def __init__(self, monto: float):
        message = f"El monto {monto} no es válido. Debe ser mayor a 0"
        super().__init__(message, "INVALID_AMOUNT")
        self.monto = monto


class InvalidPeriodicityError(MonevoException):
    """Error cuando la periodicidad es inválida"""
    
    def __init__(self, periodicidad: str):
        valid_periods = ["diario", "semanal", "mensual", "anual"]
        message = f"Periodicidad '{periodicidad}' inválida. Debe ser: {', '.join(valid_periods)}"
        super().__init__(message, "INVALID_PERIODICITY")
        self.periodicidad = periodicidad


class MovimientoException(MonevoException):
    """Excepciones relacionadas con movimientos"""
    pass


class InvalidMovementTypeError(MovimientoException):
    """Error cuando el tipo de movimiento es inválido"""
    
    def __init__(self, tipo: str):
        message = f"Tipo de movimiento '{tipo}' inválido. Debe ser 'gasto' o 'ingreso'"
        super().__init__(message, "INVALID_MOVEMENT_TYPE")
        self.tipo = tipo


class DatabaseException(MonevoException):
    """Excepciones relacionadas con la base de datos"""
    pass


class DatabaseConnectionError(DatabaseException):
    """Error de conexión a la base de datos"""
    
    def __init__(self, details: str = ""):
        message = f"Error conectando a la base de datos. {details}".strip()
        super().__init__(message, "DATABASE_CONNECTION_ERROR")


class ValidationException(MonevoException):
    """Excepciones de validación"""
    pass


class EmptyCategoryError(ValidationException):
    """Error cuando la categoría está vacía"""
    
    def __init__(self):
        message = "La categoría no puede estar vacía"
        super().__init__(message, "EMPTY_CATEGORY")


class CategoryTooLongError(ValidationException):
    """Error cuando la categoría es muy larga"""
    
    def __init__(self, categoria: str, max_length: int = 50):
        message = f"La categoría '{categoria}' es muy larga. Máximo {max_length} caracteres"
        super().__init__(message, "CATEGORY_TOO_LONG")
        self.categoria = categoria
        self.max_length = max_length


class MessageParsingException(MonevoException):
    """Excepciones del procesamiento de mensajes"""
    pass


class UnknownMessagePatternError(MessageParsingException):
    """Error cuando no se puede procesar el mensaje"""
    
    def __init__(self, mensaje: str):
        message = f"No se pudo entender el mensaje: '{mensaje}'"
        super().__init__(message, "UNKNOWN_MESSAGE_PATTERN")
        self.mensaje = mensaje


def handle_monevo_exception(exception: MonevoException) -> str:
    """
    Convierte una excepción de Monevo en un mensaje amigable para el usuario
    
    Args:
        exception: La excepción de Monevo a manejar
        
    Returns:
        Mensaje amigable para mostrar al usuario
    """
    error_messages = {
        "PRESUPUESTO_NOT_FOUND": "⚠️ {message}. Usa /crear para crearlo primero.",
        "PRESUPUESTO_ALREADY_EXISTS": "⚠️ {message}. Usa /actualizar para modificarlo.",
        "INVALID_AMOUNT": "⚠️ {message}.",
        "INVALID_PERIODICITY": "⚠️ {message}.",
        "INVALID_MOVEMENT_TYPE": "⚠️ Error interno: {message}.",
        "DATABASE_CONNECTION_ERROR": "❌ Error de base de datos. Inténtalo más tarde.",
        "EMPTY_CATEGORY": "⚠️ {message}.",
        "CATEGORY_TOO_LONG": "⚠️ {message}.",
        "UNKNOWN_MESSAGE_PATTERN": "❌ {message}. Usa /start para ver ejemplos."
    }
    
    template = error_messages.get(exception.error_code, "❌ {message}")
    return template.format(message=exception.message)
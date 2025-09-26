from typing import List, Optional
from models import Presupuesto, Movimiento, ResumenPresupuesto
from database import DatabaseInterface


class PresupuestoService:
    """Servicio para gestión de presupuestos (Single Responsibility)"""
    
    def __init__(self, repository: DatabaseInterface):
        self._repository = repository
    
    def crear_presupuesto(self, usuario_id: str, categoria: str, monto: float, periodicidad: str = "mensual") -> tuple[bool, str]:
        """Crea un nuevo presupuesto con validaciones"""
        # Validaciones
        if not categoria.strip():
            return False, "La categoría no puede estar vacía"
        
        if monto <= 0:
            return False, "El monto debe ser mayor a 0"
        
        if periodicidad.lower() not in ["diario", "semanal", "mensual", "anual"]:
            return False, "Periodicidad debe ser: diario, semanal, mensual, anual"
        
        # Crear presupuesto
        presupuesto = Presupuesto(
            usuario_id=usuario_id,
            categoria=categoria,
            monto=monto,
            periodicidad=periodicidad.lower()
        )
        
        success = self._repository.crear_presupuesto(presupuesto)
        if success:
            return True, f"Presupuesto '{categoria}' creado exitosamente"
        else:
            return False, f"Ya existe un presupuesto para '{categoria}'"
    
    def actualizar_presupuesto(self, usuario_id: str, categoria: str, monto: float, periodicidad: Optional[str] = None) -> tuple[bool, str]:
        """Actualiza un presupuesto existente"""
        if monto <= 0:
            return False, "El monto debe ser mayor a 0"
        
        if periodicidad and periodicidad.lower() not in ["diario", "semanal", "mensual", "anual"]:
            return False, "Periodicidad debe ser: diario, semanal, mensual, anual"
        
        success = self._repository.actualizar_presupuesto(usuario_id, categoria, monto, periodicidad)
        if success:
            return True, f"Presupuesto '{categoria}' actualizado exitosamente"
        else:
            return False, f"No existe presupuesto '{categoria}'"
    
    def eliminar_presupuesto(self, usuario_id: str, categoria: str) -> tuple[bool, str]:
        """Elimina un presupuesto y todos sus movimientos"""
        success = self._repository.eliminar_presupuesto(usuario_id, categoria)
        if success:
            return True, f"Presupuesto '{categoria}' eliminado exitosamente"
        else:
            return False, f"No existe presupuesto '{categoria}'"
    
    def obtener_resumen(self, usuario_id: str) -> List[ResumenPresupuesto]:
        """Obtiene el resumen de todos los presupuestos"""
        return self._repository.obtener_resumen(usuario_id)
    
    def presupuesto_existe(self, usuario_id: str, categoria: str) -> bool:
        """Verifica si existe un presupuesto"""
        return self._repository.presupuesto_existe(usuario_id, categoria)


class MovimientoService:
    """Servicio para gestión de movimientos (Single Responsibility)"""
    
    def __init__(self, repository: DatabaseInterface, presupuesto_service: PresupuestoService):
        self._repository = repository
        self._presupuesto_service = presupuesto_service
    
    def registrar_gasto(self, usuario_id: str, categoria: str, monto: float, concepto: str = "") -> tuple[bool, str]:
        """Registra un gasto"""
        return self._registrar_movimiento(usuario_id, categoria, "gasto", monto, concepto)
    
    def registrar_ingreso(self, usuario_id: str, categoria: str, monto: float, concepto: str = "") -> tuple[bool, str]:
        """Registra un ingreso"""
        return self._registrar_movimiento(usuario_id, categoria, "ingreso", monto, concepto)
    
    def _registrar_movimiento(self, usuario_id: str, categoria: str, tipo: str, monto: float, concepto: str = "") -> tuple[bool, str]:
        """Registra un movimiento con validaciones"""
        # Validaciones
        if not self._presupuesto_service.presupuesto_existe(usuario_id, categoria):
            return False, f"No existe presupuesto '{categoria}'. Créalo primero con /crear"
        
        if monto <= 0:
            return False, "El monto debe ser mayor a 0"
        
        # Crear movimiento
        try:
            movimiento = Movimiento(
                usuario_id=usuario_id,
                categoria=categoria,
                tipo=tipo,
                monto=monto,
                concepto=concepto
            )
            
            success = self._repository.registrar_movimiento(movimiento)
            if success:
                accion = "Gasto registrado" if tipo == "gasto" else "Ingreso registrado"
                return True, f"💸 {accion}: ${monto:,.0f} en {categoria}" + (f" - {concepto}" if concepto else "")
            else:
                return False, "Error al registrar el movimiento"
                
        except ValueError as e:
            return False, str(e)
    
    def obtener_historial(self, usuario_id: str, categoria: str) -> tuple[bool, str, List[Movimiento]]:
        """Obtiene el historial de movimientos de una categoría"""
        if not self._presupuesto_service.presupuesto_existe(usuario_id, categoria):
            return False, f"No existe presupuesto '{categoria}'", []
        
        movimientos = self._repository.obtener_historial(usuario_id, categoria)
        if not movimientos:
            return False, f"No hay movimientos registrados para '{categoria}'", []
        
        return True, "Historial obtenido exitosamente", movimientos


class MonevoFacade:
    """Facade que unifica todos los servicios (Facade Pattern)"""
    
    def __init__(self, repository: DatabaseInterface):
        self.presupuesto_service = PresupuestoService(repository)
        self.movimiento_service = MovimientoService(repository, self.presupuesto_service)
    
    # Métodos de presupuesto
    def crear_presupuesto(self, usuario_id: str, categoria: str, monto: float, periodicidad: str = "mensual") -> tuple[bool, str]:
        return self.presupuesto_service.crear_presupuesto(usuario_id, categoria, monto, periodicidad)
    
    def actualizar_presupuesto(self, usuario_id: str, categoria: str, monto: float, periodicidad: Optional[str] = None) -> tuple[bool, str]:
        return self.presupuesto_service.actualizar_presupuesto(usuario_id, categoria, monto, periodicidad)
    
    def eliminar_presupuesto(self, usuario_id: str, categoria: str) -> tuple[bool, str]:
        return self.presupuesto_service.eliminar_presupuesto(usuario_id, categoria)
    
    def obtener_resumen(self, usuario_id: str) -> List[ResumenPresupuesto]:
        return self.presupuesto_service.obtener_resumen(usuario_id)
    
    # Métodos de movimientos
    def registrar_gasto(self, usuario_id: str, categoria: str, monto: float, concepto: str = "") -> tuple[bool, str]:
        return self.movimiento_service.registrar_gasto(usuario_id, categoria, monto, concepto)
    
    def registrar_ingreso(self, usuario_id: str, categoria: str, monto: float, concepto: str = "") -> tuple[bool, str]:
        return self.movimiento_service.registrar_ingreso(usuario_id, categoria, monto, concepto)
    
    def obtener_historial(self, usuario_id: str, categoria: str) -> tuple[bool, str, List[Movimiento]]:
        return self.movimiento_service.obtener_historial(usuario_id, categoria)
    
    def presupuesto_existe(self, usuario_id: str, categoria: str) -> bool:
        return self.presupuesto_service.presupuesto_existe(usuario_id, categoria)
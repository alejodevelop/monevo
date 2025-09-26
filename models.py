from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Presupuesto:
    """Modelo de datos para presupuesto"""
    categoria: str
    monto: float
    periodicidad: str
    usuario_id: Optional[str] = None
    id: Optional[int] = None
    creado_en: Optional[datetime] = None
    
    def __post_init__(self):
        if self.creado_en is None:
            self.creado_en = datetime.now()
        self.categoria = self.categoria.lower().strip()


@dataclass
class Movimiento:
    """Modelo de datos para movimiento"""
    categoria: str
    tipo: str
    monto: float
    usuario_id: Optional[str] = None
    concepto: Optional[str] = ""
    fecha: Optional[datetime] = None
    id: Optional[int] = None
    
    def __post_init__(self):
        if self.fecha is None:
            self.fecha = datetime.now()
        self.categoria = self.categoria.lower().strip()
        
        if self.tipo not in ["gasto", "ingreso"]:
            raise ValueError("Tipo debe ser 'gasto' o 'ingreso'")


@dataclass
class ResumenPresupuesto:
    """Modelo para resumen de presupuesto"""
    categoria: str
    monto_inicial: float
    gastos: float
    ingresos: float
    saldo: float
    periodicidad: str
    
    @property
    def porcentaje_usado(self) -> float:
        """Calcula el porcentaje del presupuesto usado"""
        if self.monto_inicial == 0:
            return 0.0
        return (self.gastos / self.monto_inicial) * 100
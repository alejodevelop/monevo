import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import List, Optional
from datetime import datetime

from models import Presupuesto, Movimiento, ResumenPresupuesto


class DatabaseInterface(ABC):
    """Interface para operaciones de base de datos (Dependency Inversion)"""
    
    @abstractmethod
    def crear_presupuesto(self, presupuesto: Presupuesto) -> bool:
        pass
    
    @abstractmethod
    def actualizar_presupuesto(self, usuario_id: str, categoria: str, monto: float, periodicidad: Optional[str] = None) -> bool:
        pass
    
    @abstractmethod
    def eliminar_presupuesto(self, usuario_id: str, categoria: str) -> bool:
        pass
    
    @abstractmethod
    def presupuesto_existe(self, usuario_id: str, categoria: str) -> bool:
        pass
    
    @abstractmethod
    def registrar_movimiento(self, movimiento: Movimiento) -> bool:
        pass
    
    @abstractmethod
    def obtener_historial(self, usuario_id: str, categoria: str) -> List[Movimiento]:
        pass
    
    @abstractmethod
    def obtener_resumen(self, usuario_id: str) -> List[ResumenPresupuesto]:
        pass


class SQLiteRepository(DatabaseInterface):
    """Implementación concreta para SQLite"""
    
    def __init__(self, db_name: str = "monevo.db"):
        self.db_name = db_name
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        """Context manager para conexiones de BD"""
        conn = sqlite3.connect(self.db_name)
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_db(self):
        """Inicializa la base de datos"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            
            # Tabla presupuestos
            cur.execute("""
                CREATE TABLE IF NOT EXISTS presupuestos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id TEXT NOT NULL,
                    categoria TEXT NOT NULL,
                    monto REAL NOT NULL,
                    periodicidad TEXT NOT NULL DEFAULT 'mensual',
                    creado_en TEXT NOT NULL,
                    UNIQUE(usuario_id, categoria)
                )
            """)
            
            # Tabla movimientos
            cur.execute("""
                CREATE TABLE IF NOT EXISTS movimientos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id TEXT NOT NULL,
                    categoria TEXT NOT NULL,
                    tipo TEXT NOT NULL CHECK (tipo IN ('gasto', 'ingreso')),
                    monto REAL NOT NULL,
                    concepto TEXT DEFAULT '',
                    fecha TEXT NOT NULL
                )
            """)
            
            # Índices para mejor rendimiento
            cur.execute("CREATE INDEX IF NOT EXISTS idx_presupuestos_usuario ON presupuestos(usuario_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_movimientos_usuario_categoria ON movimientos(usuario_id, categoria)")
            
            conn.commit()
    
    def crear_presupuesto(self, presupuesto: Presupuesto) -> bool:
        """Crea un nuevo presupuesto"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            
            # Verificar si ya existe
            if self.presupuesto_existe(presupuesto.usuario_id, presupuesto.categoria):
                return False
            
            cur.execute("""
                INSERT INTO presupuestos (usuario_id, categoria, monto, periodicidad, creado_en) 
                VALUES (?, ?, ?, ?, ?)
            """, (
                presupuesto.usuario_id,
                presupuesto.categoria,
                presupuesto.monto,
                presupuesto.periodicidad,
                presupuesto.creado_en.isoformat()
            ))
            
            conn.commit()
            return True
    
    def actualizar_presupuesto(self, usuario_id: str, categoria: str, monto: float, periodicidad: Optional[str] = None) -> bool:
        """Actualiza un presupuesto existente"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            
            if not self.presupuesto_existe(usuario_id, categoria):
                return False
            
            if periodicidad:
                cur.execute("""
                    UPDATE presupuestos 
                    SET monto = ?, periodicidad = ? 
                    WHERE usuario_id = ? AND categoria = ?
                """, (monto, periodicidad, usuario_id, categoria))
            else:
                cur.execute("""
                    UPDATE presupuestos 
                    SET monto = ? 
                    WHERE usuario_id = ? AND categoria = ?
                """, (monto, usuario_id, categoria))
            
            conn.commit()
            return True
    
    def eliminar_presupuesto(self, usuario_id: str, categoria: str) -> bool:
        """Elimina un presupuesto y todos sus movimientos"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            
            if not self.presupuesto_existe(usuario_id, categoria):
                return False
            
            # Eliminar presupuesto y movimientos en transacción
            cur.execute("DELETE FROM presupuestos WHERE usuario_id = ? AND categoria = ?", 
                       (usuario_id, categoria))
            cur.execute("DELETE FROM movimientos WHERE usuario_id = ? AND categoria = ?", 
                       (usuario_id, categoria))
            
            conn.commit()
            return True
    
    def presupuesto_existe(self, usuario_id: str, categoria: str) -> bool:
        """Verifica si existe un presupuesto"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM presupuestos WHERE usuario_id = ? AND categoria = ?", 
                       (usuario_id, categoria.lower().strip()))
            return cur.fetchone() is not None
    
    def registrar_movimiento(self, movimiento: Movimiento) -> bool:
        """Registra un nuevo movimiento"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO movimientos (usuario_id, categoria, tipo, monto, concepto, fecha) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                movimiento.usuario_id,
                movimiento.categoria,
                movimiento.tipo,
                movimiento.monto,
                movimiento.concepto,
                movimiento.fecha.isoformat()
            ))
            
            conn.commit()
            return True
    
    def obtener_historial(self, usuario_id: str, categoria: str) -> List[Movimiento]:
        """Obtiene el historial de movimientos de una categoría"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, tipo, monto, concepto, fecha 
                FROM movimientos 
                WHERE usuario_id = ? AND categoria = ? 
                ORDER BY fecha DESC
            """, (usuario_id, categoria.lower().strip()))
            
            movimientos = []
            for row in cur.fetchall():
                movimiento = Movimiento(
                    categoria=categoria,
                    tipo=row[1],
                    monto=row[2],
                    usuario_id=usuario_id,
                    concepto=row[3],
                    fecha=datetime.fromisoformat(row[4]),
                    id=row[0]
                )
                movimientos.append(movimiento)
            
            return movimientos
    
    def obtener_resumen(self, usuario_id: str) -> List[ResumenPresupuesto]:
        """Obtiene el resumen de todos los presupuestos de un usuario"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            
            # Obtener presupuestos
            cur.execute("""
                SELECT categoria, monto, periodicidad 
                FROM presupuestos 
                WHERE usuario_id = ?
            """, (usuario_id,))
            
            resumenes = []
            for categoria, monto, periodicidad in cur.fetchall():
                # Calcular gastos
                cur.execute("""
                    SELECT COALESCE(SUM(monto), 0) 
                    FROM movimientos 
                    WHERE usuario_id = ? AND categoria = ? AND tipo = 'gasto'
                """, (usuario_id, categoria))
                gastos = cur.fetchone()[0]
                
                # Calcular ingresos
                cur.execute("""
                    SELECT COALESCE(SUM(monto), 0) 
                    FROM movimientos 
                    WHERE usuario_id = ? AND categoria = ? AND tipo = 'ingreso'
                """, (usuario_id, categoria))
                ingresos = cur.fetchone()[0]
                
                saldo = monto + ingresos - gastos
                
                resumen = ResumenPresupuesto(
                    categoria=categoria,
                    monto_inicial=monto,
                    gastos=gastos,
                    ingresos=ingresos,
                    saldo=saldo,
                    periodicidad=periodicidad
                )
                resumenes.append(resumen)
            
            return resumenes
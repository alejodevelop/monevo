import re
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod


class MessagePattern(ABC):
    """Patrón base para procesar mensajes (Strategy Pattern)"""
    
    @abstractmethod
    def can_handle(self, mensaje: str) -> bool:
        """Determina si este patrón puede manejar el mensaje"""
        pass
    
    @abstractmethod
    def extract_data(self, mensaje: str) -> Optional[Dict[str, Any]]:
        """Extrae datos del mensaje"""
        pass
    
    @abstractmethod
    def get_action(self) -> str:
        """Retorna la acción asociada al patrón"""
        pass


class GastoPattern(MessagePattern):
    """Patrón para detectar gastos"""
    
    def __init__(self):
        self.pattern = re.compile(r'(gast[ée]|saqué)\s+(\d+)\s+(de)\s+(\w+)(\s+por\s+(.+))?', re.IGNORECASE)
    
    def can_handle(self, mensaje: str) -> bool:
        return self.pattern.search(mensaje) is not None
    
    def extract_data(self, mensaje: str) -> Optional[Dict[str, Any]]:
        match = self.pattern.search(mensaje)
        if match:
            return {
                'monto': int(match.group(2)),
                'categoria': match.group(4).lower().strip(),
                'concepto': match.group(6).strip() if match.group(6) else ""
            }
        return None
    
    def get_action(self) -> str:
        return "gasto"


class IngresoPattern(MessagePattern):
    """Patrón para detectar ingresos"""
    
    def __init__(self):
        self.pattern = re.compile(r'(añad[íi]|agregu[ée]|sum[ée])\s+(\d+)\s+(a)\s+(\w+)(\s+por\s+(.+))?', re.IGNORECASE)
    
    def can_handle(self, mensaje: str) -> bool:
        return self.pattern.search(mensaje) is not None
    
    def extract_data(self, mensaje: str) -> Optional[Dict[str, Any]]:
        match = self.pattern.search(mensaje)
        if match:
            return {
                'monto': int(match.group(2)),
                'categoria': match.group(4).lower().strip(),
                'concepto': match.group(6).strip() if match.group(6) else ""
            }
        return None
    
    def get_action(self) -> str:
        return "ingreso"


class VerPresupuestoPattern(MessagePattern):
    """Patrón para ver presupuesto individual"""
    
    def __init__(self):
        self.pattern = re.compile(r'ver\s+(presupuesto\s+)?(\w+)', re.IGNORECASE)
    
    def can_handle(self, mensaje: str) -> bool:
        return self.pattern.search(mensaje) is not None
    
    def extract_data(self, mensaje: str) -> Optional[Dict[str, Any]]:
        match = self.pattern.search(mensaje)
        if match:
            return {
                'categoria': match.group(2).lower().strip()
            }
        return None
    
    def get_action(self) -> str:
        return "ver_presupuesto"


class MessageParser:
    """Parser de mensajes usando Strategy Pattern"""
    
    def __init__(self):
        self.patterns = [
            GastoPattern(),
            IngresoPattern(),
            VerPresupuestoPattern()
        ]
    
    def parse(self, mensaje: str) -> Optional[Dict[str, Any]]:
        """
        Parsea un mensaje y retorna la acción y datos extraídos
        
        Returns:
            Dict con 'action' y 'data' si se encontró un patrón, None si no
        """
        mensaje = mensaje.strip()
        
        for pattern in self.patterns:
            if pattern.can_handle(mensaje):
                data = pattern.extract_data(mensaje)
                if data:
                    return {
                        'action': pattern.get_action(),
                        'data': data
                    }
        
        return None
    
    def add_pattern(self, pattern: MessagePattern):
        """Permite agregar nuevos patrones (Open/Closed Principle)"""
        self.patterns.append(pattern)


class MessageProcessor:
    """Procesador principal de mensajes (Single Responsibility)"""
    
    def __init__(self, monevo_service, parser: MessageParser = None):
        self.monevo_service = monevo_service
        self.parser = parser or MessageParser()
    
    def process_message(self, usuario_id: str, mensaje: str) -> str:
        """Procesa un mensaje de texto y ejecuta la acción correspondiente"""
        result = self.parser.parse(mensaje)
        
        if not result:
            return self._get_help_message()
        
        action = result['action']
        data = result['data']
        
        # Dispatch según la acción
        if action == "gasto":
            return self._handle_gasto(usuario_id, data)
        elif action == "ingreso":
            return self._handle_ingreso(usuario_id, data)
        elif action == "ver_presupuesto":
            return self._handle_ver_presupuesto(usuario_id, data)
        
        return self._get_help_message()
    
    def _handle_gasto(self, usuario_id: str, data: Dict[str, Any]) -> str:
        """Maneja registro de gasto"""
        success, message = self.monevo_service.registrar_gasto(
            usuario_id, 
            data['categoria'], 
            data['monto'], 
            data['concepto']
        )
        return message
    
    def _handle_ingreso(self, usuario_id: str, data: Dict[str, Any]) -> str:
        """Maneja registro de ingreso"""
        success, message = self.monevo_service.registrar_ingreso(
            usuario_id, 
            data['categoria'], 
            data['monto'], 
            data['concepto']
        )
        return message
    
    def _handle_ver_presupuesto(self, usuario_id: str, data: Dict[str, Any]) -> str:
        """Maneja consulta de presupuesto individual"""
        categoria = data['categoria']
        resumenes = self.monevo_service.obtener_resumen(usuario_id)
        
        for resumen in resumenes:
            if resumen.categoria == categoria:
                return (f"📊 Presupuesto {categoria.capitalize()}:\n"
                       f"💰 Saldo: ${resumen.saldo:,.0f}\n"
                       f"📅 Periodicidad: {resumen.periodicidad}\n"
                       f"📈 Usado: {resumen.porcentaje_usado:.1f}%")
        
        return f"⚠️ No se encontró presupuesto '{categoria}'"
    
    def _get_help_message(self) -> str:
        """Mensaje de ayuda cuando no se entiende el comando"""
        return ("❌ No entendí el mensaje. Ejemplos:\n"
               "• 'Gasté 3000 de moto por gasolina'\n"
               "• 'Añadí 5000 a inversión por salario'\n"
               "• 'Ver presupuesto moto'")
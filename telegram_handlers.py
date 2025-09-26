from telegram import Update
from telegram.ext import ContextTypes
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.error import BadRequest
from datetime import datetime
from typing import List
import logging

from services import MonevoFacade
from message_parser import MessageProcessor
from models import ResumenPresupuesto, Movimiento


class TelegramHandlers:
    """Handlers para el bot de Telegram (Single Responsibility)"""

    def __init__(self, monevo_service: MonevoFacade):
        self.monevo_service = monevo_service
        self.message_processor = MessageProcessor(monevo_service)
        self.logger = logging.getLogger(__name__)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja mensajes de texto normales"""
        usuario_id = str(update.message.from_user.id)
        mensaje = update.message.text.strip()
        state = context.user_data.get("state")

        # Manejar cancelación en cualquier estado
        if mensaje == "❌ Cancelar":
            context.user_data.clear()
            await update.message.reply_text("Operación cancelada.", reply_markup=ReplyKeyboardRemove())
            await update.message.reply_text("Menú principal:", reply_markup=self._main_menu_keyboard())
            return

        # Estados para crear presupuesto
        if state == "ESPERA_CATEGORIA_NUEVA":
            categoria = mensaje.lower().strip()
            if not categoria:
                await update.message.reply_text("⚠️ La categoría no puede estar vacía. Intenta de nuevo.", 
                                               reply_markup=self._cancel_keyboard())
                return
            
            # Verificar si ya existe
            if self.monevo_service.presupuesto_existe(usuario_id, categoria):
                await update.message.reply_text(f"⚠️ Ya existe un presupuesto para '{categoria}'. Usa actualizar en su lugar.", 
                                               reply_markup=self._cancel_keyboard())
                return
            
            context.user_data["categoria"] = categoria
            context.user_data["state"] = "ESPERA_MONTO_PRESUPUESTO"
            await update.message.reply_text(f"Categoría: *{categoria.capitalize()}*\nEscribe el monto del presupuesto:", 
                                           parse_mode="Markdown", reply_markup=self._cancel_keyboard())
            return

        if state == "ESPERA_MONTO_PRESUPUESTO":
            # Limpiamos formato: quitamos puntos y comas
            txt = mensaje.replace(".", "").replace(",", "")
            if not txt.isdigit():
                await update.message.reply_text("⚠️ Solo números. Intenta de nuevo.", reply_markup=self._cancel_keyboard())
                return
            
            monto = int(txt)
            if monto <= 0:
                await update.message.reply_text("⚠️ El monto debe ser mayor a 0. Intenta de nuevo.", 
                                               reply_markup=self._cancel_keyboard())
                return
            
            context.user_data["monto"] = monto
            context.user_data["state"] = "ESPERA_PERIODICIDAD"
            await update.message.reply_text("Selecciona la periodicidad:", 
                                           reply_markup=self._periodicity_keyboard())
            return

        if state == "ESPERA_PERIODICIDAD":
            periodicidades_validas = ["diario", "semanal", "mensual", "anual"]
            periodicidad = mensaje.lower().strip()
            
            if periodicidad not in periodicidades_validas:
                await update.message.reply_text("⚠️ Selecciona una opción válida.", 
                                               reply_markup=self._periodicity_keyboard())
                return
            
            # Crear el presupuesto
            categoria = context.user_data.get("categoria")
            monto = context.user_data.get("monto")
            
            success, message = self.monevo_service.crear_presupuesto(
                usuario_id, categoria, monto, periodicidad
            )
            
            context.user_data.clear()
            emoji = "✅" if success else "⚠️"
            await update.message.reply_text(f"{emoji} {message}", reply_markup=ReplyKeyboardRemove())
            await update.message.reply_text("Menú principal:", reply_markup=self._main_menu_keyboard())
            return

        # Estados para actualizar presupuesto  
        if state == "ESPERA_MONTO_ACTUALIZAR":
            txt = mensaje.replace(".", "").replace(",", "")
            if not txt.isdigit():
                await update.message.reply_text("⚠️ Solo números. Intenta de nuevo.", reply_markup=self._cancel_keyboard())
                return
            
            monto = int(txt)
            if monto <= 0:
                await update.message.reply_text("⚠️ El monto debe ser mayor a 0. Intenta de nuevo.", 
                                               reply_markup=self._cancel_keyboard())
                return
            
            context.user_data["monto"] = monto
            context.user_data["state"] = "ESPERA_PERIODICIDAD_ACTUALIZAR"
            await update.message.reply_text("¿Cambiar también la periodicidad?", 
                                           reply_markup=self._periodicity_update_keyboard())
            return

        if state == "ESPERA_PERIODICIDAD_ACTUALIZAR":
            periodicidades_validas = ["diario", "semanal", "mensual", "anual", "mantener actual"]
            opcion = mensaje.lower().strip()
            
            if opcion not in periodicidades_validas:
                await update.message.reply_text("⚠️ Selecciona una opción válida.", 
                                               reply_markup=self._periodicity_update_keyboard())
                return
            
            # Actualizar el presupuesto
            categoria = context.user_data.get("categoria")
            monto = context.user_data.get("monto")
            periodicidad = None if opcion == "mantener actual" else opcion
            
            success, message = self.monevo_service.actualizar_presupuesto(
                usuario_id, categoria, monto, periodicidad
            )
            
            context.user_data.clear()
            emoji = "✅" if success else "⚠️"
            await update.message.reply_text(f"{emoji} {message}", reply_markup=ReplyKeyboardRemove())
            await update.message.reply_text("Menú principal:", reply_markup=self._main_menu_keyboard())
            return

        # Estados para gastos e ingresos
        if state in ("ESPERA_MONTO", "ESPERA_CONCEPTO"):
            if mensaje == "⬅️ Cambiar categoría":
                accion = context.user_data.get("accion", "gasto")
                context.user_data.clear()
                resumenes = self.monevo_service.obtener_resumen(str(update.message.from_user.id))
                await update.message.reply_text("Elige otra categoría:", reply_markup=ReplyKeyboardRemove())
                await update.message.reply_text("Categorías:", reply_markup=self._category_keyboard(resumenes, accion))
                return

        # 1) Flujo guiado por estados (monto/concepto)
        if state == "ESPERA_MONTO":
            # Limpiamos formato: quitamos puntos y comas
            txt = mensaje.replace(".", "").replace(",", "")
            if not txt.isdigit():
                await update.message.reply_text("⚠️ Solo números. Intenta de nuevo.", reply_markup=self._cancel_keyboard())
                return
            context.user_data["monto"] = int(txt)
            context.user_data["state"] = "ESPERA_CONCEPTO"
            await update.message.reply_text("Escribe el concepto (opcional). Envía '-' para omitir.", reply_markup=self._cancel_keyboard())
            return

        if state == "ESPERA_CONCEPTO":
            concepto = "" if mensaje == "-" else mensaje
            accion = context.user_data.get("accion")
            cat = context.user_data.get("categoria")
            monto = context.user_data.get("monto")

            if not accion or not cat or not monto:
                # Estado inconsistente: limpiar y volver al menú
                context.user_data.clear()
                await update.message.reply_text("Se reinició el flujo.", reply_markup=ReplyKeyboardRemove())
                await update.message.reply_text("Menú principal:", reply_markup=self._main_menu_keyboard())
                return

            if accion == "gasto":
                ok, msg = self.monevo_service.registrar_gasto(
                    usuario_id, cat, monto, concepto)
            else:
                ok, msg = self.monevo_service.registrar_ingreso(
                    usuario_id, cat, monto, concepto)

            context.user_data.clear()
            await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
            # Ofrecer atajos para seguir
            await update.message.reply_text(
                "¿Qué sigue?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Menú", callback_data="a=menu")],
                    [InlineKeyboardButton(
                        "Registrar otro", callback_data=f"a={accion}|c={cat}")],
                    [InlineKeyboardButton(
                        "📊 Ver resumen", callback_data="a=resumen")]
                ])
            )
            return

        # 2) Si no hay estado, usamos tu parser existente
        respuesta = self.message_processor.process_message(usuario_id, mensaje)

        # Si el parser no entendió (mensaje de ayuda), ofrecemos menú inline en vez de solo texto
        if respuesta.startswith("❌ No entendí el mensaje"):
            await update.message.reply_text(respuesta)
            await update.message.reply_text("También puedes usar el menú:", reply_markup=self._main_menu_keyboard())
            return

        await update.message.reply_text(respuesta)

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        mensaje = self._get_welcome_message()
        await update.message.reply_text(
            mensaje,
            reply_markup=self._main_menu_keyboard()
        )

    async def _safe_edit_message(self, query, text: str, reply_markup=None, parse_mode=None):
        """Edita un mensaje de forma segura, manejando el error de contenido duplicado"""
        try:
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        except BadRequest as e:
            if "Message is not modified" in str(e):
                # Si el mensaje es idéntico, responder con callback answer
                await query.answer("✅ Menú actualizado", show_alert=False)
                self.logger.debug(f"Mensaje duplicado detectado: {text[:50]}...")
            else:
                # Si es otro tipo de BadRequest, re-lanzar la excepción
                raise e

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja callbacks de botones inline"""
        query = update.callback_query
        await query.answer()
        data = query.data or ""

        # Mini-parser: a=<accion>|c=<categoria>
        params = dict(part.split("=", 1)
                      for part in data.split("|") if "=" in part)
        accion = params.get("a")
        categoria = params.get("c")
        usuario_id = str(query.from_user.id)

        if accion == "menu":
            await self._safe_edit_message(
                query, 
                "Menú principal:", 
                reply_markup=self._main_menu_keyboard()
            )
            return

        if accion == "resumen":
            resumenes = self.monevo_service.obtener_resumen(usuario_id)
            if not resumenes:
                await self._safe_edit_message(
                    query, 
                    "⚠️ No tienes presupuestos registrados aún.", 
                    reply_markup=self._main_menu_keyboard()
                )
                return
            # Enviamos resumen (texto) y luego botones por categoría
            texto = self._format_resumen(resumenes)
            await self._safe_edit_message(query, texto, parse_mode="Markdown")
            # Enviar un mensaje nuevo con acciones por categoría
            await query.message.reply_text(
                "Acciones por categoría:",
                reply_markup=self._resumen_actions_keyboard(resumenes)
            )
            return

        if accion == "crear":
            # Flujo para crear presupuesto
            context.user_data.update({
                "accion": "crear",
                "state": "ESPERA_CATEGORIA_NUEVA"
            })
            await self._safe_edit_message(query, "Crear nuevo presupuesto")
            await query.message.reply_text(
                "Escribe el nombre de la nueva categoría:",
                reply_markup=self._cancel_keyboard()
            )
            return

        if accion == "actualizar":
            # Seleccionar categoría a actualizar
            if not categoria:
                resumenes = self.monevo_service.obtener_resumen(usuario_id)
                if not resumenes:
                    await self._safe_edit_message(
                        query, 
                        "⚠️ No tienes presupuestos para actualizar.", 
                        reply_markup=self._main_menu_keyboard()
                    )
                    return
                await self._safe_edit_message(
                    query,
                    "Elige la categoría a actualizar:",
                    reply_markup=self._category_keyboard(resumenes, "actualizar")
                )
                return
            
            # Iniciar flujo de actualización para la categoría seleccionada
            context.user_data.update({
                "accion": "actualizar",
                "categoria": categoria,
                "state": "ESPERA_MONTO_ACTUALIZAR"
            })
            await self._safe_edit_message(
                query,
                f"Actualizar: *{categoria.capitalize()}*",
                parse_mode="Markdown"
            )
            await query.message.reply_text(
                "Escribe el nuevo monto del presupuesto:",
                reply_markup=self._cancel_keyboard()
            )
            return

        if accion in ("gasto", "ingreso"):
            # Si no hay categoría aún, mostrar selección basada en BD
            if not categoria:
                resumenes = self.monevo_service.obtener_resumen(usuario_id)
                if not resumenes:
                    await self._safe_edit_message(
                        query, 
                        "⚠️ Primero crea un presupuesto con /crear", 
                        reply_markup=self._main_menu_keyboard()
                    )
                    return
                await self._safe_edit_message(
                    query,
                    f"Selecciona la categoría para {'gasto' if accion == 'gasto' else 'ingreso'}:",
                    reply_markup=self._category_keyboard(resumenes, accion)
                )
                return

            # Si ya tenemos categoría, pedimos monto por TEXTO (no botones)
            context.user_data.update({
                "accion": accion,
                "categoria": categoria,
                "state": "ESPERA_MONTO"
            })

            # Edita el mensaje original SOLO con texto
            await self._safe_edit_message(
                query,
                f"Categoría: *{categoria.capitalize()}*",
                parse_mode="Markdown"
            )

            # Envía un MENSAJE NUEVO para pedir el monto
            await query.message.reply_text(
                "Escribe el monto en números (ej. 15000).",
                reply_markup=self._cancel_keyboard()
            )
            return

        if accion == "hist":
            resumenes = self.monevo_service.obtener_resumen(usuario_id)
            if not resumenes:
                await self._safe_edit_message(
                    query, 
                    "⚠️ No tienes presupuestos registrados aún.", 
                    reply_markup=self._main_menu_keyboard()
                )
                return
            
            # Si ya hay una categoría seleccionada, mostrar historial directamente
            if categoria:
                success, message, movimientos = self.monevo_service.obtener_historial(usuario_id, categoria)
                if not success:
                    await self._safe_edit_message(
                        query, 
                        f"⚠️ {message}", 
                        reply_markup=self._main_menu_keyboard()
                    )
                    return
                
                # Mostrar historial
                historial_texto = self._format_historial(categoria, movimientos)
                await self._safe_edit_message(query, historial_texto, parse_mode="Markdown")
                
                # Agregar botones de acción
                await query.message.reply_text(
                    "Acciones:",
                    reply_markup=self._category_quick_actions_keyboard(categoria)
                )
                return
            
            # Si no hay categoría, mostrar selector
            await self._safe_edit_message(
                query,
                "Elige una categoría para ver historial:",
                reply_markup=self._category_keyboard(resumenes, "hist")
            )
            return

        if accion == "ver":
            if not categoria:
                await query.answer("Selecciona una categoría", show_alert=False)
                return
            resumenes = self.monevo_service.obtener_resumen(usuario_id)
            for r in resumenes:
                if r.categoria == categoria:
                    await self._safe_edit_message(
                        query,
                        (f"📊 Presupuesto {categoria.capitalize()}:\n"
                         f"💰 Saldo: ${r.saldo:,.0f}\n"
                         f"📅 Periodicidad: {r.periodicidad}\n"
                         f"📈 Usado: {r.porcentaje_usado:.1f}%"),
                    )
                    # Atajos para actuar sobre la categoría
                    await query.message.reply_text(
                        "Acciones:",
                        reply_markup=self._category_quick_actions_keyboard(categoria)
                    )
                    return
            await self._safe_edit_message(
                query, 
                f"⚠️ No se encontró presupuesto '{categoria}'", 
                reply_markup=self._main_menu_keyboard()
            )
            return

        if accion == "confirm_eliminar":
            # Espera c=<categoria>
            if not categoria:
                await query.answer("Falta categoría", show_alert=False)
                return
            ok, msg = self.monevo_service.eliminar_presupuesto(usuario_id, categoria)
            await self._safe_edit_message(
                query,
                f"{'✅' if ok else '⚠️'} {msg}",
                reply_markup=self._main_menu_keyboard()
            )
            return

        if accion == "eliminar":
            # Mostrar confirmación
            if not categoria:
                # Elegir primero la categoría
                resumenes = self.monevo_service.obtener_resumen(usuario_id)
                if not resumenes:
                    await self._safe_edit_message(
                        query, 
                        "⚠️ No tienes presupuestos para eliminar.", 
                        reply_markup=self._main_menu_keyboard()
                    )
                    return
                await self._safe_edit_message(
                    query,
                    "Elige la categoría a eliminar:",
                    reply_markup=self._category_keyboard(resumenes, "eliminar")
                )
                return
            await self._safe_edit_message(
                query,
                f"¿Eliminar presupuesto '{categoria}'?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "✅ Confirmar", callback_data=f"a=confirm_eliminar|c={categoria}")],
                    [InlineKeyboardButton(
                        "❌ Cancelar", callback_data="a=menu")]
                ])
            )
            return

        # fallback
        await self._safe_edit_message(
            query, 
            "Menú principal:", 
            reply_markup=self._main_menu_keyboard()
        )

    async def handle_crear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /crear - Crear presupuesto"""
        usuario_id = str(update.message.from_user.id)
        args = context.args

        if len(args) < 2:
            await update.message.reply_text(
                "⚠️ Uso: /crear <categoria> <monto> [periodicidad]\n"
                "Ejemplo: /crear disfrute 500000 mensual"
            )
            return

        categoria = args[0].lower().strip()

        try:
            monto = float(args[1])
        except ValueError:
            await update.message.reply_text("⚠️ El monto debe ser un número válido.")
            return

        periodicidad = args[2].lower() if len(args) >= 3 else "mensual"

        success, message = self.monevo_service.crear_presupuesto(
            usuario_id, categoria, monto, periodicidad)

        emoji = "✅" if success else "⚠️"
        await update.message.reply_text(f"{emoji} {message}")

    async def handle_actualizar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /actualizar - Actualizar presupuesto existente"""
        usuario_id = str(update.message.from_user.id)
        args = context.args

        if len(args) < 2:
            await update.message.reply_text(
                "⚠️ Uso: /actualizar <categoria> <nuevo_monto> [nueva_periodicidad]\n"
                "Ejemplo: /actualizar disfrute 600000 semanal"
            )
            return

        categoria = args[0].lower().strip()

        try:
            monto = float(args[1])
        except ValueError:
            await update.message.reply_text("⚠️ El monto debe ser un número válido.")
            return

        periodicidad = args[2].lower() if len(args) >= 3 else None

        success, message = self.monevo_service.actualizar_presupuesto(
            usuario_id, categoria, monto, periodicidad)

        emoji = "✅" if success else "⚠️"
        await update.message.reply_text(f"{emoji} {message}")

    async def handle_eliminar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /eliminar - Eliminar presupuesto"""
        usuario_id = str(update.message.from_user.id)
        args = context.args

        if len(args) < 1:
            await update.message.reply_text(
                "⚠️ Uso: /eliminar <categoria>\n"
                "Ejemplo: /eliminar disfrute"
            )
            return

        categoria = args[0].lower().strip()

        success, message = self.monevo_service.eliminar_presupuesto(
            usuario_id, categoria)

        emoji = "✅" if success else "⚠️"
        await update.message.reply_text(f"{emoji} {message}")

    async def handle_historial(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /historial - Ver movimientos de una categoría"""
        usuario_id = str(update.message.from_user.id)
        args = context.args

        if len(args) < 1:
            await update.message.reply_text(
                "⚠️ Uso: /historial <categoria>\n"
                "Ejemplo: /historial moto"
            )
            return

        categoria = args[0].lower().strip()

        success, message, movimientos = self.monevo_service.obtener_historial(
            usuario_id, categoria)

        if not success:
            await update.message.reply_text(f"⚠️ {message}")
            return

        respuesta = self._format_historial(categoria, movimientos)
        await update.message.reply_text(respuesta, parse_mode="Markdown")

    async def handle_resumen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /resumen - Ver resumen de todos los presupuestos"""
        usuario_id = str(update.message.from_user.id)
        resumenes = self.monevo_service.obtener_resumen(usuario_id)

        if not resumenes:
            await update.message.reply_text("⚠️ No tienes presupuestos registrados aún.")
            return

        respuesta = self._format_resumen(resumenes)
        await update.message.reply_text(respuesta, parse_mode="Markdown")

    def _format_historial(self, categoria: str, movimientos: List[Movimiento]) -> str:
        """Formatea el historial de movimientos para mostrar"""
        respuesta = f"📜 *Historial de {categoria.capitalize()}*\n\n"

        for movimiento in movimientos:
            concepto_texto = f" - {movimiento.concepto}" if movimiento.concepto else ""
            fecha_formateada = movimiento.fecha.strftime("%d/%m/%Y %H:%M")

            if movimiento.tipo == "gasto":
                respuesta += f"💸 ${movimiento.monto:,.0f}{concepto_texto} ({fecha_formateada})\n"
            else:
                respuesta += f"💰 ${movimiento.monto:,.0f}{concepto_texto} ({fecha_formateada})\n"

        return respuesta

    def _format_resumen(self, resumenes: List[ResumenPresupuesto]) -> str:
        """Formatea el resumen de presupuestos para mostrar"""
        respuesta = "📊 *Resumen de Presupuestos*\n\n"

        total_saldo = 0
        for resumen in resumenes:
            total_saldo += resumen.saldo

            # Emoji basado en el porcentaje usado
            if resumen.porcentaje_usado <= 50:
                emoji_estado = "🟢"
            elif resumen.porcentaje_usado <= 80:
                emoji_estado = "🟡"
            else:
                emoji_estado = "🔴"

            respuesta += (f"{emoji_estado} *{resumen.categoria.capitalize()}*\n"
                        f"   💰 Saldo: ${resumen.saldo:,.0f}\n"
                        f"   📊 Usado: {resumen.porcentaje_usado:.1f}%\n"
                        f"   📅 {resumen.periodicidad.capitalize()}\n\n")

        respuesta += f"💵 *Total disponible: ${total_saldo:,.0f}*"

        return respuesta

    def _main_menu_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Resumen", callback_data="a=resumen")],
            [InlineKeyboardButton("💸 Gasto", callback_data="a=gasto"),
             InlineKeyboardButton("💰 Ingreso", callback_data="a=ingreso")],
            [InlineKeyboardButton("📜 Historial", callback_data="a=hist")],
            [InlineKeyboardButton("➕ Crear presupuesto", callback_data="a=crear"),
             InlineKeyboardButton("✏️ Actualizar", callback_data="a=actualizar")],
            [InlineKeyboardButton("🗑️ Eliminar presupuesto", callback_data="a=eliminar")]
        ])

    def _resumen_actions_keyboard(self, resumenes: list[ResumenPresupuesto]) -> InlineKeyboardMarkup:
        # Por cada categoría: Ver | +Ingreso | -Gasto | Historial
        rows = []
        for r in resumenes:
            c = r.categoria
            rows.append([InlineKeyboardButton(
                f"{c.capitalize()} – Ver", callback_data=f"a=ver|c={c}")])
            rows.append([
                InlineKeyboardButton(
                    "+Ingreso", callback_data=f"a=ingreso|c={c}"),
                InlineKeyboardButton("-Gasto", callback_data=f"a=gasto|c={c}"),
                InlineKeyboardButton(
                    "Historial", callback_data=f"a=hist|c={c}")
            ])
        # Botón volver
        rows.append([InlineKeyboardButton("⬅️ Menú", callback_data="a=menu")])
        return InlineKeyboardMarkup(rows)

    def _category_keyboard(self, resumenes: list[ResumenPresupuesto], accion: str) -> InlineKeyboardMarkup:
        # Genera botones de categorías para la acción dada
        rows = []
        for r in resumenes:
            c = r.categoria
            rows.append([InlineKeyboardButton(c.capitalize(),
                        callback_data=f"a={accion}|c={c}")])
        rows.append([InlineKeyboardButton("⬅️ Menú", callback_data="a=menu")])
        return InlineKeyboardMarkup(rows)

    def _category_quick_actions_keyboard(self, categoria: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("+Ingreso", callback_data=f"a=ingreso|c={categoria}"),
             InlineKeyboardButton("-Gasto", callback_data=f"a=gasto|c={categoria}")],
            [InlineKeyboardButton("📜 Historial", callback_data=f"a=hist|c={categoria}")],
            [InlineKeyboardButton("📊 Resumen", callback_data="a=resumen"),
             InlineKeyboardButton("⬅️ Menú", callback_data="a=menu")]
        ])

    def _periodicity_keyboard(self) -> ReplyKeyboardMarkup:
        """Teclado para seleccionar periodicidad al crear presupuesto"""
        return ReplyKeyboardMarkup([
            ["Diario", "Semanal"],
            ["Mensual", "Anual"],
            ["❌ Cancelar"]
        ], resize_keyboard=True, one_time_keyboard=True)
    
    def _periodicity_update_keyboard(self) -> ReplyKeyboardMarkup:
        """Teclado para actualizar periodicidad"""
        return ReplyKeyboardMarkup([
            ["Diario", "Semanal"],
            ["Mensual", "Anual"],
            ["Mantener actual"],
            ["❌ Cancelar"]
        ], resize_keyboard=True, one_time_keyboard=True)

    def _cancel_keyboard(self) -> ReplyKeyboardMarkup:
        # ReplyKeyboard minimal para controlar mientras se teclea monto/concepto
        return ReplyKeyboardMarkup([["❌ Cancelar", "⬅️ Cambiar categoría"]], resize_keyboard=True)

    def _get_welcome_message(self) -> str:
        """Mensaje de bienvenida"""
        return """
👋 ¡Hola! Bienvenido a *Monevo*.

🤖 *Comandos disponibles:*

📝 *Gestión de Presupuestos:*
• `/crear <categoria> <monto> [periodicidad]` - Crear presupuesto
• `/actualizar <categoria> <monto> [periodicidad]` - Actualizar presupuesto
• `/eliminar <categoria>` - Eliminar presupuesto

📊 *Consultas:*
• `/resumen` - Ver todos los presupuestos
• `/historial <categoria>` - Ver movimientos de una categoría
• `Ver presupuesto <categoria>` - Ver detalles de un presupuesto

💸 *Registro de Movimientos:*
• `Gasté <monto> de <categoria> por <concepto>`
• `Añadí <monto> a <categoria> por <concepto>`

📌 *Nota:* Para registrar movimientos, la categoría debe existir previamente.

💡 *Ejemplo completo:*
1. `/crear moto 100000 mensual`
2. `Gasté 15000 de moto por gasolina`
3. `Ver presupuesto moto`
"""
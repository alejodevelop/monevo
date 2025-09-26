
---

## 🚀 **Monevo** — *Bot de Telegram para presupuestos personales*

> Minimalista, rápido y sin dependencias externas. Registra gastos e ingresos en lenguaje natural y consulta resúmenes por categoría.

---

### ✨ **Características principales**

- **Registro rápido por texto:**  
    Ejemplo:  
    ```
    Gasté 15000 de moto por gasolina
    Añadí 50000 a ahorro por bono
    ```
- **Comandos guiados:**  
    Crear, actualizar, eliminar presupuestos, ver resumen e historial.
- **Persistencia en SQLite:**  
    Sin dependencias externas.
- **Arquitectura limpia:**  
    - Modelos `dataclass`
    - Servicios y fachada
    - Parser de mensajes
    - Handlers de Telegram

---

### 🧱 **Estructura del proyecto**

```plaintext
/bot.py                 # Arranque del bot (polling)
/telegram_handlers.py   # UI y flujos en Telegram
/message_parser.py      # Intents: gasto/ingreso/ver
/services.py            # Presupuesto/Movimiento + Facade
/database.py            # SQLiteRepository
/models.py              # Dataclasses
/config.py              # .env + validaciones
/exceptions.py          # Errores amigables
/requirements.txt       # Dependencias
```

---

### ⚙️ **Requisitos**

- **Python 3.10+**
- **Token de bot de Telegram** en `.env`:

    ```env
    MONEVO_API_KEY_TELEGRAM=xxx
    DATABASE_NAME=monevo.db
    TIMEZONE=America/Bogota
    LOG_LEVEL=INFO
    ```

- Variables y validaciones se cargan desde `config.py`.

---

### 🚀 **Instalación local**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # crea tu .env si quieres partir de un template
python bot.py
```

> El bot usa polling (no necesitas exponer puertos).

---

### 🧪 **Uso rápido en Telegram**

- **Crear presupuesto:**  
    `/crear moto 100000 mensual`
- **Registrar movimiento:**  
    `Gasté 15000 de moto por gasolina`  
    `Añadí 50000 a moto por ajuste`
- **Consultar:**  
    `/resumen`  
    `/historial moto`  
    `Ver presupuesto moto`

---

### 🧠 **Reglas de negocio clave**

- Categorías y tipos normalizados; valida montos > 0 y periodicidades.
- Resumen calcula saldo = presupuesto + ingresos − gastos; % usado basado en gastos/monto inicial.
- Mensajería de error coherente con excepciones del dominio.

---

### 🗄️ **Base de datos**

- Se inicializa automáticamente (tablas presupuestos y movimientos, índices).
- El archivo por defecto es `monevo.db` (configurable).

---
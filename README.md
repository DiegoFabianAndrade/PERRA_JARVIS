# 🤖 PERRA_JARVIS

> **Asistente personal inteligente tipo Jarvis, 100% en tu bolsillo vía Telegram, con control operativo directo sobre tu computador Windows y $0.00 USD en costos de infraestructura.**

---

## 🌟 ¿Qué es PERRA_JARVIS?

Inspirado en la visión de sistemas de IA autónomos locales (como *OpenJarvis*), **PERRA_JARVIS** es un asistente ejecutor diseñado para que puedas controlar tu computador personal desde el celular en cualquier momento y lugar, recibir reportes financieros en tiempo real y ejecutar tareas por voz o texto.

---

## 🦾 Capacidades Principales

### 1. 📱 Control Remoto Total de tu PC (Windows)
- 📸 **Captura de Pantalla en Tiempo Real:** "¿Qué tengo abierto en el PC?" -> Recibe un screenshot instantáneo en Telegram.
- 🔋 **Telemetría de Hardware:** Monitoreo de batería (% y estado de carga), consumo de CPU, memoria RAM y espacio en disco.
- 🔒 **Seguridad Inmediata:** Bloqueo de estación de trabajo (`LockWorkStation`) con un solo toque desde la calle.
- 🚀 **Lanzador de Apps:** "Abre Spotify", "Abre Chrome", "Abre VS Code".
- 🔊 **Control Multimedia:** Subir/bajar volumen, silenciar (Mute) y reproducir/pausar música.
- 📁 **Gestión de Descargas:** Listar y consultar archivos descargados recientemente.
- ⌨️ **Terminal Remota:** Ejecutar comandos de PowerShell vía `/run <comando>` con salida protegida.

### 2. 🧠 Cerebro Inteligente Híbrido (Gemini 2.5 Flash + Fallback)
- **Comprensión en Lenguaje Natural:** Entiende órdenes conversacionales sin necesidad de comandos rígidos.
- **Notas de Voz:** Puedes enviarle audios de voz por Telegram; el asistente los escucha, los transcribe y ejecuta la acción solicitada.
- **Function Calling:** El modelo de IA decide autónomamente qué herramienta del PC activar según tu petición.
- **Modo Offline/Local:** Si no hay conexión o no tienes API Key configurada, cuenta con un motor semántico local integrado.

### 3. 📊 Tracker Financiero (Heredado de DollarBot)
- 🏛️ **TRM Oficial USD/COP:** Datos abiertos en tiempo real de la Superintendencia Financiera de Colombia.
- 💎 **Criptomonedas:** Cotización 24h de Bitcoin, Ethereum y Solana.
- 📈 **Gráficas Visuales Dark Mode:** Generación de gráficos históricos en formato PNG con `matplotlib`.

### 4. 🛡️ Seguridad Blindada
- **Whitelist Estricta:** El bot solo responde al Telegram Chat ID del dueño (`1257398092`). Cualquier otra persona que intente interactuar es rechazada automáticamente.

---

## 📂 Arquitectura del Proyecto

```
PERRA_JARVIS/
├── .env                  # Variables de entorno y tokens secretos (ignorado por Git)
├── .env.example          # Plantilla de configuración
├── config.py             # Lectura y validación de parámetros del sistema
├── main.py               # Entrada principal del bot asíncrono
├── requirements.txt      # Dependencias de Python
├── modules/
│   ├── pc_controller.py  # Control de Windows: capturas, hardware, volumen, apps
│   ├── market_tracker.py # TRM Colombia, criptos y gráficas con matplotlib
│   ├── ai_brain.py       # Cerebro con Gemini 2.5 Flash, notas de voz y tools
│   └── telegram_ui.py    # Menú táctil (Inline Keyboards), comandos y callbacks
└── scripts/
    ├── run.bat           # Ejecución interactiva con consola visible
    ├── start_hidden.vbs  # Ejecución 100% invisible en segundo plano
    └── stop_jarvis.bat   # Detener instancias en ejecución
```

---

## 🚀 Puesta en Marcha Rápida

### 1. Requisitos
- Windows 10 u 11
- Python 3.10 o superior

### 2. Configurar variables (.env)
Asegúrate de que tu archivo `.env` contenga:
```ini
TELEGRAM_BOT_TOKEN=tu_token_de_telegram
ALLOWED_CHAT_ID=1257398092
GEMINI_API_KEY=tu_api_key_gratis_de_gemini
ASSISTANT_NAME=PERRA_JARVIS
```
> *Nota: Puedes obtener tu Gemini API Key gratis en [Google AI Studio](https://aistudio.google.com/app/apikey).*

### 3. Ejecutar
- **Modo desarrollo (con ventana de terminal):**
  Doble clic en `scripts/run.bat` o:
  ```powershell
  python main.py
  ```
- **Modo silencioso 24/7 (segundo plano invisible):**
  Doble clic en `scripts/start_hidden.vbs`

---

## ☁️ ¿Y Azure? Estrategia de Costo $0.00
- **PC Local:** El control del hardware y las acciones en tu equipo corren en tu propia máquina a costo **$0.00 USD**.
- **IA:** La API de Gemini Flash ofrece 1,500 solicitudes diarias gratuitas (**$0.00 USD**).
- **Azure (Opcional):** Si en el futuro deseas que Jarvis responda cuando tu PC esté completamente apagado, se puede desplegar un *Azure Function Serverless* (1 millón de peticiones gratis al mes) como agente de relevo en la nube sin tocar tu crédito universitario.

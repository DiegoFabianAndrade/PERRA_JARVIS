# ☁️ PERRA_JARVIS 24/7 - Arquitectura Híbrida Serverless ($0.00 USD)

Este módulo permite que **PERRA_JARVIS** funcione **24/7 de forma ininterrumpida en la nube**, respondiendo desde tu móvil en Telegram incluso cuando tu computador personal esté **completamente apagado, suspendido o sin conexión**.

---

## 💰 Verificación de Costo Mínimo: $0.00 USD Garantizado

Operamos bajo una política estricta de costo cero mensual:

1. **Azure Functions (Consumption / Dynamic Plan en Linux):**
   * **1,000,000 de ejecuciones gratuitas** al mes de por vida.
   * **400,000 GB-segundos** de cómputo gratis al mes.
   * Con ~1,000 a 3,000 interacciones al mes, solo consumes el **0.3%** del límite gratuito.
2. **Cuenta de Almacenamiento Azure (`stperrajarvis125` Standard_LRS):**
   * Almacenamiento básico de cola y estado (< 15 MB). Costo mensual: ~$0.0003 USD (menos de 2 pesos colombianos), cubierto al 100% por tu suscripción de *Azure for Students*.
3. **Google Gemini 3.5 Flash Lite:**
   * Google AI Studio Free Tier (15 peticiones por minuto gratis, $0.00 USD).
4. **Google Calendar API v3:**
   * Cupo gratuito oficial de Google Cloud (1,000,000 peticiones diarias gratuitas).
5. **Open-Meteo & Superfinanciera TRM:**
   * APIs públicas abiertas con acceso libre ($0.00 USD).
6. **Tu saldo de estudiante de Azure ($100 USD):**
   * Permanece **intacto**.

---

## 🔄 Arquitectura Híbrida en Producción

```
                       ┌──> [ ☁️ Azure Serverless Core (24/7 SIEMPRE ACTIVO) ]
                       │       • Responde en Telegram 24/7 con el PC APAGADO.
                       │       • Atiende mensajes de voz (.ogg) con Gemini Flash Lite.
                       │       • Gestiona Google Calendar (crear y leer eventos).
                       │       • Despacha correos vía Gmail SMTP.
                       │       • Consulta Clima Bogotá y TRM oficial Superfinanciera.
                       │       • Analiza documentos PDF y código adjunto.
                       │       • Encola órdenes para cuando tu computador se encienda.
[ 📱 Tu Telegram ] ────┤
                       │
                       └──> [ 💻 Local Windows Companion (Cuando tu PC está ENCENDIDO) ]
                               • Envía señal de vida (Heartbeat) a la nube cada 25s.
                               • Ejecuta pantallazos en tiempo real (`pyautogui`).
                               • Bloquea la sesión de Windows de inmediato.
                               • Corre suites de pruebas unitarias locales (`mvnw`, `pytest`).
                               • Monitorea y administra repositorios Git locales.
```

---

## 🌐 Recursos Desplegados en Azure

* **Grupo de Recursos:** `rg-perra-jarvis` (Región: `eastus`)
* **Storage Account:** `stperrajarvis125` (Standard_LRS)
* **Function App:** `func-perra-jarvis` (Linux Python 3.11 Serverless)
* **URL Webhook Oficial:**
  ```
  https://func-perra-jarvis.azurewebsites.net/api/telegram_webhook
  ```
* **Endpoint de Salud:**
  ```
  https://func-perra-jarvis.azurewebsites.net/api/health
  ```

---

## 🚀 Cómo Operar el Sistema

1. **En la Nube (Automático):**
   * Ya está configurado con Telegram Webhook activo. No requiere ninguna acción tuya.
2. **En tu PC (Modo Companion):**
   * Cuando enciendas tu computador, simplemente ejecuta:
     ```powershell
     python main.py
     ```
   * Detectará automáticamente el Webhook 24/7 activo y sincronizará las funciones locales de hardware sin interrumpir la nube.

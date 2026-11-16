# ☁️ PERRA_JARVIS 24/7 - Despliegue en Azure Serverless ($0.00 USD)

Este módulo permite que **PERRA_JARVIS** funcione **24/7 en la nube cuando tu computador personal esté completamente apagado**.

---

## 💰 ¿Por qué el costo es $0.00 USD?

En Microsoft Azure (y con tu suscripción de **Azure for Students**):
1. **Azure Functions (Consumption Plan):** Te da **1,000,000 de ejecuciones gratuitas cada mes de por vida**.
2. **Cómputo:** Los primeros 400,000 GB-segundos de cómputo al mes son gratis.
3. **Tu saldo de estudiante ($100 USD):** Queda **100% intacto**. No se consumirá porque el asistente opera dentro del cupo gratuito mensual de Azure.

---

## 🔄 ¿Cómo interactúan el PC y Azure?

```
                     ┌──> [ 💻 Tu PC (Cuando está PRENDIDO) ]
                     │       • Control total de hardware, pantalla, volumen y apps.
[ 📱 Tu Telegram ] ──┤
                     │
                     └──> [ ☁️ Azure Function (Cuando tu PC está APAGADO) ]
                             • Responde 24/7 desde la nube.
                             • Gestiona Gmail, Calendarios, Clima, TRM y Criptos.
                             • Guarda tus órdenes para el agente de código en cola.
```

---

## 🚀 Despliegue Rápido en Azure (3 Pasos)

### 1. Iniciar sesión en Azure
Si tienes instalada la extensión de Azure en VS Code o Azure CLI:
```bash
az login
```

### 2. Crear el Function App Serverless (Linux / Python)
```powershell
# Crear grupo de recursos (ej: en East US 2)
az group create --name rg-jarvis --location eastus2

# Crear cuenta de almacenamiento básica
az storage account create --name stjarvisdiego --location eastus2 --resource-group rg-jarvis --sku Standard_LRS

# Crear la Azure Function en plan Consumption ($0.00)
az functionapp create --resource-group rg-jarvis --consumption-plan-location eastus2 --runtime python --runtime-version 3.11 --functions-version 4 --name perra-jarvis-cloud --storage-account stjarvisdiego --os-type Linux
```

### 3. Configurar Variables y Desplegar Webhook
Configura las mismas variables de tu `.env`:
```powershell
az functionapp config appsettings set --name perra-jarvis-cloud --resource-group rg-jarvis --settings TELEGRAM_BOT_TOKEN="tu_token_aqui" ALLOWED_CHAT_ID="1257398092"
```

Luego despliega la carpeta `azure/`:
```bash
func azure functionapp publish perra-jarvis-cloud
```

Y enlazas el Webhook de Telegram:
```
https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://perra-jarvis-cloud.azurewebsites.net/api/telegram_webhook
```

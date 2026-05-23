# AlertaEC — Sistema de Alerta Temprana de Ingresos a Emergencias

> **hackIAthon Viamatica 2025 · Reto 4**  
> Agente IA que valida cobertura de seguros en tiempo real cuando un paciente ingresa a urgencias — notificando simultáneamente al hospital y a la aseguradora en menos de 5 segundos.

---

## Tabla de Contenidos

- [El Problema](#el-problema)
- [La Solución](#la-solución)
- [Arquitectura del Sistema](#arquitectura-del-sistema)
- [Flujo de Trabajo](#flujo-de-trabajo)
- [Contexto Ecuador](#contexto-ecuador--por-qué-aquí)
- [Stack Tecnológico](#stack-tecnológico)
- [Configuración e Instalación Local](#configuración_e_instalación_local)

---

## El Problema

Cuando un paciente llega a urgencias, el personal de admisiones enfrenta una situación crítica:

1. El paciente necesita atención **inmediata**
2. La aseguradora necesita saber si tiene **cobertura válida o no**
3. Verificar la póliza manualmente toma entre **30 minutos, 4 horas o incluso 1 día**
4. Mientras tanto, el hospital está asumiendo un **riesgo financiero sin garantía**
5. Si es en el lugar donde se encuentra asegurado/a igual la atención es **lenta** por procesos tediosos o terceros
6. En caso de ser un accidente de tránsito, nadie recuerda activar el **SOAT** primero

**Resultado:** demoras en la atención, conflictos hospital-aseguradora, y pérdidas económicas para ambas partes o en el peor de los casos **VITALES**.

---

## La Solución

**AlertaEC** es un agente IA que, al recibir el ingreso de un paciente a emergencias vía webhook, ejecuta automáticamente en paralelo:

```
Cédula del paciente ingresa
        │
        ▼
┌────────────────────────────────────────────────────────┐
│  AGENTE IA (Claude Sonnet)                             │
│                                                        │
│  1. Valida cédula ecuatoriana                          │
│  2. Consulta póliza en Notion                          │
│  3. Verifica pre-existencias                           │
│  4. Analiza cobertura + SOAT(de ser necesario)         │
│  5. Genera score de riesgo (0-100)                     │
│  6. Crea caso en Notion                                │
│  7. Notifica hospital + aseguradora                    │
└────────────────────────────────────────────────────────┘
        │
        ▼
Respuesta completa en < 10 segundos
```

---

## Arquitectura del Sistema

```
┌─────────────────┐    POST /api/webhook/admision     ┌─────────────────────────┐
│   HIS Hospital  │ ────────────────────────────────► │  FastAPI Backend        │
│   (o formulario │                                   │  (orquestador)          │
│   web de        │                                   │                         │
│   admisiones)   │                                   │  ┌─────────────────┐    │
└─────────────────┘                                   │  │ Notion Service  │◄──┐│
                                                      │  │ - Pólizas       │   ││
                                                      │  │ - Pre-exist.    │   ││
                                                      │  │ - Casos activos │   ││
                                                      │  └─────────────────┘   ││
                                                      │                        ││
                                                      │  ┌─────────────────┐   ││
                                                      │  │ Claude Agent    │───┘│
                                                      │  │ (análisis IA)   │    │
                                                      │  └─────────────────┘    │
                                                      │                         │
                                                      │  ┌─────────────────┐    │
                                                      │  │ Notification    │    │
                                                      │  │ Service         │    │
                                                      │  │ - Email (SG)    │    │
                                                      │  │ - SMS (Twilio)  │    │
                                                      │  └─────────────────┘    │
                                                      └─────────────────────────┘
                                                               │
                                          ┌────────────────────┼────────────────────┐
                                          ▼                    ▼                    ▼
                                       Médico                Gestor                 SMS
                                    de admisión             de casos             Aseguradora
```

---

## Flujo de Trabajo Detallado

### Paso 1: Disparo del Webhook
El personal de admisiones ingresa manualmente en el formulario web (o la escanea la cédula del paciente). Esto envía automáticamente un `POST` con los datos al sistema.

### Paso 2: Validación de Cédula Ecuatoriana
El sistema valida la cédula con el **algoritmo oficial ecuatoriano** (módulo 10, verificación de provincia 01-24 o 30 para extranjeros/IESS).

### Paso 3: Consultas Paralelas a Notion
En paralelo (usando `asyncio.gather`):
- Obtiene los datos completos de la **póliza del paciente**
- Obtiene el historial de **pre-existencias declaradas**

### Paso 4: Análisis con Agente Claude
El agente recibe todo el contexto y evalúa:
- ¿La póliza está **vigente**?
- ¿**Cubre emergencias**?
- ¿Está cumplido el **período de carencia**?
- ¿Hay **límite suficiente** disponible?
- ¿El motivo de la emergencia se relaciona con alguna **pre-existencia** declarada o no declarada?
- ¿Es un **accidente de tránsito**? → Activar SOAT (ANT Ecuador)

### Paso 5: Score de Riesgo (0–100)

| Rango | Estado | Acción |
|-------|--------|--------|
| 0–30 | CONFIRMADA | Proceder con atención completa |
| 31–70 | EN REVISIÓN | Atención urgente básica, gestor revisa en < 1 hora |
| 71–100 | ALERTA CRÍTICA | Atención urgente garantizada, revisión inmediata |
| N/A | SIN COBERTURA | Sin póliza — evaluar IESS, MSP, particular |

> **Nota importante:** El sistema SIEMPRE garantiza la atención médica urgente. La cobertura se resuelve post-atención si es necesario. Ningún paciente puede ser negado atención de emergencia por motivos de cobertura.

### Paso 6: Notificaciones Simultáneas
En paralelo se envían:

**Al Hospital (médico de admisiones):**
- Estado de cobertura y score
- Límite financiero disponible
- Alertas específicas del caso
- Recomendaciones de admisión
- Documentos que debe recopilar
- Datos del gestor de casos de la aseguradora

**A la Aseguradora (gestor de casos + departamento):**
- Alerta de nuevo ingreso con todos los datos
- Análisis de pre-existencias
- Impacto financiero estimado
- Enlace directo al caso en Notion
- Recomendaciones de acción

---

## Configuración e Instalación Local

Sigue estos pasos para clonar el proyecto, configurar las variables de entorno y ejecutar el agente de Alerta Temprana en tu máquina.

### Prerrequisitos
* Python 3.11.x.
* Una cuenta en [Anthropic](https://console.anthropic.com/) (para el modelo de IA).
* Una cuenta en [Notion](https://www.notion.so/my-integrations) (con acceso a las bases de datos integradas).
* Una cuenta en [Twilio](https://www.twilio.com/) y [SendGrid](https://sendgrid.com/) para los módulos de alertas.

---

### Paso 1: Clonar el repositorio y preparar el entorno

Abre tu terminal y ejecuta los siguientes comandos:

```bash
# 1. Clonar el repositorio
git clone [https://github.com/ElAlfa3007/reto4-AlertaTemprana-de-emergencias.git](https://github.com/ElAlfa3007/reto4-AlertaTemprana-de-emergencias.git)

# 2. Entrar al directorio del proyecto
cd reto4-AlertaTemprana-de-emergencias

# 3. Crear un entorno virtual (Recomendado)
python -m venv venv

# 4. Activar el entorno virtual
# En Windows:
venv\Scripts\activate
# En Linux/macOS:
source venv/bin/activate

# 5. Instalar las dependencias del proyecto
pip install -r requirements.txt
```
### Paso 2: Crear y configurar el archivo de variables de entorno (`.env`)

El proyecto utiliza variables de entorno para gestionar las credenciales de servicios externos de forma segura. 

1. En la raíz del proyecto, crea un archivo de texto plano y llámalo exactamente **`.env`** (debe empezar con un punto y no llevar extensión `.txt`).
2. Copia la siguiente estructura exacta dentro del archivo. 
3. Rellena tus claves privadas en los campos que están vacíos (`ANTHROPIC_API_KEY`, `NOTION_TOKEN`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` y `SENDGRID_API_KEY`). Los identificadores de las bases de datos, el teléfono de origen y el correo remitente **ya están configurados por defecto** y no necesitan modificarse.

```env
# --- Configuración del Modelo de IA ---
ANTHROPIC_API_KEY=tu_clave_de_anthropic_aqui

# --- Integración con Notion ---
NOTION_TOKEN=tu_token_secreto_de_notion_aqui

# Identificadores fijos de las Bases de Datos del Reto
NOTION_POLIZAS_DB=7c1cd9afa42342549530a79a2b238bec
NOTION_CASOS_DB=0f7798f0d6a9413f95f087267652f12f
NOTION_PREEXISTENCIAS_DB=03c447e9d67c4cd1a268e111ef08c694

# --- Módulo de Notificaciones (Alertas) ---
TWILIO_ACCOUNT_SID=tu_account_sid_de_twilio_aqui
TWILIO_AUTH_TOKEN=tu_auth_token_de_twilio_aqui
TWILIO_PHONE_FROM=+19129142159

SENDGRID_API_KEY=tu_api_key_de_sendgrid_aqui
EMAIL_FROM=alertaec@r4viamatica.com

# --- Configuración del Entorno ---
ENVIRONMENT=production
```

---
## 🇪🇨 Contexto Ecuador — Por qué aquí

### Regulación aplicada

| Marco Legal | Aplicación en AlertaEC |
|-------------|------------------------|
| **LOPDP 2021** (Ley Orgánica de Protección de Datos) | Datos médicos como categoría especial, consentimiento explícito requerido |
| **Ley General de Seguros** (SBS) | Reglas de carencia, cobertura mínima, período de gracia |
| **SOAT** (ANT Ecuador) | Detección automática de accidentes de tránsito, activación prioritaria |
| **Codificación CIE-10** | Sistema usado por IESS y MSP para diagnósticos |

### El SOAT — Diferenciador único de Ecuador
El **Seguro Obligatorio de Accidentes de Tránsito** cubre hasta $5,000 USD y debe activarse **antes** del seguro privado en casos de accidentes de tráfico. AlertaEC detecta automáticamente estos casos y genera la alerta correspondiente, evitando que la aseguradora privada pague lo que corresponde al SOAT.

### Penetración de seguros en Ecuador
- ~37 aseguradoras activas controladas por la SBS
- Primas netas anuales: ~$3B USD
- Penetración del seguro: 2.1% del PIB (vs. promedio LATAM 3.2%)
- Alta oportunidad de digitalización — la mayoría de aseguradoras aún usan procesos manuales (por no decir TODAS)

### Validación de cédula ecuatoriana
El sistema implementa el **algoritmo oficial de verificación de cédulas** del Registro Civil ecuatoriano:
- 10 dígitos
- Primeros 2 dígitos = provincia (01-24) o 30 (IESS/extranjeros)
- Algoritmo de módulo 10 con coeficientes alternados [2,1,2,1,2,1,2,1,2]

---

## Stack Tecnológico

| Capa | Tecnología | Justificación |
|------|-----------|---------------|
| **IA / Agente** | Claude Sonnet (Anthropic) | Mejor comprensión de documentos médicos en español, razonamiento sobre coberturas complejas |
| **Backend** | FastAPI (Python) | Alta performance, tipado estricto con Pydantic, async nativo, Swagger automático |
| **Base de datos** | Notion API | Requerimiento del hackathon, permite gestión visual de pólizas sin código |
| **Notificaciones SMS** | Twilio | API estable, soporte Ecuador, números locales disponibles |
| **Notificaciones Email** | SendGrid | Alta entregabilidad, plantillas profesionales, gratuito hasta 100 emails/día |
| **Frontend** | HTML/CSS/JS vanilla | Sin dependencias, carga instantánea, funciona en cualquier dispositivo del hospital |
| **Deploy** | Railway / Render / Fly.io | Deploy en minutos, SSL automático, costo cero en tier gratuito |

---



<div align="center">

**AlertaEC** · hackIAthon Viamatica 2025 · Reto 4  
*Porque cada segundo cuenta en una emergencia*

</div>

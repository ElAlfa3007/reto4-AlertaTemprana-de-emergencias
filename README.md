# 🚨 AlertaEC — Sistema de Alerta Temprana de Ingresos a Emergencias

> **hackIAthon Viamatica 2025 · Reto 4**  
> Agente IA que valida cobertura de seguros en tiempo real cuando un paciente ingresa a urgencias — notificando simultáneamente al hospital y a la aseguradora en menos de 5 segundos.

---

## 📋 Tabla de Contenidos

- [El Problema](#-el-problema)
- [La Solución](#-la-solución)
- [Arquitectura del Sistema](#-arquitectura-del-sistema)
- [Flujo de Trabajo](#-flujo-de-trabajo)
- [Contexto Ecuador](#-contexto-ecuador--por-qué-aquí)
- [Stack Tecnológico](#-stack-tecnológico)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Instalación y Configuración](#-instalación-y-configuración)
- [Configurar Notion](#-configurar-notion)
- [Uso de la API](#-uso-de-la-api)
- [Datos de Prueba (Demo)](#-datos-de-prueba-demo)
- [Roadmap Enterprise](#-roadmap-enterprise)
- [Marco Legal Ecuador](#-marco-legal-ecuador)
- [Equipo](#-equipo)

---

## 🔴 El Problema

Cuando un paciente llega a urgencias, el personal de admisiones enfrenta una situación crítica:

1. El paciente necesita atención **inmediata**
2. La aseguradora necesita saber si tiene **cobertura válida**
3. Verificar la póliza manualmente toma entre **30 minutos y 4 horas**
4. Mientras tanto, el hospital está asumiendo un **riesgo financiero sin garantía**
5. Si hay un accidente de tránsito, nadie recuerda activar el **SOAT** primero

**Resultado:** demoras en la atención, conflictos hospital-aseguradora, y pérdidas económicas para ambas partes.

---

## ✅ La Solución

**AlertaEC** es un agente IA que, al recibir el ingreso de un paciente a emergencias vía webhook, ejecuta automáticamente en paralelo:

```
Cédula del paciente ingresa
        │
        ▼
┌───────────────────────────────────────┐
│  AGENTE IA (Claude Sonnet)            │
│                                       │
│  1. Valida cédula ecuatoriana         │
│  2. Consulta póliza en Notion         │
│  3. Verifica pre-existencias          │
│  4. Analiza cobertura + SOAT          │
│  5. Genera score de riesgo (0-100)    │
│  6. Crea caso en Notion               │
│  7. Notifica hospital + aseguradora   │
└───────────────────────────────────────┘
        │
        ▼
Respuesta completa en < 5 segundos
```

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────┐    POST /api/webhook/admision    ┌─────────────────────────┐
│   HIS Hospital  │ ────────────────────────────────► │  FastAPI Backend        │
│   (o formulario │                                   │  (orquestador)          │
│   web de        │                                   │                         │
│   admisiones)   │                                   │  ┌─────────────────┐    │
└─────────────────┘                                   │  │ Notion Service  │◄──┐│
                                                      │  │ - Pólizas       │  ││
                                                      │  │ - Pre-exist.    │  ││
                                                      │  │ - Casos activos │  ││
                                                      │  └─────────────────┘  ││
                                                      │                        ││
                                                      │  ┌─────────────────┐  ││
                                                      │  │ Claude Agent    │──┘│
                                                      │  │ (análisis IA)   │   │
                                                      │  └─────────────────┘   │
                                                      │                        │
                                                      │  ┌─────────────────┐   │
                                                      │  │ Notification    │   │
                                                      │  │ Service         │   │
                                                      │  │ - Email (SG)    │   │
                                                      │  │ - SMS (Twilio)  │   │
                                                      │  └─────────────────┘   │
                                                      └─────────────────────────┘
                                                               │
                                          ┌────────────────────┼────────────────────┐
                                          ▼                    ▼                    ▼
                                   📧 Médico              📧 Gestor            📱 SMS
                                   de admisión            de casos             Aseguradora
```

---

## 🔄 Flujo de Trabajo Detallado

### Paso 1: Disparo del Webhook
El personal de admisiones escanea la cédula del paciente (o la ingresa manualmente en el formulario web). Esto envía automáticamente un `POST` con los datos al sistema.

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
| 0–30 | ✅ CONFIRMADA | Proceder con atención completa |
| 31–70 | ⚠️ EN REVISIÓN | Atención urgente básica, gestor revisa en < 1 hora |
| 71–100 | 🚨 ALERTA CRÍTICA | Atención urgente garantizada, revisión inmediata |
| N/A | ❌ SIN COBERTURA | Sin póliza — evaluar IESS, MSP, particular |

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
- Alta oportunidad de digitalización — la mayoría de aseguradoras aún usan procesos manuales

### Validación de cédula ecuatoriana
El sistema implementa el **algoritmo oficial de verificación de cédulas** del Registro Civil ecuatoriano:
- 10 dígitos
- Primeros 2 dígitos = provincia (01-24) o 30 (IESS/extranjeros)
- Algoritmo de módulo 10 con coeficientes alternados [2,1,2,1,2,1,2,1,2]

---

## 🛠️ Stack Tecnológico

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

## 📁 Estructura del Proyecto

```
reto4-alerta-emergencias/
├── backend/
│   ├── main.py                    # Entrada FastAPI + CORS + rutas
│   ├── config.py                  # Variables de entorno y constantes Ecuador
│   ├── requirements.txt           # Dependencias Python
│   ├── .env.example               # Template de variables de entorno
│   ├── agents/
│   │   └── emergencia_agent.py    # 🧠 Agente Claude — corazón del sistema
│   ├── routes/
│   │   ├── webhook.py             # POST /api/webhook/admision (flujo principal)
│   │   ├── dashboard.py           # GET /api/dashboard/stats
│   │   └── cases.py               # GET/PATCH /api/cases
│   ├── services/
│   │   ├── notion_service.py      # Integración Notion (pólizas, casos, pre-existencias)
│   │   └── notification_service.py # SMS + Email simultáneos
│   └── models/
│       └── schemas.py             # Modelos Pydantic (tipos de dominio)
├── frontend/
│   └── index.html                 # UI de admisión + dashboard en vivo
└── README.md
```

---

## ⚙️ Instalación y Configuración

### Requisitos previos
- Python 3.11+
- Una cuenta en [Anthropic Console](https://console.anthropic.com/) (para el API key de Claude)
- Una cuenta en [Notion](https://notion.so/) con una integración creada

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/reto4-alerta-emergencias.git
cd reto4-alerta-emergencias
```

### 2. Crear entorno virtual e instalar dependencias

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
cp .env.example .env
nano .env   # o abre con tu editor favorito
```

Rellena al menos:
```env
ANTHROPIC_API_KEY=sk-ant-api03-...     # Obligatorio
NOTION_TOKEN=secret_...                 # Opcional (sin esto usa datos demo)
ENVIRONMENT=development                 # Para que las notificaciones sean en consola
```

### 4. Iniciar el servidor

```bash
python main.py
```

El servidor estará disponible en:
- **Frontend:** http://localhost:8000
- **API docs:** http://localhost:8000/docs (Swagger UI automático de FastAPI)
- **Health check:** http://localhost:8000/health

### 5. Modo Demo (sin credenciales)

El sistema funciona **100% sin credenciales reales** gracias a datos de demo integrados:
- Sin `ANTHROPIC_API_KEY`: usa análisis de respaldo basado en reglas
- Sin `NOTION_TOKEN`: usa pólizas de demo incluidas en el código
- Sin Twilio/SendGrid: imprime las notificaciones en la consola del servidor

---

## 📓 Configurar Notion

Para usar Notion real (en producción), necesitas crear 3 bases de datos:

### Base de datos: Pólizas

| Propiedad | Tipo | Descripción |
|-----------|------|-------------|
| `cedula_titular` | Text | Cédula del asegurado (10 dígitos) |
| `numero_poliza` | Text | Código único de la póliza |
| `aseguradora` | Text | Nombre de la aseguradora |
| `plan` | Select | Plan contratado |
| `vigente` | Checkbox | ¿Póliza activa? |
| `fecha_inicio` | Date | Inicio de vigencia |
| `fecha_fin` | Date | Fin de vigencia |
| `limite_anual` | Number | Límite anual en USD |
| `consumido_anual` | Number | Monto ya utilizado en USD |
| `cubre_emergencias` | Checkbox | ¿Cubre urgencias? |
| `periodo_carencia_dias` | Number | Días de carencia del contrato |
| `dias_carencia_cumplidos` | Checkbox | ¿Se cumplió el período? |
| `deducible` | Number | Deducible en USD |
| `porcentaje_coaseguro` | Number | % que paga el paciente |
| `gestor_casos_nombre` | Text | Nombre del gestor asignado |
| `gestor_casos_email` | Text | Email del gestor |
| `gestor_casos_telefono` | Text | Teléfono del gestor |
| `email_aseguradora` | Text | Email del depto. de siniestros |

### Base de datos: Casos Activos

| Propiedad | Tipo |
|-----------|------|
| `caso_id` (Title) | Text |
| `cedula_paciente` | Text |
| `nombre_paciente` | Text |
| `hospital_id` | Text |
| `estado_cobertura` | Select (CONFIRMADA / EN_REVISION / ALERTA_CRITICA / SIN_COBERTURA) |
| `score_riesgo` | Number |
| `resumen` | Text |
| `fecha_ingreso` | Date |
| `activo` | Checkbox |

### Base de datos: Pre-existencias

| Propiedad | Tipo |
|-----------|------|
| `cedula_paciente` | Text |
| `condicion` | Text |
| `codigo_cie10` | Text |
| `declarada` | Checkbox |
| `fecha_diagnostico` | Date |
| `excluida_de_cobertura` | Checkbox |

---

## 📡 Uso de la API

### POST /api/webhook/admision

Endpoint principal. Recibe el ingreso de un paciente y retorna el análisis completo.

**Request:**
```json
{
  "cedula_paciente": "1723456784",
  "nombre_paciente": "Juan Carlos Andrade Mejía",
  "hospital_id": "H001",
  "motivo_emergencia": "Paciente presenta dolor torácico severo irradiado al brazo izquierdo, diaforesis y disnea de inicio súbito hace 45 minutos.",
  "tipo_emergencia": "CARDIOVASCULAR",
  "codigo_cie10": "I21.0",
  "es_accidente_transito": false,
  "medico_admision": "Dr. Andrés Moncayo Salazar",
  "email_medico": "amoncayo@clinicakennedy.ec"
}
```

**Response:**
```json
{
  "caso_id": "EC-20240115-A3F8C2",
  "timestamp": "2024-01-15T14:32:01.543Z",
  "paciente": "Juan Carlos Andrade Mejía",
  "cedula": "1723456784",
  "hospital": "H001",
  "estado_cobertura": "CONFIRMADA",
  "score_cobertura": 12,
  "nivel_urgencia": "CRITICA",
  "resumen": "Paciente con póliza vigente en Aseguradora del Sur. Cobertura de emergencias confirmada. Disponible $41,500.00 USD. Posible infarto agudo de miocardio (I21.0) — activar protocolo cardiovascular de urgencia.",
  "alertas": [
    "Costo estimado puede superar el deducible de $200.00",
    "Notificar a gestor de casos por la complejidad del caso"
  ],
  "limite_disponible": 41500.0,
  "notificaciones_enviadas": [
    "EMAIL → amoncayo@clinicakennedy.ec: ✓",
    "EMAIL → mvasquez@aseguradoradelsur.ec: ✓",
    "SMS → +593987654321: ✓"
  ],
  "notion_caso_url": "https://notion.so/EC-20240115-A3F8C2"
}
```

### GET /api/dashboard/stats
```json
{
  "total_casos": 8,
  "confirmados": 5,
  "en_revision": 2,
  "alertas_criticas": 1,
  "sin_cobertura": 0,
  "casos_soat": 1
}
```

### GET /api/cases/
Lista todos los casos activos de la sesión.

### PATCH /api/cases/{caso_id}/cerrar
Marca un caso como cerrado (alta del paciente).

### GET /health
```json
{"status": "ok", "service": "AlertaEC", "version": "1.0.0"}
```

---

## 🧪 Datos de Prueba (Demo)

El sistema incluye 3 cédulas con diferentes escenarios para probar sin Notion:

| Cédula | Nombre | Escenario |
|--------|--------|-----------|
| `1723456784` | Juan Carlos Andrade | ✅ Póliza Premium vigente, $41,500 disponibles, hipertensión declarada |
| `0912345675` | Rosa Elena Gutiérrez | ⚠️ Plan Básico, solo $800 disponibles, en revisión por límite bajo |
| `1700000001` | Pedro Sin Seguro | ❌ Póliza vencida, sin cobertura |

Puedes hacer clic en los badges de cédula en el formulario web para autocompletar.

---

## 🚀 Roadmap Enterprise

### Fase 1 — MVP (Hackathon) ✅
- [x] Webhook de admisión funcional
- [x] Integración Claude Sonnet para análisis
- [x] Datos demo integrados (funciona sin credenciales)
- [x] Notificaciones email + SMS
- [x] Registro de casos en Notion
- [x] Dashboard en vivo
- [x] Validación de cédula ecuatoriana

### Fase 2 — Piloto (3-6 meses)
- [ ] Integración directa con HIS hospitalarios (OpenMRS, HL7 FHIR)
- [ ] Scanner de cédula mediante lector de código de barras
- [ ] SLA garantizados (< 10 segundos)
- [ ] Autenticación JWT para hospitales
- [ ] Logs de auditoría para la SBS

### Fase 3 — Escala (6-18 meses)
- [ ] Verificación automática del SOAT con API de la ANT Ecuador
- [ ] Predicción de días de hospitalización y costo esperado
- [ ] Integración con farmacéuticas para dispensación directa
- [ ] App móvil para gestores de casos
- [ ] Dashboard ejecutivo con analytics de siniestralidad

### Fase 4 — Plataforma Regional (18-36 meses)
- [ ] API estándar para cualquier aseguradora del Ecuador
- [ ] Certificación SBS como proveedor tecnológico asegurador
- [ ] Expansión a Colombia, Perú, Bolivia
- [ ] Modelo de ML propio entrenado en data ecuatoriana

---

## ⚖️ Marco Legal Ecuador

Este sistema fue diseñado con cumplimiento legal desde el principio:

| Ley / Regulación | Cumplimiento |
|-----------------|--------------|
| **LOPDP (2021)** — Ley Orgánica de Protección de Datos | Consentimiento explícito antes de procesar datos médicos. Los datos se clasifican como categoría especial. |
| **Ley General de Seguros** (SBS) | Respeta períodos de carencia, cobertura mínima de emergencias, y derechos del asegurado. |
| **Código de Ética Médica** | El sistema nunca niega la atención de emergencia. La cobertura es secundaria a la vida del paciente. |
| **SOAT** (ANT) | Detección automática de accidentes de tránsito con activación prioritaria del seguro obligatorio. |

> ⚠️ **Importante:** Este sistema es una herramienta de apoyo a la decisión. Las decisiones finales sobre cobertura deben ser validadas por profesionales de seguros habilitados. El sistema no reemplaza el criterio médico.

---

## 👥 Equipo

| Rol | Nombre |
|-----|--------|
| Desarrollador Principal | [Tu nombre] |
| Universidad | [Tu universidad] |
| Carrera | [Tu carrera] |
| Contacto | [Tu email] |

---

## 📄 Licencia

MIT License — Ver [LICENSE](LICENSE) para detalles.

---

## 🙏 Agradecimientos

- **Viamatica** por organizar el hackIAthon y proponer retos con impacto real
- **Anthropic** por Claude Sonnet y la API
- **Notion** por la flexibilidad de su API como backend sin código
- **Aseguradora del Sur** (partner del evento) por el contexto del sector

---

<div align="center">

**AlertaEC** · hackIAthon Viamatica 2025 · Reto 4  
*Porque cada segundo cuenta en una emergencia*

</div>

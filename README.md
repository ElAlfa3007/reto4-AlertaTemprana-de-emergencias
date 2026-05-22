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

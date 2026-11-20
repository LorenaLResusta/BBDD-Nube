---
title: "Prácticas y evaluación"
weight: 50
bookToc: true
---

# Cómo son las prácticas y la evaluación

## Tipos de práctica

| Tipo | Qué es | ¿Se entrega? |
|---|---|---|
| **Guiada** | Procedimiento paso a paso para aprender el servicio | No: se revisa en clase con la lista de comprobación |
| **Autónoma** | Un encargo sin pasos; tienes que decidir cómo hacerlo | Sí |
| **Reto** | Un problema abierto o más avanzado | Opcional, sube nota |
| **Proyecto** | La tarea de TaquillaAlacant de cada unidad | Sí, siempre |

Todas las prácticas tienen la misma estructura: **ficha** (duración, dificultad, RA/CE, software y entrega) → **objetivo** → **desarrollo** → **comprobación** → **limpieza** → problemas habituales → ampliación.

## Qué se entrega

En tu repositorio `taquilla-<alumno>`, carpeta de la unidad:

- `README.md` con el **informe**: decisiones tomadas y por qué, órdenes ejecutadas, comprobaciones y **coste estimado**.
- El código: `*.tf`, scripts `*.sh`/`*.py`, consultas `*.sql`.
- Capturas en `img/`, con el nombre del recurso visible (que se vea tu `ta-<alumno>`).
- Nunca: `terraform.tfstate`, `.terraform/`, ficheros `credentials`, contraseñas o claves.

## Rúbrica común de las prácticas entregables

| Criterio | 0 – 4 | 5 – 6 | 7 – 8 | 9 – 10 |
|---|---|---|---|---|
| **Funciona** (40 %) | No funciona o no se puede comprobar | Funciona con ayuda o parcialmente | Funciona y se comprueba | Funciona, se comprueba y se ha probado un fallo y la recuperación |
| **Seguridad** (20 %) | Datos públicos o sin cifrar sin justificación | Cifrado y acceso básicos | Mínimo privilegio y auditoría | Además, revisado con herramientas (Access Analyzer, Security Hub…) |
| **Coste** (15 %) | No se tiene en cuenta | Estimación sin justificar | Estimación con la calculadora | Además, propuesta razonada de ahorro |
| **IaC y automatización** (15 %) | Todo a mano sin documentar | Órdenes documentadas | IaC o scripts reproducibles | IaC limpia, con variables y salidas |
| **Informe** (10 %) | Incompleto | Describe lo hecho | Justifica las decisiones | Claro, conciso y con conclusiones útiles |

## Evaluación

- Cada **RA** se califica con las prácticas entregables, la tarea del proyecto y una **prueba práctica** individual que reproduce, en tiempo limitado, una parte de lo trabajado.
- Peso orientativo dentro de cada RA: **prácticas y proyecto 60 %**, **prueba práctica 40 %**.
- La nota del módulo es la media ponderada por horas de los RA (ver [RA y criterios](/guia/ra-ce/)), siempre que todos estén superados.
- Las prácticas entregadas con recursos que siguen activos días después sin justificación bajan un punto en el criterio de coste: **limpiar también se evalúa**.

> [!WARNING]
> Las prácticas son individuales. Puedes consultar documentación, foros y asistentes de IA, pero tienes que poder **explicar y repetir** todo lo que entregas en la defensa oral.

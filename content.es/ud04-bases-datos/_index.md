---
title: "UD04. Bases de datos administradas"
weight: 40
---

# UD04 · Bases de datos administradas

Las ventas de TaquillaAlacant no pueden perderse ni pararse un viernes por la noche antes de un concierto. En esta unidad administras bases de datos **relacionales** (Amazon RDS y Aurora) y **NoSQL** (DynamoDB) en la nube: región y alta disponibilidad, cifrado, usuarios y auditoría, cambios de tamaño y versión, copias y recuperación a un instante, monitorización del rendimiento y optimizaciones sencillas.

{{< ra "RA4:a,b,c,d,e,f,g" >}}

| Página | Contenido |
|---|---|
| [Teoría](/ud04-bases-datos/ud04-teoria/) | Modelos de servicio, motores, Multi-AZ y réplicas, cifrado, red y usuarios, auditoría, ciclo de vida, copias y PITR, rendimiento, optimización y DynamoDB (8 h) |
| [Prácticas](/ud04-bases-datos/ud04-practicas/) | RDS PostgreSQL con OpenTofu, usuarios y TLS, copias y PITR, réplicas y Multi-AZ, rendimiento y optimización, DynamoDB, Aurora y la tarea del proyecto (16 h) |

**Duración:** 24 horas (8 h de teoría y 16 h de prácticas).

> [!WARNING]
> Es la unidad que más crédito consume. **Detén** (`aws rds stop-db-instance`) o **destruye** las bases de datos al terminar cada sesión.

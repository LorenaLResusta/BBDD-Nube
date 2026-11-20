# Bases de datos y almacenamiento en la nube · Apuntes

Apuntes y prácticas del módulo **5162 Administración de bases de datos y almacenamiento en la nube** (100 h · 12 ECTS) del **Curso de especialización de FP de grado superior en Recursos y servicios en la nube** ([RD 145/2026](https://www.boe.es/buscar/act.php?id=BOE-A-2026-4673)), curso 2026/27. Sitio estático con [Hugo](https://gohugo.io/) y el tema [hugo-book](https://github.com/alex-shpak/hugo-book), **en castellano y en valenciano**, con la misma estructura que los repositorios de BBDD y Contenedores.

## Estructura

```text
content.es/                               castellano
content.val/                              valenciano (mismos ficheros y nombres)
├── _index.md                             portada: unidades, RA y horas
├── guia/                                 RA/CE, temporalización, entorno, proyecto, prácticas y evaluación
├── ud01-seleccion-almacenamiento/        _index · ud01-teoria · ud01-practicas   (RA1, 10 h)
├── ud02-almacenamiento-objetos/          S3, KMS, CloudFront, ciclo de vida      (RA2, 16 h)
├── ud03-bloques-ficheros/                EBS, EFS, AWS Backup                    (RA3, 12 h)
├── ud04-bases-datos/                     RDS, Aurora, DynamoDB                   (RA4, 24 h)
├── ud05-transferencia-sincronizacion/    CLI, rclone, DMS, Transfer Family       (RA5, 12 h)
├── ud06-nube-hibrida/                    SSH, WireGuard, replicación, Garage     (RA6, 12 h)
└── ud07-analitica-olap/                  Parquet, Glue, Athena, Iceberg, Redshift (RA7, 14 h, práctica final)
data/curriculo.yaml · curriculo_val.yaml  RA y CE del RD 145/2026 (redacción adaptada: cotejar con el BOE)
i18n/es.toml · val.toml                   textos de los shortcodes y del tema
layouts/_shortcodes/                      practica, ra, quiz, descarga, figura, sw (bilingües)
static/recursos/taquilla/                 esquema.sql y generar_ventas.py del proyecto TaquillaAlacant
```

## Entorno de las prácticas

- **AWS Academy Learner Lab** (`us-east-1`/`us-west-2`, rol `LabRole`), con AWS CLI v2 y **OpenTofu** para la IaC.
- Máquina local **`local-lab`** (Debian 13 + Docker) que hace de oficina: PostgreSQL 17, Garage (S3 local), rclone, WireGuard y DuckDB.
- Proyecto transversal **TaquillaAlacant**: una ticketera ficticia de Alicante cuyos datos se llevan a la nube unidad a unidad.

## Prácticas

Cada práctica empieza con la ficha `{{< practica ... >}}` (número, tipo, duración, dificultad, RA/CE, software y entrega) y sigue el esquema Objetivo · Desarrollo (`{{% steps %}}`) · Comprobación · Limpieza · Problemas habituales · Ampliación. El atributo `tipo` se escribe siempre en castellano (`Guiada`, `Autónoma`, `Reto`, `Proyecto`); la etiqueta se traduce sola.

## Mantener las dos lenguas

Las páginas de `content.val/` tienen el mismo nombre y ruta que las de `content.es/`. Los bloques de código son idénticos en las dos versiones; si cambias un bloque en castellano, cópialo también en la versión valenciana.

## Uso local

```bash
git submodule update --init --recursive   # descarga el tema hugo-book
hugo server -D                            # http://localhost:1313/BBDD-Nube/
```

Hace falta **Hugo extended ≥ 0.158** (la Action usa la 0.166). La GitHub Action de `.github/workflows/hugo.yaml` publica el sitio en GitHub Pages al hacer `push` a `main`: en el repositorio, *Settings → Pages → Source: GitHub Actions*.

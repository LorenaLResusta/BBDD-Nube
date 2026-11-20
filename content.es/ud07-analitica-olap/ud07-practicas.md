---
title: "UD07 · Prácticas"
weight: 2
bookToc: true
---

# UD07 · Prácticas

{{< ra "RA7:a,b,c,d,e,f,g" >}}

| Práctica | Tipo | Nivel | Horas | CE principales |
|---|---|---|--:|---|
| [7.1 Un lago en local con DuckDB](#práctica-71--un-lago-en-local-con-duckdb) | Guiada | ●○○ | 1,5 | RA7: d, g |
| [7.2 Lago en S3, Glue y Athena con OpenTofu](#práctica-72--lago-en-s3-glue-y-athena-con-opentofu) | Guiada | ●●○ | 2,5 | RA7: a, b, c, g |
| [7.3 ETL supervisada](#práctica-73--etl-supervisada) | Guiada | ●●○ | 2 | RA7: d, e |
| [7.4 Iceberg: retención, compactación y viaje en el tiempo](#práctica-74--iceberg-retención-compactación-y-viaje-en-el-tiempo) | Guiada | ●●● | 1,5 | RA7: d, f, g |
| [7.5 Redshift Serverless](#práctica-75--redshift-serverless) | Reto | ●●● | 1 | RA7: a, b, f, g |
| [7.6 Práctica final: TaquillaAlacant de extremo a extremo](#práctica-76--práctica-final-taquillaalacant-de-extremo-a-extremo) | Proyecto | ●●● | 1,5 | Todos |
| **Total** | | | **10 h** | |

---

## Práctica 7.1 · Un lago en local con DuckDB

{{< practica num="7.1" tipo="Guiada" duracion="1,5 h" nivel="1" ra="RA7: d, g" entorno="local-lab · DuckDB · Python 3" entrega="no" >}}

#### Objetivo

Comprobar con datos reales, y sin gastar crédito, cuánto cambian el espacio y el tiempo de las consultas al pasar de CSV a Parquet particionado.

#### Desarrollo

{{% steps %}}

1. **Instala DuckDB** (un único binario) y genera 2 millones de ventas:

    ```bash
    curl -fsSLO https://github.com/duckdb/duckdb/releases/latest/download/duckdb_cli-linux-amd64.zip
    unzip -o duckdb_cli-linux-amd64.zip && sudo mv duckdb /usr/local/bin/ && duckdb --version
    python3 generar_ventas.py --ventas 2000000 --salida ventas.csv
    ls -lh ventas.csv
    ```

2. **Convierte a Parquet particionado** por año y mes:

    ```bash
    duckdb lago.duckdb <<'SQL'
    COPY (
      SELECT *, year(fecha_venta) AS anio, month(fecha_venta) AS mes
      FROM read_csv('ventas.csv', header = true, types = {'cp_cliente': 'VARCHAR'})
    ) TO 'lago/ventas' (FORMAT parquet, PARTITION_BY (anio, mes), COMPRESSION zstd, OVERWRITE_OR_IGNORE);
    SQL
    du -sh ventas.csv lago/ventas
    find lago/ventas -name '*.parquet' | wc -l
    ```

3. **Compara la misma consulta** sobre los dos formatos:

    ```bash
    duckdb <<'SQL'
    .timer on
    SELECT canal, count(*), sum(importe) FROM read_csv('ventas.csv', header = true)
    WHERE fecha_venta >= '2024-06-01' AND fecha_venta < '2024-07-01' GROUP BY canal;

    SELECT canal, count(*), sum(importe) FROM read_parquet('lago/ventas/*/*/*.parquet', hive_partitioning = true)
    WHERE anio = 2024 AND mes = 6 GROUP BY canal;
    SQL
    ```

4. **Mira qué lee cada consulta** con `EXPLAIN ANALYZE`: en la de Parquet verás el filtro de particiones y que solo lee tres columnas.

5. **Consultas de negocio** para la dirección (guárdalas, las repetirás en Athena):

    ```sql
    -- Ventas por categoría y año
    SELECT anio, categoria, sum(entradas) AS entradas, round(sum(importe)) AS euros
    FROM read_parquet('lago/ventas/*/*/*.parquet', hive_partitioning = true)
    GROUP BY ALL ORDER BY anio, euros DESC;

    -- Antelación media de compra por categoría (días)
    SELECT categoria, round(avg(date_diff('day', fecha_venta, fecha_evento)), 1) AS dias_antelacion
    FROM read_parquet('lago/ventas/*/*/*.parquet', hive_partitioning = true)
    GROUP BY categoria ORDER BY dias_antelacion DESC;
    ```

{{% /steps %}}

#### Comprobación

- [ ] Tienes una tabla con: tamaño CSV, tamaño Parquet, número de ficheros, tiempo de cada consulta.
- [ ] Sabes explicar por qué la consulta en Parquet lee menos datos.

---

## Práctica 7.2 · Lago en S3, Glue y Athena con OpenTofu

{{< practica num="7.2" tipo="Guiada" duracion="2,5 h" nivel="2" ra="RA7: a, b, c, g" entorno="OpenTofu · S3 · KMS · Glue Data Catalog · Athena" entrega="no" >}}

#### Objetivo

Crear con IaC un lago cifrado con su catálogo y un grupo de trabajo de Athena que **fuerza** el cifrado de resultados y **limita** los datos escaneados, y comparar el coste de consultar CSV y Parquet.

#### Desarrollo

{{% steps %}}

1. **`ud07/lab/main.tf`** (cabecera habitual con `random_id`):

    ```hcl
    resource "aws_kms_key" "lago" {
      description             = "TaquillaAlacant ${var.alumno}: data lake"
      enable_key_rotation     = true
      deletion_window_in_days = 7
    }

    resource "aws_s3_bucket" "lago" {
      bucket        = "ta-${var.alumno}-lago-${random_id.sufijo.hex}"
      force_destroy = true
    }
    resource "aws_s3_bucket" "resultados" {
      bucket        = "ta-${var.alumno}-athena-${random_id.sufijo.hex}"
      force_destroy = true
    }

    resource "aws_s3_bucket_server_side_encryption_configuration" "cifrado" {
      for_each = { lago = aws_s3_bucket.lago.id, resultados = aws_s3_bucket.resultados.id }
      bucket   = each.value
      rule {
        apply_server_side_encryption_by_default {
          sse_algorithm     = "aws:kms"
          kms_master_key_id = aws_kms_key.lago.arn
        }
        bucket_key_enabled = true
      }
    }

    resource "aws_s3_bucket_public_access_block" "bloqueo" {
      for_each                = { lago = aws_s3_bucket.lago.id, resultados = aws_s3_bucket.resultados.id }
      bucket                  = each.value
      block_public_acls       = true
      block_public_policy     = true
      ignore_public_acls      = true
      restrict_public_buckets = true
    }

    # Retención: raw 90 días; resultados de Athena 7 días
    resource "aws_s3_bucket_lifecycle_configuration" "lago" {
      bucket = aws_s3_bucket.lago.id
      rule {
        id     = "raw-90-dias"
        status = "Enabled"
        filter { prefix = "raw/" }
        expiration { days = 90 }
      }
    }
    resource "aws_s3_bucket_lifecycle_configuration" "resultados" {
      bucket = aws_s3_bucket.resultados.id
      rule {
        id     = "resultados-7-dias"
        status = "Enabled"
        filter {}
        expiration { days = 7 }
      }
    }

    resource "aws_glue_catalog_database" "taquilla" {
      name = "ta_${var.alumno}_taquilla"           # guiones bajos: Glue/Athena no admiten guiones
    }

    resource "aws_athena_workgroup" "analistas" {
      name          = "ta-${var.alumno}-analistas"
      force_destroy = true
      configuration {
        enforce_workgroup_configuration    = true
        publish_cloudwatch_metrics_enabled = true
        bytes_scanned_cutoff_per_query     = 1073741824
        result_configuration {
          output_location = "s3://${aws_s3_bucket.resultados.bucket}/resultados/"
          encryption_configuration {
            encryption_option = "SSE_KMS"
            kms_key_arn       = aws_kms_key.lago.arn
          }
        }
      }
    }

    output "lago" { value = aws_s3_bucket.lago.bucket }
    output "bd" { value = aws_glue_catalog_database.taquilla.name }
    output "grupo" { value = aws_athena_workgroup.analistas.name }
    ```

    ```bash
    tofu init && tofu apply -var alumno=$ALUMNO
    export LAGO=$(tofu output -raw lago) BD=$(tofu output -raw bd) WG=$(tofu output -raw grupo)
    ```

2. **Sube los datos** a las dos zonas del lago (CSV a `raw/`, Parquet de la práctica 7.1 a `curated/`):

    ```bash
    aws s3 cp ventas.csv s3://$LAGO/raw/ventas/ventas.csv
    aws s3 sync lago/ventas s3://$LAGO/curated/ventas/
    ```

3. **Script de consultas** para la terminal (`athena.sh`), que espera al resultado y muestra datos escaneados y tiempo:

    ```bash
    #!/usr/bin/env bash
    # Uso: ./athena.sh "SELECT ..."
    set -euo pipefail
    ID=$(aws athena start-query-execution --work-group "$WG" \
          --query-execution-context Database="$BD" --query-string "$1" --query QueryExecutionId --output text)
    while true; do
      ESTADO=$(aws athena get-query-execution --query-execution-id "$ID" --query QueryExecution.Status.State --output text)
      case $ESTADO in SUCCEEDED|FAILED|CANCELLED) break;; esac; sleep 1
    done
    aws athena get-query-execution --query-execution-id "$ID" --query 'QueryExecution.{Estado:Status.State,
      Motivo:Status.StateChangeReason, MB:Statistics.DataScannedInBytes, ms:Statistics.TotalExecutionTimeInMillis}'
    [ "$ESTADO" = SUCCEEDED ] && aws athena get-query-results --query-execution-id "$ID" --output text --max-items 20
    ```

4. **Define las tablas** en el catálogo:

    ```bash
    ./athena.sh "CREATE EXTERNAL TABLE ventas_csv (
      id_venta bigint, fecha_venta string, canal string, entradas int, importe decimal(8,2),
      id_evento int, titulo string, categoria string, fecha_evento string, recinto string,
      id_cliente int, cp_cliente string)
    ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
    LOCATION 's3://$LAGO/raw/ventas/'
    TBLPROPERTIES ('skip.header.line.count'='1')"

    ./athena.sh "CREATE EXTERNAL TABLE ventas_parquet (
      id_venta bigint, fecha_venta timestamp, canal string, entradas bigint, importe double,
      id_evento bigint, titulo string, categoria string, fecha_evento timestamp, recinto string,
      id_cliente bigint, cp_cliente string)
    PARTITIONED BY (anio int, mes int)
    STORED AS PARQUET
    LOCATION 's3://$LAGO/curated/ventas/'"

    ./athena.sh "MSCK REPAIR TABLE ventas_parquet"
    ./athena.sh "SHOW PARTITIONS ventas_parquet"
    ```

    > [!NOTE]
    > Los tipos de la tabla Parquet tienen que coincidir con los que escribió DuckDB. Si una columna da error de tipo, consulta el esquema real con `duckdb -c "DESCRIBE SELECT * FROM 'lago/ventas/anio=2024/mes=6/*.parquet'"`.

5. **Compara datos escaneados** con la misma pregunta:

    ```bash
    ./athena.sh "SELECT canal, count(*), sum(importe) FROM ventas_csv
                 WHERE fecha_venta >= '2024-06-01' AND fecha_venta < '2024-07-01' GROUP BY canal"
    ./athena.sh "SELECT canal, count(*), sum(importe) FROM ventas_parquet
                 WHERE anio = 2024 AND mes = 6 GROUP BY canal"
    ```

    Calcula el coste de cada consulta y el de ejecutarla 1000 veces al mes.

6. **Comprueba los límites del grupo de trabajo**: intenta cambiar la ubicación de resultados desde la consola (no te deja) y verifica el cifrado de un fichero de resultados con `head-object`.

7. **Métricas**: en CloudWatch → *AWS/Athena*, filtra por tu grupo de trabajo y observa `ProcessedBytes` y `TotalExecutionTime`.

{{% /steps %}}

#### Comprobación

- [ ] Los resultados de Athena se guardan cifrados con tu clave en el bucket de resultados.
- [ ] La consulta Parquet escanea una fracción mínima de la CSV, y lo cuantificas en euros.
- [ ] Sabes qué permisos darías a un analista para que solo pueda usar tu grupo de trabajo.

---

## Práctica 7.3 · ETL supervisada

{{< practica num="7.3" tipo="Guiada" duracion="2 h" nivel="2" ra="RA7: d, e" entorno="Athena (CTAS e INSERT) · Glue Crawler · EventBridge · SNS" entrega="no" >}}

#### Objetivo

Convertir los CSV que llegan cada día a `raw/` en datos limpios y particionados en `curated/`, con un proceso **idempotente**, **supervisado** y que **avisa** si falla.

#### Desarrollo

{{% steps %}}

1. **Transformación inicial** con CTAS (crea tabla y ficheros a la vez), limpiando y tipando:

    ```bash
    ./athena.sh "CREATE TABLE ventas_etl
    WITH (format = 'PARQUET', write_compression = 'ZSTD',
          external_location = 's3://$LAGO/curated/ventas_etl/',
          partitioned_by = ARRAY['anio', 'mes'])
    AS SELECT id_venta, CAST(fecha_venta AS timestamp) AS fecha_venta, canal, entradas, importe,
              categoria, recinto, cp_cliente,
              year(CAST(fecha_venta AS timestamp)) AS anio, month(CAST(fecha_venta AS timestamp)) AS mes
       FROM ventas_csv
       WHERE importe >= 0 AND canal IN ('web', 'app', 'taquilla')"
    ```

    Observa que la tabla resultante **no** tiene `id_cliente` ni `titulo`: los analistas no necesitan identificar clientes.

2. **Carga incremental idempotente**: llegan las ventas de un día nuevo a `raw/ventas/dia=2026-11-20/`. Simúlalo y cárgalas **solo si no están ya**:

    ```bash
    python3 generar_ventas.py --ventas 3000 --fecha 2026-11-20 --id-inicial 9000001 --salida dia.csv
    aws s3 cp dia.csv s3://$LAGO/raw/ventas/dia=2026-11-20/ventas.csv
    ./athena.sh "INSERT INTO ventas_etl
      SELECT id_venta, CAST(fecha_venta AS timestamp), canal, entradas, importe, categoria, recinto, cp_cliente,
             year(CAST(fecha_venta AS timestamp)), month(CAST(fecha_venta AS timestamp))
      FROM ventas_csv c
      WHERE \"\$path\" LIKE '%dia=2026-11-20%'
        AND NOT EXISTS (SELECT 1 FROM ventas_etl e WHERE e.anio = 2026 AND e.mes = 11 AND e.id_venta = c.id_venta)"
    ```

    Ejecuta el `INSERT` **dos veces** y comprueba con `count(*)` que la segunda no duplica.

3. **Validación**: recuentos y sumas de control entre `raw` y `curated` para el día cargado:

    ```bash
    ./athena.sh "SELECT (SELECT count(*) FROM ventas_csv WHERE \"\$path\" LIKE '%dia=2026-11-20%') AS raw,
                        (SELECT count(*) FROM ventas_etl WHERE anio = 2026 AND mes = 11
                           AND date(fecha_venta) = DATE '2026-11-20') AS curated"
    ```

4. **Un rastreador de Glue** que mantenga el catálogo de `raw/` (usa `LabRole`) y su supervisión:

    ```bash
    CUENTA=$(aws sts get-caller-identity --query Account --output text)
    aws glue create-crawler --name ta-$ALUMNO-raw --role arn:aws:iam::$CUENTA:role/LabRole \
      --database-name $BD --table-prefix raw_ \
      --targets "{\"S3Targets\":[{\"Path\":\"s3://$LAGO/raw/ventas/\"}]}"
    aws glue start-crawler --name ta-$ALUMNO-raw
    sleep 90
    aws glue get-crawler-metrics --crawler-name-list ta-$ALUMNO-raw
    aws glue get-crawler --name ta-$ALUMNO-raw --query 'Crawler.LastCrawl'
    ```

    Busca su registro en CloudWatch Logs (`/aws-glue/crawlers`).

5. **Alertas**: una regla de EventBridge que avise por SNS cuando una consulta de Athena de tu grupo de trabajo **falle**, y otra cuando falle un rastreador:

    ```bash
    TOPIC=$(aws sns create-topic --name ta-$ALUMNO-etl --query TopicArn --output text)
    aws sns subscribe --topic-arn $TOPIC --protocol email --notification-endpoint TU_CORREO
    aws events put-rule --name ta-$ALUMNO-athena-fallo --event-pattern "{
      \"source\": [\"aws.athena\"],
      \"detail-type\": [\"Athena Query State Change\"],
      \"detail\": {\"currentState\": [\"FAILED\"], \"workgroupName\": [\"$WG\"]}}"
    aws events put-targets --rule ta-$ALUMNO-athena-fallo --targets "Id=sns,Arn=$TOPIC"
    aws events put-rule --name ta-$ALUMNO-crawler-fallo --event-pattern "{
      \"source\": [\"aws.glue\"], \"detail-type\": [\"Glue Crawler State Change\"],
      \"detail\": {\"state\": [\"Failed\"]}}"
    aws events put-targets --rule ta-$ALUMNO-crawler-fallo --targets "Id=sns,Arn=$TOPIC"
    ```

    > [!NOTE]
    > Para que EventBridge publique en el tema, la política del tema SNS debe permitir `events.amazonaws.com`. Añádela con `aws sns set-topic-attributes --attribute-name Policy ...` si no llegan los avisos.

6. **Provoca un fallo** (una consulta con una columna inexistente, o una que supere el límite de 1 GB escaneando la tabla CSV sin filtros varias veces unida) y comprueba que llega el correo. Revisa el **historial** del grupo de trabajo: estado, motivo, datos escaneados y tiempo.

{{% /steps %}}

#### Comprobación

- [ ] `ventas_etl` está particionada, sin datos personales, y el `INSERT` incremental no duplica.
- [ ] La validación da los mismos recuentos en `raw` y `curated`.
- [ ] Recibes el aviso de una consulta fallida.

---

## Práctica 7.4 · Iceberg: retención, compactación y viaje en el tiempo

{{< practica num="7.4" tipo="Guiada" duracion="1,5 h" nivel="3" ra="RA7: d, f, g" entorno="Athena · Apache Iceberg · S3" entrega="no" >}}

#### Objetivo

Gestionar una tabla Iceberg como lo harías en producción: cargas pequeñas frecuentes, compactación, borrado de datos antiguos por retención, recuperación con viaje en el tiempo y limpieza de versiones.

#### Desarrollo

{{% steps %}}

1. **Crea la tabla Iceberg** con particionado oculto por mes:

    ```bash
    ./athena.sh "CREATE TABLE ventas_ice (
      id_venta bigint, fecha_venta timestamp, canal string, entradas int, importe decimal(8,2),
      categoria string, recinto string)
    PARTITIONED BY (month(fecha_venta))
    LOCATION 's3://$LAGO/curated/ventas_ice/'
    TBLPROPERTIES ('table_type' = 'ICEBERG', 'format' = 'parquet', 'write_compression' = 'zstd',
                   'vacuum_max_snapshot_age_seconds' = '3600')"
    ```

2. **Simula cargas frecuentes**: diez `INSERT` pequeños (uno por «cada 5 minutos»):

    ```bash
    for i in $(seq 0 9); do
      ./athena.sh "INSERT INTO ventas_ice SELECT id_venta, fecha_venta, canal, CAST(entradas AS int),
        CAST(importe AS decimal(8,2)), categoria, recinto FROM ventas_etl
        WHERE anio = 2024 AND id_venta % 10 = $i" > /dev/null
    done
    aws s3 ls s3://$LAGO/curated/ventas_ice/data/ --recursive | wc -l       # muchos ficheros
    ./athena.sh 'SELECT count(*), sum(file_size_in_bytes)/1024 AS kb FROM "ventas_ice$files"'
    ./athena.sh 'SELECT snapshot_id, committed_at, operation FROM "ventas_ice$snapshots" ORDER BY committed_at'
    ```

3. **Mide**, **compacta** y vuelve a medir:

    ```bash
    ./athena.sh "SELECT recinto, sum(importe) FROM ventas_ice GROUP BY recinto"     # anota tiempo
    ./athena.sh "OPTIMIZE ventas_ice REWRITE DATA USING BIN_PACK"
    ./athena.sh 'SELECT count(*) FROM "ventas_ice$files"'
    ./athena.sh "SELECT recinto, sum(importe) FROM ventas_ice GROUP BY recinto"     # compara
    ```

4. **Retención**: la política de la empresa es conservar en esta tabla solo desde el segundo semestre. Borra lo anterior:

    ```bash
    ./athena.sh "DELETE FROM ventas_ice WHERE fecha_venta < TIMESTAMP '2024-07-01 00:00:00'"
    ./athena.sh "SELECT min(fecha_venta), count(*) FROM ventas_ice"
    ```

5. **¡Error!** Ese borrado no debía hacerse todavía. Consulta la tabla **como estaba antes** y recupera:

    ```bash
    ./athena.sh 'SELECT snapshot_id, committed_at, operation FROM "ventas_ice$snapshots" ORDER BY committed_at DESC LIMIT 3'
    ./athena.sh "SELECT count(*) FROM ventas_ice FOR VERSION AS OF <snapshot_id_anterior_al_delete>"
    ./athena.sh "INSERT INTO ventas_ice SELECT * FROM ventas_ice FOR VERSION AS OF <snapshot_id_anterior_al_delete>
                 WHERE fecha_venta < TIMESTAMP '2024-07-01 00:00:00'"
    ```

6. **Limpia versiones** antiguas (pasada una hora, por la propiedad de la tabla) y comprueba el espacio:

    ```bash
    aws s3 ls s3://$LAGO/curated/ventas_ice/ --recursive --summarize | tail -2
    ./athena.sh "VACUUM ventas_ice"
    aws s3 ls s3://$LAGO/curated/ventas_ice/ --recursive --summarize | tail -2
    ```

    Tras `VACUUM`, ¿podrías volver a hacer el paso 5 con versiones de hace dos horas? ¿Qué te protege entonces? (Pista: versionado de S3 y copias.)

{{% /steps %}}

#### Comprobación

- [ ] El número de ficheros baja tras `OPTIMIZE` y la consulta tarda menos.
- [ ] Has recuperado los datos borrados con viaje en el tiempo.
- [ ] Sabes explicar el compromiso entre retención de versiones (seguridad) y espacio (coste).

---

## Práctica 7.5 · Redshift Serverless

{{< practica num="7.5" tipo="Reto" duracion="1 h" nivel="3" ra="RA7: a, b, f, g" entorno="Amazon Redshift Serverless (o aprovisionado) · S3" entrega="ud07/p7_5.md" >}}

#### Enunciado

Si el laboratorio lo permite, crea un **espacio de nombres y grupo de trabajo de Redshift Serverless** con la capacidad base mínima, cifrado con tu clave de KMS y sin acceso público. Si no está permitido, usa un clúster aprovisionado de un nodo del tipo más pequeño disponible y justifícalo.

1. Carga la tabla `ventas` desde el Parquet del lago con `COPY ... FORMAT AS PARQUET` usando `LabRole`.
2. Ejecuta las consultas de negocio de la 7.1 y compara tiempos con Athena.
3. Consulta `SYS_QUERY_HISTORY` y las métricas de CloudWatch (capacidad usada, duración de las consultas).
4. Crea una **instantánea manual**, programa la retención de las automáticas y explica cómo la copiarías a otra región.
5. Estima el coste mensual de Redshift frente a Athena para la dirección de TaquillaAlacant (unas 200 consultas al mes) y recomienda uno.

**Borra** el grupo de trabajo y el espacio de nombres al terminar.

---

## Práctica 7.6 · Práctica final: TaquillaAlacant de extremo a extremo

{{< practica num="7.6" tipo="Proyecto" duracion="1,5 h" nivel="3" ra="RA2 – RA7" entorno="Todo el entorno del módulo" entrega="ud07/ + defensa oral de 10 minutos" >}}

#### Objetivo

Demostrar que la plataforma de datos de TaquillaAlacant funciona **de extremo a extremo** y que sabes administrarla. Es la práctica final del módulo.

#### Requisitos

1. **Flujo completo** automatizado: una venta nueva en RDS → exportación diaria (CSV comprimido) a `raw/` → transformación a `curated/` (Parquet o Iceberg particionado) → consulta de negocio en Athena. Todo con un script o un temporizador, idempotente.
2. **Lago** con IaC: cifrado con clave propia, retención de `raw/` y de resultados, versionado del bucket `curated`, grupo de trabajo con límites y cifrado forzado, catálogo definido en código.
3. **Permisos**: documento de política IAM para el perfil *analista* (solo su grupo de trabajo, solo lectura de `curated/`, sin columnas personales) y explicación de cómo lo harías con Lake Formation.
4. **Supervisión**: alertas de fallo de la ETL, validación de recuentos tras cada carga y un **panel** de CloudWatch con: datos escaneados por día, duración de la ETL, tamaño del lago y última carga correcta.
5. **Compactación y retención** programadas (OPTIMIZE/VACUUM o reescritura de particiones).
6. **Copias**: estrategia para el lago y el catálogo, con una restauración probada.
7. **Informe final** (`ud07/README.md`): arquitectura completa de TaquillaAlacant (UD01 – UD07) en un diagrama, tabla de costes mensuales en producción por servicio, tabla de RA/CE cumplidos con enlaces a las evidencias de cada unidad y lecciones aprendidas.

#### Defensa

En 10 minutos: demostración en directo de una venta que aparece en el informe de Athena, provocación de un fallo en la ETL y cómo te enteras, y respuesta a dos preguntas del docente sobre cualquier unidad.

#### Comprobación

- [ ] El flujo funciona sin intervención desde la venta hasta el informe.
- [ ] La alerta llega al provocar un fallo.
- [ ] La destrucción de toda la infraestructura con IaC deja la cuenta sin recursos del proyecto.

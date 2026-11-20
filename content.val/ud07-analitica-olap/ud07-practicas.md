---
title: "UD07 · Pràctiques"
weight: 2
bookToc: true
---

# UD07 · Pràctiques

{{< ra "RA7:a,b,c,d,e,f,g" >}}

| Pràctica | Tipus | Nivell | Hores | CA principals |
|---|---|---|--:|---|
| [7.1 Un llac en local amb DuckDB](#pràctica-71--un-llac-en-local-amb-duckdb) | Guiada | ●○○ | 1,5 | RA7: d, g |
| [7.2 Llac en S3, Glue i Athena amb OpenTofu](#pràctica-72--llac-en-s3-glue-i-athena-amb-opentofu) | Guiada | ●●○ | 2,5 | RA7: a, b, c, g |
| [7.3 ETL supervisada](#pràctica-73--etl-supervisada) | Guiada | ●●○ | 2 | RA7: d, e |
| [7.4 Iceberg: retenció, compactació i viatge en el temps](#pràctica-74--iceberg-retenció-compactació-i-viatge-en-el-temps) | Guiada | ●●● | 1,5 | RA7: d, f, g |
| [7.5 Redshift Serverless](#pràctica-75--redshift-serverless) | Repte | ●●● | 1 | RA7: a, b, f, g |
| [7.6 Pràctica final: TaquillaAlacant d'extrem a extrem](#pràctica-76--pràctica-final-taquillaalacant-dextrem-a-extrem) | Projecte | ●●● | 1,5 | Tots |
| **Total** | | | **10 h** | |

---

## Pràctica 7.1 · Un llac en local amb DuckDB

{{< practica num="7.1" tipo="Guiada" duracion="1,5 h" nivel="1" ra="RA7: d, g" entorno="local-lab · DuckDB · Python 3" entrega="no" >}}

#### Objectiu

Comprovar amb dades reals, i sense gastar crèdit, quant canvien l'espai i el temps de les consultes en passar de CSV a Parquet particionat.

#### Desenvolupament

{{% steps %}}

1. **Instal·la DuckDB** (un únic binari) i genera 2 milions de vendes:

    ```bash
    curl -fsSLO https://github.com/duckdb/duckdb/releases/latest/download/duckdb_cli-linux-amd64.zip
    unzip -o duckdb_cli-linux-amd64.zip && sudo mv duckdb /usr/local/bin/ && duckdb --version
    python3 generar_ventas.py --ventas 2000000 --salida ventas.csv
    ls -lh ventas.csv
    ```

2. **Convertix a Parquet particionat** per any i mes:

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

3. **Compara la mateixa consulta** sobre els dos formats:

    ```bash
    duckdb <<'SQL'
    .timer on
    SELECT canal, count(*), sum(importe) FROM read_csv('ventas.csv', header = true)
    WHERE fecha_venta >= '2024-06-01' AND fecha_venta < '2024-07-01' GROUP BY canal;

    SELECT canal, count(*), sum(importe) FROM read_parquet('lago/ventas/*/*/*.parquet', hive_partitioning = true)
    WHERE anio = 2024 AND mes = 6 GROUP BY canal;
    SQL
    ```

4. **Mira què llig cada consulta** amb `EXPLAIN ANALYZE`: en la de Parquet veuràs el filtre de particions i que només llig tres columnes.

5. **Consultes de negoci** per a la direcció (guarda-les, les repetiràs en Athena):

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

#### Comprovació

- [ ] Tens una taula amb: grandària CSV, grandària Parquet, nombre de fitxers, temps de cada consulta.
- [ ] Saps explicar per què la consulta en Parquet llig menys dades.

---

## Pràctica 7.2 · Llac en S3, Glue i Athena amb OpenTofu

{{< practica num="7.2" tipo="Guiada" duracion="2,5 h" nivel="2" ra="RA7: a, b, c, g" entorno="OpenTofu · S3 · KMS · Glue Data Catalog · Athena" entrega="no" >}}

#### Objectiu

Crear amb IaC un llac xifrat amb el seu catàleg i un grup de treball d'Athena que **força** el xifratge de resultats i **limita** les dades escanejades, i comparar el cost de consultar CSV i Parquet.

#### Desenvolupament

{{% steps %}}

1. **`ud07/lab/main.tf`** (capçalera habitual amb `random_id`):

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

2. **Puja les dades** a les dues zones del llac (CSV a `raw/`, Parquet de la pràctica 7.1 a `curated/`):

    ```bash
    aws s3 cp ventas.csv s3://$LAGO/raw/ventas/ventas.csv
    aws s3 sync lago/ventas s3://$LAGO/curated/ventas/
    ```

3. **Script de consultes** per al terminal (`athena.sh`), que espera el resultat i mostra dades escanejades i temps:

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

4. **Definix les taules** en el catàleg:

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
    > Els tipus de la taula Parquet han de coincidir amb els que va escriure DuckDB. Si una columna dona error de tipus, consulta l'esquema real amb `duckdb -c "DESCRIBE SELECT * FROM 'lago/ventas/anio=2024/mes=6/*.parquet'"`.

5. **Compara dades escanejades** amb la mateixa pregunta:

    ```bash
    ./athena.sh "SELECT canal, count(*), sum(importe) FROM ventas_csv
                 WHERE fecha_venta >= '2024-06-01' AND fecha_venta < '2024-07-01' GROUP BY canal"
    ./athena.sh "SELECT canal, count(*), sum(importe) FROM ventas_parquet
                 WHERE anio = 2024 AND mes = 6 GROUP BY canal"
    ```

    Calcula el cost de cada consulta i el d'executar-la 1000 vegades al mes.

6. **Comprova els límits del grup de treball**: intenta canviar la ubicació de resultats des de la consola (no et deixa) i verifica el xifratge d'un fitxer de resultats amb `head-object`.

7. **Mètriques**: en CloudWatch → *AWS/Athena*, filtra pel teu grup de treball i observa `ProcessedBytes` i `TotalExecutionTime`.

{{% /steps %}}

#### Comprovació

- [ ] Els resultats d'Athena es guarden xifrats amb la teua clau en el bucket de resultats.
- [ ] La consulta Parquet escaneja una fracció mínima de la CSV, i ho quantifiques en euros.
- [ ] Saps quins permisos donaries a un analista perquè només puga usar el teu grup de treball.

---

## Pràctica 7.3 · ETL supervisada

{{< practica num="7.3" tipo="Guiada" duracion="2 h" nivel="2" ra="RA7: d, e" entorno="Athena (CTAS i INSERT) · Glue Crawler · EventBridge · SNS" entrega="no" >}}

#### Objectiu

Convertir els CSV que arriben cada dia a `raw/` en dades netes i particionades en `curated/`, amb un procés **idempotent**, **supervisat** i que **avisa** si falla.

#### Desenvolupament

{{% steps %}}

1. **Transformació inicial** amb CTAS (crea taula i fitxers alhora), netejant i tipant:

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

    Observa que la taula resultant **no** té `id_cliente` ni `titulo`: els analistes no necessiten identificar clients.

2. **Càrrega incremental idempotent**: arriben les vendes d'un dia nou a `raw/ventas/dia=2026-11-20/`. Simula-ho i carrega-les **només si no hi són ja**:

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

    Executa l'`INSERT` **dues vegades** i comprova amb `count(*)` que la segona no duplica.

3. **Validació**: recomptes i sumes de control entre `raw` i `curated` per al dia carregat:

    ```bash
    ./athena.sh "SELECT (SELECT count(*) FROM ventas_csv WHERE \"\$path\" LIKE '%dia=2026-11-20%') AS raw,
                        (SELECT count(*) FROM ventas_etl WHERE anio = 2026 AND mes = 11
                           AND date(fecha_venta) = DATE '2026-11-20') AS curated"
    ```

4. **Un rastrejador de Glue** que mantinga el catàleg de `raw/` (usa `LabRole`) i la seua supervisió:

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

    Busca el seu registre en CloudWatch Logs (`/aws-glue/crawlers`).

5. **Alertes**: una regla d'EventBridge que avise per SNS quan una consulta d'Athena del teu grup de treball **falle**, i una altra quan falle un rastrejador:

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
    > Perquè EventBridge publique en el tema, la política del tema SNS ha de permetre `events.amazonaws.com`. Afig-la amb `aws sns set-topic-attributes --attribute-name Policy ...` si no arriben els avisos.

6. **Provoca una fallada** (una consulta amb una columna inexistent, o una que supere el límit d'1 GB escanejant la taula CSV sense filtres diverses vegades unida) i comprova que arriba el correu. Revisa l'**historial** del grup de treball: estat, motiu, dades escanejades i temps.

{{% /steps %}}

#### Comprovació

- [ ] `ventas_etl` està particionada, sense dades personals, i l'`INSERT` incremental no duplica.
- [ ] La validació dona els mateixos recomptes en `raw` i `curated`.
- [ ] Reps l'avís d'una consulta fallida.

---

## Pràctica 7.4 · Iceberg: retenció, compactació i viatge en el temps

{{< practica num="7.4" tipo="Guiada" duracion="1,5 h" nivel="3" ra="RA7: d, f, g" entorno="Athena · Apache Iceberg · S3" entrega="no" >}}

#### Objectiu

Gestionar una taula Iceberg com ho faries en producció: càrregues xicotetes freqüents, compactació, esborrament de dades antigues per retenció, recuperació amb viatge en el temps i neteja de versions.

#### Desenvolupament

{{% steps %}}

1. **Crea la taula Iceberg** amb particionament ocult per mes:

    ```bash
    ./athena.sh "CREATE TABLE ventas_ice (
      id_venta bigint, fecha_venta timestamp, canal string, entradas int, importe decimal(8,2),
      categoria string, recinto string)
    PARTITIONED BY (month(fecha_venta))
    LOCATION 's3://$LAGO/curated/ventas_ice/'
    TBLPROPERTIES ('table_type' = 'ICEBERG', 'format' = 'parquet', 'write_compression' = 'zstd',
                   'vacuum_max_snapshot_age_seconds' = '3600')"
    ```

2. **Simula càrregues freqüents**: deu `INSERT` xicotets (un per «cada 5 minuts»):

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

3. **Mesura**, **compacta** i torna a mesurar:

    ```bash
    ./athena.sh "SELECT recinto, sum(importe) FROM ventas_ice GROUP BY recinto"     # anota tiempo
    ./athena.sh "OPTIMIZE ventas_ice REWRITE DATA USING BIN_PACK"
    ./athena.sh 'SELECT count(*) FROM "ventas_ice$files"'
    ./athena.sh "SELECT recinto, sum(importe) FROM ventas_ice GROUP BY recinto"     # compara
    ```

4. **Retenció**: la política de l'empresa és conservar en esta taula només des del segon semestre. Esborra el que és anterior:

    ```bash
    ./athena.sh "DELETE FROM ventas_ice WHERE fecha_venta < TIMESTAMP '2024-07-01 00:00:00'"
    ./athena.sh "SELECT min(fecha_venta), count(*) FROM ventas_ice"
    ```

5. **Error!** Eixe esborrament encara no s'havia de fer. Consulta la taula **com estava abans** i recupera:

    ```bash
    ./athena.sh 'SELECT snapshot_id, committed_at, operation FROM "ventas_ice$snapshots" ORDER BY committed_at DESC LIMIT 3'
    ./athena.sh "SELECT count(*) FROM ventas_ice FOR VERSION AS OF <snapshot_id_anterior_al_delete>"
    ./athena.sh "INSERT INTO ventas_ice SELECT * FROM ventas_ice FOR VERSION AS OF <snapshot_id_anterior_al_delete>
                 WHERE fecha_venta < TIMESTAMP '2024-07-01 00:00:00'"
    ```

6. **Neteja versions** antigues (passada una hora, per la propietat de la taula) i comprova l'espai:

    ```bash
    aws s3 ls s3://$LAGO/curated/ventas_ice/ --recursive --summarize | tail -2
    ./athena.sh "VACUUM ventas_ice"
    aws s3 ls s3://$LAGO/curated/ventas_ice/ --recursive --summarize | tail -2
    ```

    Després de `VACUUM`, podries tornar a fer el pas 5 amb versions de fa dues hores? Què et protegix aleshores? (Pista: versionat de S3 i còpies.)

{{% /steps %}}

#### Comprovació

- [ ] El nombre de fitxers baixa després d'`OPTIMIZE` i la consulta tarda menys.
- [ ] Has recuperat les dades esborrades amb viatge en el temps.
- [ ] Saps explicar el compromís entre retenció de versions (seguretat) i espai (cost).

---

## Pràctica 7.5 · Redshift Serverless

{{< practica num="7.5" tipo="Reto" duracion="1 h" nivel="3" ra="RA7: a, b, f, g" entorno="Amazon Redshift Serverless (o aprovisionat) · S3" entrega="ud07/p7_5.md" >}}

#### Enunciat

Si el laboratori ho permet, crea un **espai de noms i grup de treball de Redshift Serverless** amb la capacitat base mínima, xifrat amb la teua clau de KMS i sense accés públic. Si no està permés, usa un clúster aprovisionat d'un node del tipus més xicotet disponible i justifica-ho.

1. Carrega la taula `ventas` des del Parquet del llac amb `COPY ... FORMAT AS PARQUET` usant `LabRole`.
2. Executa les consultes de negoci de la 7.1 i compara temps amb Athena.
3. Consulta `SYS_QUERY_HISTORY` i les mètriques de CloudWatch (capacitat usada, durada de les consultes).
4. Crea una **instantània manual**, programa la retenció de les automàtiques i explica com la copiaries a una altra regió.
5. Estima el cost mensual de Redshift davant d'Athena per a la direcció de TaquillaAlacant (unes 200 consultes al mes) i recomana'n un.

**Esborra** el grup de treball i l'espai de noms en acabar.

---

## Pràctica 7.6 · Pràctica final: TaquillaAlacant d'extrem a extrem

{{< practica num="7.6" tipo="Proyecto" duracion="1,5 h" nivel="3" ra="RA2 – RA7" entorno="Tot l'entorn del mòdul" entrega="ud07/ + defensa oral de 10 minuts" >}}

#### Objectiu

Demostrar que la plataforma de dades de TaquillaAlacant funciona **d'extrem a extrem** i que saps administrar-la. És la pràctica final del mòdul.

#### Requisits

1. **Flux complet** automatitzat: una venda nova en RDS → exportació diària (CSV comprimit) a `raw/` → transformació a `curated/` (Parquet o Iceberg particionat) → consulta de negoci en Athena. Tot amb un script o un temporitzador, idempotent.
2. **Llac** amb IaC: xifratge amb clau pròpia, retenció de `raw/` i de resultats, versionat del bucket `curated`, grup de treball amb límits i xifratge forçat, catàleg definit en codi.
3. **Permisos**: document de política IAM per al perfil *analista* (només el seu grup de treball, només lectura de `curated/`, sense columnes personals) i explicació de com ho faries amb Lake Formation.
4. **Supervisió**: alertes de fallada de l'ETL, validació de recomptes després de cada càrrega i un **tauler** de CloudWatch amb: dades escanejades per dia, durada de l'ETL, grandària del llac i última càrrega correcta.
5. **Compactació i retenció** programades (OPTIMIZE/VACUUM o reescriptura de particions).
6. **Còpies**: estratègia per al llac i el catàleg, amb una restauració provada.
7. **Informe final** (`ud07/README.md`): arquitectura completa de TaquillaAlacant (UD01 – UD07) en un diagrama, taula de costos mensuals en producció per servei, taula de RA/CA complits amb enllaços a les evidències de cada unitat i lliçons apreses.

#### Defensa

En 10 minuts: demostració en directe d'una venda que apareix en l'informe d'Athena, provocació d'una fallada en l'ETL i com te n'assabentes, i resposta a dues preguntes del docent sobre qualsevol unitat.

#### Comprovació

- [ ] El flux funciona sense intervenció des de la venda fins a l'informe.
- [ ] L'alerta arriba en provocar una fallada.
- [ ] La destrucció de tota la infraestructura amb IaC deixa el compte sense recursos del projecte.

---
title: "UD05 · Prácticas"
weight: 2
bookToc: true
---

# UD05 · Prácticas

{{< ra "RA5:a,b,c,d,e,f,g,h" >}}

| Práctica | Tipo | Nivel | Horas | CE principales |
|---|---|---|--:|---|
| [5.1 Subidas eficientes y verificables](#práctica-51--subidas-eficientes-y-verificables) | Guiada | ●○○ | 1,5 | RA5: a, c, h |
| [5.2 Sincronización desatendida con rclone](#práctica-52--sincronización-desatendida-con-rclone) | Guiada | ●●○ | 1,5 | RA5: e, f, h |
| [5.3 Migrar la base de datos de la oficina](#práctica-53--migrar-la-base-de-datos-de-la-oficina) | Guiada | ●●○ | 2 | RA5: c, g, h |
| [5.4 Preparar una transferencia física](#práctica-54--preparar-una-transferencia-física) | Autónoma | ●●○ | 1 | RA5: a, b, d |
| [5.5 SFTP gestionado para socios](#práctica-55--sftp-gestionado-para-socios) | Reto | ●●● | 1 | RA5: a, c, e |
| [5.6 La oficina de TaquillaAlacant, sincronizada](#práctica-56--la-oficina-de-taquillaalacant-sincronizada) | Proyecto | ●●● | 1 | RA5: a – h |
| **Total** | | | **8 h** | |

> [!NOTE]
> Estas prácticas se hacen **desde `local-lab`**, que representa la oficina. Necesitas un bucket de destino: crea `ta-$ALUMNO-oficina-$SUFIJO` con versionado activado (como en la UD02) y exporta `BUCKET`.

---

## Práctica 5.1 · Subidas eficientes y verificables

{{< practica num="5.1" tipo="Guiada" duracion="1,5 h" nivel="1" ra="RA5: a, c, h" entorno="local-lab · AWS CLI v2 · S3" entrega="no" >}}

#### Objetivo

Medir cómo afectan la concurrencia, el tamaño de parte y el empaquetado al tiempo de subida, y comprobar la integridad de lo subido.

#### Desarrollo

{{% steps %}}

1. **Genera datos de prueba**: 2000 ficheros pequeños y 3 grandes.

    ```bash
    mkdir -p ~/oficina/escaneos ~/oficina/videos
    for i in $(seq -w 1 2000); do head -c 20000 /dev/urandom > ~/oficina/escaneos/ticket-$i.jpg; done
    for i in 1 2 3; do head -c 300M /dev/urandom > ~/oficina/videos/promo-$i.mp4; done
    du -sh ~/oficina/*
    ```

2. **Línea base** con la configuración por defecto:

    ```bash
    aws configure get default.s3.max_concurrent_requests      # vacío = 10
    time aws s3 cp ~/oficina/escaneos s3://$BUCKET/prueba1/escaneos/ --recursive --only-show-errors
    time aws s3 cp ~/oficina/videos   s3://$BUCKET/prueba1/videos/   --recursive --only-show-errors
    ```

3. **Ajusta** la concurrencia y el tamaño de parte, y repite en otro prefijo:

    ```bash
    aws configure set default.s3.max_concurrent_requests 32
    aws configure set default.s3.multipart_chunksize 64MB
    time aws s3 cp ~/oficina/escaneos s3://$BUCKET/prueba2/escaneos/ --recursive --only-show-errors
    time aws s3 cp ~/oficina/videos   s3://$BUCKET/prueba2/videos/   --recursive --only-show-errors
    ```

4. **Empaqueta** los ficheros pequeños y compara (tiempo y número de peticiones):

    ```bash
    time (tar -C ~/oficina -cf - escaneos | zstd -T0 -q -o /tmp/escaneos.tar.zst && \
          aws s3 cp /tmp/escaneos.tar.zst s3://$BUCKET/prueba3/)
    ```

5. **Sube con una suma de comprobación SHA-256** y compárala con la local:

    ```bash
    aws s3 cp ~/oficina/videos/promo-1.mp4 s3://$BUCKET/prueba4/ --checksum-algorithm SHA256
    aws s3api get-object-attributes --bucket $BUCKET --key prueba4/promo-1.mp4 \
      --object-attributes Checksum ObjectParts ObjectSize
    sha256sum ~/oficina/videos/promo-1.mp4 | cut -d' ' -f1 | xxd -r -p | base64
    ```

    > [!NOTE]
    > En los objetos multiparte, la suma que devuelve S3 es la **suma de las sumas de las partes** (termina en `-N`), no la del fichero completo. Para comparar con el hash local, súbelo en una sola parte o compara parte a parte.

6. **Sincroniza** solo los cambios y prueba el borrado en seco:

    ```bash
    touch ~/oficina/escaneos/ticket-0001.jpg; rm ~/oficina/escaneos/ticket-0002.jpg
    aws s3 sync ~/oficina/escaneos s3://$BUCKET/prueba2/escaneos/ --delete --dryrun
    ```

    Explica por qué aparece `ticket-0001.jpg` aunque su contenido no ha cambiado (pista: `sync` compara tamaño y fecha).

{{% /steps %}}

#### Comprobación

- [ ] Tienes una tabla con los tiempos de las tres estrategias y has calculado el número aproximado de peticiones `PUT` de cada una.
- [ ] La suma SHA-256 de S3 coincide con la local (en una sola parte).
- [ ] Sabes qué haría `sync --delete` sin `--dryrun`.

#### Limpieza

`aws s3 rm s3://$BUCKET --recursive` (las versiones antiguas expirarán con la regla de ciclo de vida; si no tienes, vacía el bucket como en la práctica 2.5).

---

## Práctica 5.2 · Sincronización desatendida con rclone

{{< practica num="5.2" tipo="Guiada" duracion="1,5 h" nivel="2" ra="RA5: e, f, h" entorno="local-lab · rclone · systemd · CloudWatch" entrega="no" >}}

#### Objetivo

Sincronizar la carpeta de escaneos de la oficina con S3 **cada 15 minutos**, sin intervención, con registros, protección frente a borrados masivos, comprobación de integridad y aviso cuando falle.

#### Desarrollo

{{% steps %}}

1. **Configura el remoto** de rclone usando las credenciales de la CLI (`env_auth`):

    ```bash
    mkdir -p ~/.config/rclone
    cat > ~/.config/rclone/rclone.conf <<'EOF'
    [aws]
    type = s3
    provider = AWS
    env_auth = true
    region = us-east-1
    server_side_encryption = AES256
    EOF
    rclone lsd aws:
    ```

2. **Primera sincronización** unidireccional, en seco y después real:

    ```bash
    rclone sync ~/oficina/escaneos aws:$BUCKET/oficina/escaneos --dry-run
    rclone sync ~/oficina/escaneos aws:$BUCKET/oficina/escaneos --transfers 16 --checksum -P
    rclone check ~/oficina/escaneos aws:$BUCKET/oficina/escaneos --one-way
    ```

3. **Script desatendido** `~/bin/sync_escaneos.sh`:

    ```bash
    #!/usr/bin/env bash
    # Sincroniza los escaneos de la taquilla con S3. Uso desatendido (systemd).
    set -euo pipefail
    ORIGEN="$HOME/oficina/escaneos"
    DESTINO="aws:${BUCKET}/oficina/escaneos"
    LOG="$HOME/logs/sync_escaneos.log"
    mkdir -p "$(dirname "$LOG")"

    exec 9>/tmp/sync_escaneos.lock
    flock -n 9 || { echo "$(date -Is) ya hay otra ejecución" >> "$LOG"; exit 0; }

    # Protección: si el origen está vacío (disco sin montar), no sincronizar
    [ "$(find "$ORIGEN" -type f | head -1)" ] || { echo "$(date -Is) ERROR origen vacío" >> "$LOG"; exit 2; }

    echo "$(date -Is) inicio" >> "$LOG"
    rclone sync "$ORIGEN" "$DESTINO" --transfers 16 --checksum --max-delete 50 \
      --bwlimit "08:00,20M 21:00,off" --log-file "$LOG" --log-level INFO --stats-one-line
    rclone check "$ORIGEN" "$DESTINO" --one-way --log-file "$LOG"
    echo "$(date -Is) fin OK" >> "$LOG"

    # Métrica de «última sincronización correcta» para la alarma
    aws cloudwatch put-metric-data --namespace TaquillaAlacant --metric-name SyncEscaneosOK \
      --dimensions Alumno="$ALUMNO" --value 1
    ```

    ```bash
    chmod +x ~/bin/sync_escaneos.sh && ~/bin/sync_escaneos.sh && tail ~/logs/sync_escaneos.log
    ```

4. **Prográmalo** con un temporizador de systemd de usuario:

    ```bash
    mkdir -p ~/.config/systemd/user
    cat > ~/.config/systemd/user/sync-escaneos.service <<EOF
    [Unit]
    Description=Sincroniza escaneos de la taquilla con S3
    [Service]
    Type=oneshot
    Environment=BUCKET=$BUCKET ALUMNO=$ALUMNO
    ExecStart=%h/bin/sync_escaneos.sh
    EOF
    cat > ~/.config/systemd/user/sync-escaneos.timer <<'EOF'
    [Unit]
    Description=Cada 15 minutos
    [Timer]
    OnBootSec=2min
    OnUnitActiveSec=15min
    Persistent=true
    [Install]
    WantedBy=timers.target
    EOF
    systemctl --user daemon-reload
    systemctl --user enable --now sync-escaneos.timer
    loginctl enable-linger $USER          # que funcione sin sesión abierta
    systemctl --user list-timers
    ```

5. **Alarma por ausencia**: si en 1 hora no llega ninguna `SyncEscaneosOK`, algo va mal.

    ```bash
    aws cloudwatch put-metric-alarm --alarm-name ta-$ALUMNO-sync-escaneos \
      --namespace TaquillaAlacant --metric-name SyncEscaneosOK --dimensions Name=Alumno,Value=$ALUMNO \
      --statistic Sum --period 3600 --evaluation-periods 1 --threshold 1 \
      --comparison-operator LessThanThreshold --treat-missing-data breaching
    ```

6. **Provoca fallos** y comprueba que el sistema reacciona:
    - Renombra la carpeta de origen: el script sale con código 2 y no borra nada en S3.
    - Borra 60 ficheros del origen: `--max-delete 50` detiene la sincronización.
    - Para el temporizador una hora: la alarma pasa a `ALARM`.

7. **Bidireccional** (para la carpeta de plantillas que también editan desde la nube):

    ```bash
    mkdir -p ~/oficina/plantillas && echo "v1" > ~/oficina/plantillas/cartel.txt
    rclone bisync ~/oficina/plantillas aws:$BUCKET/oficina/plantillas --resync      # solo la primera vez
    echo "nuevo en la nube" | rclone rcat aws:$BUCKET/oficina/plantillas/nube.txt
    echo "v2 local" > ~/oficina/plantillas/cartel.txt
    rclone bisync ~/oficina/plantillas aws:$BUCKET/oficina/plantillas -v
    ls ~/oficina/plantillas
    ```

    Modifica el mismo fichero en los dos lados y vuelve a ejecutar `bisync`: observa cómo renombra las versiones en conflicto.

{{% /steps %}}

#### Comprobación

- [ ] `systemctl --user list-timers` muestra la próxima ejecución y el registro tiene varias ejecuciones `fin OK`.
- [ ] Las tres pruebas de fallo se comportan como se espera.
- [ ] Sabes explicar cómo resuelve `bisync` un conflicto.

---

## Práctica 5.3 · Migrar la base de datos de la oficina

{{< practica num="5.3" tipo="Guiada" duracion="2 h" nivel="2" ra="RA5: c, g, h" entorno="Docker · PostgreSQL 17 · pg_dump · S3 · RDS" entrega="no" >}}

#### Objetivo

Migrar de forma **supervisada** la base de datos de la taquilla física (PostgreSQL en la oficina) a RDS, pasando por S3, y **validar** que llega completa.

#### Requisitos previos

La instancia RDS y el bastión de la UD04 (laboratorio `ud04/lab/`) en marcha.

#### Desarrollo

{{% steps %}}

1. **La base de datos de la oficina** en `local-lab`:

    ```bash
    docker run -d --name oficina-pg -e POSTGRES_PASSWORD=oficina -e POSTGRES_DB=taquilla_oficina \
      -p 127.0.0.1:5433:5432 -v oficina-pg:/var/lib/postgresql/data postgres:17
    export PGHOST=127.0.0.1 PGPORT=5433 PGUSER=postgres PGPASSWORD=oficina PGDATABASE=taquilla_oficina
    curl -fsSLO https://lorenalresusta.github.io/BBDD-Nube/recursos/taquilla/esquema.sql
    curl -fsSLO https://lorenalresusta.github.io/BBDD-Nube/recursos/taquilla/generar_ventas.py
    psql -q -f esquema.sql && python3 generar_ventas.py --ventas 100000 --sql | psql -q
    ```

2. **Huella de validación** en el origen (la guardarás para comparar):

    ```bash
    cat > validar.sql <<'EOF'
    SELECT 'recinto' t, count(*), NULL::numeric s FROM recinto
    UNION ALL SELECT 'evento', count(*), sum(precio_base) FROM evento
    UNION ALL SELECT 'cliente', count(*), NULL FROM cliente
    UNION ALL SELECT 'venta', count(*), sum(importe) FROM venta
    UNION ALL SELECT 'venta_md5', NULL, ('x' || substr(md5(string_agg(id_venta::text || importe::text, ',' ORDER BY id_venta)), 1, 15))::bit(60)::bigint
             FROM venta
    ORDER BY 1;
    EOF
    psql -f validar.sql | tee huella_origen.txt
    ```

3. **Exporta** en formato personalizado y genera el hash:

    ```bash
    pg_dump -Fc --no-owner --no-privileges -f oficina.dump
    sha256sum oficina.dump | tee oficina.dump.sha256
    ```

4. **Transfiere** a S3 por HTTPS con suma de comprobación:

    ```bash
    aws s3 cp oficina.dump s3://$BUCKET/migracion/ --checksum-algorithm SHA256
    aws s3 cp oficina.dump.sha256 s3://$BUCKET/migracion/
    aws s3 cp validar.sql s3://$BUCKET/migracion/
    aws s3 cp huella_origen.txt s3://$BUCKET/migracion/
    ```

5. **En el bastión** (UD04), descarga, verifica e **importa** en una base de datos nueva de RDS:

    ```bash
    aws s3 cp s3://$BUCKET/migracion/ . --recursive
    sha256sum -c oficina.dump.sha256
    psql -d taquilla -c "CREATE DATABASE taquilla_oficina;"
    time pg_restore -d taquilla_oficina --no-owner --no-privileges -j 2 oficina.dump
    ```

6. **Valida** comparando la huella:

    ```bash
    psql -d taquilla_oficina -f validar.sql > huella_destino.txt
    diff huella_origen.txt huella_destino.txt && echo "MIGRACIÓN VALIDADA"
    ```

7. **Importación desde S3 con la extensión `aws_s3`** (otra vía, para CSV). Asocia el rol del laboratorio a la instancia para la función `s3Import`:

    ```bash
    CUENTA=$(aws sts get-caller-identity --query Account --output text)
    aws rds add-role-to-db-instance --db-instance-identifier ta-$ALUMNO-pg \
      --role-arn arn:aws:iam::$CUENTA:role/LabRole --feature-name s3Import
    python3 generar_ventas.py --ventas 5000 --salida ventas_taquilla.csv
    aws s3 cp ventas_taquilla.csv s3://$BUCKET/migracion/
    ```

    ```sql
    CREATE EXTENSION IF NOT EXISTS aws_s3 CASCADE;
    CREATE TABLE venta_csv (id_venta bigint, fecha_venta timestamp, canal text, entradas int, importe numeric,
      id_evento int, titulo text, categoria text, fecha_evento timestamp, recinto text, id_cliente int, cp_cliente text);
    SELECT aws_s3.table_import_from_s3('venta_csv', '', '(format csv, header true)',
           aws_commons.create_s3_uri('BUCKET', 'migracion/ventas_taquilla.csv', 'us-east-1'));
    SELECT count(*) FROM venta_csv;
    ```

    > [!NOTE]
    > Si el laboratorio no permite asociar `LabRole` a RDS, documenta el error y carga el CSV con `\copy venta_csv FROM 'ventas_taquilla.csv' CSV HEADER` desde el bastión.

{{% /steps %}}

#### Comprobación

- [ ] `sha256sum -c` es correcto en el destino.
- [ ] `diff` de las huellas no muestra diferencias.
- [ ] Sabes qué fases de una migración supervisada has hecho y cuáles faltarían en producción (congelar escrituras, cambiar la aplicación, vigilar).

---

## Práctica 5.4 · Preparar una transferencia física

{{< practica num="5.4" tipo="Autónoma" duracion="1 h" nivel="2" ra="RA5: a, b, d" entorno="local-lab · LUKS (cryptsetup) · sha256sum" entrega="ud05/p5_4.md" >}}

#### Enunciado

TaquillaAlacant ha comprado el archivo fotográfico de una antigua promotora: **18 TB** en discos USB. La oficina tiene una línea de **300 Mbps** que no puede ocupar en horario laboral (8:00 – 21:00).

1. **Calcula** cuánto tardaría por red usando solo las noches y fines de semana, y su coste (entrada y peticiones a S3, almacenamiento del primer mes en la clase que elijas).
2. **Compara** con una transferencia física en un **AWS Data Transfer Terminal** o con un socio: tiempos, costes y riesgos. Indica la fuente de cada dato.
3. **Simula la preparación** de un disco con un fichero de imagen de 1 GB:

    ```bash
    truncate -s 1G disco.img
    sudo cryptsetup luksFormat --type luks2 disco.img          # clave robusta, que no viaja con el disco
    sudo cryptsetup open disco.img traslado
    sudo mkfs.ext4 -L traslado /dev/mapper/traslado
    sudo mount /dev/mapper/traslado /mnt
    ```

    Copia en él una carpeta de prueba, genera el **manifiesto** `MANIFIESTO.sha256`, desmonta, cierra el volumen y simula la llegada: ábrelo y verifica el manifiesto.
4. Redacta un **procedimiento de cadena de custodia** de una página (quién, cuándo, precintos, registro, destrucción final).
5. Concluye qué opción recomiendas.

#### Comprobación

- [ ] Los cálculos de tiempo y coste son correctos y están justificados.
- [ ] El disco simulado se abre solo con la clave y el manifiesto se verifica sin errores.
- [ ] El procedimiento de custodia es aplicable.

---

## Práctica 5.5 · SFTP gestionado para socios

{{< practica num="5.5" tipo="Reto" duracion="1 h" nivel="3" ra="RA5: a, c, e" entorno="AWS Transfer Family · S3 · CloudWatch" entrega="ud05/p5_5.md" >}}

#### Enunciado

La promotora *Conciertos del Sureste* enviará cada noche un CSV de ventas por **SFTP**.

1. Crea un servidor **AWS Transfer Family** SFTP con punto de enlace público, identidades gestionadas por el servicio y almacenamiento en S3 (usa `LabRole` como rol de registro y de usuario).
2. Crea el usuario `sureste` con **clave SSH** (no contraseña) y un **directorio lógico** que solo le deje ver `s3://$BUCKET/socios/sureste/`.
3. Conéctate con `sftp -i clave_sureste` y sube un CSV. Comprueba que no puede salir de su directorio.
4. Localiza la sesión en los registros de CloudWatch del servidor.
5. Calcula el coste mensual del servidor (cobra por hora aunque nadie lo use) y propón cómo reducirlo.
6. **Borra el servidor** al terminar.

---

## Práctica 5.6 · La oficina de TaquillaAlacant, sincronizada

{{< practica num="5.6" tipo="Proyecto" duracion="1 h" nivel="3" ra="RA5: a, b, c, d, e, f, g, h" entorno="rclone · systemd · S3 · RDS · CloudWatch" entrega="ud05/ (scripts, unidades systemd, README.md, capturas)" >}}

#### Requisitos

- **Plan de transferencia** de todos los datos de la oficina (tabla del proyecto): herramienta, sentido, frecuencia, latencia máxima y coste mensual de cada uno.
- **Sincronización unidireccional** desatendida de `escaneos/` (cada 15 min) y **bidireccional** de `plantillas/` (cada hora), con bloqueo, registros, `--max-delete`, comprobación de integridad, métrica y alarma.
- **Política IAM** mínima que necesitaría el usuario o rol de la oficina en producción (solo los prefijos y acciones imprescindibles), aunque en el laboratorio uses las credenciales de `voclabs`.
- **Migración** supervisada de la base de datos de la oficina a RDS, con script de validación y el resultado del `diff`.
- **Exportación** semanal de la tabla `venta` de RDS a S3 en CSV comprimido (la usarás en la UD07).
- En el informe, la **hoja de ruta** de la migración en producción con fechas, corte previsto y plan de vuelta atrás.

#### Comprobación

- [ ] Los temporizadores funcionan y hay al menos 4 ejecuciones correctas en el registro.
- [ ] La alarma salta al detener la sincronización.
- [ ] La migración está validada y documentada.

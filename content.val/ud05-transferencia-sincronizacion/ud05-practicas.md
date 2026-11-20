---
title: "UD05 · Pràctiques"
weight: 2
bookToc: true
---

# UD05 · Pràctiques

{{< ra "RA5:a,b,c,d,e,f,g,h" >}}

| Pràctica | Tipus | Nivell | Hores | CA principals |
|---|---|---|--:|---|
| [5.1 Pujades eficients i verificables](#pràctica-51--pujades-eficients-i-verificables) | Guiada | ●○○ | 1,5 | RA5: a, c, h |
| [5.2 Sincronització desatesa amb rclone](#pràctica-52--sincronització-desatesa-amb-rclone) | Guiada | ●●○ | 1,5 | RA5: e, f, h |
| [5.3 Migrar la base de dades de l'oficina](#pràctica-53--migrar-la-base-de-dades-de-loficina) | Guiada | ●●○ | 2 | RA5: c, g, h |
| [5.4 Preparar una transferència física](#pràctica-54--preparar-una-transferència-física) | Autònoma | ●●○ | 1 | RA5: a, b, d |
| [5.5 SFTP gestionat per a socis](#pràctica-55--sftp-gestionat-per-a-socis) | Repte | ●●● | 1 | RA5: a, c, e |
| [5.6 L'oficina de TaquillaAlacant, sincronitzada](#pràctica-56--loficina-de-taquillaalacant-sincronitzada) | Projecte | ●●● | 1 | RA5: a – h |
| **Total** | | | **8 h** | |

> [!NOTE]
> Estes pràctiques es fan **des de `local-lab`**, que representa l'oficina. Necessites un bucket de destinació: crea `ta-$ALUMNO-oficina-$SUFIJO` amb versionat activat (com en la UD02) i exporta `BUCKET`.

---

## Pràctica 5.1 · Pujades eficients i verificables

{{< practica num="5.1" tipo="Guiada" duracion="1,5 h" nivel="1" ra="RA5: a, c, h" entorno="local-lab · AWS CLI v2 · S3" entrega="no" >}}

#### Objectiu

Mesurar com afecten la concurrència, la grandària de part i l'empaquetatge al temps de pujada, i comprovar la integritat del que s'ha pujat.

#### Desenvolupament

{{% steps %}}

1. **Genera dades de prova**: 2000 fitxers xicotets i 3 de grans.

    ```bash
    mkdir -p ~/oficina/escaneos ~/oficina/videos
    for i in $(seq -w 1 2000); do head -c 20000 /dev/urandom > ~/oficina/escaneos/ticket-$i.jpg; done
    for i in 1 2 3; do head -c 300M /dev/urandom > ~/oficina/videos/promo-$i.mp4; done
    du -sh ~/oficina/*
    ```

2. **Línia base** amb la configuració per defecte:

    ```bash
    aws configure get default.s3.max_concurrent_requests      # vacío = 10
    time aws s3 cp ~/oficina/escaneos s3://$BUCKET/prueba1/escaneos/ --recursive --only-show-errors
    time aws s3 cp ~/oficina/videos   s3://$BUCKET/prueba1/videos/   --recursive --only-show-errors
    ```

3. **Ajusta** la concurrència i la grandària de part, i repetix en un altre prefix:

    ```bash
    aws configure set default.s3.max_concurrent_requests 32
    aws configure set default.s3.multipart_chunksize 64MB
    time aws s3 cp ~/oficina/escaneos s3://$BUCKET/prueba2/escaneos/ --recursive --only-show-errors
    time aws s3 cp ~/oficina/videos   s3://$BUCKET/prueba2/videos/   --recursive --only-show-errors
    ```

4. **Empaqueta** els fitxers xicotets i compara (temps i nombre de peticions):

    ```bash
    time (tar -C ~/oficina -cf - escaneos | zstd -T0 -q -o /tmp/escaneos.tar.zst && \
          aws s3 cp /tmp/escaneos.tar.zst s3://$BUCKET/prueba3/)
    ```

5. **Puja amb una suma de comprovació SHA-256** i compara-la amb la local:

    ```bash
    aws s3 cp ~/oficina/videos/promo-1.mp4 s3://$BUCKET/prueba4/ --checksum-algorithm SHA256
    aws s3api get-object-attributes --bucket $BUCKET --key prueba4/promo-1.mp4 \
      --object-attributes Checksum ObjectParts ObjectSize
    sha256sum ~/oficina/videos/promo-1.mp4 | cut -d' ' -f1 | xxd -r -p | base64
    ```

    > [!NOTE]
    > En els objectes multipart, la suma que retorna S3 és la **suma de les sumes de les parts** (acaba en `-N`), no la del fitxer complet. Per a comparar amb el hash local, puja'l en una sola part o compara part a part.

6. **Sincronitza** només els canvis i prova l'esborrament en sec:

    ```bash
    touch ~/oficina/escaneos/ticket-0001.jpg; rm ~/oficina/escaneos/ticket-0002.jpg
    aws s3 sync ~/oficina/escaneos s3://$BUCKET/prueba2/escaneos/ --delete --dryrun
    ```

    Explica per què apareix `ticket-0001.jpg` encara que el seu contingut no ha canviat (pista: `sync` compara grandària i data).

{{% /steps %}}

#### Comprovació

- [ ] Tens una taula amb els temps de les tres estratègies i has calculat el nombre aproximat de peticions `PUT` de cadascuna.
- [ ] La suma SHA-256 de S3 coincidix amb la local (en una sola part).
- [ ] Saps què faria `sync --delete` sense `--dryrun`.

#### Neteja

`aws s3 rm s3://$BUCKET --recursive` (les versions antigues caducaran amb la regla de cicle de vida; si no en tens, buida el bucket com en la pràctica 2.5).

---

## Pràctica 5.2 · Sincronització desatesa amb rclone

{{< practica num="5.2" tipo="Guiada" duracion="1,5 h" nivel="2" ra="RA5: e, f, h" entorno="local-lab · rclone · systemd · CloudWatch" entrega="no" >}}

#### Objectiu

Sincronitzar la carpeta d'escanejos de l'oficina amb S3 **cada 15 minuts**, sense intervenció, amb registres, protecció davant d'esborraments massius, comprovació d'integritat i avís quan falle.

#### Desenvolupament

{{% steps %}}

1. **Configura el remot** de rclone usant les credencials de la CLI (`env_auth`):

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

2. **Primera sincronització** unidireccional, en sec i després real:

    ```bash
    rclone sync ~/oficina/escaneos aws:$BUCKET/oficina/escaneos --dry-run
    rclone sync ~/oficina/escaneos aws:$BUCKET/oficina/escaneos --transfers 16 --checksum -P
    rclone check ~/oficina/escaneos aws:$BUCKET/oficina/escaneos --one-way
    ```

3. **Script desatés** `~/bin/sync_escaneos.sh`:

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

4. **Programa'l** amb un temporitzador de systemd d'usuari:

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

5. **Alarma per absència**: si en 1 hora no arriba cap `SyncEscaneosOK`, alguna cosa va malament.

    ```bash
    aws cloudwatch put-metric-alarm --alarm-name ta-$ALUMNO-sync-escaneos \
      --namespace TaquillaAlacant --metric-name SyncEscaneosOK --dimensions Name=Alumno,Value=$ALUMNO \
      --statistic Sum --period 3600 --evaluation-periods 1 --threshold 1 \
      --comparison-operator LessThanThreshold --treat-missing-data breaching
    ```

6. **Provoca fallades** i comprova que el sistema reacciona:
    - Canvia el nom de la carpeta d'origen: l'script ix amb codi 2 i no esborra res en S3.
    - Esborra 60 fitxers de l'origen: `--max-delete 50` deté la sincronització.
    - Atura el temporitzador una hora: l'alarma passa a `ALARM`.

7. **Bidireccional** (per a la carpeta de plantilles que també editen des del núvol):

    ```bash
    mkdir -p ~/oficina/plantillas && echo "v1" > ~/oficina/plantillas/cartel.txt
    rclone bisync ~/oficina/plantillas aws:$BUCKET/oficina/plantillas --resync      # solo la primera vez
    echo "nuevo en la nube" | rclone rcat aws:$BUCKET/oficina/plantillas/nube.txt
    echo "v2 local" > ~/oficina/plantillas/cartel.txt
    rclone bisync ~/oficina/plantillas aws:$BUCKET/oficina/plantillas -v
    ls ~/oficina/plantillas
    ```

    Modifica el mateix fitxer en tots dos costats i torna a executar `bisync`: observa com canvia el nom de les versions en conflicte.

{{% /steps %}}

#### Comprovació

- [ ] `systemctl --user list-timers` mostra la pròxima execució i el registre té diverses execucions `fin OK`.
- [ ] Les tres proves de fallada es comporten com s'espera.
- [ ] Saps explicar com resol `bisync` un conflicte.

---

## Pràctica 5.3 · Migrar la base de dades de l'oficina

{{< practica num="5.3" tipo="Guiada" duracion="2 h" nivel="2" ra="RA5: c, g, h" entorno="Docker · PostgreSQL 17 · pg_dump · S3 · RDS" entrega="no" >}}

#### Objectiu

Migrar de manera **supervisada** la base de dades de la taquilla física (PostgreSQL en l'oficina) a RDS, passant per S3, i **validar** que arriba completa.

#### Requisits previs

La instància RDS i el bastió de la UD04 (laboratori `ud04/lab/`) en marxa.

#### Desenvolupament

{{% steps %}}

1. **La base de dades de l'oficina** en `local-lab`:

    ```bash
    docker run -d --name oficina-pg -e POSTGRES_PASSWORD=oficina -e POSTGRES_DB=taquilla_oficina \
      -p 127.0.0.1:5433:5432 -v oficina-pg:/var/lib/postgresql/data postgres:17
    export PGHOST=127.0.0.1 PGPORT=5433 PGUSER=postgres PGPASSWORD=oficina PGDATABASE=taquilla_oficina
    curl -fsSLO https://lorenalresusta.github.io/BBDD-Nube/recursos/taquilla/esquema.sql
    curl -fsSLO https://lorenalresusta.github.io/BBDD-Nube/recursos/taquilla/generar_ventas.py
    psql -q -f esquema.sql && python3 generar_ventas.py --ventas 100000 --sql | psql -q
    ```

2. **Empremta de validació** en l'origen (la guardaràs per a comparar):

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

3. **Exporta** en format personalitzat i genera el hash:

    ```bash
    pg_dump -Fc --no-owner --no-privileges -f oficina.dump
    sha256sum oficina.dump | tee oficina.dump.sha256
    ```

4. **Transferix** a S3 per HTTPS amb suma de comprovació:

    ```bash
    aws s3 cp oficina.dump s3://$BUCKET/migracion/ --checksum-algorithm SHA256
    aws s3 cp oficina.dump.sha256 s3://$BUCKET/migracion/
    aws s3 cp validar.sql s3://$BUCKET/migracion/
    aws s3 cp huella_origen.txt s3://$BUCKET/migracion/
    ```

5. **En el bastió** (UD04), descarrega, verifica i **importa** en una base de dades nova de RDS:

    ```bash
    aws s3 cp s3://$BUCKET/migracion/ . --recursive
    sha256sum -c oficina.dump.sha256
    psql -d taquilla -c "CREATE DATABASE taquilla_oficina;"
    time pg_restore -d taquilla_oficina --no-owner --no-privileges -j 2 oficina.dump
    ```

6. **Valida** comparant l'empremta:

    ```bash
    psql -d taquilla_oficina -f validar.sql > huella_destino.txt
    diff huella_origen.txt huella_destino.txt && echo "MIGRACIÓN VALIDADA"
    ```

7. **Importació des de S3 amb l'extensió `aws_s3`** (una altra via, per a CSV). Associa el rol del laboratori a la instància per a la funció `s3Import`:

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
    > Si el laboratori no permet associar `LabRole` a RDS, documenta l'error i carrega el CSV amb `\copy venta_csv FROM 'ventas_taquilla.csv' CSV HEADER` des del bastió.

{{% /steps %}}

#### Comprovació

- [ ] `sha256sum -c` és correcte en la destinació.
- [ ] `diff` de les empremtes no mostra diferències.
- [ ] Saps quines fases d'una migració supervisada has fet i quines faltarien en producció (congelar escriptures, canviar l'aplicació, vigilar).

---

## Pràctica 5.4 · Preparar una transferència física

{{< practica num="5.4" tipo="Autónoma" duracion="1 h" nivel="2" ra="RA5: a, b, d" entorno="local-lab · LUKS (cryptsetup) · sha256sum" entrega="ud05/p5_4.md" >}}

#### Enunciat

TaquillaAlacant ha comprat l'arxiu fotogràfic d'una antiga promotora: **18 TB** en discos USB. L'oficina té una línia de **300 Mbps** que no pot ocupar en horari laboral (8:00 – 21:00).

1. **Calcula** quant tardaria per xarxa usant només les nits i els caps de setmana, i el seu cost (entrada i peticions a S3, emmagatzematge del primer mes en la classe que tries).
2. **Compara** amb una transferència física en un **AWS Data Transfer Terminal** o amb un soci: temps, costos i riscos. Indica la font de cada dada.
3. **Simula la preparació** d'un disc amb un fitxer d'imatge d'1 GB:

    ```bash
    truncate -s 1G disco.img
    sudo cryptsetup luksFormat --type luks2 disco.img          # clave robusta, que no viaja con el disco
    sudo cryptsetup open disco.img traslado
    sudo mkfs.ext4 -L traslado /dev/mapper/traslado
    sudo mount /dev/mapper/traslado /mnt
    ```

    Copia-hi una carpeta de prova, genera el **manifest** `MANIFIESTO.sha256`, desmunta, tanca el volum i simula l'arribada: obri'l i verifica el manifest.
4. Redacta un **procediment de cadena de custòdia** d'una pàgina (qui, quan, precintes, registre, destrucció final).
5. Conclou quina opció recomanes.

#### Comprovació

- [ ] Els càlculs de temps i cost són correctes i estan justificats.
- [ ] El disc simulat s'obri només amb la clau i el manifest es verifica sense errors.
- [ ] El procediment de custòdia és aplicable.

---

## Pràctica 5.5 · SFTP gestionat per a socis

{{< practica num="5.5" tipo="Reto" duracion="1 h" nivel="3" ra="RA5: a, c, e" entorno="AWS Transfer Family · S3 · CloudWatch" entrega="ud05/p5_5.md" >}}

#### Enunciat

La promotora *Conciertos del Sureste* enviarà cada nit un CSV de vendes per **SFTP**.

1. Crea un servidor **AWS Transfer Family** SFTP amb punt d'enllaç públic, identitats gestionades pel servei i emmagatzematge en S3 (usa `LabRole` com a rol de registre i d'usuari).
2. Crea l'usuari `sureste` amb **clau SSH** (no contrasenya) i un **directori lògic** que només li deixe veure `s3://$BUCKET/socios/sureste/`.
3. Connecta't amb `sftp -i clave_sureste` i puja un CSV. Comprova que no pot eixir del seu directori.
4. Localitza la sessió en els registres de CloudWatch del servidor.
5. Calcula el cost mensual del servidor (cobra per hora encara que ningú l'use) i proposa com reduir-lo.
6. **Esborra el servidor** en acabar.

---

## Pràctica 5.6 · L'oficina de TaquillaAlacant, sincronitzada

{{< practica num="5.6" tipo="Proyecto" duracion="1 h" nivel="3" ra="RA5: a, b, c, d, e, f, g, h" entorno="rclone · systemd · S3 · RDS · CloudWatch" entrega="ud05/ (scripts, unitats systemd, README.md, captures)" >}}

#### Requisits

- **Pla de transferència** de totes les dades de l'oficina (taula del projecte): ferramenta, sentit, freqüència, latència màxima i cost mensual de cadascuna.
- **Sincronització unidireccional** desatesa d'`escaneos/` (cada 15 min) i **bidireccional** de `plantillas/` (cada hora), amb bloqueig, registres, `--max-delete`, comprovació d'integritat, mètrica i alarma.
- **Política IAM** mínima que necessitaria l'usuari o el rol de l'oficina en producció (només els prefixos i les accions imprescindibles), encara que en el laboratori uses les credencials de `voclabs`.
- **Migració** supervisada de la base de dades de l'oficina a RDS, amb script de validació i el resultat del `diff`.
- **Exportació** setmanal de la taula `venta` de RDS a S3 en CSV comprimit (la usaràs en la UD07).
- En l'informe, el **full de ruta** de la migració en producció amb dates, tall previst i pla de marxa arrere.

#### Comprovació

- [ ] Els temporitzadors funcionen i hi ha almenys 4 execucions correctes en el registre.
- [ ] L'alarma salta en aturar la sincronització.
- [ ] La migració està validada i documentada.

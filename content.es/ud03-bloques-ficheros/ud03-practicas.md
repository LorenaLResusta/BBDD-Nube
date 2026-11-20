---
title: "UD03 · Prácticas"
weight: 2
bookToc: true
---

# UD03 · Prácticas

{{< ra "RA3:a,b,c,d,e,f,g" >}}

| Práctica | Tipo | Nivel | Horas | CE principales |
|---|---|---|--:|---|
| [3.1 Volumen EBS cifrado con OpenTofu](#práctica-31--volumen-ebs-cifrado-con-opentofu) | Guiada | ●●○ | 2 | RA3: a, c, e |
| [3.2 Ampliar, cambiar y restaurar un volumen](#práctica-32--ampliar-cambiar-y-restaurar-un-volumen) | Guiada | ●●○ | 1,5 | RA3: b, f, g |
| [3.3 EFS compartido, con TLS y solo lectura](#práctica-33--efs-compartido-con-tls-y-solo-lectura) | Guiada | ●●○ | 2 | RA3: a, b, d, e |
| [3.4 Plan de copias con AWS Backup](#práctica-34--plan-de-copias-con-aws-backup) | Autónoma | ●●○ | 1 | RA3: d, g |
| [3.5 El servidor de aplicaciones de TaquillaAlacant](#práctica-35--el-servidor-de-aplicaciones-de-taquillaalacant) | Proyecto | ●●● | 1,5 | RA3: a – g |
| **Total** | | | **8 h** | |

> [!NOTE]
> Para entrar por SSH a las instancias descarga la clave del laboratorio (*AWS Details → Download PEM*, fichero `labsuser.pem`) y dale permisos: `chmod 400 labsuser.pem`. Las instancias usan **Amazon Linux 2023** (usuario `ec2-user`).

---

## Práctica 3.1 · Volumen EBS cifrado con OpenTofu

{{< practica num="3.1" tipo="Guiada" duracion="2 h" nivel="2" ra="RA3: a, c, e" entorno="OpenTofu · EC2 · EBS · KMS" entrega="no" >}}

#### Objetivo

Desplegar una instancia con un **segundo volumen gp3 cifrado con tu clave de KMS**, formatearlo, montarlo de forma persistente y comprobar el modo de solo lectura.

#### Desarrollo

{{% steps %}}

1. **Carpeta `ud03/lab/`** con este `main.tf` (lo reutilizarás en toda la unidad):

    ```hcl
    terraform {
      required_providers {
        aws = { source = "hashicorp/aws", version = "~> 6.0" }
      }
    }

    provider "aws" {
      region = "us-east-1"
      default_tags {
        tags = { Proyecto = "TaquillaAlacant", Alumno = var.alumno, Modulo = "5162" }
      }
    }

    variable "alumno" { type = string }
    variable "mi_ip" {
      description = "Tu IP pública en formato CIDR (curl -s ifconfig.me)/32"
      type        = string
    }

    data "aws_vpc" "default" { default = true }

    data "aws_ssm_parameter" "al2023" {
      name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
    }

    resource "aws_kms_key" "discos" {
      description             = "TaquillaAlacant ${var.alumno}: discos"
      enable_key_rotation     = true
      deletion_window_in_days = 7
    }

    resource "aws_security_group" "app" {
      name   = "ta-${var.alumno}-app"
      vpc_id = data.aws_vpc.default.id
      ingress {
        description = "SSH desde mi IP"
        from_port   = 22
        to_port     = 22
        protocol    = "tcp"
        cidr_blocks = [var.mi_ip]
      }
      egress {
        from_port   = 0
        to_port     = 0
        protocol    = "-1"
        cidr_blocks = ["0.0.0.0/0"]
      }
    }

    resource "aws_instance" "app" {
      ami                    = data.aws_ssm_parameter.al2023.value
      instance_type          = "t3.micro"
      availability_zone      = "us-east-1a"
      key_name               = "vockey"
      iam_instance_profile   = "LabInstanceProfile"
      vpc_security_group_ids = [aws_security_group.app.id]
      root_block_device {
        volume_type = "gp3"
        volume_size = 8
        encrypted   = true
        kms_key_id  = aws_kms_key.discos.arn
      }
      tags = { Name = "ta-${var.alumno}-app" }
    }

    resource "aws_ebs_volume" "logs" {
      availability_zone = aws_instance.app.availability_zone
      size              = 10
      type              = "gp3"
      iops              = 3000
      throughput        = 125
      encrypted         = true
      kms_key_id        = aws_kms_key.discos.arn
      tags              = { Name = "ta-${var.alumno}-logs", Backup = "diario" }
    }

    resource "aws_volume_attachment" "logs" {
      device_name = "/dev/sdf"
      volume_id   = aws_ebs_volume.logs.id
      instance_id = aws_instance.app.id
    }

    output "ip" { value = aws_instance.app.public_ip }
    output "volumen" { value = aws_ebs_volume.logs.id }
    ```

2. **Despliega y conéctate**:

    ```bash
    tofu init
    tofu apply -var alumno=$ALUMNO -var mi_ip=$(curl -s ifconfig.me)/32
    ssh -i labsuser.pem ec2-user@$(tofu output -raw ip)
    ```

3. **Identifica el volumen** dentro de la instancia. El número de serie NVMe contiene el identificador del volumen:

    ```bash
    lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,SERIAL
    ```

    ```text
    NAME          SIZE TYPE FSTYPE MOUNTPOINT SERIAL
    nvme0n1         8G disk                   vol0a1b2c3d4e5f60001
    ├─nvme0n1p1     8G part xfs    /
    ...
    nvme1n1        10G disk                   vol0f9e8d7c6b5a40002
    ```

4. **Formatea y monta** de forma persistente:

    ```bash
    sudo mkfs.xfs -L logs /dev/nvme1n1
    sudo mkdir -p /datos/logs
    echo "LABEL=logs /datos/logs xfs defaults,nofail 0 2" | sudo tee -a /etc/fstab
    sudo systemctl daemon-reload && sudo mount -a
    df -hT /datos/logs
    ```

5. **Genera datos** para las siguientes prácticas:

    ```bash
    for d in $(seq -w 1 30); do
      sudo sh -c "seq 1 20000 | sed 's/^/2026-11-$d venta OK /' > /datos/logs/app-2026-11-$d.log"
    done
    du -sh /datos/logs
    ```

6. **Comprueba que sobrevive a un reinicio**: `sudo reboot`, vuelve a entrar y `findmnt /datos/logs`.

7. **Modo solo lectura**:

    ```bash
    sudo mount -o remount,ro /datos/logs
    touch /datos/logs/prueba            # Read-only file system
    sudo mount -o remount,rw /datos/logs
    ```

8. **Comprueba el cifrado** desde fuera:

    ```bash
    aws ec2 describe-volumes --volume-ids $(tofu output -raw volumen) \
      --query 'Volumes[0].[Encrypted,KmsKeyId,VolumeType,Iops,Throughput,AvailabilityZone]'
    ```

{{% /steps %}}

#### Comprobación

- [ ] El volumen está cifrado con **tu** clave y montado en `/datos/logs` tras reiniciar.
- [ ] Sabes relacionar `/dev/sdf` de la consola con `nvme1n1` dentro de la instancia.
- [ ] El montaje en `ro` impide escribir.

> [!NOTE]
> **No destruyas** el laboratorio: lo usan las prácticas 3.2 a 3.4. Si terminas la sesión, la instancia se para pero los volúmenes siguen ahí.

---

## Práctica 3.2 · Ampliar, cambiar y restaurar un volumen

{{< practica num="3.2" tipo="Guiada" duracion="1,5 h" nivel="2" ra="RA3: b, f, g" entorno="AWS CLI · EBS · instantáneas" entrega="no" >}}

#### Objetivo

Hacer los cambios típicos de la vida de un volumen (ampliar, cambiar rendimiento) sin parar el servicio, y recuperar datos desde una instantánea, también en otra región.

#### Desarrollo

{{% steps %}}

1. **Instantánea** antes de tocar nada:

    ```bash
    VOL=$(tofu output -raw volumen)
    SNAP=$(aws ec2 create-snapshot --volume-id $VOL --description "antes de ampliar" \
      --tag-specifications "ResourceType=snapshot,Tags=[{Key=Alumno,Value=$ALUMNO}]" \
      --query SnapshotId --output text)
    aws ec2 wait snapshot-completed --snapshot-ids $SNAP && echo "lista"
    ```

2. **Amplía** el volumen a 15 GB y sube el rendimiento a 250 MB/s, **con el volumen montado**:

    ```bash
    aws ec2 modify-volume --volume-id $VOL --size 15 --throughput 250
    aws ec2 describe-volumes-modifications --volume-ids $VOL \
      --query 'VolumesModifications[0].[ModificationState,Progress]'
    ```

3. **Extiende el sistema de ficheros** dentro de la instancia (aquí no hay partición, el XFS ocupa todo el disco):

    ```bash
    lsblk /dev/nvme1n1           # ya ve 15G
    df -h /datos/logs            # aún 10G
    sudo xfs_growfs -d /datos/logs
    df -h /datos/logs            # 15G
    ```

4. **Intenta reducirlo** a 12 GB y lee el error. Explica en tus notas cómo lo harías (volumen nuevo + copia con `rsync`).

5. **Simula un desastre**: borra los registros de los días 01 al 10.

    ```bash
    sudo rm /datos/logs/app-2026-11-0*.log /datos/logs/app-2026-11-10.log
    ```

6. **Restaura** desde la instantánea en un volumen nuevo, móntalo en **solo lectura** y recupera lo borrado:

    ```bash
    NUEVO=$(aws ec2 create-volume --snapshot-id $SNAP --availability-zone us-east-1a \
      --volume-type gp3 --encrypted --query VolumeId --output text)
    aws ec2 wait volume-available --volume-ids $NUEVO
    aws ec2 attach-volume --volume-id $NUEVO --instance-id $(aws ec2 describe-instances \
      --filters Name=tag:Name,Values=ta-$ALUMNO-app Name=instance-state-name,Values=running \
      --query 'Reservations[0].Instances[0].InstanceId' --output text) --device /dev/sdg
    ```

    En la instancia (el volumen restaurado tiene la **misma etiqueta y UUID** que el original, por eso se monta con `nouuid` y por dispositivo):

    ```bash
    sudo mkdir -p /mnt/restaurado
    sudo mount -o ro,nouuid /dev/nvme2n1 /mnt/restaurado
    sudo cp -av /mnt/restaurado/app-2026-11-0*.log /mnt/restaurado/app-2026-11-10.log /datos/logs/
    sudo umount /mnt/restaurado
    ```

7. **Retira el volumen restaurado** correctamente: desmontado (hecho), desconectado y borrado.

    ```bash
    aws ec2 detach-volume --volume-id $NUEVO && aws ec2 wait volume-available --volume-ids $NUEVO
    aws ec2 delete-volume --volume-id $NUEVO
    ```

8. **Copia la instantánea a Oregón** (recuperación ante desastre):

    ```bash
    aws ec2 copy-snapshot --region us-west-2 --source-region us-east-1 --source-snapshot-id $SNAP \
      --encrypted --description "DR logs $ALUMNO"
    ```

    Como la clave de origen es de `us-east-1`, la copia se cifra con la clave por defecto `aws/ebs` de Oregón (o con la que indiques en `--kms-key-id`).

{{% /steps %}}

#### Comprobación

- [ ] `df -h` muestra 15 GB sin haber desmontado el volumen.
- [ ] Los ficheros borrados están de vuelta.
- [ ] Hay una copia de la instantánea en `us-west-2`.

#### Limpieza parcial

Borra la instantánea de Oregón cuando termine la copia (`aws ec2 delete-snapshot --region us-west-2 --snapshot-id ...`). Conserva el resto para la 3.3.

---

## Práctica 3.3 · EFS compartido, con TLS y solo lectura

{{< practica num="3.3" tipo="Guiada" duracion="2 h" nivel="2" ra="RA3: a, b, d, e" entorno="OpenTofu · EFS · amazon-efs-utils" entrega="no" >}}

#### Objetivo

Crear el sistema de ficheros de **plantillas** de TaquillaAlacant, montarlo desde dos instancias en zonas distintas (una escribe, otra solo lee) con TLS obligatorio y puntos de acceso.

#### Desarrollo

{{% steps %}}

1. **Añade a `ud03/lab/main.tf`** una segunda instancia en otra AZ, el sistema de ficheros, sus puntos de montaje y dos puntos de acceso:

    ```hcl
    data "aws_subnets" "default" {
      filter {
        name   = "vpc-id"
        values = [data.aws_vpc.default.id]
      }
      filter {
        name   = "availability-zone"
        values = ["us-east-1a", "us-east-1b"]
      }
    }

    resource "aws_instance" "lector" {
      ami                    = data.aws_ssm_parameter.al2023.value
      instance_type          = "t3.micro"
      availability_zone      = "us-east-1b"
      key_name               = "vockey"
      iam_instance_profile   = "LabInstanceProfile"
      vpc_security_group_ids = [aws_security_group.app.id]
      tags                   = { Name = "ta-${var.alumno}-lector" }
    }

    resource "aws_security_group" "efs" {
      name   = "ta-${var.alumno}-efs"
      vpc_id = data.aws_vpc.default.id
      ingress {
        description     = "NFS solo desde las instancias de la aplicacion"
        from_port       = 2049
        to_port         = 2049
        protocol        = "tcp"
        security_groups = [aws_security_group.app.id]
      }
    }

    resource "aws_efs_file_system" "plantillas" {
      creation_token  = "ta-${var.alumno}-plantillas"
      encrypted       = true
      kms_key_id      = aws_kms_key.discos.arn
      throughput_mode = "elastic"
      lifecycle_policy { transition_to_ia = "AFTER_30_DAYS" }
      lifecycle_policy { transition_to_primary_storage_class = "AFTER_1_ACCESS" }
      tags = { Name = "ta-${var.alumno}-plantillas", Backup = "diario" }
    }

    resource "aws_efs_mount_target" "mt" {
      for_each        = toset(data.aws_subnets.default.ids)
      file_system_id  = aws_efs_file_system.plantillas.id
      subnet_id       = each.value
      security_groups = [aws_security_group.efs.id]
    }

    resource "aws_efs_access_point" "escritura" {
      file_system_id = aws_efs_file_system.plantillas.id
      posix_user {
        uid = 1001
        gid = 1001
      }
      root_directory {
        path = "/plantillas"
        creation_info {
          owner_uid   = 1001
          owner_gid   = 1001
          permissions = "755"
        }
      }
      tags = { Name = "escritura" }
    }

    resource "aws_efs_access_point" "lectura" {
      file_system_id = aws_efs_file_system.plantillas.id
      posix_user {
        uid = 2002
        gid = 2002
      }
      root_directory { path = "/plantillas" }
      tags = { Name = "lectura" }
    }

    # Política: exigir TLS; el punto de acceso de lectura no puede escribir
    resource "aws_efs_file_system_policy" "plantillas" {
      file_system_id = aws_efs_file_system.plantillas.id
      policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
          {
            Sid       = "ExigirTLS"
            Effect    = "Deny"
            Principal = { AWS = "*" }
            Action    = "*"
            Resource  = aws_efs_file_system.plantillas.arn
            Condition = { Bool = { "aws:SecureTransport" = "false" } }
          },
          {
            Sid       = "MontarYEscribir"
            Effect    = "Allow"
            Principal = { AWS = "*" }
            Action    = ["elasticfilesystem:ClientMount", "elasticfilesystem:ClientWrite"]
            Resource  = aws_efs_file_system.plantillas.arn
            Condition = { StringEquals = { "elasticfilesystem:AccessPointArn" = aws_efs_access_point.escritura.arn } }
          },
          {
            Sid       = "SoloMontar"
            Effect    = "Allow"
            Principal = { AWS = "*" }
            Action    = ["elasticfilesystem:ClientMount"]
            Resource  = aws_efs_file_system.plantillas.arn
            Condition = { StringEquals = { "elasticfilesystem:AccessPointArn" = aws_efs_access_point.lectura.arn } }
          }
        ]
      })
    }

    output "efs" { value = aws_efs_file_system.plantillas.id }
    output "ap_escritura" { value = aws_efs_access_point.escritura.id }
    output "ap_lectura" { value = aws_efs_access_point.lectura.id }
    output "ip_lector" { value = aws_instance.lector.public_ip }
    ```

    ```bash
    tofu apply -var alumno=$ALUMNO -var mi_ip=$(curl -s ifconfig.me)/32
    ```

2. **En la instancia `app`** (escritura): instala el asistente y monta con TLS e IAM a través del punto de acceso de escritura:

    ```bash
    sudo dnf install -y amazon-efs-utils
    sudo mkdir -p /srv/plantillas
    sudo mount -t efs -o tls,iam,accesspoint=FSAP_ESCRITURA FS_ID:/ /srv/plantillas
    echo "Plantilla de entrada v1" > /srv/plantillas/entrada.html
    ls -ln /srv/plantillas          # propietario 1001:1001, aunque escribas como ec2-user
    ```

3. **En la instancia `lector`**, monta por el punto de acceso de lectura:

    ```bash
    sudo dnf install -y amazon-efs-utils
    sudo mkdir -p /srv/plantillas
    sudo mount -t efs -o tls,iam,accesspoint=FSAP_LECTURA FS_ID:/ /srv/plantillas
    cat /srv/plantillas/entrada.html
    touch /srv/plantillas/no            # debe fallar: Permission denied / Read-only
    ```

4. **Comprueba que sin TLS no entra** (en `lector`):

    ```bash
    sudo mkdir -p /mnt/sintls
    sudo mount -t nfs4 -o nfsvers=4.1 FS_ID.efs.us-east-1.amazonaws.com:/ /mnt/sintls   # access denied
    ```

5. **Hazlo persistente** en `/etc/fstab` de `app`:

    ```text
    FS_ID:/ /srv/plantillas efs _netdev,noresvport,tls,iam,accesspoint=FSAP_ESCRITURA 0 0
    ```

6. **Observa las métricas** en CloudWatch → EFS: `ClientConnections` (debe ser 2), `StorageBytes` y `MeteredIOBytes`.

{{% /steps %}}

#### Comprobación

- [ ] Ambas instancias, en AZ distintas, ven el mismo fichero.
- [ ] El lector no puede escribir y nadie puede montar sin TLS.
- [ ] Los ficheros pertenecen al UID del punto de acceso.

#### Problemas habituales

| Síntoma | Causa | Solución |
|---|---|---|
| `mount.nfs4: Connection timed out` | Grupo de seguridad o el punto de montaje aún no está disponible | Espera a `available`; revisa la regla 2049 |
| `access denied by server` con el punto de acceso correcto | La política exige `iam` y montas sin esa opción | Añade `iam` a las opciones |
| `Failed to resolve "fs-...efs.us-east-1.amazonaws.com"` | La VPC no tiene activada la resolución DNS | La VPC por defecto sí la tiene; revisa la VPC |

---

## Práctica 3.4 · Plan de copias con AWS Backup

{{< practica num="3.4" tipo="Autónoma" duracion="1 h" nivel="2" ra="RA3: d, g" entorno="AWS Backup · EBS · EFS" entrega="ud03/p3_4.md" >}}

#### Objetivo

Proteger el volumen de logs y el EFS de plantillas con un **plan de AWS Backup** por etiquetas y **demostrar** que se pueden restaurar.

#### Enunciado

1. Crea (con la consola, la CLI u OpenTofu, y documentándolo) una **bóveda** `ta-<alumno>-boveda` cifrada con tu clave de KMS.
2. Crea un **plan** con dos reglas: diaria a las 02:00 UTC con retención de 14 días, y mensual con retención de 365 días y copia a una bóveda en `us-west-2`.
3. **Asigna** al plan los recursos con la etiqueta `Backup=diario`, usando `LabRole` como rol de servicio.
4. Lanza una **copia bajo demanda** de cada recurso y espera a que termine.
5. **Restaura** el EFS en un sistema de ficheros nuevo (o en un directorio del mismo) y el volumen EBS en un volumen nuevo; comprueba el contenido y anota el **tiempo de restauración**.
6. Calcula el coste mensual del plan y propón el RPO y el RTO que ofrece.

#### Comprobación

- [ ] Hay trabajos de copia `COMPLETED` de los dos recursos.
- [ ] Hay al menos una restauración comprobada de cada uno, con el tiempo medido.
- [ ] El informe indica RPO, RTO y coste.

#### Limpieza

Borra los puntos de recuperación, las bóvedas y el plan, y después: `tofu destroy -var alumno=$ALUMNO -var mi_ip=0.0.0.0/32`.

---

## Práctica 3.5 · El servidor de aplicaciones de TaquillaAlacant

{{< practica num="3.5" tipo="Proyecto" duracion="1,5 h" nivel="3" ra="RA3: a, b, c, d, e, f, g" entorno="OpenTofu · EC2 · EBS · EFS · CloudWatch · AWS Backup" entrega="ud03/ (código *.tf, scripts, README.md y capturas)" >}}

#### Objetivo

Dejar preparada con IaC la capa de almacenamiento de los servidores de aplicaciones.

#### Requisitos

- **Disco de logs** gp3 cifrado con clave propia, montado en `/datos/logs` de forma persistente, con un tamaño justificado a partir del volumen de logs del proyecto (5 GB/semana) y su retención.
- Un **script `rotar_logs.sh`** que comprima los logs de más de 7 días y los suba al bucket de la UD02 (prefijo `logs/`), y los borre del disco tras comprobar la subida.
- **EFS de plantillas** Regional, cifrado, con ciclo de vida a IA, TLS obligatorio, punto de acceso de escritura para la aplicación y de lectura para el equipo de marketing.
- **Alarmas** de CloudWatch: disco de logs por encima del 80 % (agente de CloudWatch, métrica `disk_used_percent`) y `PercentIOLimit` de EFS por encima del 90 %.
- **Copias**: el plan de la práctica 3.4 aplicado por etiqueta.
- **Informe**: elección de tipos y clases, región de producción, tabla de costes mensual y procedimiento documentado para **ampliar** el disco y para **restaurar** un fichero de plantillas borrado.

#### Comprobación

- [ ] Despliegue y destrucción completos con `tofu apply`/`tofu destroy`.
- [ ] La alarma de disco se dispara al llenar el volumen (`fallocate -l 9G /datos/logs/relleno`).
- [ ] El procedimiento de restauración está probado y cronometrado.

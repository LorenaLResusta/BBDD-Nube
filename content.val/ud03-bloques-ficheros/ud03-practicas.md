---
title: "UD03 · Pràctiques"
weight: 2
bookToc: true
---

# UD03 · Pràctiques

{{< ra "RA3:a,b,c,d,e,f,g" >}}

| Pràctica | Tipus | Nivell | Hores | CA principals |
|---|---|---|--:|---|
| [3.1 Volum EBS xifrat amb OpenTofu](#pràctica-31--volum-ebs-xifrat-amb-opentofu) | Guiada | ●●○ | 2 | RA3: a, c, e |
| [3.2 Ampliar, canviar i restaurar un volum](#pràctica-32--ampliar-canviar-i-restaurar-un-volum) | Guiada | ●●○ | 1,5 | RA3: b, f, g |
| [3.3 EFS compartit, amb TLS i només lectura](#pràctica-33--efs-compartit-amb-tls-i-només-lectura) | Guiada | ●●○ | 2 | RA3: a, b, d, e |
| [3.4 Pla de còpies amb AWS Backup](#pràctica-34--pla-de-còpies-amb-aws-backup) | Autònoma | ●●○ | 1 | RA3: d, g |
| [3.5 El servidor d'aplicacions de TaquillaAlacant](#pràctica-35--el-servidor-daplicacions-de-taquillaalacant) | Projecte | ●●● | 1,5 | RA3: a – g |
| **Total** | | | **8 h** | |

> [!NOTE]
> Per a entrar per SSH a les instàncies descarrega la clau del laboratori (*AWS Details → Download PEM*, fitxer `labsuser.pem`) i dona-li permisos: `chmod 400 labsuser.pem`. Les instàncies usen **Amazon Linux 2023** (usuari `ec2-user`).

---

## Pràctica 3.1 · Volum EBS xifrat amb OpenTofu

{{< practica num="3.1" tipo="Guiada" duracion="2 h" nivel="2" ra="RA3: a, c, e" entorno="OpenTofu · EC2 · EBS · KMS" entrega="no" >}}

#### Objectiu

Desplegar una instància amb un **segon volum gp3 xifrat amb la teua clau de KMS**, formatar-lo, muntar-lo de manera persistent i comprovar el mode de només lectura.

#### Desenvolupament

{{% steps %}}

1. **Carpeta `ud03/lab/`** amb este `main.tf` (el reutilitzaràs en tota la unitat):

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

2. **Desplega i connecta't**:

    ```bash
    tofu init
    tofu apply -var alumno=$ALUMNO -var mi_ip=$(curl -s ifconfig.me)/32
    ssh -i labsuser.pem ec2-user@$(tofu output -raw ip)
    ```

3. **Identifica el volum** dins de la instància. El número de sèrie NVMe conté l'identificador del volum:

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

4. **Formata i munta** de manera persistent:

    ```bash
    sudo mkfs.xfs -L logs /dev/nvme1n1
    sudo mkdir -p /datos/logs
    echo "LABEL=logs /datos/logs xfs defaults,nofail 0 2" | sudo tee -a /etc/fstab
    sudo systemctl daemon-reload && sudo mount -a
    df -hT /datos/logs
    ```

5. **Genera dades** per a les pràctiques següents:

    ```bash
    for d in $(seq -w 1 30); do
      sudo sh -c "seq 1 20000 | sed 's/^/2026-11-$d venta OK /' > /datos/logs/app-2026-11-$d.log"
    done
    du -sh /datos/logs
    ```

6. **Comprova que sobreviu a un reinici**: `sudo reboot`, torna a entrar i `findmnt /datos/logs`.

7. **Mode només lectura**:

    ```bash
    sudo mount -o remount,ro /datos/logs
    touch /datos/logs/prueba            # Read-only file system
    sudo mount -o remount,rw /datos/logs
    ```

8. **Comprova el xifratge** des de fora:

    ```bash
    aws ec2 describe-volumes --volume-ids $(tofu output -raw volumen) \
      --query 'Volumes[0].[Encrypted,KmsKeyId,VolumeType,Iops,Throughput,AvailabilityZone]'
    ```

{{% /steps %}}

#### Comprovació

- [ ] El volum està xifrat amb la **teua** clau i muntat en `/datos/logs` després de reiniciar.
- [ ] Saps relacionar `/dev/sdf` de la consola amb `nvme1n1` dins de la instància.
- [ ] El muntatge en `ro` impedix escriure.

> [!NOTE]
> **No destruïsques** el laboratori: l'usen les pràctiques 3.2 a 3.4. Si acabes la sessió, la instància s'atura però els volums continuen ací.

---

## Pràctica 3.2 · Ampliar, canviar i restaurar un volum

{{< practica num="3.2" tipo="Guiada" duracion="1,5 h" nivel="2" ra="RA3: b, f, g" entorno="AWS CLI · EBS · instantànies" entrega="no" >}}

#### Objectiu

Fer els canvis típics de la vida d'un volum (ampliar, canviar el rendiment) sense aturar el servei, i recuperar dades des d'una instantània, també en una altra regió.

#### Desenvolupament

{{% steps %}}

1. **Instantània** abans de tocar res:

    ```bash
    VOL=$(tofu output -raw volumen)
    SNAP=$(aws ec2 create-snapshot --volume-id $VOL --description "antes de ampliar" \
      --tag-specifications "ResourceType=snapshot,Tags=[{Key=Alumno,Value=$ALUMNO}]" \
      --query SnapshotId --output text)
    aws ec2 wait snapshot-completed --snapshot-ids $SNAP && echo "lista"
    ```

2. **Amplia** el volum a 15 GB i puja el rendiment a 250 MB/s, **amb el volum muntat**:

    ```bash
    aws ec2 modify-volume --volume-id $VOL --size 15 --throughput 250
    aws ec2 describe-volumes-modifications --volume-ids $VOL \
      --query 'VolumesModifications[0].[ModificationState,Progress]'
    ```

3. **Estén el sistema de fitxers** dins de la instància (ací no hi ha partició, l'XFS ocupa tot el disc):

    ```bash
    lsblk /dev/nvme1n1           # ya ve 15G
    df -h /datos/logs            # aún 10G
    sudo xfs_growfs -d /datos/logs
    df -h /datos/logs            # 15G
    ```

4. **Intenta reduir-lo** a 12 GB i llig l'error. Explica en les teues notes com ho faries (volum nou + còpia amb `rsync`).

5. **Simula un desastre**: esborra els registres dels dies 01 al 10.

    ```bash
    sudo rm /datos/logs/app-2026-11-0*.log /datos/logs/app-2026-11-10.log
    ```

6. **Restaura** des de la instantània en un volum nou, munta'l en **només lectura** i recupera el que s'ha esborrat:

    ```bash
    NUEVO=$(aws ec2 create-volume --snapshot-id $SNAP --availability-zone us-east-1a \
      --volume-type gp3 --encrypted --query VolumeId --output text)
    aws ec2 wait volume-available --volume-ids $NUEVO
    aws ec2 attach-volume --volume-id $NUEVO --instance-id $(aws ec2 describe-instances \
      --filters Name=tag:Name,Values=ta-$ALUMNO-app Name=instance-state-name,Values=running \
      --query 'Reservations[0].Instances[0].InstanceId' --output text) --device /dev/sdg
    ```

    En la instància (el volum restaurat té la **mateixa etiqueta i UUID** que l'original, per això es munta amb `nouuid` i per dispositiu):

    ```bash
    sudo mkdir -p /mnt/restaurado
    sudo mount -o ro,nouuid /dev/nvme2n1 /mnt/restaurado
    sudo cp -av /mnt/restaurado/app-2026-11-0*.log /mnt/restaurado/app-2026-11-10.log /datos/logs/
    sudo umount /mnt/restaurado
    ```

7. **Retira el volum restaurat** correctament: desmuntat (fet), desconnectat i esborrat.

    ```bash
    aws ec2 detach-volume --volume-id $NUEVO && aws ec2 wait volume-available --volume-ids $NUEVO
    aws ec2 delete-volume --volume-id $NUEVO
    ```

8. **Copia la instantània a Oregon** (recuperació davant de desastres):

    ```bash
    aws ec2 copy-snapshot --region us-west-2 --source-region us-east-1 --source-snapshot-id $SNAP \
      --encrypted --description "DR logs $ALUMNO"
    ```

    Com que la clau d'origen és d'`us-east-1`, la còpia es xifra amb la clau per defecte `aws/ebs` d'Oregon (o amb la que indiques en `--kms-key-id`).

{{% /steps %}}

#### Comprovació

- [ ] `df -h` mostra 15 GB sense haver desmuntat el volum.
- [ ] Els fitxers esborrats han tornat.
- [ ] Hi ha una còpia de la instantània en `us-west-2`.

#### Neteja parcial

Esborra la instantània d'Oregon quan acabe la còpia (`aws ec2 delete-snapshot --region us-west-2 --snapshot-id ...`). Conserva la resta per a la 3.3.

---

## Pràctica 3.3 · EFS compartit, amb TLS i només lectura

{{< practica num="3.3" tipo="Guiada" duracion="2 h" nivel="2" ra="RA3: a, b, d, e" entorno="OpenTofu · EFS · amazon-efs-utils" entrega="no" >}}

#### Objectiu

Crear el sistema de fitxers de **plantilles** de TaquillaAlacant, muntar-lo des de dues instàncies en zones diferents (una escriu, l'altra només llig) amb TLS obligatori i punts d'accés.

#### Desenvolupament

{{% steps %}}

1. **Afig a `ud03/lab/main.tf`** una segona instància en una altra AZ, el sistema de fitxers, els seus punts de muntatge i dos punts d'accés:

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

2. **En la instància `app`** (escriptura): instal·la l'assistent i munta amb TLS i IAM a través del punt d'accés d'escriptura:

    ```bash
    sudo dnf install -y amazon-efs-utils
    sudo mkdir -p /srv/plantillas
    sudo mount -t efs -o tls,iam,accesspoint=FSAP_ESCRITURA FS_ID:/ /srv/plantillas
    echo "Plantilla de entrada v1" > /srv/plantillas/entrada.html
    ls -ln /srv/plantillas          # propietario 1001:1001, aunque escribas como ec2-user
    ```

3. **En la instància `lector`**, munta pel punt d'accés de lectura:

    ```bash
    sudo dnf install -y amazon-efs-utils
    sudo mkdir -p /srv/plantillas
    sudo mount -t efs -o tls,iam,accesspoint=FSAP_LECTURA FS_ID:/ /srv/plantillas
    cat /srv/plantillas/entrada.html
    touch /srv/plantillas/no            # debe fallar: Permission denied / Read-only
    ```

4. **Comprova que sense TLS no entra** (en `lector`):

    ```bash
    sudo mkdir -p /mnt/sintls
    sudo mount -t nfs4 -o nfsvers=4.1 FS_ID.efs.us-east-1.amazonaws.com:/ /mnt/sintls   # access denied
    ```

5. **Fes-lo persistent** en `/etc/fstab` d'`app`:

    ```text
    FS_ID:/ /srv/plantillas efs _netdev,noresvport,tls,iam,accesspoint=FSAP_ESCRITURA 0 0
    ```

6. **Observa les mètriques** en CloudWatch → EFS: `ClientConnections` (ha de ser 2), `StorageBytes` i `MeteredIOBytes`.

{{% /steps %}}

#### Comprovació

- [ ] Totes dues instàncies, en AZ diferents, veuen el mateix fitxer.
- [ ] El lector no pot escriure i ningú pot muntar sense TLS.
- [ ] Els fitxers pertanyen a l'UID del punt d'accés.

#### Problemes habituals

| Símptoma | Causa | Solució |
|---|---|---|
| `mount.nfs4: Connection timed out` | Grup de seguretat o el punt de muntatge encara no està disponible | Espera a `available`; revisa la regla 2049 |
| `access denied by server` amb el punt d'accés correcte | La política exigix `iam` i muntes sense eixa opció | Afig `iam` a les opcions |
| `Failed to resolve "fs-...efs.us-east-1.amazonaws.com"` | La VPC no té activada la resolució DNS | La VPC per defecte sí que la té; revisa la VPC |

---

## Pràctica 3.4 · Pla de còpies amb AWS Backup

{{< practica num="3.4" tipo="Autónoma" duracion="1 h" nivel="2" ra="RA3: d, g" entorno="AWS Backup · EBS · EFS" entrega="ud03/p3_4.md" >}}

#### Objectiu

Protegir el volum de logs i l'EFS de plantilles amb un **pla d'AWS Backup** per etiquetes i **demostrar** que es poden restaurar.

#### Enunciat

1. Crea (amb la consola, la CLI o OpenTofu, i documentant-ho) una **volta** `ta-<alumne>-boveda` xifrada amb la teua clau de KMS.
2. Crea un **pla** amb dues regles: diària a les 02:00 UTC amb retenció de 14 dies, i mensual amb retenció de 365 dies i còpia a una volta en `us-west-2`.
3. **Assigna** al pla els recursos amb l'etiqueta `Backup=diario`, usant `LabRole` com a rol de servei.
4. Llança una **còpia sota demanda** de cada recurs i espera que acabe.
5. **Restaura** l'EFS en un sistema de fitxers nou (o en un directori del mateix) i el volum EBS en un volum nou; comprova el contingut i anota el **temps de restauració**.
6. Calcula el cost mensual del pla i proposa el RPO i el RTO que oferix.

#### Comprovació

- [ ] Hi ha treballs de còpia `COMPLETED` dels dos recursos.
- [ ] Hi ha almenys una restauració comprovada de cadascun, amb el temps mesurat.
- [ ] L'informe indica RPO, RTO i cost.

#### Neteja

Esborra els punts de recuperació, les voltes i el pla, i després: `tofu destroy -var alumno=$ALUMNO -var mi_ip=0.0.0.0/32`.

---

## Pràctica 3.5 · El servidor d'aplicacions de TaquillaAlacant

{{< practica num="3.5" tipo="Proyecto" duracion="1,5 h" nivel="3" ra="RA3: a, b, c, d, e, f, g" entorno="OpenTofu · EC2 · EBS · EFS · CloudWatch · AWS Backup" entrega="ud03/ (codi *.tf, scripts, README.md i captures)" >}}

#### Objectiu

Deixar preparada amb IaC la capa d'emmagatzematge dels servidors d'aplicacions.

#### Requisits

- **Disc de logs** gp3 xifrat amb clau pròpia, muntat en `/datos/logs` de manera persistent, amb una grandària justificada a partir del volum de logs del projecte (5 GB/setmana) i la seua retenció.
- Un **script `rotar_logs.sh`** que comprimisca els logs de més de 7 dies i els pugue al bucket de la UD02 (prefix `logs/`), i els esborre del disc després de comprovar la pujada.
- **EFS de plantilles** Regional, xifrat, amb cicle de vida a IA, TLS obligatori, punt d'accés d'escriptura per a l'aplicació i de lectura per a l'equip de màrqueting.
- **Alarmes** de CloudWatch: disc de logs per damunt del 80 % (agent de CloudWatch, mètrica `disk_used_percent`) i `PercentIOLimit` d'EFS per damunt del 90 %.
- **Còpies**: el pla de la pràctica 3.4 aplicat per etiqueta.
- **Informe**: elecció de tipus i classes, regió de producció, taula de costos mensual i procediment documentat per a **ampliar** el disc i per a **restaurar** un fitxer de plantilles esborrat.

#### Comprovació

- [ ] Desplegament i destrucció complets amb `tofu apply`/`tofu destroy`.
- [ ] L'alarma de disc salta en omplir el volum (`fallocate -l 9G /datos/logs/relleno`).
- [ ] El procediment de restauració està provat i cronometrat.

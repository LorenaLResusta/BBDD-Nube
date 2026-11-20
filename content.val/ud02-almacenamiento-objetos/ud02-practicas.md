---
title: "UD02 · Pràctiques"
weight: 2
bookToc: true
---

# UD02 · Pràctiques

{{< ra "RA2:a,b,c,d,e,f,g,h" >}}

| Pràctica | Tipus | Nivell | Hores | CA principals |
|---|---|---|--:|---|
| [2.1 Primer bucket amb la CLI](#pràctica-21--primer-bucket-amb-la-cli) | Guiada | ●○○ | 1,5 | RA2: a, b, c |
| [2.2 Bucket xifrat i blindat amb OpenTofu](#pràctica-22--bucket-xifrat-i-blindat-amb-opentofu) | Guiada | ●●○ | 2 | RA2: d, e |
| [2.3 Cartells públics per HTTPS amb CloudFront](#pràctica-23--cartells-públics-per-https-amb-cloudfront) | Guiada | ●●○ | 2 | RA2: e, f |
| [2.4 Cicle de vida, versions i recuperació](#pràctica-24--cicle-de-vida-versions-i-recuperació) | Guiada | ●●○ | 1,5 | RA2: g, h |
| [2.5 Replicació entre regions](#pràctica-25--replicació-entre-regions) | Guiada | ●●○ | 1,5 | RA2: c, h |
| [2.6 Auditoria i alarmes](#pràctica-26--auditoria-i-alarmes) | Repte | ●●● | 1 | RA2: e |
| [2.7 Els buckets de TaquillaAlacant](#pràctica-27--els-buckets-de-taquillaalacant) | Projecte | ●●● | 1,5 | RA2: a – h |
| **Total** | | | **11 h** | |

> [!NOTE]
> En totes les pràctiques, definix en començar estes variables en el terminal (canvia-les per les teues):
> ```bash
> export ALUMNO=lmartinez
> export SUFIJO=$(openssl rand -hex 2)   # p. ex. 7f3a; apunta'l per a reutilitzar-lo
> export AWS_REGION=us-east-1
> ```

---

## Pràctica 2.1 · Primer bucket amb la CLI

{{< practica num="2.1" tipo="Guiada" duracion="1,5 h" nivel="1" ra="RA2: a, b, c" entorno="AWS CLI v2 · CloudShell o local-lab" entrega="no" >}}

#### Objectiu

Crear un bucket, pujar objectes amb metadades, etiquetes i classes diferents, i veure les diferències entre l'API d'alt nivell (`aws s3`) i la de baix nivell (`aws s3api`).

#### Desenvolupament

{{% steps %}}

1. **Prova noms no vàlids** i llig els errors:

    ```bash
    aws s3 mb s3://TA-Prueba             # mayúsculas
    aws s3 mb s3://ta                    # demasiado corto
    aws s3 mb s3://192.168.10.20         # formato IP
    ```

2. **Crea el bucket** en la regió del laboratori i comprova la seua regió i la configuració per defecte:

    ```bash
    export BUCKET=ta-$ALUMNO-pruebas-$SUFIJO
    aws s3api create-bucket --bucket $BUCKET --region us-east-1
    aws s3api get-bucket-location --bucket $BUCKET
    aws s3api get-public-access-block --bucket $BUCKET
    aws s3api get-bucket-ownership-controls --bucket $BUCKET
    aws s3api get-bucket-encryption --bucket $BUCKET
    ```

    > [!NOTE]
    > En qualsevol regió que no siga `us-east-1` cal afegir `--create-bucket-configuration LocationConstraint=<regió>`.

3. **Etiqueta el bucket** per al seguiment de costos:

    ```bash
    aws s3api put-bucket-tagging --bucket $BUCKET \
      --tagging 'TagSet=[{Key=Proyecto,Value=TaquillaAlacant},{Key=Alumno,Value='$ALUMNO'},{Key=Modulo,Value=5162}]'
    ```

4. **Puja objectes** amb tipus MIME, metadades d'usuari, etiquetes i classe:

    ```bash
    echo "<h1>Mascletà</h1>" > cartel.html
    aws s3api put-object --bucket $BUCKET --key carteles/2026/mascleta.html --body cartel.html \
      --content-type "text/html; charset=utf-8" \
      --metadata autor=$ALUMNO,evento=mascleta-2026 \
      --tagging "confidencial=no&ud=02"
    dd if=/dev/urandom of=historico.bin bs=1M count=5 status=none
    aws s3 cp historico.bin s3://$BUCKET/historico/2022/historico.bin --storage-class STANDARD_IA
    ```

5. **Inspecciona** el que has pujat:

    ```bash
    aws s3 ls s3://$BUCKET --recursive --human-readable
    aws s3api head-object --bucket $BUCKET --key carteles/2026/mascleta.html
    aws s3api get-object-tagging --bucket $BUCKET --key carteles/2026/mascleta.html
    aws s3api list-objects-v2 --bucket $BUCKET --query 'Contents[].[Key,StorageClass,Size]' --output table
    ```

6. **Canvia la classe** d'un objecte existent (es fa copiant-lo sobre si mateix):

    ```bash
    aws s3 cp s3://$BUCKET/carteles/2026/mascleta.html s3://$BUCKET/carteles/2026/mascleta.html \
      --storage-class GLACIER_IR --metadata-directive COPY
    ```

7. **Comprova els límits d'etiquetes**: intenta posar 11 etiquetes a un objecte i llig l'error.

{{% /steps %}}

#### Comprovació

- [ ] `head-object` mostra `ContentType`, les teues metadades `x-amz-meta-*` i `ServerSideEncryption: AES256`.
- [ ] `list-objects-v2` mostra tres classes diferents en el bucket.
- [ ] Saps explicar per què les metadades no es canvien sense copiar l'objecte i les etiquetes sí.

#### Neteja

```bash
aws s3 rb s3://$BUCKET --force
```

---

## Pràctica 2.2 · Bucket xifrat i blindat amb OpenTofu

{{< practica num="2.2" tipo="Guiada" duracion="2 h" nivel="2" ra="RA2: d, e" entorno="OpenTofu · AWS KMS · S3" entrega="no" >}}

#### Objectiu

Crear amb **infraestructura com a codi** el bucket privat de les entrades: clau pròpia de KMS amb rotació, SSE-KMS amb Bucket Key, bloqueig d'accés públic, ACL desactivades, versionat i una política que obliga a usar HTTPS.

#### Desenvolupament

{{% steps %}}

1. **Crea la carpeta** `ud02/p2_2/` amb este `main.tf`:

    ```hcl
    terraform {
      required_providers {
        aws    = { source = "hashicorp/aws", version = "~> 6.0" }
        random = { source = "hashicorp/random", version = "~> 3.6" }
      }
    }

    provider "aws" {
      region = "us-east-1"
      default_tags {
        tags = { Proyecto = "TaquillaAlacant", Alumno = var.alumno, Modulo = "5162" }
      }
    }

    variable "alumno" { type = string }

    resource "random_id" "sufijo" { byte_length = 2 }

    # --- Clave propia de KMS ---
    resource "aws_kms_key" "datos" {
      description             = "TaquillaAlacant ${var.alumno}: datos de clientes"
      enable_key_rotation     = true
      deletion_window_in_days = 7
    }

    resource "aws_kms_alias" "datos" {
      name          = "alias/ta-${var.alumno}-datos"
      target_key_id = aws_kms_key.datos.key_id
    }

    # --- Bucket ---
    resource "aws_s3_bucket" "entradas" {
      bucket        = "ta-${var.alumno}-entradas-${random_id.sufijo.hex}"
      force_destroy = true          # SOLO en el laboratorio: permite destruirlo con objetos
    }

    resource "aws_s3_bucket_public_access_block" "entradas" {
      bucket                  = aws_s3_bucket.entradas.id
      block_public_acls       = true
      block_public_policy     = true
      ignore_public_acls      = true
      restrict_public_buckets = true
    }

    resource "aws_s3_bucket_ownership_controls" "entradas" {
      bucket = aws_s3_bucket.entradas.id
      rule { object_ownership = "BucketOwnerEnforced" }
    }

    resource "aws_s3_bucket_versioning" "entradas" {
      bucket = aws_s3_bucket.entradas.id
      versioning_configuration { status = "Enabled" }
    }

    resource "aws_s3_bucket_server_side_encryption_configuration" "entradas" {
      bucket = aws_s3_bucket.entradas.id
      rule {
        apply_server_side_encryption_by_default {
          sse_algorithm     = "aws:kms"
          kms_master_key_id = aws_kms_key.datos.arn
        }
        bucket_key_enabled = true
      }
    }

    data "aws_iam_policy_document" "entradas" {
      statement {
        sid       = "SoloHTTPS"
        effect    = "Deny"
        actions   = ["s3:*"]
        resources = [aws_s3_bucket.entradas.arn, "${aws_s3_bucket.entradas.arn}/*"]
        principals {
          type        = "*"
          identifiers = ["*"]
        }
        condition {
          test     = "Bool"
          variable = "aws:SecureTransport"
          values   = ["false"]
        }
      }
    }

    resource "aws_s3_bucket_policy" "entradas" {
      bucket     = aws_s3_bucket.entradas.id
      policy     = data.aws_iam_policy_document.entradas.json
      depends_on = [aws_s3_bucket_public_access_block.entradas]
    }

    output "bucket" { value = aws_s3_bucket.entradas.id }
    output "kms_key_arn" { value = aws_kms_key.datos.arn }
    ```

2. **Desplega**:

    ```bash
    cd ud02/p2_2
    tofu init
    tofu plan -var alumno=$ALUMNO
    tofu apply -var alumno=$ALUMNO
    export BUCKET=$(tofu output -raw bucket)
    ```

3. **Comprova el xifratge** d'un objecte nou:

    ```bash
    echo "entrada de prueba" > venta-00000001.pdf
    aws s3 cp venta-00000001.pdf s3://$BUCKET/entradas/2026/06/
    aws s3api head-object --bucket $BUCKET --key entradas/2026/06/venta-00000001.pdf \
      --query '[ServerSideEncryption,SSEKMSKeyId,BucketKeyEnabled]'
    ```

    ```text
    [
        "aws:kms",
        "arn:aws:kms:us-east-1:123456789012:key/....",
        true
    ]
    ```

4. **Comprova que HTTP es rebutja** (la CLI usa HTTPS; força HTTP amb el punt d'enllaç):

    ```bash
    aws s3 ls s3://$BUCKET --endpoint-url http://s3.us-east-1.amazonaws.com
    ```

    Ha de fallar amb `AccessDenied`.

5. **Comprova que no es pot fer públic** encara que ho intentes:

    ```bash
    aws s3api put-bucket-acl --bucket $BUCKET --acl public-read
    ```

    Falla perquè les ACL estan desactivades (`BucketOwnerEnforced`).

6. **La clau controla l'accés**: desactiva-la, intenta descarregar l'objecte i torna a activar-la.

    ```bash
    KEY=$(tofu output -raw kms_key_arn)
    aws kms disable-key --key-id $KEY
    aws s3 cp s3://$BUCKET/entradas/2026/06/venta-00000001.pdf /tmp/   # falla: KMS.DisabledException
    aws kms enable-key --key-id $KEY
    aws kms get-key-rotation-status --key-id $KEY
    ```

7. **Revisa en la consola** (S3 → bucket → *Permissions*) el resum d'accés: ha d'indicar *Bucket and objects not public*.

{{% /steps %}}

#### Comprovació

- [ ] L'objecte apareix xifrat amb la **teua** clau i amb Bucket Key.
- [ ] Les peticions HTTP i les ACL públiques fallen.
- [ ] En desactivar la clau no es pot llegir l'objecte, encara que tens permisos sobre S3.

#### Neteja

Si continuaràs amb la 2.4 i la 2.5 pots conservar el bucket. Si no: `tofu destroy -var alumno=$ALUMNO` (la clau queda **pendent d'esborrament** 7 dies).

#### Problemes habituals

| Símptoma | Causa | Solució |
|---|---|---|
| `AccessDenied` en crear la política | La política s'aplica abans que el bloqueig públic | `depends_on` com en l'exemple |
| `AccessDeniedException` en crear la clau | Permisos del laboratori | Comprova que estàs en `us-east-1`; reinicia la sessió |
| La clau no desapareix en destruir | Les claus no s'esborren de seguida | És normal: `PendingDeletion` |

---

## Pràctica 2.3 · Cartells públics per HTTPS amb CloudFront

{{< practica num="2.3" tipo="Guiada" duracion="2 h" nivel="2" ra="RA2: e, f" entorno="OpenTofu · S3 · CloudFront · ACM (opcional)" entrega="no" >}}

#### Objectiu

Publicar els cartells a Internet per **HTTPS** sense que el bucket siga públic, amb una distribució de CloudFront i control d'accés d'origen (OAC). Opcionalment, amb un **domini propi** i certificat.

#### Desenvolupament

{{% steps %}}

1. **Carpeta `ud02/p2_3/`**. Copia la capçalera (`terraform`, `provider`, `variable`, `random_id`) de la pràctica anterior i afig:

    ```hcl
    resource "aws_s3_bucket" "carteles" {
      bucket        = "ta-${var.alumno}-carteles-${random_id.sufijo.hex}"
      force_destroy = true
    }

    resource "aws_s3_bucket_public_access_block" "carteles" {
      bucket                  = aws_s3_bucket.carteles.id
      block_public_acls       = true
      block_public_policy     = true
      ignore_public_acls      = true
      restrict_public_buckets = true
    }

    resource "aws_cloudfront_origin_access_control" "carteles" {
      name                              = "ta-${var.alumno}-carteles-oac"
      origin_access_control_origin_type = "s3"
      signing_behavior                  = "always"
      signing_protocol                  = "sigv4"
    }

    data "aws_cloudfront_cache_policy" "optimizada" {
      name = "Managed-CachingOptimized"
    }

    resource "aws_cloudfront_distribution" "carteles" {
      enabled             = true
      comment             = "Carteles TaquillaAlacant (${var.alumno})"
      default_root_object = "index.html"
      price_class         = "PriceClass_100"     # solo Europa y Norteamérica: más barato

      origin {
        origin_id                = "s3-carteles"
        domain_name              = aws_s3_bucket.carteles.bucket_regional_domain_name
        origin_access_control_id = aws_cloudfront_origin_access_control.carteles.id
      }

      default_cache_behavior {
        target_origin_id       = "s3-carteles"
        viewer_protocol_policy = "redirect-to-https"
        allowed_methods        = ["GET", "HEAD"]
        cached_methods         = ["GET", "HEAD"]
        cache_policy_id        = data.aws_cloudfront_cache_policy.optimizada.id
        compress               = true
      }

      restrictions {
        geo_restriction { restriction_type = "none" }
      }

      viewer_certificate {
        cloudfront_default_certificate = true
      }
    }

    # Solo esta distribución puede leer el bucket
    data "aws_iam_policy_document" "carteles" {
      statement {
        sid       = "SoloCloudFront"
        actions   = ["s3:GetObject"]
        resources = ["${aws_s3_bucket.carteles.arn}/*"]
        principals {
          type        = "Service"
          identifiers = ["cloudfront.amazonaws.com"]
        }
        condition {
          test     = "StringEquals"
          variable = "AWS:SourceArn"
          values   = [aws_cloudfront_distribution.carteles.arn]
        }
      }
    }

    resource "aws_s3_bucket_policy" "carteles" {
      bucket     = aws_s3_bucket.carteles.id
      policy     = data.aws_iam_policy_document.carteles.json
      depends_on = [aws_s3_bucket_public_access_block.carteles]
    }

    output "bucket" { value = aws_s3_bucket.carteles.id }
    output "url" { value = "https://${aws_cloudfront_distribution.carteles.domain_name}" }
    ```

2. **Desplega** (la distribució tarda uns minuts a propagar-se):

    ```bash
    tofu init && tofu apply -var alumno=$ALUMNO
    export BUCKET=$(tofu output -raw bucket) URL=$(tofu output -raw url)
    ```

3. **Puja una pàgina i un cartell** amb el seu tipus MIME i una capçalera de memòria cau:

    ```bash
    cat > index.html <<'HTML'
    <!doctype html><meta charset="utf-8"><title>TaquillaAlacant</title>
    <h1>Próximos eventos</h1><img src="carteles/2026/mascleta.svg" width="300" alt="Mascletà">
    HTML
    cat > mascleta.svg <<'SVG'
    <svg xmlns="http://www.w3.org/2000/svg" width="300" height="200"><rect width="300" height="200" fill="#c2410c"/><text x="20" y="110" font-size="32" fill="#fff">Mascletà 2026</text></svg>
    SVG
    aws s3 cp index.html s3://$BUCKET/ --content-type "text/html; charset=utf-8" --cache-control "max-age=300"
    aws s3 cp mascleta.svg s3://$BUCKET/carteles/2026/ --content-type image/svg+xml --cache-control "max-age=86400"
    ```

4. **Comprova** l'accés per la CDN i el bloqueig de l'accés directe:

    ```bash
    curl -sI $URL/ | head -5                                   # 200 y x-cache
    curl -sI http://${URL#https://}/ | grep -i location        # redirección a HTTPS
    curl -sI https://$BUCKET.s3.amazonaws.com/index.html | head -1   # 403: el bucket no es público
    ```

    Obri `$URL` en el navegador.

5. **Invalida la memòria cau** després de canviar un fitxer:

    ```bash
    DIST=$(aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='Carteles TaquillaAlacant ($ALUMNO)'].Id" --output text)
    aws cloudfront create-invalidation --distribution-id $DIST --paths "/index.html"
    ```

6. **(Opcional) Domini propi.** Si disposes d'un domini o d'un subdomini que et delegue el docent (per exemple `lmartinez.clase.example`):

    - Demana un certificat en **ACM, regió `us-east-1`**, per a `carteles.<el-teu-domini>`, amb validació per **DNS**, i crea el registre CNAME de validació que t'indica.
    - Quan el certificat estiga *Issued*, canvia el bloc `viewer_certificate` i afig l'àlies:

      ```hcl
      aliases = ["carteles.lmartinez.clase.example"]
      viewer_certificate {
        acm_certificate_arn      = var.certificado_arn
        ssl_support_method       = "sni-only"
        minimum_protocol_version = "TLSv1.2_2021"
      }
      ```

    - En el DNS, crea un **CNAME** `carteles` → `dxxxxxxxx.cloudfront.net` i comprova amb `curl -I https://carteles.<el-teu-domini>`.

{{% /steps %}}

#### Comprovació

- [ ] La web es veu per `https://dxxxx.cloudfront.net` i HTTP redirigix a HTTPS.
- [ ] L'accés directe al bucket retorna `403`.
- [ ] El tauler de *Permissions* del bucket continua dient que **no** és públic.
- [ ] (Opcional) El domini propi servix la web amb un certificat vàlid.

#### Neteja

`tofu destroy -var alumno=$ALUMNO`. La distribució tarda uns minuts a desactivar-se abans d'esborrar-se.

#### Problemes habituals

| Símptoma | Causa | Solució |
|---|---|---|
| `403 AccessDenied` des de CloudFront | Falta la política del bucket o el `SourceArn` no coincidix | Revisa la política; espera que acabe el desplegament |
| La imatge es descarrega en compte de veure's | `Content-Type` incorrecte | Puja-la amb `--content-type` |
| Els canvis no es veuen | Memòria cau de CloudFront | Invalida la ruta o usa noms versionats (`cartel.v2.svg`) |
| El certificat no apareix en triar-lo | Es va demanar en una altra regió | Per a CloudFront, **sempre** `us-east-1` |

---

## Pràctica 2.4 · Cicle de vida, versions i recuperació

{{< practica num="2.4" tipo="Guiada" duracion="1,5 h" nivel="2" ra="RA2: g, h" entorno="AWS CLI · S3" entrega="no" >}}

#### Objectiu

Recuperar objectes sobreescrits i esborrats gràcies al versionat, i definir regles de cicle de vida que abaratisquen i netegen el bucket.

#### Desenvolupament

Usa el bucket d'entrades de la pràctica 2.2 (té versionat) o crea'n un de nou i activa el versionat amb `aws s3api put-bucket-versioning --bucket $BUCKET --versioning-configuration Status=Enabled`.

{{% steps %}}

1. **Crea tres versions** d'un objecte:

    ```bash
    for v in 1 2 3; do echo "versión $v" > estado.txt; aws s3 cp estado.txt s3://$BUCKET/pruebas/estado.txt; done
    aws s3api list-object-versions --bucket $BUCKET --prefix pruebas/ \
      --query 'Versions[].[VersionId,IsLatest,LastModified]' --output table
    ```

2. **Recupera la versió 1** descarregant-la pel seu identificador i tornant-la a pujar:

    ```bash
    V1=$(aws s3api list-object-versions --bucket $BUCKET --prefix pruebas/estado.txt \
         --query 'Versions[-1].VersionId' --output text)
    aws s3api get-object --bucket $BUCKET --key pruebas/estado.txt --version-id $V1 recuperado.txt
    cat recuperado.txt
    ```

3. **Esborra** l'objecte i observa el marcador d'esborrament:

    ```bash
    aws s3 rm s3://$BUCKET/pruebas/estado.txt
    aws s3 ls s3://$BUCKET/pruebas/                        # ya no aparece
    aws s3api list-object-versions --bucket $BUCKET --prefix pruebas/ \
      --query 'DeleteMarkers[].[VersionId,IsLatest]' --output table
    ```

4. **Desfés l'esborrament** eliminant el marcador:

    ```bash
    DM=$(aws s3api list-object-versions --bucket $BUCKET --prefix pruebas/estado.txt \
         --query 'DeleteMarkers[0].VersionId' --output text)
    aws s3api delete-object --bucket $BUCKET --key pruebas/estado.txt --version-id $DM
    aws s3 cp s3://$BUCKET/pruebas/estado.txt -          # vuelve a estar: "versión 3"
    ```

5. **Definix el cicle de vida** en `ciclo.json`:

    ```json
    {
      "Rules": [
        {
          "ID": "entradas-a-archivo",
          "Status": "Enabled",
          "Filter": { "Prefix": "entradas/" },
          "Transitions": [
            { "Days": 30,  "StorageClass": "STANDARD_IA" },
            { "Days": 120, "StorageClass": "GLACIER" }
          ],
          "Expiration": { "Days": 1825 },
          "NoncurrentVersionExpiration": { "NoncurrentDays": 30 }
        },
        {
          "ID": "pruebas-1-dia",
          "Status": "Enabled",
          "Filter": { "Prefix": "pruebas/" },
          "Expiration": { "Days": 1 }
        },
        {
          "ID": "limpiar-multiparte",
          "Status": "Enabled",
          "Filter": {},
          "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
        }
      ]
    }
    ```

    ```bash
    aws s3api put-bucket-lifecycle-configuration --bucket $BUCKET --lifecycle-configuration file://ciclo.json
    aws s3api get-bucket-lifecycle-configuration --bucket $BUCKET
    ```

6. **Comprova quina regla afecta cada objecte**: S3 ho indica en la capçalera `Expiration`.

    ```bash
    aws s3api head-object --bucket $BUCKET --key pruebas/estado.txt --query Expiration
    ```

    ```text
    "expiry-date=\"Sun, 22 Nov 2026 00:00:00 GMT\", rule-id=\"pruebas-1-dia\""
    ```

7. **Intenta una transició impossible** (Standard-IA als 10 dies) i llig l'error.

{{% /steps %}}

#### Comprovació

- [ ] Has recuperat una versió anterior i un objecte esborrat.
- [ ] `head-object` mostra la regla de caducitat aplicada.
- [ ] Saps explicar per què sense `NoncurrentVersionExpiration` el bucket creixeria sense fi.

#### Ampliació

Crea un bucket amb **Object Lock** en mode **governança** i 1 dia de retenció, puja un objecte i intenta esborrar la seua versió. Quina capçalera permet saltar-se la governança i quin permís exigix?

---

## Pràctica 2.5 · Replicació entre regions

{{< practica num="2.5" tipo="Guiada" duracion="1,5 h" nivel="2" ra="RA2: c, h" entorno="AWS CLI · S3 · us-east-1 → us-west-2" entrega="no" >}}

#### Objectiu

Configurar la replicació d'un bucket d'`us-east-1` a un altre d'`us-west-2`, comprovar-ne l'estat i veure què es replica i què no.

#### Desenvolupament

{{% steps %}}

1. **Crea els dos buckets** amb versionat:

    ```bash
    export ORIGEN=ta-$ALUMNO-rep-origen-$SUFIJO DESTINO=ta-$ALUMNO-rep-destino-$SUFIJO
    aws s3api create-bucket --bucket $ORIGEN --region us-east-1
    aws s3api create-bucket --bucket $DESTINO --region us-west-2 \
      --create-bucket-configuration LocationConstraint=us-west-2
    for b in $ORIGEN $DESTINO; do
      aws s3api put-bucket-versioning --bucket $b --versioning-configuration Status=Enabled
    done
    ```

2. **Puja un objecte abans** de configurar la replicació (després veuràs que no es copia):

    ```bash
    echo "anterior" > antes.txt && aws s3 cp antes.txt s3://$ORIGEN/
    ```

3. **Configura la regla** amb el rol del laboratori:

    ```bash
    CUENTA=$(aws sts get-caller-identity --query Account --output text)
    cat > replicacion.json <<EOF
    {
      "Role": "arn:aws:iam::$CUENTA:role/LabRole",
      "Rules": [{
        "ID": "todo-a-oregon",
        "Status": "Enabled",
        "Priority": 1,
        "Filter": {},
        "DeleteMarkerReplication": { "Status": "Disabled" },
        "Destination": { "Bucket": "arn:aws:s3:::$DESTINO", "StorageClass": "STANDARD_IA" }
      }]
    }
    EOF
    aws s3api put-bucket-replication --bucket $ORIGEN --replication-configuration file://replicacion.json
    ```

4. **Puja objectes nous** i seguix el seu estat de replicació:

    ```bash
    for i in 1 2 3; do echo "cartel $i" > c$i.txt; aws s3 cp c$i.txt s3://$ORIGEN/carteles/; done
    aws s3api head-object --bucket $ORIGEN --key carteles/c1.txt --query ReplicationStatus   # PENDING → COMPLETED
    sleep 60
    aws s3api head-object --bucket $DESTINO --key carteles/c1.txt --region us-west-2 \
      --query '[ReplicationStatus,StorageClass]'                                            # REPLICA, STANDARD_IA
    aws s3 ls s3://$DESTINO --recursive --region us-west-2
    ```

5. **Analitza què no es replica**:
    - `antes.txt` (anterior a la regla).
    - Un esborrament en l'origen (`aws s3 rm s3://$ORIGEN/carteles/c1.txt`): amb `DeleteMarkerReplication` desactivat, la destinació el conserva.

{{% /steps %}}

#### Comprovació

- [ ] Els objectes nous apareixen a Oregon amb estat `REPLICA` i classe Standard-IA.
- [ ] Saps per què `antes.txt` no hi és i com es copiaria (S3 Batch Replication).
- [ ] Saps explicar quan convé **no** replicar els marcadors d'esborrament.

#### Neteja

```bash
aws s3 rb s3://$ORIGEN --force
aws s3api list-object-versions --bucket $DESTINO --region us-west-2 --output json \
  --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' > borrar.json
aws s3api delete-objects --bucket $DESTINO --region us-west-2 --delete file://borrar.json
aws s3 rb s3://$DESTINO --region us-west-2
```

> [!NOTE]
> `aws s3 rb --force` no esborra les versions antigues d'un bucket versionat; per això la destinació es buida amb `delete-objects`. Si queden marcadors d'esborrament, repetix amb `DeleteMarkers[]` en lloc de `Versions[]`.

---

## Pràctica 2.6 · Auditoria i alarmes

{{< practica num="2.6" tipo="Reto" duracion="1 h" nivel="3" ra="RA2: e" entorno="CloudTrail · CloudWatch · S3 · IAM Access Analyzer" entrega="ud02/p2_6.md" >}}

#### Objectiu

Saber **qui** accedix als PDF d'entrades i **assabentar-te** quan alguna cosa va malament.

#### Enunciat

Sobre el bucket d'entrades de la pràctica 2.2:

1. Activa els **registres d'accés al servidor** cap a un bucket `ta-$ALUMNO-logs-$SUFIJO` (amb prefix `s3-entradas/`).
2. Crea un **registre de seguiment de CloudTrail** que capture **esdeveniments de dades** de lectura i escriptura només d'eixe bucket, i localitza-hi el teu propi `GetObject`.
3. Activa les **mètriques de peticions** de S3 per al prefix `entradas/` i crea una **alarma de CloudWatch** quan `4xxErrors` supere 10 en 5 minuts. Provoca-la amb descàrregues de claus inexistents.
4. Crea un **analitzador d'IAM Access Analyzer** del compte i comprova quins buckets apareixen com a compartits. Explica per què el de cartells (si el conserves) no apareix com a públic.
5. Calcula el cost mensual d'esta auditoria si hi haguera 3 milions de descàrregues al mes.

#### Comprovació

- [ ] Mostres una línia del registre d'accés i un esdeveniment de CloudTrail amb el teu `GetObject`.
- [ ] L'alarma passa a `ALARM` i torna a `OK`.
- [ ] L'informe inclou el cost estimat i una recomanació raonada (tot amb esdeveniments de dades o només registres d'accés?).

---

## Pràctica 2.7 · Els buckets de TaquillaAlacant

{{< practica num="2.7" tipo="Proyecto" duracion="1,5 h" nivel="3" ra="RA2: a, b, c, d, e, f, g, h" entorno="OpenTofu · S3 · KMS · CloudFront" entrega="ud02/ (codi *.tf + README.md + captures)" >}}

#### Objectiu

Unir les pràctiques anteriors en **un únic projecte d'OpenTofu** amb els dos buckets del projecte.

#### Requisits

| Bucket | Requisits |
|---|---|
| `ta-<alumne>-carteles-<sufix>` | Privat, servit només per CloudFront amb HTTPS; memòria cau d'1 dia per a `carteles/`; versionat amb caducitat de versions antigues als 7 dies; etiqueta `Datos=publicos` |
| `ta-<alumne>-entradas-<sufix>` | SSE-KMS amb clau pròpia i rotació; només HTTPS; versionat; cicle de vida 30 dies → Standard-IA, 120 → Glacier Flexible Retrieval, caducitat als 5 anys; neteja de multipart; registres d'accés a un bucket de logs amb caducitat als 90 dies; etiqueta `Datos=personales` |

A més:

- **Replicació** del bucket d'entrades a `us-west-2` (la clau KMS de destinació pot ser una altra; investiga `SourceSelectionCriteria` i `ReplicaKmsKeyID`), **o** bé un pla d'**AWS Backup** amb còpies contínues, justificant quin tries.
- Un script `subir_entrada.sh <id_venta>` que pugue un PDF de prova amb la clau `entradas/AAAA/MM/venta-<id>.pdf` i retorne una **URL presignada** de 15 minuts.
- En el `README.md`: regió que usaries en producció i per què, cost mensual estimat amb els volums del projecte i una taula que relacione cada recurs amb el criteri d'avaluació que compleix.

#### Comprovació

- [ ] `tofu apply` des de zero ho crea tot sense errors i `tofu destroy` ho elimina.
- [ ] La web de cartells funciona per HTTPS i el bucket no és públic.
- [ ] Un PDF pujat amb l'script es descarrega amb la URL presignada i deixa de funcionar als 15 minuts.
- [ ] Cada criteri RA2.a – RA2.h està justificat en l'informe.

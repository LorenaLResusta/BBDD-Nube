---
title: "UD02 · Prácticas"
weight: 2
bookToc: true
---

# UD02 · Prácticas

{{< ra "RA2:a,b,c,d,e,f,g,h" >}}

| Práctica | Tipo | Nivel | Horas | CE principales |
|---|---|---|--:|---|
| [2.1 Primer bucket con la CLI](#práctica-21--primer-bucket-con-la-cli) | Guiada | ●○○ | 1,5 | RA2: a, b, c |
| [2.2 Bucket cifrado y blindado con OpenTofu](#práctica-22--bucket-cifrado-y-blindado-con-opentofu) | Guiada | ●●○ | 2 | RA2: d, e |
| [2.3 Carteles públicos por HTTPS con CloudFront](#práctica-23--carteles-públicos-por-https-con-cloudfront) | Guiada | ●●○ | 2 | RA2: e, f |
| [2.4 Ciclo de vida, versiones y recuperación](#práctica-24--ciclo-de-vida-versiones-y-recuperación) | Guiada | ●●○ | 1,5 | RA2: g, h |
| [2.5 Replicación entre regiones](#práctica-25--replicación-entre-regiones) | Guiada | ●●○ | 1,5 | RA2: c, h |
| [2.6 Auditoría y alarmas](#práctica-26--auditoría-y-alarmas) | Reto | ●●● | 1 | RA2: e |
| [2.7 Los buckets de TaquillaAlacant](#práctica-27--los-buckets-de-taquillaalacant) | Proyecto | ●●● | 1,5 | RA2: a – h |
| **Total** | | | **11 h** | |

> [!NOTE]
> En todas las prácticas, define al empezar estas variables en la terminal (cámbialas por las tuyas):
> ```bash
> export ALUMNO=lmartinez
> export SUFIJO=$(openssl rand -hex 2)   # p. ej. 7f3a; apúntalo para reutilizarlo
> export AWS_REGION=us-east-1
> ```

---

## Práctica 2.1 · Primer bucket con la CLI

{{< practica num="2.1" tipo="Guiada" duracion="1,5 h" nivel="1" ra="RA2: a, b, c" entorno="AWS CLI v2 · CloudShell o local-lab" entrega="no" >}}

#### Objetivo

Crear un bucket, subir objetos con metadatos, etiquetas y clases distintas, y ver las diferencias entre la API de alto nivel (`aws s3`) y la de bajo nivel (`aws s3api`).

#### Desarrollo

{{% steps %}}

1. **Prueba nombres inválidos** y lee los errores:

    ```bash
    aws s3 mb s3://TA-Prueba             # mayúsculas
    aws s3 mb s3://ta                    # demasiado corto
    aws s3 mb s3://192.168.10.20         # formato IP
    ```

2. **Crea el bucket** en la región del laboratorio y comprueba su región y su configuración por defecto:

    ```bash
    export BUCKET=ta-$ALUMNO-pruebas-$SUFIJO
    aws s3api create-bucket --bucket $BUCKET --region us-east-1
    aws s3api get-bucket-location --bucket $BUCKET
    aws s3api get-public-access-block --bucket $BUCKET
    aws s3api get-bucket-ownership-controls --bucket $BUCKET
    aws s3api get-bucket-encryption --bucket $BUCKET
    ```

    > [!NOTE]
    > En cualquier región que no sea `us-east-1` hay que añadir `--create-bucket-configuration LocationConstraint=<región>`.

3. **Etiqueta el bucket** para el seguimiento de costes:

    ```bash
    aws s3api put-bucket-tagging --bucket $BUCKET \
      --tagging 'TagSet=[{Key=Proyecto,Value=TaquillaAlacant},{Key=Alumno,Value='$ALUMNO'},{Key=Modulo,Value=5162}]'
    ```

4. **Sube objetos** con tipo MIME, metadatos de usuario, etiquetas y clase:

    ```bash
    echo "<h1>Mascletà</h1>" > cartel.html
    aws s3api put-object --bucket $BUCKET --key carteles/2026/mascleta.html --body cartel.html \
      --content-type "text/html; charset=utf-8" \
      --metadata autor=$ALUMNO,evento=mascleta-2026 \
      --tagging "confidencial=no&ud=02"
    dd if=/dev/urandom of=historico.bin bs=1M count=5 status=none
    aws s3 cp historico.bin s3://$BUCKET/historico/2022/historico.bin --storage-class STANDARD_IA
    ```

5. **Inspecciona** lo que has subido:

    ```bash
    aws s3 ls s3://$BUCKET --recursive --human-readable
    aws s3api head-object --bucket $BUCKET --key carteles/2026/mascleta.html
    aws s3api get-object-tagging --bucket $BUCKET --key carteles/2026/mascleta.html
    aws s3api list-objects-v2 --bucket $BUCKET --query 'Contents[].[Key,StorageClass,Size]' --output table
    ```

6. **Cambia la clase** de un objeto existente (se hace copiándolo sobre sí mismo):

    ```bash
    aws s3 cp s3://$BUCKET/carteles/2026/mascleta.html s3://$BUCKET/carteles/2026/mascleta.html \
      --storage-class GLACIER_IR --metadata-directive COPY
    ```

7. **Comprueba los límites de etiquetas**: intenta poner 11 etiquetas a un objeto y lee el error.

{{% /steps %}}

#### Comprobación

- [ ] `head-object` muestra `ContentType`, tus metadatos `x-amz-meta-*` y `ServerSideEncryption: AES256`.
- [ ] `list-objects-v2` muestra tres clases distintas en el bucket.
- [ ] Sabes explicar por qué los metadatos no se cambian sin copiar el objeto y las etiquetas sí.

#### Limpieza

```bash
aws s3 rb s3://$BUCKET --force
```

---

## Práctica 2.2 · Bucket cifrado y blindado con OpenTofu

{{< practica num="2.2" tipo="Guiada" duracion="2 h" nivel="2" ra="RA2: d, e" entorno="OpenTofu · AWS KMS · S3" entrega="no" >}}

#### Objetivo

Crear con **infraestructura como código** el bucket privado de las entradas: clave propia de KMS con rotación, SSE-KMS con Bucket Key, bloqueo de acceso público, ACL desactivadas, versionado y una política que obliga a usar HTTPS.

#### Desarrollo

{{% steps %}}

1. **Crea la carpeta** `ud02/p2_2/` con este `main.tf`:

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

2. **Despliega**:

    ```bash
    cd ud02/p2_2
    tofu init
    tofu plan -var alumno=$ALUMNO
    tofu apply -var alumno=$ALUMNO
    export BUCKET=$(tofu output -raw bucket)
    ```

3. **Comprueba el cifrado** de un objeto nuevo:

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

4. **Comprueba que HTTP se rechaza** (la CLI usa HTTPS; fuerza HTTP con el punto de enlace):

    ```bash
    aws s3 ls s3://$BUCKET --endpoint-url http://s3.us-east-1.amazonaws.com
    ```

    Debe fallar con `AccessDenied`.

5. **Comprueba que no se puede hacer público** aunque lo intentes:

    ```bash
    aws s3api put-bucket-acl --bucket $BUCKET --acl public-read
    ```

    Falla porque las ACL están desactivadas (`BucketOwnerEnforced`).

6. **La clave controla el acceso**: desactívala, intenta descargar el objeto y vuelve a activarla.

    ```bash
    KEY=$(tofu output -raw kms_key_arn)
    aws kms disable-key --key-id $KEY
    aws s3 cp s3://$BUCKET/entradas/2026/06/venta-00000001.pdf /tmp/   # falla: KMS.DisabledException
    aws kms enable-key --key-id $KEY
    aws kms get-key-rotation-status --key-id $KEY
    ```

7. **Revisa en la consola** (S3 → bucket → *Permissions*) el resumen de acceso: debe indicar *Bucket and objects not public*.

{{% /steps %}}

#### Comprobación

- [ ] El objeto aparece cifrado con **tu** clave y con Bucket Key.
- [ ] Las peticiones HTTP y las ACL públicas fallan.
- [ ] Al desactivar la clave no se puede leer el objeto, aunque tienes permisos sobre S3.

#### Limpieza

Si vas a seguir con la 2.4 y la 2.5 puedes conservar el bucket. Si no: `tofu destroy -var alumno=$ALUMNO` (la clave queda **pendiente de borrado** 7 días).

#### Problemas habituales

| Síntoma | Causa | Solución |
|---|---|---|
| `AccessDenied` al crear la política | La política se aplica antes que el bloqueo público | `depends_on` como en el ejemplo |
| `AccessDeniedException` al crear la clave | Permisos del laboratorio | Comprueba que estás en `us-east-1`; reinicia la sesión |
| La clave no aparece al destruir | Las claves no se borran al momento | Es normal: `PendingDeletion` |

---

## Práctica 2.3 · Carteles públicos por HTTPS con CloudFront

{{< practica num="2.3" tipo="Guiada" duracion="2 h" nivel="2" ra="RA2: e, f" entorno="OpenTofu · S3 · CloudFront · ACM (opcional)" entrega="no" >}}

#### Objetivo

Publicar los carteles en Internet por **HTTPS** sin que el bucket sea público, con una distribución de CloudFront y control de acceso de origen (OAC). Opcionalmente, con un **dominio propio** y certificado.

#### Desarrollo

{{% steps %}}

1. **Carpeta `ud02/p2_3/`**. Copia la cabecera (`terraform`, `provider`, `variable`, `random_id`) de la práctica anterior y añade:

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

2. **Despliega** (la distribución tarda unos minutos en propagarse):

    ```bash
    tofu init && tofu apply -var alumno=$ALUMNO
    export BUCKET=$(tofu output -raw bucket) URL=$(tofu output -raw url)
    ```

3. **Sube una página y un cartel** con su tipo MIME y una cabecera de caché:

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

4. **Comprueba** el acceso por la CDN y el bloqueo del acceso directo:

    ```bash
    curl -sI $URL/ | head -5                                   # 200 y x-cache
    curl -sI http://${URL#https://}/ | grep -i location        # redirección a HTTPS
    curl -sI https://$BUCKET.s3.amazonaws.com/index.html | head -1   # 403: el bucket no es público
    ```

    Abre `$URL` en el navegador.

5. **Invalida la caché** tras cambiar un fichero:

    ```bash
    DIST=$(aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='Carteles TaquillaAlacant ($ALUMNO)'].Id" --output text)
    aws cloudfront create-invalidation --distribution-id $DIST --paths "/index.html"
    ```

6. **(Opcional) Dominio propio.** Si dispones de un dominio o de un subdominio que te delegue el docente (por ejemplo `lmartinez.clase.example`):

    - Pide un certificado en **ACM, región `us-east-1`**, para `carteles.<tu-dominio>`, con validación por **DNS**, y crea el registro CNAME de validación que te indica.
    - Cuando el certificado esté *Issued*, cambia el bloque `viewer_certificate` y añade el alias:

      ```hcl
      aliases = ["carteles.lmartinez.clase.example"]
      viewer_certificate {
        acm_certificate_arn      = var.certificado_arn
        ssl_support_method       = "sni-only"
        minimum_protocol_version = "TLSv1.2_2021"
      }
      ```

    - En el DNS, crea un **CNAME** `carteles` → `dxxxxxxxx.cloudfront.net` y comprueba con `curl -I https://carteles.<tu-dominio>`.

{{% /steps %}}

#### Comprobación

- [ ] La web se ve por `https://dxxxx.cloudfront.net` y HTTP redirige a HTTPS.
- [ ] El acceso directo al bucket devuelve `403`.
- [ ] El panel de *Permissions* del bucket sigue diciendo que **no** es público.
- [ ] (Opcional) El dominio propio sirve la web con un certificado válido.

#### Limpieza

`tofu destroy -var alumno=$ALUMNO`. La distribución tarda unos minutos en desactivarse antes de borrarse.

#### Problemas habituales

| Síntoma | Causa | Solución |
|---|---|---|
| `403 AccessDenied` desde CloudFront | Falta la política del bucket o el `SourceArn` no coincide | Revisa la política; espera a que termine el despliegue |
| La imagen se descarga en vez de verse | `Content-Type` incorrecto | Súbela con `--content-type` |
| Los cambios no se ven | Caché de CloudFront | Invalida la ruta o usa nombres versionados (`cartel.v2.svg`) |
| El certificado no aparece al elegirlo | Se pidió en otra región | Para CloudFront, **siempre** `us-east-1` |

---

## Práctica 2.4 · Ciclo de vida, versiones y recuperación

{{< practica num="2.4" tipo="Guiada" duracion="1,5 h" nivel="2" ra="RA2: g, h" entorno="AWS CLI · S3" entrega="no" >}}

#### Objetivo

Recuperar objetos sobrescritos y borrados gracias al versionado, y definir reglas de ciclo de vida que abaraten y limpien el bucket.

#### Desarrollo

Usa el bucket de entradas de la práctica 2.2 (tiene versionado) o crea uno nuevo y activa el versionado con `aws s3api put-bucket-versioning --bucket $BUCKET --versioning-configuration Status=Enabled`.

{{% steps %}}

1. **Crea tres versiones** de un objeto:

    ```bash
    for v in 1 2 3; do echo "versión $v" > estado.txt; aws s3 cp estado.txt s3://$BUCKET/pruebas/estado.txt; done
    aws s3api list-object-versions --bucket $BUCKET --prefix pruebas/ \
      --query 'Versions[].[VersionId,IsLatest,LastModified]' --output table
    ```

2. **Recupera la versión 1** descargándola por su identificador y volviéndola a subir:

    ```bash
    V1=$(aws s3api list-object-versions --bucket $BUCKET --prefix pruebas/estado.txt \
         --query 'Versions[-1].VersionId' --output text)
    aws s3api get-object --bucket $BUCKET --key pruebas/estado.txt --version-id $V1 recuperado.txt
    cat recuperado.txt
    ```

3. **Borra** el objeto y observa el marcador de borrado:

    ```bash
    aws s3 rm s3://$BUCKET/pruebas/estado.txt
    aws s3 ls s3://$BUCKET/pruebas/                        # ya no aparece
    aws s3api list-object-versions --bucket $BUCKET --prefix pruebas/ \
      --query 'DeleteMarkers[].[VersionId,IsLatest]' --output table
    ```

4. **Deshaz el borrado** eliminando el marcador:

    ```bash
    DM=$(aws s3api list-object-versions --bucket $BUCKET --prefix pruebas/estado.txt \
         --query 'DeleteMarkers[0].VersionId' --output text)
    aws s3api delete-object --bucket $BUCKET --key pruebas/estado.txt --version-id $DM
    aws s3 cp s3://$BUCKET/pruebas/estado.txt -          # vuelve a estar: "versión 3"
    ```

5. **Define el ciclo de vida** en `ciclo.json`:

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

6. **Comprueba qué regla afecta a cada objeto**: S3 lo indica en la cabecera `Expiration`.

    ```bash
    aws s3api head-object --bucket $BUCKET --key pruebas/estado.txt --query Expiration
    ```

    ```text
    "expiry-date=\"Sun, 22 Nov 2026 00:00:00 GMT\", rule-id=\"pruebas-1-dia\""
    ```

7. **Intenta una transición imposible** (Standard-IA a los 10 días) y lee el error.

{{% /steps %}}

#### Comprobación

- [ ] Has recuperado una versión anterior y un objeto borrado.
- [ ] `head-object` muestra la regla de expiración aplicada.
- [ ] Sabes explicar por qué sin `NoncurrentVersionExpiration` el bucket crecería sin fin.

#### Ampliación

Crea un bucket con **Object Lock** en modo **gobernanza** y 1 día de retención, sube un objeto e intenta borrar su versión. ¿Qué cabecera permite saltarse la gobernanza y qué permiso exige?

---

## Práctica 2.5 · Replicación entre regiones

{{< practica num="2.5" tipo="Guiada" duracion="1,5 h" nivel="2" ra="RA2: c, h" entorno="AWS CLI · S3 · us-east-1 → us-west-2" entrega="no" >}}

#### Objetivo

Configurar la replicación de un bucket de `us-east-1` a otro de `us-west-2`, comprobar su estado y ver qué se replica y qué no.

#### Desarrollo

{{% steps %}}

1. **Crea los dos buckets** con versionado:

    ```bash
    export ORIGEN=ta-$ALUMNO-rep-origen-$SUFIJO DESTINO=ta-$ALUMNO-rep-destino-$SUFIJO
    aws s3api create-bucket --bucket $ORIGEN --region us-east-1
    aws s3api create-bucket --bucket $DESTINO --region us-west-2 \
      --create-bucket-configuration LocationConstraint=us-west-2
    for b in $ORIGEN $DESTINO; do
      aws s3api put-bucket-versioning --bucket $b --versioning-configuration Status=Enabled
    done
    ```

2. **Sube un objeto antes** de configurar la replicación (luego verás que no se copia):

    ```bash
    echo "anterior" > antes.txt && aws s3 cp antes.txt s3://$ORIGEN/
    ```

3. **Configura la regla** con el rol del laboratorio:

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

4. **Sube objetos nuevos** y sigue su estado de replicación:

    ```bash
    for i in 1 2 3; do echo "cartel $i" > c$i.txt; aws s3 cp c$i.txt s3://$ORIGEN/carteles/; done
    aws s3api head-object --bucket $ORIGEN --key carteles/c1.txt --query ReplicationStatus   # PENDING → COMPLETED
    sleep 60
    aws s3api head-object --bucket $DESTINO --key carteles/c1.txt --region us-west-2 \
      --query '[ReplicationStatus,StorageClass]'                                            # REPLICA, STANDARD_IA
    aws s3 ls s3://$DESTINO --recursive --region us-west-2
    ```

5. **Analiza qué no se replica**:
    - `antes.txt` (anterior a la regla).
    - Un borrado en el origen (`aws s3 rm s3://$ORIGEN/carteles/c1.txt`): con `DeleteMarkerReplication` desactivado, el destino lo conserva.

{{% /steps %}}

#### Comprobación

- [ ] Los objetos nuevos aparecen en Oregón con estado `REPLICA` y clase Standard-IA.
- [ ] Sabes por qué `antes.txt` no está y cómo se copiaría (S3 Batch Replication).
- [ ] Sabes explicar cuándo conviene **no** replicar los marcadores de borrado.

#### Limpieza

```bash
aws s3 rb s3://$ORIGEN --force
aws s3api list-object-versions --bucket $DESTINO --region us-west-2 --output json \
  --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' > borrar.json
aws s3api delete-objects --bucket $DESTINO --region us-west-2 --delete file://borrar.json
aws s3 rb s3://$DESTINO --region us-west-2
```

> [!NOTE]
> `aws s3 rb --force` no borra las versiones antiguas de un bucket versionado; por eso el destino se vacía con `delete-objects`. Si quedan marcadores de borrado, repite con `DeleteMarkers[]` en lugar de `Versions[]`.

---

## Práctica 2.6 · Auditoría y alarmas

{{< practica num="2.6" tipo="Reto" duracion="1 h" nivel="3" ra="RA2: e" entorno="CloudTrail · CloudWatch · S3 · IAM Access Analyzer" entrega="ud02/p2_6.md" >}}

#### Objetivo

Saber **quién** accede a los PDF de entradas y **enterarte** cuando algo va mal.

#### Enunciado

Sobre el bucket de entradas de la práctica 2.2:

1. Activa los **registros de acceso al servidor** hacia un bucket `ta-$ALUMNO-logs-$SUFIJO` (con prefijo `s3-entradas/`).
2. Crea un **registro de seguimiento de CloudTrail** que capture **eventos de datos** de lectura y escritura solo de ese bucket, y localiza en él tu propio `GetObject`.
3. Activa las **métricas de peticiones** de S3 para el prefijo `entradas/` y crea una **alarma de CloudWatch** cuando `4xxErrors` supere 10 en 5 minutos. Provócala con descargas de claves inexistentes.
4. Crea un **analizador de IAM Access Analyzer** de la cuenta y comprueba qué buckets aparecen como compartidos. Explica por qué el de carteles (si lo conservas) no aparece como público.
5. Calcula el coste mensual de esta auditoría si hubiera 3 millones de descargas al mes.

#### Comprobación

- [ ] Muestras una línea del registro de acceso y un evento de CloudTrail con tu `GetObject`.
- [ ] La alarma pasa a `ALARM` y vuelve a `OK`.
- [ ] El informe incluye el coste estimado y una recomendación razonada (¿todo con eventos de datos o solo registros de acceso?).

---

## Práctica 2.7 · Los buckets de TaquillaAlacant

{{< practica num="2.7" tipo="Proyecto" duracion="1,5 h" nivel="3" ra="RA2: a, b, c, d, e, f, g, h" entorno="OpenTofu · S3 · KMS · CloudFront" entrega="ud02/ (código *.tf + README.md + capturas)" >}}

#### Objetivo

Unir las prácticas anteriores en **un único proyecto de OpenTofu** con los dos buckets del proyecto.

#### Requisitos

| Bucket | Requisitos |
|---|---|
| `ta-<alumno>-carteles-<sufijo>` | Privado, servido solo por CloudFront con HTTPS; caché de 1 día para `carteles/`; versionado con expiración de versiones antiguas a los 7 días; etiqueta `Datos=publicos` |
| `ta-<alumno>-entradas-<sufijo>` | SSE-KMS con clave propia y rotación; solo HTTPS; versionado; ciclo de vida 30 días → Standard-IA, 120 → Glacier Flexible Retrieval, expiración a los 5 años; limpieza de multiparte; registros de acceso a un bucket de logs con expiración a los 90 días; etiqueta `Datos=personales` |

Además:

- **Replicación** del bucket de entradas a `us-west-2` (la clave KMS de destino puede ser otra; investiga `SourceSelectionCriteria` y `ReplicaKmsKeyID`), **o** bien un plan de **AWS Backup** con copias continuas, justificando cuál eliges.
- Un script `subir_entrada.sh <id_venta>` que suba un PDF de prueba con la clave `entradas/AAAA/MM/venta-<id>.pdf` y devuelva una **URL prefirmada** de 15 minutos.
- En el `README.md`: región que usarías en producción y por qué, coste mensual estimado con los volúmenes del proyecto y una tabla que relacione cada recurso con el criterio de evaluación que cumple.

#### Comprobación

- [ ] `tofu apply` desde cero crea todo sin errores y `tofu destroy` lo elimina.
- [ ] La web de carteles funciona por HTTPS y el bucket no es público.
- [ ] Un PDF subido con el script se descarga con la URL prefirmada y deja de funcionar a los 15 minutos.
- [ ] Cada criterio RA2.a – RA2.h está justificado en el informe.

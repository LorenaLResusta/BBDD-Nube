---
title: "UD01 · Prácticas"
weight: 2
bookToc: true
---

# UD01 · Prácticas

{{< ra "RA1:a,b,c,d,e" >}}

| Práctica | Tipo | Nivel | Horas | CE principales |
|---|---|---|--:|---|
| [1.1 Entorno de trabajo y regiones](#práctica-11--entorno-de-trabajo-y-regiones) | Guiada | ●○○ | 1,5 | RA1: b, c |
| [1.2 Estimar costes con la calculadora](#práctica-12--estimar-costes-con-la-calculadora) | Guiada | ●○○ | 1,5 | RA1: d, e |
| [1.3 Matriz de selección](#práctica-13--matriz-de-selección) | Autónoma | ●●○ | 1,5 | RA1: a, b, c, d |
| [1.4 Informe de selección de TaquillaAlacant](#práctica-14--informe-de-selección-de-taquillaalacant) | Proyecto | ●●○ | 1,5 | RA1: a, b, c, d, e |
| **Total** | | | **6 h** | |

---

## Práctica 1.1 · Entorno de trabajo y regiones

{{< practica num="1.1" tipo="Guiada" duracion="1,5 h" nivel="1" ra="RA1: b, c" entorno="AWS Learner Lab · AWS CLI · CloudShell" entrega="no" >}}

#### Objetivo

Dejar listo el acceso al laboratorio desde la consola, CloudShell y tu máquina, y aprender a consultar **qué servicios hay en cada región** sin salir de la terminal.

#### Desarrollo

{{% steps %}}

1. **Arranca el laboratorio** (*Start Lab*) y abre la consola. Comprueba arriba a la derecha que estás en **N. Virginia (`us-east-1`)**.

2. **Abre CloudShell** y comprueba tu identidad:

    ```bash
    aws sts get-caller-identity
    aws configure list
    ```

3. **Configura la CLI en `local-lab`** copiando el bloque de *AWS Details → AWS CLI* en `~/.aws/credentials`, como se explica en el [entorno](/guia/entorno/). Repite `aws sts get-caller-identity`.

4. **Lista las regiones** que conoce la cuenta y sus zonas de disponibilidad:

    ```bash
    aws ec2 describe-regions --all-regions --query 'Regions[].[RegionName,OptInStatus]' --output table
    aws ec2 describe-availability-zones --region us-east-1 --query 'AvailabilityZones[].[ZoneName,ZoneId,State]' --output table
    ```

    > [!NOTE]
    > Verás regiones que no puedes usar: la cuenta las conoce, pero las políticas del laboratorio te impiden crear recursos en ellas.

5. **Consulta qué servicios hay en una región.** AWS publica la infraestructura global como parámetros públicos de Systems Manager:

    ```bash
    for r in us-east-1 eu-south-2 eu-west-1; do
      echo "== $r: $(aws ssm get-parameters-by-path \
          --path /aws/service/global-infrastructure/regions/$r/services \
          --query 'length(Parameters)' --output text) servicios"
    done
    ```

    Y qué servicios hay en `us-east-1` que **no** están en `eu-south-2` (España):

    ```bash
    servicios() {
      aws ssm get-parameters-by-path --region us-east-1 \
        --path /aws/service/global-infrastructure/regions/$1/services \
        --query 'Parameters[].Value' --output text | tr '\t' '\n' | sort
    }
    comm -23 <(servicios us-east-1) <(servicios eu-south-2) | head -40
    ```

6. **Compara con la documentación**: abre *AWS Services by Region* y busca los mismos servicios. Anota cualquier diferencia.

7. **Disponibilidad de versiones de motor** (lo necesitarás en la UD04):

    ```bash
    aws rds describe-db-engine-versions --engine postgres \
      --query 'DBEngineVersions[].EngineVersion' --output text | tr '\t' '\n' | tail -5
    ```

{{% /steps %}}

#### Comprobación

- [ ] `aws sts get-caller-identity` funciona en CloudShell y en `local-lab`.
- [ ] Sabes cuántas AZ tiene `us-east-1` y cuál es la diferencia entre `ZoneName` y `ZoneId`.
- [ ] Has encontrado al menos un servicio o clase de almacenamiento que **no** está en `eu-south-2` y sí en `us-east-1`.

#### Problemas habituales

| Síntoma | Causa | Solución |
|---|---|---|
| `ExpiredToken` | Has reiniciado la sesión del laboratorio | Copia de nuevo las credenciales |
| `AccessDenied` en otra región | Restricción del Learner Lab | Trabaja en `us-east-1` o `us-west-2` |
| `Could not connect to the endpoint URL` | Región mal escrita | Revisa `~/.aws/config` |

---

## Práctica 1.2 · Estimar costes con la calculadora

{{< practica num="1.2" tipo="Guiada" duracion="1,5 h" nivel="1" ra="RA1: d, e" entorno="AWS Pricing Calculator" entrega="no" >}}

#### Objetivo

Construir una estimación completa del almacenamiento de objetos y comprobar **qué parámetros mueven el coste**.

#### Desarrollo

{{% steps %}}

1. Abre <https://calculator.aws/> → **Create estimate** → busca **Amazon S3**. Región: **Europe (Spain)**.

2. **Escenario A · Carteles:** S3 Standard, 20 GB, 1000 `PUT` y 3 000 000 de `GET` al mes. En **Data Transfer** añade 150 GB/mes de salida a Internet. Anota el total.

3. **Cambia la región** a US East (N. Virginia) sin tocar nada más. ¿Cuánto varía?

4. **Escenario B · Entradas en PDF:** 2 000 000 de objetos de 80 KB (≈ 160 GB). Calcula tres variantes:
    - Todo en S3 Standard.
    - Todo en S3 Standard-IA.
    - 10 % en Standard (eventos próximos) y 90 % en Glacier Instant Retrieval.

    Fíjate en el **coste por petición** y en el **tamaño mínimo facturable** de las clases IA (128 KB por objeto): con objetos de 80 KB, ¿sigue saliendo a cuenta Standard-IA?

5. **Escenario C · CDN:** añade **Amazon CloudFront** con 150 GB de salida y 3 000 000 de peticiones HTTPS, y quita la salida a Internet de S3. Compara con el escenario A.

6. **Guarda** la estimación (*Save and share*) y copia el enlace.

{{% /steps %}}

#### Comprobación

- [ ] Tienes una estimación compartida con los escenarios A, B (3 variantes) y C.
- [ ] Sabes explicar por qué Standard-IA puede salir **más cara** que Standard con objetos pequeños.
- [ ] Sabes qué concepto domina el coste de cada escenario.

> [!TIP]
> Haz siempre una tabla con «concepto / cantidad / precio unitario / total». Si la calculadora y tu tabla no coinciden, has olvidado un concepto.

---

## Práctica 1.3 · Matriz de selección

{{< practica num="1.3" tipo="Autónoma" duracion="1,5 h" nivel="2" ra="RA1: a, b, c, d" entorno="Documentación del proveedor · calculadora" entrega="ud01/p1_3.md" >}}

#### Objetivo

Aplicar el método de la teoría a casos que no son del proyecto.

#### Enunciado

Para cada caso, completa una fila de la matriz: **tipo de almacenamiento, servicio y clase, región de producción, garantías que cumple (con enlace a la documentación), alternativa descartada y por qué, y coste mensual estimado**.

1. Un centro educativo guarda las grabaciones de clase (2 TB/año). Se ven la semana siguiente y luego casi nunca. Hay que conservarlas 4 años.
2. Una clínica dental necesita el disco de su servidor de historias clínicas: 200 GB, 3000 IOPS, datos de salud.
3. Tres servidores de una tienda online comparten las imágenes de producto subidas por los administradores (50 GB).
4. Una aplicación de domótica recibe 5000 lecturas por segundo de sensores; se consultan por dispositivo y fecha.
5. Un despacho de abogados quiere un archivo de documentos cerrados que debe conservar 10 años y casi nunca consulta.
6. Un videojuego necesita guardar partidas (pocos KB) de 1 millón de jugadores, con latencia baja en todo el mundo.

#### Comprobación

- [ ] Las seis filas tienen requisitos **con números** (supón valores razonables si faltan y dilo).
- [ ] Cada garantía tiene un enlace a la documentación oficial.
- [ ] En al menos dos casos has descartado algo por la región o por el coste, y lo justificas.

---

## Práctica 1.4 · Informe de selección de TaquillaAlacant

{{< practica num="1.4" tipo="Proyecto" duracion="1,5 h" nivel="2" ra="RA1: a, b, c, d, e" entorno="Calculadora · documentación · Markdown" entrega="ud01/README.md + enlace a la estimación" >}}

#### Objetivo

Decidir dónde va cada dato de [TaquillaAlacant](/guia/proyecto-taquilla/) y cuánto cuesta. Este informe es la «hoja de ruta» del resto del módulo.

#### Desarrollo

1. Crea tu repositorio privado `taquilla-<alumno>` con la carpeta `ud01/` y un `.gitignore` que excluya `*.tfstate*`, `.terraform/` y `*.pem`.
2. Para cada fila de la tabla de datos del proyecto, escribe los **requisitos** con números.
3. Elige **servicio, clase y región de producción**; justifica la residencia de los datos personales.
4. Indica qué **no** está disponible en la región elegida y cómo lo resuelves.
5. Haz la **estimación mensual** en la calculadora y pega el enlace.
6. Propón **tres ajustes** que reducen el coste sin incumplir requisitos (por ejemplo: ciclo de vida de las entradas, CDN para los carteles, retención de copias) y cuantifica el ahorro.

#### Comprobación

- [ ] Las ocho clases de datos del proyecto están clasificadas y justificadas.
- [ ] La región elegida cumple el RGPD y está razonada frente a `us-east-1`.
- [ ] Hay una estimación compartida y tres ajustes de coste cuantificados.

#### Ampliación

Repite la estimación con **Azure** (<https://azure.microsoft.com/pricing/calculator/>) o **Google Cloud** para los carteles y las entradas, y compara.

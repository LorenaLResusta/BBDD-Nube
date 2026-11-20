---
title: "UD01 · Pràctiques"
weight: 2
bookToc: true
---

# UD01 · Pràctiques

{{< ra "RA1:a,b,c,d,e" >}}

| Pràctica | Tipus | Nivell | Hores | CA principals |
|---|---|---|--:|---|
| [1.1 Entorn de treball i regions](#pràctica-11--entorn-de-treball-i-regions) | Guiada | ●○○ | 1,5 | RA1: b, c |
| [1.2 Estimar costos amb la calculadora](#pràctica-12--estimar-costos-amb-la-calculadora) | Guiada | ●○○ | 1,5 | RA1: d, e |
| [1.3 Matriu de selecció](#pràctica-13--matriu-de-selecció) | Autònoma | ●●○ | 1,5 | RA1: a, b, c, d |
| [1.4 Informe de selecció de TaquillaAlacant](#pràctica-14--informe-de-selecció-de-taquillaalacant) | Projecte | ●●○ | 1,5 | RA1: a, b, c, d, e |
| **Total** | | | **6 h** | |

---

## Pràctica 1.1 · Entorn de treball i regions

{{< practica num="1.1" tipo="Guiada" duracion="1,5 h" nivel="1" ra="RA1: b, c" entorno="AWS Learner Lab · AWS CLI · CloudShell" entrega="no" >}}

#### Objectiu

Deixar preparat l'accés al laboratori des de la consola, CloudShell i la teua màquina, i aprendre a consultar **quins serveis hi ha en cada regió** sense eixir del terminal.

#### Desenvolupament

{{% steps %}}

1. **Arranca el laboratori** (*Start Lab*) i obri la consola. Comprova dalt a la dreta que estàs en **N. Virginia (`us-east-1`)**.

2. **Obri CloudShell** i comprova la teua identitat:

    ```bash
    aws sts get-caller-identity
    aws configure list
    ```

3. **Configura la CLI en `local-lab`** copiant el bloc d'*AWS Details → AWS CLI* en `~/.aws/credentials`, com s'explica en l'[entorn](/guia/entorno/). Repetix `aws sts get-caller-identity`.

4. **Llista les regions** que coneix el compte i les seues zones de disponibilitat:

    ```bash
    aws ec2 describe-regions --all-regions --query 'Regions[].[RegionName,OptInStatus]' --output table
    aws ec2 describe-availability-zones --region us-east-1 --query 'AvailabilityZones[].[ZoneName,ZoneId,State]' --output table
    ```

    > [!NOTE]
    > Veuràs regions que no pots usar: el compte les coneix, però les polítiques del laboratori t'impedixen crear-hi recursos.

5. **Consulta quins serveis hi ha en una regió.** AWS publica la infraestructura global com a paràmetres públics de Systems Manager:

    ```bash
    for r in us-east-1 eu-south-2 eu-west-1; do
      echo "== $r: $(aws ssm get-parameters-by-path \
          --path /aws/service/global-infrastructure/regions/$r/services \
          --query 'length(Parameters)' --output text) servicios"
    done
    ```

    I quins serveis hi ha en `us-east-1` que **no** estan en `eu-south-2` (Espanya):

    ```bash
    servicios() {
      aws ssm get-parameters-by-path --region us-east-1 \
        --path /aws/service/global-infrastructure/regions/$1/services \
        --query 'Parameters[].Value' --output text | tr '\t' '\n' | sort
    }
    comm -23 <(servicios us-east-1) <(servicios eu-south-2) | head -40
    ```

6. **Compara amb la documentació**: obri *AWS Services by Region* i busca els mateixos serveis. Anota qualsevol diferència.

7. **Disponibilitat de versions de motor** (la necessitaràs en la UD04):

    ```bash
    aws rds describe-db-engine-versions --engine postgres \
      --query 'DBEngineVersions[].EngineVersion' --output text | tr '\t' '\n' | tail -5
    ```

{{% /steps %}}

#### Comprovació

- [ ] `aws sts get-caller-identity` funciona en CloudShell i en `local-lab`.
- [ ] Saps quantes AZ té `us-east-1` i quina és la diferència entre `ZoneName` i `ZoneId`.
- [ ] Has trobat almenys un servei o classe d'emmagatzematge que **no** està en `eu-south-2` i sí en `us-east-1`.

#### Problemes habituals

| Símptoma | Causa | Solució |
|---|---|---|
| `ExpiredToken` | Has reiniciat la sessió del laboratori | Copia de nou les credencials |
| `AccessDenied` en una altra regió | Restricció del Learner Lab | Treballa en `us-east-1` o `us-west-2` |
| `Could not connect to the endpoint URL` | Regió mal escrita | Revisa `~/.aws/config` |

---

## Pràctica 1.2 · Estimar costos amb la calculadora

{{< practica num="1.2" tipo="Guiada" duracion="1,5 h" nivel="1" ra="RA1: d, e" entorno="AWS Pricing Calculator" entrega="no" >}}

#### Objectiu

Construir una estimació completa de l'emmagatzematge d'objectes i comprovar **quins paràmetres mouen el cost**.

#### Desenvolupament

{{% steps %}}

1. Obri <https://calculator.aws/> → **Create estimate** → busca **Amazon S3**. Regió: **Europe (Spain)**.

2. **Escenari A · Cartells:** S3 Standard, 20 GB, 1000 `PUT` i 3 000 000 de `GET` al mes. En **Data Transfer** afig 150 GB/mes d'eixida a Internet. Anota el total.

3. **Canvia la regió** a US East (N. Virginia) sense tocar res més. Quant varia?

4. **Escenari B · Entrades en PDF:** 2 000 000 d'objectes de 80 KB (≈ 160 GB). Calcula tres variants:
    - Tot en S3 Standard.
    - Tot en S3 Standard-IA.
    - 10 % en Standard (esdeveniments pròxims) i 90 % en Glacier Instant Retrieval.

    Fixa't en el **cost per petició** i en la **grandària mínima facturable** de les classes IA (128 KB per objecte): amb objectes de 80 KB, encara ix a compte Standard-IA?

5. **Escenari C · CDN:** afig **Amazon CloudFront** amb 150 GB d'eixida i 3 000 000 de peticions HTTPS, i lleva l'eixida a Internet de S3. Compara amb l'escenari A.

6. **Guarda** l'estimació (*Save and share*) i copia l'enllaç.

{{% /steps %}}

#### Comprovació

- [ ] Tens una estimació compartida amb els escenaris A, B (3 variants) i C.
- [ ] Saps explicar per què Standard-IA pot eixir **més cara** que Standard amb objectes xicotets.
- [ ] Saps quin concepte domina el cost de cada escenari.

> [!TIP]
> Fes sempre una taula amb «concepte / quantitat / preu unitari / total». Si la calculadora i la teua taula no coincidixen, has oblidat un concepte.

---

## Pràctica 1.3 · Matriu de selecció

{{< practica num="1.3" tipo="Autónoma" duracion="1,5 h" nivel="2" ra="RA1: a, b, c, d" entorno="Documentació del proveïdor · calculadora" entrega="ud01/p1_3.md" >}}

#### Objectiu

Aplicar el mètode de la teoria a casos que no són del projecte.

#### Enunciat

Per a cada cas, completa una fila de la matriu: **tipus d'emmagatzematge, servei i classe, regió de producció, garanties que compleix (amb enllaç a la documentació), alternativa descartada i per què, i cost mensual estimat**.

1. Un centre educatiu guarda les gravacions de classe (2 TB/any). Es veuen la setmana següent i després quasi mai. Cal conservar-les 4 anys.
2. Una clínica dental necessita el disc del seu servidor d'històries clíniques: 200 GB, 3000 IOPS, dades de salut.
3. Tres servidors d'una botiga en línia compartixen les imatges de producte que pugen els administradors (50 GB).
4. Una aplicació de domòtica rep 5000 lectures per segon de sensors; es consulten per dispositiu i data.
5. Un despatx d'advocats vol un arxiu de documents tancats que ha de conservar 10 anys i quasi mai consulta.
6. Un videojoc necessita guardar partides (pocs KB) d'1 milió de jugadors, amb latència baixa en tot el món.

#### Comprovació

- [ ] Les sis files tenen requisits **amb números** (suposa valors raonables si en falten i digues-ho).
- [ ] Cada garantia té un enllaç a la documentació oficial.
- [ ] En almenys dos casos has descartat alguna cosa per la regió o pel cost, i ho justifiques.

---

## Pràctica 1.4 · Informe de selecció de TaquillaAlacant

{{< practica num="1.4" tipo="Proyecto" duracion="1,5 h" nivel="2" ra="RA1: a, b, c, d, e" entorno="Calculadora · documentació · Markdown" entrega="ud01/README.md + enllaç a l'estimació" >}}

#### Objectiu

Decidir on va cada dada de [TaquillaAlacant](/guia/proyecto-taquilla/) i quant costa. Este informe és el «full de ruta» de la resta del mòdul.

#### Desenvolupament

1. Crea el teu repositori privat `taquilla-<alumne>` amb la carpeta `ud01/` i un `.gitignore` que excloga `*.tfstate*`, `.terraform/` i `*.pem`.
2. Per a cada fila de la taula de dades del projecte, escriu els **requisits** amb números.
3. Tria **servei, classe i regió de producció**; justifica la residència de les dades personals.
4. Indica què **no** està disponible en la regió triada i com ho resols.
5. Fes l'**estimació mensual** en la calculadora i apega l'enllaç.
6. Proposa **tres ajustos** que reduïxen el cost sense incomplir requisits (per exemple: cicle de vida de les entrades, CDN per als cartells, retenció de còpies) i quantifica l'estalvi.

#### Comprovació

- [ ] Les huit classes de dades del projecte estan classificades i justificades.
- [ ] La regió triada compleix l'RGPD i està raonada davant d'`us-east-1`.
- [ ] Hi ha una estimació compartida i tres ajustos de cost quantificats.

#### Ampliació

Repetix l'estimació amb **Azure** (<https://azure.microsoft.com/pricing/calculator/>) o **Google Cloud** per als cartells i les entrades, i compara.

---
title: "Projecte: TaquillaAlacant"
weight: 40
bookToc: true
---

# Projecte transversal: TaquillaAlacant

**TaquillaAlacant** és una empresa fictícia d'Alacant que ven entrades per a concerts, teatre, partits i actes de les festes. Va començar amb una taquilla física i un servidor en l'oficina; ara vol portar les seues dades al núvol sense perdre el control de la seguretat ni del cost. Tu eres la persona que administra eixes dades.

## Les dades de l'empresa

| Dada | Volum | Patró d'accés | On acabarà | Unitat |
|---|---|---|---|---|
| Cartells i imatges dels esdeveniments | ~20 GB, creix 1 GB/mes | Lectura pública molt freqüent; quasi mai es modifiquen | S3 + domini amb HTTPS | UD02 |
| Entrades en PDF emeses | ~2 milions de fitxers xicotets | Es descarreguen els dies previs a l'esdeveniment; després quasi mai | S3 amb cicle de vida | UD02 |
| Registres del servidor d'aplicacions | 5 GB/setmana | Escriptura contínua, lectura ocasional | EBS + exportació a S3 | UD03 |
| Plantilles i documents compartits | 50 GB | Lectura/escriptura des de diversos servidors | EFS | UD03 |
| Vendes, esdeveniments, recintes i clients | 10 GB | Transaccional, moltes escriptures xicotetes | RDS PostgreSQL | UD04 |
| Carret i cua d'espera de cada esdeveniment | Pics de milers de peticions per segon | Clau-valor, caduca en minuts | DynamoDB | UD04 |
| Base de dades i carpetes de l'oficina | 30 GB | Encara s'usen en la taquilla física | Sincronitzades amb el núvol | UD05 – UD06 |
| Històric de vendes per a anàlisi | 5 anys | Consultes d'agregació mensuals | Data lake (Parquet) + Athena | UD07 |

## El que fas en cada unitat

```mermaid
flowchart TB
    U1["UD01 · Informe de selecció<br/>tipus, regió i cost de cada dada"] --> U2["UD02 · Bucket de cartells públic amb HTTPS<br/>i bucket privat d'entrades amb cicle de vida"]
    U2 --> U3["UD03 · Servidor amb disc de logs xifrat<br/>i EFS de plantilles, amb còpies"]
    U3 --> U4["UD04 · RDS PostgreSQL amb còpies, rèplica i alarmes<br/>+ taula DynamoDB del carret"]
    U4 --> U5["UD05 · Migració de la base de dades de l'oficina<br/>i sincronització de carpetes"]
    U5 --> U6["UD06 · Túnel VPN oficina–VPC<br/>i rèplica contínua"]
    U6 --> U7["UD07 · Data lake de vendes, Athena<br/>i pràctica final"]
```

## Recursos del projecte

L'esquema de la base de dades i un generador de dades de vendes realistes (amb esdeveniments d'Alacant, recintes i dates de festes):

{{< descarga "recursos/taquilla/esquema.sql" >}}

{{< descarga "recursos/taquilla/generar_ventas.py" >}}

Ús del generador:

```bash
python3 generar_ventas.py --ventas 200000 --salida ventas.csv     # CSV per a càrregues i anàlisi
python3 generar_ventas.py --ventas 5000 --sql > datos.sql          # INSERT per a PostgreSQL
```

> [!IMPORTANT]
> El projecte es lliura **en un únic repositori Git privat per alumne** (`taquilla-<alumne>`), amb una carpeta per unitat (`ud01/`, `ud02/`…) que conté el codi d'OpenTofu, els scripts, l'informe en Markdown i les captures. L'estat d'OpenTofu i les credencials **no** es pugen.

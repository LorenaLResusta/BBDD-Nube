---
title: "UD04. Bases de dades administrades"
weight: 40
---

# UD04 · Bases de dades administrades

Les vendes de TaquillaAlacant no poden perdre's ni aturar-se un divendres a la nit abans d'un concert. En esta unitat administres bases de dades **relacionals** (Amazon RDS i Aurora) i **NoSQL** (DynamoDB) en el núvol: regió i alta disponibilitat, xifratge, usuaris i auditoria, canvis de grandària i versió, còpies i recuperació a un instant, monitorització del rendiment i optimitzacions senzilles.

{{< ra "RA4:a,b,c,d,e,f,g" >}}

| Pàgina | Contingut |
|---|---|
| [Teoria](/ud04-bases-datos/ud04-teoria/) | Models de servei, motors, Multi-AZ i rèpliques, xifratge, xarxa i usuaris, auditoria, cicle de vida, còpies i PITR, rendiment, optimització i DynamoDB (8 h) |
| [Pràctiques](/ud04-bases-datos/ud04-practicas/) | RDS PostgreSQL amb OpenTofu, usuaris i TLS, còpies i PITR, rèpliques i Multi-AZ, rendiment i optimització, DynamoDB, Aurora i la tasca del projecte (16 h) |

**Durada:** 24 hores (8 h de teoria i 16 h de pràctiques).

> [!WARNING]
> És la unitat que més crèdit consumix. **Atura** (`aws rds stop-db-instance`) o **destruïx** les bases de dades en acabar cada sessió.

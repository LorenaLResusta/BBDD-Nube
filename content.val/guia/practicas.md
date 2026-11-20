---
title: "Pràctiques i avaluació"
weight: 50
bookToc: true
---

# Com són les pràctiques i l'avaluació

## Tipus de pràctica

| Tipus | Què és | Es lliura? |
|---|---|---|
| **Guiada** | Procediment pas a pas per a aprendre el servei | No: es revisa a classe amb la llista de comprovació |
| **Autònoma** | Un encàrrec sense passos; has de decidir com fer-lo | Sí |
| **Repte** | Un problema obert o més avançat | Opcional, puja nota |
| **Projecte** | La tasca de TaquillaAlacant de cada unitat | Sí, sempre |

Totes les pràctiques tenen la mateixa estructura: **fitxa** (durada, dificultat, RA/CA, programari i lliurament) → **objectiu** → **desenvolupament** → **comprovació** → **neteja** → problemes habituals → ampliació.

## Què es lliura

En el teu repositori `taquilla-<alumne>`, carpeta de la unitat:

- `README.md` amb l'**informe**: decisions preses i per què, ordres executades, comprovacions i **cost estimat**.
- El codi: `*.tf`, scripts `*.sh`/`*.py`, consultes `*.sql`.
- Captures en `img/`, amb el nom del recurs visible (que es veja el teu `ta-<alumne>`).
- Mai: `terraform.tfstate`, `.terraform/`, fitxers `credentials`, contrasenyes o claus.

## Rúbrica comuna de les pràctiques lliurables

| Criteri | 0 – 4 | 5 – 6 | 7 – 8 | 9 – 10 |
|---|---|---|---|---|
| **Funciona** (40 %) | No funciona o no es pot comprovar | Funciona amb ajuda o parcialment | Funciona i es comprova | Funciona, es comprova i s'ha provat una fallada i la recuperació |
| **Seguretat** (20 %) | Dades públiques o sense xifrar sense justificació | Xifratge i accés bàsics | Mínim privilegi i auditoria | A més, revisat amb ferramentes (Access Analyzer, Security Hub…) |
| **Cost** (15 %) | No es té en compte | Estimació sense justificar | Estimació amb la calculadora | A més, proposta raonada d'estalvi |
| **IaC i automatització** (15 %) | Tot a mà sense documentar | Ordres documentades | IaC o scripts reproduïbles | IaC neta, amb variables i eixides |
| **Informe** (10 %) | Incomplet | Descriu el que s'ha fet | Justifica les decisions | Clar, concís i amb conclusions útils |

## Avaluació

- Cada **RA** es qualifica amb les pràctiques lliurables, la tasca del projecte i una **prova pràctica** individual que reproduïx, en temps limitat, una part del que s'ha treballat.
- Pes orientatiu dins de cada RA: **pràctiques i projecte 60 %**, **prova pràctica 40 %**.
- La nota del mòdul és la mitjana ponderada per hores dels RA (vegeu [RA i criteris](/guia/ra-ce/)), sempre que tots estiguen superats.
- Les pràctiques lliurades amb recursos que continuen actius dies després sense justificació baixen un punt en el criteri de cost: **netejar també s'avalua**.

> [!WARNING]
> Les pràctiques són individuals. Pots consultar documentació, fòrums i assistents d'IA, però has de poder **explicar i repetir** tot el que lliures en la defensa oral.

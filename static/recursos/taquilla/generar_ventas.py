#!/usr/bin/env python3
"""TaquillaAlacant · generador de datos de prueba.

Genera eventos, clientes y ventas con una semilla fija (los datos son siempre los mismos).

  python3 generar_ventas.py --ventas 200000 --salida ventas.csv   # CSV de ventas desnormalizado
  python3 generar_ventas.py --ventas 5000 --sql > datos.sql        # INSERT para esquema.sql
  python3 generar_ventas.py --ventas 3000 --fecha 2026-11-20 --id-inicial 9000001 --salida dia.csv
                                                                   # ventas de un solo día (cargas incrementales)

Solo usa la biblioteca estándar de Python 3.9 o superior.
"""
import argparse
import csv
import random
import sys
from datetime import datetime, timedelta

RECINTOS = [  # (id, nombre, aforo) en el mismo orden que esquema.sql
    (1, "Plaza de Toros de Alicante", 11000),
    (2, "Teatro Principal", 1300),
    (3, "Estadio José Rico Pérez", 29500),
    (4, "ADDA Auditorio", 1600),
    (5, "Centro de Congresos de Elche", 1000),
    (6, "Explanada de España", 20000),
]
TITULOS = {
    "concierto": ["Noches de la Explanada", "Festival de la Terreta", "Gira Mediterrània", "Rock al Castell"],
    "teatro": ["La Celestina", "Luces de bohemia", "Comedia en el Principal", "Monólogos de verano"],
    "deporte": ["Hércules CF - Rival", "Final de pelota valenciana", "Gala de boxeo"],
    "fiestas": ["Mascletà de Luceros", "Concurso de Hogueras", "Nit de la Cremà"],
    "infantil": ["Títeres de verano", "Musical familiar", "Magia para peques"],
}
RECINTO_POR_CATEGORIA = {"concierto": [1, 6, 4], "teatro": [2, 5], "deporte": [3], "fiestas": [6], "infantil": [2, 4, 5]}
PRECIO = {"concierto": (25, 70), "teatro": (12, 40), "deporte": (15, 60), "fiestas": (5, 20), "infantil": (6, 15)}
NOMBRES = ["Lucía", "Hugo", "Martina", "Pau", "Vega", "Àlex", "Carla", "Jordi", "Nerea", "Iker", "Aitana", "Marc"]
APELLIDOS = ["García", "Martínez", "Pérez", "Sánchez", "Ferrer", "Soler", "Llorca", "Ivorra", "Pastor", "Climent"]
CPS = ["03001", "03002", "03003", "03004", "03005", "03010", "03015", "03201", "03550", "03560", "03690"]


def generar(n_ventas, seed=2627, dia=None, id_inicial=1):
    rnd = random.Random(seed)
    inicio = datetime(2022, 1, 1)
    eventos = []
    for i in range(1, 401):
        cat = rnd.choice(list(TITULOS))
        fecha = inicio + timedelta(days=rnd.randint(0, 4 * 365), hours=rnd.choice([12, 18, 20, 21, 22]))
        if cat == "fiestas":  # las Hogueras, del 20 al 24 de junio
            fecha = datetime(rnd.choice([2022, 2023, 2024, 2025]), 6, rnd.randint(20, 24), 14)
        lo, hi = PRECIO[cat]
        eventos.append({
            "id_evento": i, "id_recinto": rnd.choice(RECINTO_POR_CATEGORIA[cat]),
            "titulo": f"{rnd.choice(TITULOS[cat])} {fecha.year}", "categoria": cat,
            "fecha": fecha, "precio_base": round(rnd.uniform(lo, hi), 2),
            "cartel_s3": f"carteles/{fecha.year}/evento-{i:04d}.webp",
        })
    clientes = []
    for i in range(1, 5001):
        nom = f"{rnd.choice(NOMBRES)} {rnd.choice(APELLIDOS)}"
        clientes.append({"id_cliente": i, "email": f"cliente{i:05d}@example.com", "nombre": nom, "cp": rnd.choice(CPS)})
    ventas = []
    for i in range(id_inicial, id_inicial + n_ventas):
        ev = rnd.choice(eventos)
        if dia:  # todas las ventas en el día indicado
            fv = dia + timedelta(seconds=rnd.randint(0, 86399))
        else:
            dias_antes = int(rnd.expovariate(1 / 12))  # la mayoría compra pocos días antes
            fv = ev["fecha"] - timedelta(days=dias_antes, minutes=rnd.randint(0, 1440))
        n = rnd.choices([1, 2, 3, 4, 5, 6], weights=[25, 40, 12, 15, 4, 4])[0]
        canal = rnd.choices(["web", "app", "taquilla"], weights=[50, 35, 15])[0]
        ventas.append({
            "id_venta": i, "id_evento": ev["id_evento"], "id_cliente": rnd.randint(1, len(clientes)),
            "fecha_venta": fv, "canal": canal, "entradas": n,
            "importe": round(n * ev["precio_base"] * (1.0 if canal == "taquilla" else 1.08), 2),
            "pdf_s3": f"entradas/{fv:%Y/%m}/venta-{i:08d}.pdf",
        })
    return eventos, clientes, ventas


def sql_str(v):
    if isinstance(v, str):
        return "'" + v.replace("'", "''") + "'"
    if isinstance(v, datetime):
        return f"'{v:%Y-%m-%d %H:%M:%S}'"
    return str(v)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ventas", type=int, default=10000)
    ap.add_argument("--salida", default="-", help="fichero CSV (por defecto, salida estándar)")
    ap.add_argument("--sql", action="store_true", help="genera INSERT en lugar de CSV")
    ap.add_argument("--fecha", help="AAAA-MM-DD: todas las ventas en ese día")
    ap.add_argument("--id-inicial", type=int, default=1, help="primer id_venta (por defecto 1)")
    a = ap.parse_args()
    fecha = datetime.strptime(a.fecha, "%Y-%m-%d") if a.fecha else None
    eventos, clientes, ventas = generar(a.ventas, dia=fecha, id_inicial=a.id_inicial)

    if a.sql:
        out = sys.stdout
        for nombre, filas in (("evento", eventos), ("cliente", clientes), ("venta", ventas)):
            cols = list(filas[0])
            for k in range(0, len(filas), 500):
                valores = ",\n  ".join("(" + ", ".join(sql_str(f[c]) for c in cols) + ")" for f in filas[k:k + 500])
                out.write(f"INSERT INTO {nombre} ({', '.join(cols)}) VALUES\n  {valores};\n")
            out.write(f"SELECT setval(pg_get_serial_sequence('{nombre}', 'id_{nombre}'), (SELECT max(id_{nombre}) FROM {nombre}));\n")
        return

    ev_idx = {e["id_evento"]: e for e in eventos}
    rec_idx = {r[0]: r[1] for r in RECINTOS}
    cli_idx = {c["id_cliente"]: c for c in clientes}
    f = sys.stdout if a.salida == "-" else open(a.salida, "w", newline="", encoding="utf-8")
    w = csv.writer(f)
    w.writerow(["id_venta", "fecha_venta", "canal", "entradas", "importe", "id_evento", "titulo",
                "categoria", "fecha_evento", "recinto", "id_cliente", "cp_cliente"])
    for v in ventas:
        e = ev_idx[v["id_evento"]]
        w.writerow([v["id_venta"], f"{v['fecha_venta']:%Y-%m-%d %H:%M:%S}", v["canal"], v["entradas"], f"{v['importe']:.2f}",
                    e["id_evento"], e["titulo"], e["categoria"], f"{e['fecha']:%Y-%m-%d %H:%M:%S}",
                    rec_idx[e["id_recinto"]], v["id_cliente"], cli_idx[v["id_cliente"]]["cp"]])
    if f is not sys.stdout:
        f.close()


if __name__ == "__main__":
    main()

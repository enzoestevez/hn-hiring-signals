"""
Deteccion de deriva. Mira la ENTRADA y el PROCESO, no la salida.

POR QUE NO ALCANZA CON MIRAR LA SALIDA
--------------------------------------
El clasificador puede empeorar sin que el agregado se mueva: si los errores
en las dos direcciones se compensan --que es lo que ya pasa, 5 FP contra 2 FN
en el held-out-- la tasa de meta queda igual y la precision por post se
derrumba. Y no hay etiquetas nuevas todos los meses para medirlo.

LA FRAGILIDAD QUE ESTO VIGILA
-----------------------------
El 88,5% de las decisiones las toma UNA regla: el encabezado
`Empresa | Puesto | Ubicacion`. Si la convencion del hilo cambia, el 88,5% de
las decisiones cambia de golpe. El detector 1 mira exactamente eso.

    python src/deriva.py              # corre los detectores sobre el corpus
    python src/deriva.py --inyectar   # test: degrada un mes a proposito y
                                      # verifica que los detectores suenen
"""

import collections
import json
import os
import re
import statistics as st
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(DIR)
DATOS = os.path.join(RAIZ, "data")
PANEL = os.path.join(RAIZ, "docs", "panel")

sys.path.insert(0, DIR)
from clasificar import clasificar, limpiar  # noqa: E402

MES_ABIERTO = None   # se calcula: el ultimo mes del corpus sigue sumando posts


def jl(p):
    with open(os.path.join(DATOS, p), encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def rasgos(p):
    """Los rasgos que se vigilan. Se calculan del TEXTO, no de la etiqueta:
    un detector que dependa de la salida no puede avisar que la salida esta
    mal."""
    e, motivo = clasificar(p.get("texto_html"))
    t = limpiar(p.get("texto_html"))
    plano = " ".join(t.split())
    return {
        "emp": e, "motivo": motivo,
        "encabezado": motivo.startswith("encabezado"),
        "pipes": plano.count("|") >= 2,
        "url": "http" in t,
        "largo": len(plano),
        "debil": any(motivo.startswith(d) for d in (
            "senales de vacante (1/4)", "sin vacante identificable",
            "titulo de puesto en un post largo", "titulo de puesto + modalidad",
            "post corto sin ninguna senal")),
    }


def banda_loo(serie_por_mes, mes, k=3):
    """Banda calculada DEJANDO AFUERA el mes que se evalua. Incluirlo haria
    que casi nunca pueda caerse de su propia banda: el mismo error que
    evaluar un modelo con sus datos de entrenamiento."""
    otros = [v for m, v in serie_por_mes.items() if m != mes]
    if len(otros) < 4:
        return None
    mu, sd = st.mean(otros), st.stdev(otros)
    return mu, sd, mu - k * sd, mu + k * sd


DETECTORES = [
    ("motivo dominante (encabezado)", lambda ps: sum(1 for p in ps if p["encabezado"]) / len(ps), "pct"),
    ("formato: 2+ pipes",            lambda ps: sum(1 for p in ps if p["pipes"]) / len(ps), "pct"),
    ("formato: con URL",             lambda ps: sum(1 for p in ps if p["url"]) / len(ps), "pct"),
    ("largo mediano",                lambda ps: st.median(p["largo"] for p in ps), "num"),
    ("tasa de meta",                 lambda ps: sum(1 for p in ps if not p["emp"]) / len(ps), "pct"),
]


def evaluar(por_mes, mes_objetivo, cerrados):
    """Corre los 5 detectores sobre un mes. Devuelve filas con veredicto."""
    filas = []
    for nombre, f, tipo in DETECTORES:
        serie = {m: f(por_mes[m]) for m in cerrados}
        v = f(por_mes[mes_objetivo])
        b = banda_loo(serie, mes_objetivo)
        if not b:
            continue
        mu, sd, lo, hi = b
        filas.append({
            "detector": nombre, "tipo": tipo, "valor": v, "media": mu,
            "sd": sd, "lo": lo, "hi": hi, "suena": not (lo <= v <= hi),
            "umbral_pts": 3 * sd,
        })
    return filas


def imprimir(filas, titulo):
    print(f"\n  {titulo}")
    print(f"  {'detector':<32}{'valor':>9}{'esperado':>11}{'banda 3sd':>20}   ")
    for f in filas:
        fmt = (lambda x: f"{x:.1%}") if f["tipo"] == "pct" else (lambda x: f"{x:.0f}")
        print(f"  {f['detector']:<32}{fmt(f['valor']):>9}{fmt(f['media']):>11}"
              f"   [{fmt(f['lo'])}, {fmt(f['hi'])}]".ljust(22)
              + ("  <-- SUENA" if f["suena"] else ""))
    return sum(1 for f in filas if f["suena"])


def main():
    posts = jl("posts.jsonl")
    for p in posts:
        p.update(rasgos(p))
    por_mes = collections.defaultdict(list)
    for p in posts:
        por_mes[p["mes"]].append(p)
    meses = sorted(por_mes)
    abierto = meses[-1]
    cerrados = [m for m in meses if m != abierto]

    print("=" * 72)
    print("  DERIVA — se mira la ENTRADA y el PROCESO, no la salida")
    print("=" * 72)

    # ---- detector 3: consistencia en casi-duplicados -----------------------
    def norm(t):
        t = re.sub(r"https?://\S+", " U ", limpiar(t or "").lower())
        return " ".join(re.sub(r"[^a-z0-9 ]", " ", t).split())
    g = collections.defaultdict(list)
    for p in posts:
        k = norm(p.get("texto_html"))[:90]
        if len(k) >= 60:
            g[k].append(p)
    grupos = [v for v in g.values() if len({x["mes"] for x in v}) > 1]
    flips = [v for v in grupos if len({x["emp"] for x in v}) > 1]

    # ---- corrida normal ----------------------------------------------------
    total_suena = 0
    for m in meses[-3:]:
        n = imprimir(evaluar(por_mes, m, cerrados), f"MES {m}" + ("  (abierto)" if m == abierto else ""))
        total_suena += n

    print(f"\n  casi-duplicados entre meses   {len(grupos)} grupos, {sum(len(v) for v in grupos)} posts")
    print(f"  grupos con etiqueta distinta  {len(flips)}", end="   ")
    print("OK" if not flips else "<-- SUENA: el mismo aviso clasificado de dos formas")
    print("  (el clasificador es determinista: este detector no puede sonar")
    print("   hasta que haya un LLM en el loop. 0 flips tambien es un dato:")
    print("   no se tambalea ante reescrituras cosmeticas del mismo aviso.)")

    debiles = [p for p in por_mes[abierto] if p["debil"]]
    print(f"\n  COLA DE REVISION del ultimo mes: {len(debiles)} posts de baja confianza")
    print("  (NO es una tasa de acierto: revisar solo los dudosos encuentra mas")
    print("   errores que el promedio por construccion. Es un canario.)")
    for p in debiles[:8]:
        print(f"    {p['id']}  [{p['motivo'][:38]}]  {' '.join(limpiar(p['texto_html']).split())[:62]}")

    # ---- test de inyeccion -------------------------------------------------
    if "--inyectar" in sys.argv:
        print("\n" + "=" * 72)
        print("  TEST DE INYECCION — un detector sin probar no funciona")
        print("=" * 72)
        print("  Se le saca el encabezado de pipes a un X% de los posts del")
        print("  ultimo mes cerrado y se mira si los detectores suenan.")
        base = por_mes[cerrados[-1]]
        rng = __import__("random").Random(7)
        for frac in (0.02, 0.05, 0.10, 0.20):
            copia = []
            idx = set(rng.sample(range(len(base)), int(len(base) * frac)))
            for i, p in enumerate(base):
                if i in idx:
                    q = dict(p)
                    # romper el encabezado: sacar los pipes de los primeros 120 chars
                    t = p["texto_html"]
                    q["texto_html"] = t[:120].replace("|", " ") + t[120:]
                    q.update(rasgos(q))
                    copia.append(q)
                else:
                    copia.append(p)
            pm2 = dict(por_mes)
            pm2[cerrados[-1]] = copia
            filas = evaluar(pm2, cerrados[-1], cerrados)
            d1 = next(f for f in filas if f["detector"].startswith("motivo"))
            n = sum(1 for f in filas if f["suena"])
            print(f"\n  degradacion {frac:>4.0%}: encabezado {d1['valor']:.1%} "
                  f"(esperado {d1['media']:.1%}, banda hasta {d1['lo']:.1%})"
                  f"  ->  {'SUENA' if d1['suena'] else 'no suena'}"
                  f"   [{n} de {len(filas)} detectores]")
        print("\n  Registrado: 10% si, 5% si apenas, 2% no.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

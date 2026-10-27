"""
Cuanto mueve la estimacion corregir las etiquetas que se encontraron mal.

Reusa el metodo de techo.py (peso efectivo N_h/etiquetados + bootstrap dentro
de cada estrato, misma semilla) para que los numeros sean comparables. No se
reimplementa la estimacion: duplicarla fue el error de p02.
"""
import json, os, random, sys

DIR = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(DIR)
DATOS, REPORTES = os.path.join(RAIZ, "data"), os.path.join(RAIZ, "reportes")
if not os.path.isdir(REPORTES):
    REPORTES = os.path.join(RAIZ, "reports")

N_TEXTO_13M, PUBLICADO = 4054, 3909

# Errores encontrados al revisar. Todos en la misma direccion: empresa que
# contrata, marcada meta. Ninguno admite otra lectura segun la guia.
CORRECCIONES = {
    48370889: "telli | Engineering, Design, GTM | On-site | Berlin + link a su bolsa (LIMPIO)",
    46885022: "'telli is hiring [Berlin, on-site] - careers.telli.com'",
    45809383: "telli: 'checkout our openings here' + link",
    47611075: "telli (YC F24) 'looking for ambitious to join our team' - mal en LAS DOS pasadas",
    47230320: "Glitch: 'We need Engineers... Email me @ kingsley@glitchads.ai'",
}


def jl(p):
    with open(os.path.join(DATOS, p), encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def estimar(oro, N_h, semilla=20261023, reps=20000):
    por = {}
    for f in oro:
        por.setdefault(f["estrato"], []).append(f)
    for e, filas in por.items():
        w = N_h[e] / len(filas)
        for x in filas:
            x["_peso"] = w
    num = sum(x["_peso"] for fs in por.values() for x in fs if not x["es_empresa"])
    den = sum(x["_peso"] for fs in por.values() for x in fs)
    tasa = num / den
    rng = random.Random(semilla)
    bs = []
    for _ in range(reps):
        n_ = d_ = 0.0
        for fs in por.values():
            k = len(fs)
            for _ in range(k):
                x = fs[rng.randrange(k)]
                d_ += x["_peso"]
                if not x["es_empresa"]:
                    n_ += x["_peso"]
        bs.append(n_ / d_)
    bs.sort()
    lo, hi = bs[int(.025 * len(bs))], bs[int(.975 * len(bs))]
    emp = lambda t: N_TEXTO_13M * (1 - t)
    limpio = por["limpio"]
    p_l = sum(1 for x in limpio if not x["es_empresa"]) / len(limpio)
    return tasa, (lo, hi), emp(tasa), (emp(hi), emp(lo)), p_l


def main():
    diseno = json.load(open(os.path.join(REPORTES, "muestra-diseno.json"), encoding="utf-8"))
    N_h = {d["estrato"]: d["N_corpus"] for d in diseno["estratos"]}
    base = jl("oro.jsonl")

    corr = [dict(f) for f in base]
    tocados = 0
    for f in corr:
        if f["id"] in CORRECCIONES:
            if f["es_empresa"]:
                print(f"AVISO: {f['id']} ya estaba en True; no se toca")
            else:
                f["es_empresa"] = True
                tocados += 1
    print(f"correcciones aplicadas: {tocados} de {len(CORRECCIONES)}\n")
    for i, por_que in CORRECCIONES.items():
        print(f"  {i}  {por_que}")
    print()

    filas = []
    for nombre, datos in (("referencia actual", base), ("con las 5 correcciones", corr)):
        t, (lo, hi), e, (elo, ehi), p_l = estimar(datos, N_h)
        filas.append((nombre, t, lo, hi, e, elo, ehi, p_l))

    print("=" * 78)
    print(f"  {'':<24}{'tasa meta':>10}{'IC 95%':>20}{'empresas':>11}{'IC empresas':>18}")
    for n, t, lo, hi, e, elo, ehi, p_l in filas:
        print(f"  {n:<24}{t:>9.2%}  [{lo:>5.2%}, {hi:>5.2%}]{e:>11,.0f}  [{elo:>6,.0f}, {ehi:>6,.0f}]")
    print()
    print(f"  p_limpio: {filas[0][7]:.2%}  ->  {filas[1][7]:.2%}")
    mov = filas[1][4] - filas[0][4]
    print(f"\n  movimiento de la estimacion: {mov:+,.1f} empresas", end="   ")
    print("OK (<=50, consistente con 5 etiquetas)" if abs(mov) <= 50
          else "<-- FUERA: solo cambiaron 5 etiquetas, hay un error de ponderacion")
    print(f"  predicho 3.880-3.910  ->  medido {filas[1][4]:,.0f}", end="   ")
    print("dentro" if 3880 <= filas[1][4] <= 3910 else "<-- FUERA")
    print(f"\n  el analisis publicado reporta {PUBLICADO:,}")
    d0, d1 = filas[0][4] - PUBLICADO, filas[1][4] - PUBLICADO
    print(f"  distancia antes de corregir  {d0:+,.0f}")
    print(f"  distancia despues            {d1:+,.0f}")
    print("\n  PROVISORIO: solo se reviso la clase meta. La direccion contraria")
    print("  (empresas que en realidad son meta) sigue sin revisar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

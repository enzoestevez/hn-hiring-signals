"""
Agregado mensual + chequeos de deriva. Escribe docs/panel/datos.json.

Esto es lo que corre solo todos los meses: busca el hilo nuevo, baja lo que
falte, clasifica, agrega y se audita a si mismo.

NO DUPLICA CODIGO. La busqueda y la descarga son `bajar.py` llamado por
subproceso; la clasificacion es `clasificar.clasificar` importado. En p02
termine con nueve funciones copiadas entre scripts y cuando una cambiaba las
otras ocho quedaban viejas.

LO QUE ESTE SCRIPT NO PUEDE AFIRMAR
-----------------------------------
`pide_ia` no paso su techo humano (kappa 0,38): dos pasadas del mismo
etiquetador no coinciden en que es "un puesto de IA". Asi que ACA NO SE MIDE
ESO. Se mide algo distinto y mecanico: **que fraccion de los posts menciona
vocabulario de IA**, que es reproducible por construccion porque es una
expresion regular. Son dos magnitudes distintas y el panel las distingue.
"""

import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

DIR = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(DIR)
DATOS = os.path.join(RAIZ, "data")
PANEL = os.path.join(RAIZ, "docs", "panel")

sys.path.insert(0, DIR)
from clasificar import clasificar, limpiar  # noqa: E402
from deriva import DETECTORES, evaluar, rasgos  # noqa: E402

# Vocabulario de IA. Es una definicion MECANICA y declarada, no un juicio.
RX_IA = re.compile(
    r"\b(a\.?i\.?|artificial intelligence|machine learning|\bml\b|deep learning"
    r"|llms?|nlp|computer vision|data scien\w+|mlops|pytorch|tensorflow"
    r"|langchain|vllm|hugging ?face|embeddings?|rag\b|agentic|genai|gpt"
    r"|diffusion|fine[- ]?tun\w+)\b", re.I)

# Medido en la etapa 2: cuanto coincide esta regla con el juicio humano.
# Va al panel al lado del numero, porque es su error conocido.
ACUERDO_RX_HUMANO = 0.706


def jsonl(ruta):
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def norm(t):
    t = re.sub(r"https?://\S+", " URL ", limpiar(t or "").lower())
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", t).split())


def refrescar(desde):
    """Llama a bajar.py. Reanudable y append-only: pedir de mas no rompe."""
    cmd = [sys.executable, os.path.join(DIR, "bajar.py"), "--desde", desde]
    print(f"$ {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, timeout=1800)
    print(r.stdout[-1500:] if r.stdout else "", r.stderr[-800:] if r.returncode else "")
    return r.returncode == 0


def main():
    t0 = time.perf_counter()
    iniciada = datetime.now(timezone.utc)
    refresco = None
    posts_antes = 0
    ruta_posts = os.path.join(DATOS, "posts.jsonl")
    if os.path.exists(ruta_posts):
        with open(ruta_posts, encoding="utf-8") as f:
            posts_antes = sum(1 for l in f if l.strip())

    if "--refrescar" in sys.argv:
        i = sys.argv.index("--refrescar")
        desde = sys.argv[i + 1] if len(sys.argv) > i + 1 else "2025-10"
        refresco = refrescar(desde)
        if not refresco:
            print("! bajar.py fallo. Se sigue con lo que ya hay en disco.")

    posts = jsonl(os.path.join(DATOS, "posts.jsonl"))
    hilos = {h["mes"]: h for h in json.load(open(os.path.join(DATOS, "hilos.json"), encoding="utf-8"))}

    por_mes = defaultdict(list)
    for p in posts:
        por_mes[p["mes"]].append(p)

    # --- clasificar una sola vez cada post ---------------------------------
    # rasgos() vive en deriva.py y devuelve la clasificacion MAS los rasgos que
    # vigilan los detectores. Se llama una sola vez y sirve para las tres
    # cosas: agregado mensual, deteccion de deriva y registro de la corrida.
    for p in posts:
        p.update(rasgos(p))
        p["_ia"] = bool(RX_IA.search(limpiar(p.get("texto_html"))))
        p["_norm"] = norm(p.get("texto_html"))[:200]

    hoy = datetime.now(timezone.utc).strftime("%Y-%m")
    abierto_mes = None
    meses = []
    for mes in sorted(por_mes):
        ps = por_mes[mes]
        emp = [p for p in ps if p["emp"]]
        textos = Counter(p["_norm"] for p in emp)
        meses.append({
            "mes": mes,
            "hilo": hilos.get(mes, {}).get("id"),
            "posts_con_texto": len(ps),
            "empresas": len(emp),
            "meta": len(ps) - len(emp),
            "tasa_meta": round((len(ps) - len(emp)) / len(ps), 4) if ps else 0,
            "textos_distintos_en_el_mes": len(textos),
            "dup_dentro_del_mes": len(emp) - len(textos),
            "menciona_ia": sum(1 for p in emp if p["_ia"]),
            "share_ia": round(sum(1 for p in emp if p["_ia"]) / len(emp), 4) if emp else 0,
            "abierto": mes >= hoy,
        })
        if mes >= hoy:
            abierto_mes = mes

    # --- repeticion ENTRE meses: la magnitud "empresas" --------------------
    emp_todos = [p for p in posts if p["emp"]]
    distintos = len({p["_norm"] for p in emp_todos})

    # --- tendencia del vocabulario de IA, y su confusor ---------------------
    # El gradiente de supervivencia esta MEDIDO: los hilos nuevos descartan
    # mas (de ~7% a ~17%). Si los posts borrados fueran menos "de IA" que los
    # vivos, la serie subiria sola sin que el mercado cambie. No se puede
    # testear —un post borrado no tiene texto— asi que se acota:
    # se recalcula la pendiente suponiendo que TODO lo descartado era no-IA,
    # que es el supuesto mas favorable al confusor. Si la tendencia sobrevive
    # a ese piso, es real; si no sobrevive, NO SE PUEDE AFIRMAR.
    descartes = defaultdict(int)
    ruta_d = os.path.join(DATOS, "descartes.jsonl")
    if os.path.exists(ruta_d):
        for d in jsonl(ruta_d):
            if d.get("mes"):
                descartes[d["mes"]] += 1

    def pendiente(ys):
        n = len(ys)
        if n < 4:
            return None, None
        xs = list(range(n))
        mx, my = sum(xs) / n, sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs)
        b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
        res = [y - (my + b * (x - mx)) for x, y in zip(xs, ys)]
        se = (sum(r * r for r in res) / (n - 2) / sxx) ** 0.5
        return b, (b / se if se else None)

    serie = [m["share_ia"] for m in cerrados_tmp] if (cerrados_tmp := [m for m in meses if not m["abierto"]]) else []
    piso = []
    for m in cerrados_tmp:
        d = descartes.get(m["mes"], 0)
        piso.append(m["menciona_ia"] / (m["empresas"] + d) if (m["empresas"] + d) else 0)
    for m, v in zip(cerrados_tmp, piso):
        m["piso_ia"] = round(v, 4)
    for m in meses:
        m.setdefault("piso_ia", m["share_ia"])
    b_obs, t_obs = pendiente(serie)
    b_piso, t_piso = pendiente(piso)

    # --- deriva: banda LEAVE-ONE-OUT ---------------------------------------
    # La banda de cada mes se calcula SIN ese mes. Incluirlo seria evaluar con
    # el dato de entrenamiento: casi nunca podria caerse de su propia banda.
    cerrados = cerrados_tmp
    for m in meses:
        otros = [o["tasa_meta"] for o in cerrados if o["mes"] != m["mes"]]
        if len(otros) >= 3:
            mu = sum(otros) / len(otros)
            sd = (sum((x - mu) ** 2 for x in otros) / (len(otros) - 1)) ** 0.5
            lo, hi = mu - 3 * sd, mu + 3 * sd
            m["banda_loo"] = [round(lo, 4), round(hi, 4)]
            m["deriva"] = not (lo <= m["tasa_meta"] <= hi)
        else:
            m["banda_loo"], m["deriva"] = None, False

    # ------------------------------------------------------------------
    # SALUD DE LA CORRIDA. Esto es lo que un cron desatendido necesita de
    # verdad: no detectar que el mercado se movio medio punto, sino detectar
    # que el pipeline SE ROMPIO. La banda de 3 sigma sobre 12 meses solo
    # dispara con tasas de meta arriba del 7%, casi el doble del maximo
    # observado: sirve para roturas gruesas, no para cambios finos, y el
    # panel lo dice en vez de disimularlo.
    ultimo = meses[-1] if meses else None
    rango_posts = [m["posts_con_texto"] for m in cerrados]
    salud = {
        "hilo_del_mes_encontrado": bool(ultimo and ultimo.get("hilo")),
        "ultimo_mes": ultimo["mes"] if ultimo else None,
        "posts_del_ultimo_mes": ultimo["posts_con_texto"] if ultimo else 0,
        "banda_posts_historica": [min(rango_posts), max(rango_posts)] if rango_posts else None,
        "posts_fuera_de_banda": bool(ultimo and rango_posts and not
                                     (min(rango_posts) * 0.5 <= ultimo["posts_con_texto"])),
        "clasificacion_degenerada": bool(ultimo and ultimo["empresas"] in (0, ultimo["posts_con_texto"])),
        "meses_con_deriva": [m["mes"] for m in meses if m["deriva"]],
        "sensibilidad_deriva": ("con 12 meses de historia la banda de 3 sigma "
                                "recien dispara arriba del 7% de meta-comentarios, "
                                "contra un maximo observado de 5,1%. Detecta "
                                "roturas, no cambios de mercado."),
    }

    # ------------------------------------------------------------------
    # REGISTRO OPERATIVO. Una linea por corrida, append-only.
    # Construir un sistema no prueba que sepa operarlo. Lo prueba haber
    # corrido, haber fallado y haber reportado que se rompio. Esto es lo
    # unico del proyecto que vale MAS con el tiempo en vez de menos.
    # ------------------------------------------------------------------
    # Ojo: `cerrados` aca son registros agregados del mes; deriva.evaluar
    # espera los NOMBRES de los meses. Confundirlos tiraba un TypeError.
    nombres_cerrados = [m["mes"] for m in cerrados]
    sonaron = [f["detector"] for f in
               evaluar(por_mes, nombres_cerrados[-1], nombres_cerrados)
               if f["suena"]] if len(nombres_cerrados) >= 5 else []
    fila = {
        "iniciada": iniciada.isoformat(timespec="seconds"),
        "duracion_s": round(time.perf_counter() - t0, 1),
        "entorno": "github-actions" if os.environ.get("GITHUB_ACTIONS") else "local",
        "commit": (os.environ.get("GITHUB_SHA") or "")[:7] or None,
        "refresco_ok": refresco,
        "posts_antes": posts_antes,
        "posts_despues": len(posts),
        "posts_nuevos": len(posts) - posts_antes,
        "hilos": len(meses),
        "ultimo_mes": meses[-1]["mes"] if meses else None,
        "empresas": len(emp_todos),
        "empresas_distintas": distintos,
        "tasa_meta": round((len(posts) - len(emp_todos)) / len(posts), 4) if posts else None,
        "detectores_sonaron": sonaron,
        "cola_revision": sum(1 for p in por_mes[abierto_mes] if p["debil"]) if abierto_mes else 0,
        "salud_ok": bool(salud["hilo_del_mes_encontrado"]
                         and not salud["posts_fuera_de_banda"]
                         and not salud["clasificacion_degenerada"]),
    }
    with open(os.path.join(DATOS, "corridas.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(fila, ensure_ascii=False) + "\n")
    print(f"\n  registrada la corrida en data/corridas.jsonl "
          f"({fila['duracion_s']:.0f}s, {fila['posts_nuevos']:+} posts, "
          f"{len(sonaron)} detectores)")

    # las ultimas 12 corridas van al panel
    with open(os.path.join(DATOS, "corridas.jsonl"), encoding="utf-8") as f:
        corridas = [json.loads(l) for l in f if l.strip()][-12:]

    salida = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "corpus": {
            "posts_con_texto": len(posts),
            "empresas": len(emp_todos),
            "empresas_distintas": distintos,
            "repeticion": round((len(emp_todos) - distintos) / len(emp_todos), 4),
            "meses": len(meses),
        },
        "referencia_humana": {
            "estimacion": 3907, "ic95": [3804, 3977],
            "muestra": 266, "doble_ciego": 80,
            "kappa_es_empresa": 0.89,
            "etiquetas_corregidas": 9,
        },
        "publicado": {"empresas": 3909, "puestos": 9194, "validado": False},
        "clasificador": {
            "tipo": "reglas deterministas, sin LLM",
            "kappa_test": 0.870, "acierto_test": 0.947,
            "error_por_post": 0.053,
            "techo_humano": 0.89,
        },
        "vocabulario_ia": {
            "que_mide": "fraccion de posts de empresa cuyo texto menciona vocabulario de IA",
            "que_NO_mide": "si el puesto pide IA. Ese juicio no paso su techo humano (kappa 0,38)",
            "acuerdo_con_juicio_humano": ACUERDO_RX_HUMANO,
            "validado": False,
        },
        "tendencia_ia": {
            "pendiente_observada_pts_mes": round(b_obs * 100, 2) if b_obs else None,
            "t_observado": round(t_obs, 2) if t_obs else None,
            "pendiente_peor_caso_pts_mes": round(b_piso * 100, 2) if b_piso else None,
            "t_peor_caso": round(t_piso, 2) if t_piso else None,
            "t_critico_95": 2.23,
            "confusor": "los hilos nuevos descartan mas posts (de ~7% a ~17%). "
                        "Un post borrado no tiene texto, asi que no se puede "
                        "testear si era 'de IA'. El peor caso supone que NINGUN "
                        "post borrado mencionaba IA.",
            "conclusion": ("la tendencia NO sobrevive al peor caso: no se puede "
                           "afirmar que el vocabulario de IA haya subido")
                          if (t_piso or 0) < 2.23 else
                          "la tendencia sobrevive al peor caso",
        },
        "salud": salud,
        "corridas": corridas,
        "meses": meses,
    }

    os.makedirs(PANEL, exist_ok=True)
    ruta = os.path.join(PANEL, "datos.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)

    # ------------------------------- veredicto contra lo pre-registrado -----
    suma = sum(m["empresas"] for m in meses)
    print(f"\nescrito {ruta}")
    print("=" * 70)
    print(f"  {'mes':<9}{'posts':>7}{'empr':>6}{'meta':>6}{'tasa':>7}{'dup':>5}{'IA':>7}  deriva")
    for m in meses:
        print(f"  {m['mes']:<9}{m['posts_con_texto']:>7}{m['empresas']:>6}{m['meta']:>6}"
              f"{m['tasa_meta']:>7.1%}{m['dup_dentro_del_mes']:>5}{m['share_ia']:>7.1%}"
              f"  {'<-- SI' if m['deriva'] else ''}"
              f"{'  (abierto)' if m['abierto'] else ''}")
    print("=" * 70)
    print(f"  suma de empresas por mes   {suma:,}", end="   ")
    print("CIERRA contra el censo 3.903" if suma == 3903
          else f"<-- NO CIERRA (censo 3.903, diferencia {suma-3903:+})")
    rango = [m["empresas"] for m in meses if not m["abierto"]]
    print(f"  empresas por mes           {min(rango)}-{max(rango)}", end="   ")
    print("dentro de 230-330" if 230 <= min(rango) and max(rango) <= 330 else "<-- FUERA de 230-330")
    dup = sum(m["dup_dentro_del_mes"] for m in meses) / len(emp_todos)
    print(f"  duplicados DENTRO del mes  {dup:.2%}", end="   ")
    print("dentro de <2%" if dup < 0.02 else "<-- FUERA")
    ia = sum(m["menciona_ia"] for m in meses) / len(emp_todos)
    print(f"  menciona vocabulario IA    {ia:.1%}", end="   ")
    print("dentro de 45-65%" if 0.45 <= ia <= 0.65 else "<-- FUERA de 45-65%")
    n_der = sum(1 for m in meses if m["deriva"])
    print(f"  meses marcados por deriva  {n_der} de {len(meses)}", end="   ")
    print("<-- REVISAR la banda" if n_der in (0, len(meses)) and len(meses) > 3 else "OK")
    print(f"\n  repeticion entre meses     {salida['corpus']['repeticion']:.1%}"
          f"  ({len(emp_todos):,} posts -> {distintos:,} empresas distintas)")
    print("\n  TENDENCIA DEL VOCABULARIO DE IA")
    print(f"    observada    {b_obs*100:+.2f} pts/mes  t={t_obs:.2f}  "
          f"{'significativa' if abs(t_obs) > 2.23 else 'no significativa'}")
    print(f"    peor caso    {b_piso*100:+.2f} pts/mes  t={t_piso:.2f}  "
          f"{'significativa' if abs(t_piso) > 2.23 else 'NO significativa'}")
    print(f"    -> {salida['tendencia_ia']['conclusion']}")
    print("\n  SALUD DE LA CORRIDA")
    for k in ("hilo_del_mes_encontrado", "posts_fuera_de_banda", "clasificacion_degenerada"):
        print(f"    {k:<28} {salud[k]}")

    # --estricto: devuelve != 0 si algo esta roto. El cron lo corre DESPUES de
    # commitear, para que el dato quede guardado igual y la falla se vea como
    # una corrida en rojo en vez de perderse en el log.
    roto = []
    if not salud["hilo_del_mes_encontrado"]:
        roto.append("no se encontro el hilo del ultimo mes")
    if salud["posts_fuera_de_banda"]:
        roto.append("el volumen de posts del ultimo mes esta fuera de banda")
    if salud["clasificacion_degenerada"]:
        roto.append("la clasificacion es degenerada (todo empresa o todo meta)")
    if suma != sum(m["empresas"] for m in meses):
        roto.append("la suma por mes no cierra")
    if "--estricto" in sys.argv and roto:
        print("\n! FALLA:", "; ".join(roto))
        return 1
    if roto:
        print("\n! avisos:", "; ".join(roto))
    return 0


if __name__ == "__main__":
    sys.exit(main())

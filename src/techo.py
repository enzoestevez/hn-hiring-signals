"""Mide el techo humano y la tasa de meta-comentarios reponderada.

Uso:
    python src/techo.py              # con lo que haya etiquetado
    python src/techo.py --bootstrap 20000

Lee data/etiquetas-p1.jsonl, data/etiquetas-p2.jsonl y data/muestra.jsonl.
Deja reports/techo.json.

Funciona con la pasada 1 sola: da la tasa de meta y las tasas de "no dice",
y avisa que el techo necesita la pasada 2. No hay que esperar a terminar todo
para ver si el numero va por donde deberia.

================================================================================
ERROR EN MI PROPIA PREDICCION, DETECTADO ANTES DE TENER LOS DATOS

En PREDICCIONES.md registre "acuerdo entre pasadas: es_empresa >= 97%" usando
**acuerdo crudo**, que es el estadistico equivocado para una clase rara.

Si los meta-comentarios son el 3% del corpus, alguien que contesta "es empresa"
SIEMPRE, sin leer nada, saca 97% de acuerdo consigo mismo. Mi umbral se cumple
con un etiquetador que no mira la pantalla. Un numero que una estrategia
degenerada alcanza no mide nada.

El estadistico correcto es **kappa de Cohen**, que descuenta el acuerdo
esperable por azar:

    kappa = (Po - Pe) / (1 - Pe)

donde Po es el acuerdo observado y Pe el esperado si las dos pasadas fueran
independientes con las mismas marginales. kappa = 0 significa "igual que tirar
una moneda cargada"; kappa = 1, acuerdo perfecto.

Se reportan LOS DOS: el crudo porque fue lo que registre y la prediccion se
evalua como se registro, y kappa porque es el que decide. Y queda escrito que
el umbral registrado estaba mal elegido.

Convencion habitual (Landis y Koch): < 0,20 pobre · 0,21-0,40 debil ·
0,41-0,60 moderado · 0,61-0,80 bueno · > 0,80 muy bueno. Es convencion, no ley.

================================================================================
EL INTERVALO SE CALCULA POR BOOTSTRAP, NO CON LA FORMULA NORMAL

La tasa de meta se estima reponderando por estrato:

    tasa = suma(peso_i * es_meta_i) / suma(peso_i)

El intervalo de confianza normal (+-1,96 EE) supone n grande y p no muy chica.
Aca el estrato limpio puede tener 1 o 2 meta-comentarios sobre 120, y con esos
numeros la aproximacion normal da intervalos que incluyen valores negativos.
Un intervalo que contiene "menos 0,4% de meta-comentarios" delata que la
formula no aplica.

Asi que se remuestrea DENTRO de cada estrato con reemplazo, se recalcula la
estimacion ponderada miles de veces, y el intervalo son los percentiles 2,5 y
97,5 de esa distribucion. No supone nada sobre la forma.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics as st
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bajar import DATOS, RAIZ  # noqa: E402

REPORTES = RAIZ / "reports"

CAMPOS = ["es_empresa", "pide_ia", "n_puestos", "remoto", "seniority", "visa"]

# Umbrales registrados en docs/PREDICCIONES.md, en ACUERDO CRUDO.
# Se evaluan como se registraron, aunque el estadistico este mal elegido.
PRED_ACUERDO = {"es_empresa": 0.97, "visa": 0.92, "pide_ia": 0.90,
                "remoto": 0.88, "n_puestos": 0.80, "seniority": 0.78}
PRED_BRECHA_ESTRATO = 5.0    # puntos: sospechoso al menos 5 mas bajo que limpio
PRED_META = (0.02, 0.05)     # tasa de meta reponderada
PRED_P_LIMPIO = 0.005        # meta que se le escapan al filtro
PRED_SEG = 45.0              # mediana de segundos por post
EE_OBJETIVO = 0.0065         # registrado para separar 3% de 5%. Ver nota abajo.
PRED_PUBLICADO = 3909        # empresas que reporta el analisis publicado
N_TEXTO_13M = 4054           # comentarios con texto en los 13 hilos


def cargar(ruta: Path) -> dict[int, dict]:
    if not ruta.exists():
        return {}
    return {f["id"]: f for f in
            (json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip())}


def kappa(pares: list[tuple]) -> float | None:
    """Kappa de Cohen sobre pares (etiqueta_pasada1, etiqueta_pasada2)."""
    n = len(pares)
    if n == 0:
        return None
    po = sum(1 for a, b in pares if a == b) / n
    c1, c2 = Counter(a for a, _ in pares), Counter(b for _, b in pares)
    pe = sum(c1[k] / n * c2[k] / n for k in set(c1) | set(c2))
    if pe >= 1.0:
        # Las dos pasadas usaron un solo valor: kappa indefinido, y es un dato.
        return None
    return (po - pe) / (1 - pe)


def acuerdo(pares: list[tuple]) -> float | None:
    return sum(1 for a, b in pares if a == b) / len(pares) if pares else None


def etiqueta(s: str | None) -> str:
    if s is None:
        return "indefinido"
    return ("muy bueno" if s > 0.80 else "bueno" if s > 0.60 else
            "moderado" if s > 0.40 else "débil" if s > 0.20 else "pobre")


def main() -> None:
    ap = argparse.ArgumentParser(description="Techo humano y tasa de meta reponderada.")
    ap.add_argument("--bootstrap", type=int, default=20000)
    args = ap.parse_args()

    muestra = {f["id"]: f for f in
               (json.loads(l) for l in (DATOS / "muestra.jsonl")
                .read_text(encoding="utf-8").splitlines() if l.strip())}
    p1 = cargar(DATOS / "etiquetas-p1.jsonl")
    p2 = cargar(DATOS / "etiquetas-p2.jsonl")
    dobles = {i for i, f in muestra.items() if f.get("doble")}

    print(f"muestra        {len(muestra)} posts")
    print(f"pasada 1       {len(p1)} etiquetados ({len(p1)/len(muestra):.0%})")
    print(f"pasada 2       {len(p2)} de {len(dobles)} del doble ciego")
    if not p1:
        sys.exit("\nNo hay nada etiquetado todavía. Corré: python src/etiquetar.py")

    salida: dict = {"n_p1": len(p1), "n_p2": len(p2), "n_muestra": len(muestra)}

    # --------------------------------------------- tiempo humano de la tarea
    seg = [f["segundos"] for f in p1.values() if f.get("segundos")]
    if seg:
        med = st.median(seg)
        print(f"\n{'='*72}\nCOSTO HUMANO\n{'='*72}\n")
        print(f"  mediana        {med:>7.0f} s/post   predicho <= {PRED_SEG:.0f}   "
              f"{'OK' if med <= PRED_SEG else '<-- FUERA'}")
        print(f"  media          {st.mean(seg):>7.0f} s        total "
              f"{sum(seg)/3600:.1f} h en {len(seg)} posts")
        if len(seg) >= 40:
            # Fatiga: ¿el ultimo quinto va mas rapido que el primero? Si si,
            # puede ser practica (bueno) o apuro (malo). Se mira junto al acuerdo.
            q = len(seg) // 5
            print(f"  primeros {q}    {st.median(seg[:q]):>7.0f} s"
                  f"      últimos {q}: {st.median(seg[-q:]):.0f} s")
        salida["segundos_mediana"] = med

    # ------------------------------------- tasa de meta y "no dice", reponderadas
    print(f"\n{'='*72}\nTASA DE META-COMENTARIOS (reponderada por estrato)\n{'='*72}\n")

    diseno = json.loads((REPORTES / "muestra-diseno.json").read_text(encoding="utf-8"))
    N_h = {d["estrato"]: d["N_corpus"] for d in diseno["estratos"]}

    por_estrato: dict[str, list[dict]] = {}
    for i, f in p1.items():
        por_estrato.setdefault(muestra[i]["estrato"], []).append(
            {"meta": f["es_empresa"] is False})

    # PESO EFECTIVO = N_h / (los que se etiquetaron REALMENTE en ese estrato),
    # no el peso planificado que guarda muestra.jsonl. Con la muestra a medio
    # etiquetar los dos difieren, y el planificado sesga: le da a cada estrato
    # un peso proporcional a N_h * fraccion_etiquetada en vez de a N_h. Al
    # completarse coinciden, asi que el efectivo es correcto siempre.
    for e, filas in por_estrato.items():
        w = N_h[e] / len(filas)
        for x in filas:
            x["peso"] = w

    print(f"  {'estrato':12}{'etiq':>6}{'de':>5}{'N corpus':>10}{'meta':>6}"
          f"{'cruda':>8}{'peso efec.':>12}")
    for e, filas in sorted(por_estrato.items()):
        m = sum(1 for x in filas if x["meta"])
        n_plan = sum(1 for f in muestra.values() if f["estrato"] == e)
        print(f"  {e:12}{len(filas):>6}{n_plan:>5}{N_h[e]:>10,}{m:>6}"
              f"{m/len(filas):>7.1%}{filas[0]['peso']:>12.2f}")
    if len(p1) < len(muestra):
        print(f"\n  MUESTRA INCOMPLETA ({len(p1)}/{len(muestra)}). La estimación es")
        print("  válida —los etiquetados son un subconjunto aleatorio de cada")
        print("  estrato, porque el orden se mezcló al armar la muestra— pero el")
        print("  intervalo es más ancho de lo que va a ser al terminar.")

    num = sum(x["peso"] for filas in por_estrato.values() for x in filas if x["meta"])
    den = sum(x["peso"] for filas in por_estrato.values() for x in filas)
    tasa = num / den if den else 0.0

    # bootstrap DENTRO de cada estrato: no supone normalidad ni n grande
    rng = random.Random(20261023)
    reps = []
    for _ in range(args.bootstrap):
        n_, d_ = 0.0, 0.0
        for filas in por_estrato.values():
            k = len(filas)
            for _ in range(k):
                x = filas[rng.randrange(k)]
                d_ += x["peso"]
                if x["meta"]:
                    n_ += x["peso"]
        reps.append(n_ / d_ if d_ else 0.0)
    reps.sort()
    lo, hi = reps[int(0.025 * len(reps))], reps[int(0.975 * len(reps))]

    crudo = sum(1 for filas in por_estrato.values() for x in filas if x["meta"])
    n_tot = sum(len(f) for f in por_estrato.values())
    print(f"\n  tasa CRUDA sobre la muestra      {crudo/n_tot:>7.2%}  <- NO es la del corpus")
    print(f"  tasa REPONDERADA                 {tasa:>7.2%}")
    print(f"  IC 95% por bootstrap             [{lo:.2%}, {hi:.2%}]")
    print(f"  predicho                         {PRED_META[0]:.0%}–{PRED_META[1]:.0%}   "
          f"{'dentro' if PRED_META[0] <= tasa <= PRED_META[1] else '<-- FUERA'}")
    salida.update({"tasa_meta": tasa, "ic95": [lo, hi]})

    # p_limpio: lo que se le escapa al filtro. Decide el tamano de la fase 2.
    limpio = por_estrato.get("limpio", [])
    if limpio:
        p_l = sum(1 for x in limpio if x["meta"]) / len(limpio)
        print(f"\n  p_limpio (meta en el estrato limpio)  {p_l:>7.2%}   "
              f"predicho <= {PRED_P_LIMPIO:.1%}   "
              f"{'OK' if p_l <= PRED_P_LIMPIO else '<-- FUERA: el filtro deja pasar más de lo esperado'}")
        salida["p_limpio"] = p_l

    # ------------------------------------------- la regla de decision de la etapa 1b
    # ------------------------------------------------------------------
    # LA REGLA REGISTRADA TENIA LAS DOS RAMAS INVERTIDAS. Correccion del
    # 2026-10-25, derivada de nuevo en vez de copiada.
    #
    # Con 4.054 comentarios con texto en los 13 hilos:
    #     empresas estimadas = 4.054 * (1 - tasa_meta)
    # y el analisis publicado reporta 3.909 empresas.
    #
    #   tasa_meta BAJA (1%)  -> empresas ~4.013 > 3.909
    #                        -> el publicado quedo CORTO: perdio posts.
    #   tasa_meta ALTA (7%)  -> empresas ~3.770 < 3.909
    #                        -> el publicado quedo LARGO: conto no-empresas.
    #
    # Lo registre al reves: le puse "perdida silenciosa" a la rama de tasa
    # alta, cuando perder posts da un conteo MENOR, no mayor. Si hubiera
    # seguido la regla escrita habria reportado la conclusion opuesta.
    # Una regla pre-registrada hay que re-derivarla, no obedecerla.
    # ------------------------------------------------------------------
    emp_lo, emp_pt, emp_hi = (N_TEXTO_13M * (1 - x) for x in (hi, tasa, lo))
    print(f"\n  CONTRA EL ANÁLISIS PUBLICADO, en la dirección correcta:")
    print(f"    comentarios con texto, 13 hilos        {N_TEXTO_13M:>8,}")
    print(f"    empresas estimadas = texto × (1−tasa)  {emp_pt:>8,.0f}"
          f"   [{emp_lo:,.0f}, {emp_hi:,.0f}]")
    print(f"    el análisis publicado reporta          {PRED_PUBLICADO:>8,}")
    dif = emp_pt - PRED_PUBLICADO
    print(f"    diferencia                             {dif:>+8,.0f}")
    print()
    if emp_hi < PRED_PUBLICADO:
        print("    PUBLICADO POR ENCIMA de nuestro intervalo -> ese análisis")
        print("    CONTÓ COMO EMPRESAS comentarios que no lo son. Es el modo de")
        print("    falla esperable de una extracción con LLM sin validar: si le")
        print("    pedís empresa y puesto de un comentario que no es una oferta,")
        print("    el modelo igual devuelve campos. No deja de responder.")
    elif emp_lo > PRED_PUBLICADO:
        print("    PUBLICADO POR DEBAJO de nuestro intervalo -> perdió posts de")
        print("    empresa en silencio, probablemente los que no pudo parsear.")
    else:
        print(f"    El intervalo [{emp_lo:,.0f}, {emp_hi:,.0f}] CONTIENE "
              f"{PRED_PUBLICADO:,}:")
        print("    con estos datos el número publicado es compatible con el")
        print("    nuestro y no se puede afirmar que sobre ni que falte.")
    if len(p1) < len(muestra):
        print("\n    (muestra incompleta: el intervalo se va a angostar)")

    # ------------------------------------------------------------------
    # CUANTOS ETIQUETADOS FALTAN PARA DECIDIR
    #
    # El EE_OBJETIVO = 0,65% lo registre para separar "tasa 3%" de "tasa 5%".
    # Pero esa no es la decision que importa. La decision es:
    #
    #     ¿el 3.909 publicado queda FUERA de nuestro intervalo?
    #
    # que equivale a preguntar si la tasa supera
    #     u = (4.054 - 3.909) / 4.054 = 3,58%
    #
    # Con la tasa en ~6,6%, lejos de 3,58%, alcanza mucho menos precision que
    # la que registre. Apuntar al EE_OBJETIVO original costaria ~700 etiquetas
    # del estrato limpio (~7 horas) para contestar algo que no se pregunta.
    # ------------------------------------------------------------------
    umbral = (N_TEXTO_13M - PRED_PUBLICADO) / N_TEXTO_13M
    limpios = por_estrato.get("limpio") or []
    p_l = (sum(1 for x in limpios if x["meta"]) / len(limpios)) if limpios else None
    print("\n  ¿CUÁNTO FALTA PARA DECIDIR?\n")
    print(f"    la tasa tiene que superar {umbral:.2%} para que {PRED_PUBLICADO:,} quede")
    print("    por encima de nuestro intervalo (o sea: que el publicado sobrecontó)")
    print(f"    tasa {tasa:.2%} · borde inferior {lo:.2%} · "
          f"{'YA DECIDE' if lo > umbral else 'todavía no decide'}")
    if p_l and lo <= umbral < tasa:
        N_l, n_ya = N_h["limpio"], len(limpios)
        objetivo = (tasa - umbral) / 1.96
        for n in range(n_ya, N_l + 1, 5):
            ee = (N_l / N_TEXTO_13M) * ((p_l * (1 - p_l) / n) * (1 - n / N_l)) ** 0.5
            if ee <= objetivo:
                seg = salida.get("segundos_mediana", 40)
                print(f"\n    con p_limpio MEDIDO en {p_l:.2%}, hacen falta ~{n} del")
                print(f"    estrato limpio: {n - n_ya} más que los {n_ya} de ahora,")
                print(f"    unos {(n - n_ya) * seg / 60:.0f} minutos.")
                print(f"    (el EE_OBJETIVO original de {EE_OBJETIVO:.2%} pediría ~700")
                print("    y contestaría una pregunta que no se hace)")
                break
        else:
            print("\n    ni el estrato limpio entero alcanza: habría que ampliar la")
            print("    muestra del corpus, no solo etiquetar más.")

    # ---------------------------------------- "no dice": limites del corpus
    print(f"\n{'='*72}\n\"NO DICE\": QUÉ CAMPOS NO EXISTEN EN ESTE CORPUS\n{'='*72}\n")
    empresas = [(i, f) for i, f in p1.items() if f.get("es_empresa")]
    print(f"  sobre {len(empresas)} posts etiquetados como empresa, reponderado:\n")
    for campo in ("remoto", "seniority", "visa"):
        d = sum(muestra[i]["peso"] for i, f in empresas if f.get(campo) is None)
        t = sum(muestra[i]["peso"] for i, _ in empresas)
        frac = d / t if t else 0
        aviso = "  <-- por encima del 95%: ese campo sale de la etapa 3" if frac > 0.95 else ""
        print(f"    {campo:12}{frac:>8.1%} no dice{aviso}")
    print("\n  Un campo que la fuente no contiene es un límite del CORPUS, no del")
    print("  modelo. Medir precisión de extracción ahí no significa nada.")

    # -------------------------------------------------- el techo humano
    comunes = sorted(set(p1) & set(p2))
    if not comunes:
        print(f"\n{'='*72}\n  El TECHO necesita la pasada 2. Corré, después de un rato:")
        print(f"    python src/etiquetar.py --pasada 2\n{'='*72}")
        REPORTES.mkdir(exist_ok=True)
        (REPORTES / "techo.json").write_text(
            json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    print(f"\n{'='*72}\nTECHO HUMANO sobre {len(comunes)} posts etiquetados dos veces\n{'='*72}\n")
    # DOS medidas por campo, y la distincion importa:
    #
    #  - TODOS: incluye los pares donde las dos pasadas dijeron "no dice".
    #    Decir dos veces "el post no lo declara" ES consistencia, y en la
    #    etapa 3 responder correctamente "no declarado" va a ser una prediccion
    #    acertada, no una abstencion. Esta es la medida que corresponde al techo.
    #
    #  - INFORMATIVOS: solo los pares donde al menos una pasada dio un valor.
    #    Mide el criterio cuando hay algo que decidir. En un campo donde el 85%
    #    es "no dice", la primera medida se infla con los faciles y esta muestra
    #    lo dificil. Van las dos: una sola de las dos enganaria.
    print(f"  {'campo':12}{'n':>5}{'todos':>8}{'pred':>7}{'':4}"
          f"{'kappa':>7}{'':2}{'n_inf':>6}{'inform.':>9}  calidad")
    techo = {}
    for campo in CAMPOS:
        todos = [(p1[i].get(campo), p2[i].get(campo)) for i in comunes
                 if campo == "es_empresa" or (p1[i].get("es_empresa")
                                              or p2[i].get("es_empresa"))]
        inf = [(a, b) for a, b in todos if not (a is None and b is None)]
        a, k = acuerdo(todos), kappa(todos)
        a_inf = acuerdo(inf)
        pred = PRED_ACUERDO[campo]
        marca = "OK" if a is not None and a >= pred else "<--"
        print(f"  {campo:12}{len(todos):>5}{a:>8.1%}{pred:>7.0%}{marca:>4}"
              f"{(f'{k:.2f}' if k is not None else '  n/d'):>7}{'':2}{len(inf):>6}"
              f"{(f'{a_inf:.1%}' if a_inf is not None else 'n/d'):>9}  {etiqueta(k)}")
        techo[campo] = {"n": len(todos), "acuerdo": a, "kappa": k,
                        "n_informativos": len(inf), "acuerdo_informativos": a_inf}
    salida["techo"] = techo
    print("\n  `todos` incluye los pares donde las dos veces dijiste \"no dice\":")
    print("  eso es consistencia, y en la etapa 3 acertar \"no declarado\" cuenta")
    print("  como acierto. `inform.` se restringe a los casos donde hubo algo que")
    print("  decidir, y es el número honesto para un campo lleno de \"no dice\".")

    # Firma de falla registrada: un 100% no es excelencia, es sospecha.
    perfectos = [c for c, v in techo.items() if v["acuerdo"] == 1.0]
    if perfectos:
        print(f"\n  ! ACUERDO DEL 100% en {perfectos}.")
        print("    Es una firma de falla registrada, no un buen resultado. O el")
        print("    campo es trivial, o la pasada 2 no fue ciega (mismo orden, o")
        print("    se vio la etiqueta anterior). Revisar antes de reportarlo.")

    bajo_kappa = [c for c, v in techo.items()
                  if v["kappa"] is not None and v["kappa"] < 0.6]
    if bajo_kappa:
        print(f"\n  Campos con kappa por debajo de 0,60: {bajo_kappa}")
        print("    No se usan como objetivo de precisión en la etapa 3. No se le")
        print("    puede exigir a un modelo más consistencia que la de la")
        print("    referencia contra la que se lo mide.")

    # el techo partido por estrato: la leccion de p01
    print(f"\n  -- el techo partido por estrato (la lección de p01) --\n")
    print(f"  {'campo':12}{'sospechoso':>13}{'limpio':>9}{'brecha':>9}")
    for campo in CAMPOS:
        fila = {}
        for e in ("sospechoso", "limpio"):
            pares = [(p1[i].get(campo), p2[i].get(campo)) for i in comunes
                     if muestra[i]["estrato"] == e
                     and (campo == "es_empresa" or p1[i].get("es_empresa")
                          or p2[i].get("es_empresa"))]
            fila[e] = acuerdo(pares)
        if fila["sospechoso"] is None or fila["limpio"] is None:
            continue
        br = (fila["limpio"] - fila["sospechoso"]) * 100
        print(f"  {campo:12}{fila['sospechoso']:>12.1%}{fila['limpio']:>9.1%}{br:>+8.1f}")
    print(f"\n  Predicción registrada: el sospechoso al menos {PRED_BRECHA_ESTRATO:.0f} puntos")
    print("  más bajo. En p01 el techo se partió 98,7% contra 72,7% por formato,")
    print("  y el promedio global era una mentira cómoda.")

    print(f"\n{'='*72}\nSOBRE EL ESTADÍSTICO QUE REGISTRÉ MAL\n{'='*72}\n")
    print("  Registré los umbrales en ACUERDO CRUDO, que para una clase rara es")
    print("  el estadístico equivocado: si los meta son el 3%, contestar")
    print("  \"es empresa\" siempre, sin leer, da 97% de acuerdo. Mi umbral de")
    print("  es_empresa se cumple con un etiquetador que no mira la pantalla.")
    print("  Por eso se reporta kappa al lado, y por eso kappa es el que decide")
    print("  qué campos entran en la etapa 3.")

    REPORTES.mkdir(exist_ok=True)
    (REPORTES / "techo.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nEscrito reports/techo.json")


if __name__ == "__main__":
    main()

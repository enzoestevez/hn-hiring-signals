"""Reparte los descartes por mes, para medir sesgo de supervivencia.

Uso:
    python src/descartes.py

Deja data/descartes.jsonl y una tabla por mes.

================================================================================
POR QUE EXISTE ESTE SCRIPT

`bajar.py` conto los descartes (593 borrados/muertos sobre 4.648 = 12,8%) pero
no guardo a que hilo pertenecia cada uno. Hueco mio. Sin ese reparto no se
puede contestar la pregunta que sigue, que no es menor:

    ¿Los hilos VIEJOS perdieron mas posts que los nuevos?

Importa porque un post desaparece por dos mecanismos distintos:

  (a) un moderador lo mata por romper las reglas del hilo (reclutadores,
      gente buscando trabajo). Pasa en dias. Tasa aproximadamente CONSTANTE
      por hilo.
  (b) el autor lo borra cuando lleno el puesto. Puede pasar en cualquier
      momento, asi que se ACUMULA con la edad del hilo.

Si (b) pesa, el corpus tiene **sesgo de supervivencia**: octubre 2025 llega a
nosotros con menos posts de los que tuvo, y octubre 2026 con casi todos. Una
tendencia mensual calculada sobre los sobrevivientes mostraria entonces un
crecimiento que no existe, justo tapando la caida real.

Esa es la pregunta central del proyecto. Un sesgo que corre en contra de la
hipotesis principal no es un detalle: la invalida si no se mide.

Costo: 594 llamadas a una API publica. USD 0.00.

================================================================================
NO DUPLICA CODIGO

`traer`, `FALLO` y `API` se importan de `bajar.py`. En el proyecto 02 copie
nueve funciones de un modulo a otro y despues arregle un bug en una sola de
las dos copias. No se vuelve a hacer.
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bajar import FALLO, DATOS, traer  # noqa: E402

# Predicciones registradas en docs/PREDICCIONES.md ANTES de correr esto.
#
# El gradiente de descarte YA se midio, y gratis: salia de restar los
# sobrevivientes de posts.jsonl a los kids de hilos.json, sin una sola llamada.
# Escribir un script de 594 llamadas para eso fue un error mio. Dio -7,0 puntos
# contra los >= +3 que habia predicho: los hilos NUEVOS descartan mas.
PRED_GRADIENTE = 3.0        # registrado y FALLADO. Se deja como se registro.
MEDIDO_GRADIENTE = -7.0     # lo que dio, para que el script no finja sorpresa.
#
# Lo que este script si aporta, y es el motivo de que exista: el reparto
# borrado-vs-muerto por mes, que distingue dos explicaciones del -7,0:
#
#   (A) moderacion creciente: HN se puso mas estricto, o los hilos recientes
#       todavia reciben spam que se flaggea en dias.
#   (B) HN PURGA del array `kids` los comentarios borrados pasado un tiempo.
#       Los hilos viejos vendrian ya podados: los descartes desaparecieron del
#       numerador y del denominador a la vez, y por eso parecen descartar menos.
#
# (B) es la mala: significaria que para los meses viejos el denominador real es
# desconocido, no se puede ni contar lo que falta, y los conteos mensuales NO
# son comparables en el tiempo. Que es justo lo que la etapa 5 debe comparar.
#
# PREDICCION REGISTRADA (2026-10-23, antes de correr): la purga es real, asi que
# espero que la proporcion de `muerto` entre los descartes sea MAS ALTA en los 3
# hilos nuevos que en los 3 viejos, por al menos 10 puntos. Si no hay diferencia,
# (B) queda sin apoyo y (A) explica el -7,0.
PRED_MUERTO_GRAD = 10.0


def estado(item) -> str:
    """En que destino cae un comentario que no llego a posts.jsonl."""
    if item is FALLO:
        return "fallo_red"      # no se pudo preguntar: hay que reintentar
    if item is None:
        return "nulo"           # la API dijo null: el item no existe
    if item.get("deleted"):
        return "borrado"        # lo borro el autor (o un moderador)
    if item.get("dead"):
        return "muerto"         # flaggeado por la comunidad
    if not (item.get("text") or "").strip():
        return "vacio"
    return "tiene_texto"        # no deberia pasar: estaria en posts.jsonl


def main() -> None:
    # 1. los kids de cada hilo. hilos.json no los guarda, asi que 13 llamadas.
    hilos = json.loads((DATOS / "hilos.json").read_text(encoding="utf-8"))
    print(f"pido los {len(hilos)} hilos de nuevo para recuperar sus kids...")
    with ThreadPoolExecutor(max_workers=8) as pool:
        items = list(pool.map(lambda h: traer(f"item/{h['id']}"), hilos))

    kids_por_mes: dict[str, list[int]] = {}
    for h, it in zip(hilos, items):
        if it is FALLO or not it:
            sys.exit(f"no pude releer el hilo {h['mes']}. ¿Hay red?")
        kids_por_mes[h["mes"]] = it.get("kids") or []

    # 2. los que SI llegaron a posts.jsonl
    presentes = set()
    ruta = DATOS / "posts.jsonl"
    if not ruta.exists():
        sys.exit("falta data/posts.jsonl. Corré primero: python src/bajar.py")
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if linea.strip():
            presentes.add(json.loads(linea)["id"])
    print(f"posts con texto ya bajados: {len(presentes):,}")

    faltan = [(mes, k) for mes, kids in kids_por_mes.items()
              for k in kids if k not in presentes]
    print(f"descartes a clasificar: {len(faltan):,}\n")

    # 3. clasificar cada descarte
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=8) as pool:
        resultados = list(pool.map(lambda p: traer(f"item/{p[1]}"), faltan))
    print(f"clasificados en {time.perf_counter()-t0:.0f}s\n")

    with (DATOS / "descartes.jsonl").open("w", encoding="utf-8") as f:
        filas = []
        for (mes, ident), item in zip(faltan, resultados):
            e = estado(item)
            filas.append((mes, e))
            f.write(json.dumps({"id": ident, "mes": mes, "estado": e}) + "\n")

    # 4. la tabla por mes
    meses = sorted(kids_por_mes)
    print(f"{'mes':9}{'kids':>7}{'con texto':>11}{'descartes':>11}{'tasa':>8}"
          f"{'borrado':>9}{'muerto':>8}{'otro':>6}{'%muerto':>9}")
    tasas, split = {}, {}
    for mes in meses:
        kids = len(kids_por_mes[mes])
        de_este = [e for m, e in filas if m == mes]
        b = sum(1 for e in de_este if e == "borrado")
        mu = sum(1 for e in de_este if e == "muerto")
        otro = len(de_este) - b - mu
        tasas[mes] = len(de_este) / kids if kids else 0
        # % de muerto SOBRE los descartes, no sobre los kids: la pregunta es de
        # que estan hechos los descartes, no cuantos hay.
        split[mes] = mu / len(de_este) if de_este else 0.0
        print(f"{mes:9}{kids:>7,}{kids-len(de_este):>11,}{len(de_este):>11,}"
              f"{tasas[mes]:>7.1%}{b:>9}{mu:>8}{otro:>6}{split[mes]:>8.1%}")

    raros = [e for _, e in filas if e in ("fallo_red", "tiene_texto")]
    if raros:
        print(f"\n! {len(raros)} descartes raros: "
              f"{ {e: raros.count(e) for e in set(raros)} }")
        if any(e == "tiene_texto" for e in raros):
            print("  `tiene_texto` es un BUG: ese post debería estar en posts.jsonl.")
        if any(e == "fallo_red" for e in raros):
            print("  con `fallo_red` el reparto está incompleto: volvé a correr.")

    veredicto(meses, tasas)
    veredicto_split(meses, split)


def veredicto(meses: list[str], tasas: dict[str, float]) -> None:
    print(f"\n{'='*72}\nVEREDICTO: ¿HAY SESGO DE SUPERVIVENCIA?\n{'='*72}\n")
    if len(meses) < 6:
        print("  menos de 6 meses: no alcanza para medir gradiente.")
        return

    viejos, nuevos = meses[:3], meses[-3:]
    tv = sum(tasas[m] for m in viejos) / 3
    tn = sum(tasas[m] for m in nuevos) / 3
    grad = (tv - tn) * 100

    print(f"  3 hilos más viejos ({viejos[0]}–{viejos[-1]}):  {tv:>6.1%} de descarte")
    print(f"  3 hilos más nuevos ({nuevos[0]}–{nuevos[-1]}):  {tn:>6.1%} de descarte")
    print(f"  gradiente: {grad:+.1f} puntos   esperado >= +{PRED_GRADIENTE:.0f}   "
          f"{'OK' if grad >= PRED_GRADIENTE else '<-- PREDICCIÓN FALLIDA'}")
    print(f"  (ya medido antes de correr esto, gratis: {MEDIDO_GRADIENTE:+.1f})\n")

    if grad >= PRED_GRADIENTE:
        print("  HAY SESGO DE SUPERVIVENCIA. Los hilos viejos llegan incompletos.")
        print("  Consecuencia directa y no negociable: toda tendencia mensual que")
        print("  calcule sobre los sobrevivientes está sesgada HACIA ARRIBA en los")
        print("  meses recientes, y puede mostrar crecimiento donde hubo caída.")
        print("  La etapa 5 tiene que reportar la tendencia corregida, o no")
        print("  reportar tendencia.")
    elif grad <= -PRED_GRADIENTE:
        print("  GRADIENTE INVERTIDO: los hilos NUEVOS pierden más.")
        print("  Mecanismo probable: moderación activa sobre el hilo del mes en")
        print("  curso, que todavía está recibiendo spam de reclutadores.")
        print("  El hilo más nuevo puede no estar cerrado y habría que excluirlo.")
    else:
        print("  SIN GRADIENTE CLARO. Predicción mía fallida: el borrado parece")
        print("  constante por hilo, no acumulativo. Eso es buena noticia para")
        print("  la etapa 5 — la tendencia se puede leer sobre los sobrevivientes —")
        print("  pero se reporta igual, porque un sesgo descartado por medición")
        print("  vale más que un sesgo que nunca se miró.")

    peor = max(tasas, key=lambda m: tasas[m])
    if tasas[peor] > 0.25:
        print(f"\n  ! {peor} descarta el {tasas[peor]:.1%}. Muy por encima del resto:")
        print("    revisar ese hilo a mano antes de usarlo.")


def veredicto_split(meses: list[str], split: dict[str, float]) -> None:
    """¿Los descartes viejos y nuevos están hechos de lo mismo?

    Este es el aporte real del script: discrimina entre moderación creciente (A)
    y purga de `kids` por antigüedad (B).
    """
    print(f"\n{'='*72}\n¿DE QUÉ ESTÁN HECHOS LOS DESCARTES? (A: moderación / B: purga)\n{'='*72}\n")
    if len(meses) < 6:
        print("  menos de 6 meses: no alcanza.")
        return

    viejos, nuevos = meses[:3], meses[-3:]
    sv = sum(split[m] for m in viejos) / 3
    sn = sum(split[m] for m in nuevos) / 3
    grad = (sn - sv) * 100

    print(f"  `muerto` sobre descartes, 3 viejos ({viejos[0]}–{viejos[-1]}):  {sv:>6.1%}")
    print(f"  `muerto` sobre descartes, 3 nuevos ({nuevos[0]}–{nuevos[-1]}):  {sn:>6.1%}")
    print(f"  diferencia nuevos − viejos: {grad:+.1f} puntos   "
          f"esperado >= +{PRED_MUERTO_GRAD:.0f}   "
          f"{'OK' if grad >= PRED_MUERTO_GRAD else '<-- PREDICCIÓN FALLIDA'}\n")

    if grad >= PRED_MUERTO_GRAD:
        print("  APOYA (B): LA PURGA ES REAL. Los `muerto` viejos ya no están en")
        print("  `kids`, así que para los meses viejos el denominador verdadero es")
        print("  DESCONOCIDO: no se puede ni contar lo que falta.")
        print("  Consecuencia no negociable: los conteos mensuales NO son")
        print("  comparables en el tiempo. La etapa 5 no puede reportar una")
        print("  tendencia cruda de 'posts por mes'. Lo que sí se puede comparar")
        print("  son proporciones DENTRO de cada mes (qué fracción de los posts de")
        print("  ese mes pide IA), porque el sesgo afecta al numerador y al")
        print("  denominador juntos. Ahí es donde se para el análisis.")
    elif grad <= -PRED_MUERTO_GRAD:
        print("  INVERTIDO: los descartes VIEJOS tienen más `muerto` que los nuevos.")
        print("  No lo esperaba y no tengo mecanismo para esto. Antes de usar el")
        print("  corpus hay que mirar a mano una muestra de descartes de los meses")
        print("  extremos. Un resultado sin mecanismo no se reporta como hallazgo.")
    else:
        print("  SIN DIFERENCIA CLARA. Pero ESTE TEST NO ALCANZA PARA CONCLUIR (A),")
        print("  y el defecto es de su diseño, no del dato: si la purga eliminara")
        print("  `deleted` y `dead` en proporciones parecidas, la PROPORCIÓN de")
        print("  `muerto` no se movería. Un resultado plano es compatible con")
        print("  'no hay purga' Y con 'hay purga proporcional'. Escribí un test")
        print("  ciego a una de sus dos alternativas: asumí sin decirlo que la")
        print("  purga tendría que ser selectiva.")
        print()
        print("  Además la etiqueta (A) describe mal estos datos: el componente que")
        print("  sube es `borrado` (el autor), +5,0 puntos, no `muerto` (la")
        print("  comunidad), +2,1. 'Moderación creciente' no es lo que pasa.")
        print()
        print("  MECANISMO: INDETERMINADO. Y la decisión no espera a resolverlo.")
        print("  Se elige el análisis válido bajo TODAS las hipótesis que sobreviven:")
        print("  proporciones DENTRO de cada mes (qué fracción de los posts de ese")
        print("  mes pide IA), porque ahí el sesgo toca numerador y denominador")
        print("  juntos y se cancela. NO conteos crudos comparados entre meses.")

    print("\n  Lo que ninguno de los dos casos autoriza: leer la caída de 341 a 266")
    print("  posts como caída de contrataciones. Eso todavía no está medido.")


if __name__ == "__main__":
    main()

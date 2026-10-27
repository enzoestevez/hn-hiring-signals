"""Baja el corpus crudo de los hilos "Who is hiring?" de Hacker News.

Uso:
    python src/bajar.py --listar          # encuentra los hilos, sin bajar posts
    python src/bajar.py                   # baja todo (reanudable)
    python src/bajar.py --desde 2025-10 --hasta 2026-10

Deja data/hilos.json y data/posts.jsonl (append-only, una linea por post).

================================================================================
ETAPA 1 DE 7. QUE HACE Y QUE NO HACE

Hace UNA cosa: conseguir el corpus crudo y contarlo. Sin LLM, sin extraccion,
sin analisis, sin conclusiones sobre el mercado laboral.

**Cualquier conclusion sobre contrataciones sacada de esta etapa seria leer datos
sin validar**, que es exactamente el problema que este proyecto vino a arreglar.
La etapa 1 contesta una sola pregunta: ¿tengo el corpus?

================================================================================
POR QUE ESTA FUENTE Y NO OTRA

Los hilos mensuales "Ask HN: Who is hiring?" los publica la cuenta `whoishiring`
y cada comentario de primer nivel es una empresa publicando uno o varios puestos.
Son startups, muchas remotas, mucha IA.

Se baja con la **API oficial y publica de HN** (Firebase, sin clave, sin limite
documentado). No es scraping: es la interfaz que HN publica para esto.

Eso importa y es una decision, no una comodidad: LinkedIn prohibe el scraping en
sus terminos y la sancion tipica es suspender la cuenta — la misma cuenta con la
que uno postula. Un corpus que se consigue rompiendo terminos no se puede
publicar ni defender.

================================================================================
LAS PREDICCIONES ESTAN ESCRITAS ANTES DE CORRER

Ver `docs/PREDICCIONES.md`. Antes de cada etapa queda asentado que numero se
espera, que resultado significaria que el CODIGO miente (distinto de que el mundo
sea asi), y que decision cambia segun el resultado.

Este script imprime el veredicto contra esas predicciones al final. Si el
resultado cae afuera, **eso es un hallazgo y no un accidente.**

================================================================================
UN ANALISIS PUBLICADO EXISTE, Y NO ES NUESTRO CRITERIO DE VALIDACION

Hay un analisis publicado en octubre de 2026 sobre este mismo corpus que reporta
**3.909 posts de empresas y 9.194 puestos en 13 hilos** (oct-2025 a oct-2026), y
declara que uso un LLM para estructurar cada comentario **sin validar la
extraccion** — le preguntaron en los comentarios y no tenia muestra verificada.

Esa cifra es un **punto de comparacion, no un objetivo**. Si nuestro conteo
difiere, la hipotesis por defecto NO es que nos equivocamos: es que hay que
averiguar quien tiene razon, y eso ya es un hallazgo. Nuestro analisis se para
sobre nuestros datos.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

# La consola de Windows usa cp1252 y reventaria con UnicodeEncodeError al
# imprimir un "." raro o una tilde, a mitad de una corrida de 4.000 llamadas.
# Que un script se caiga por como imprime, y no por lo que hace, es inaceptable.
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001  (consolas que no lo soportan)
        pass

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "data"

API = "https://hacker-news.firebaseio.com/v0"
CUENTA = "whoishiring"

# Solo los hilos de empresas contratando. La misma cuenta publica tambien
# "Who wants to be hired?" (candidatos) y "Freelancer? Seeking freelancer?".
# Mezclarlos contaria candidatos como empresas y el numero no significaria nada.
RX_HILO = re.compile(r"who\s+is\s+hiring", re.I)
RX_MES = re.compile(r"\(([A-Za-z]+)\s+(\d{4})\)")

MESES = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], 1)}

# Errores que se arreglan esperando. Misma leccion que el proyecto 01: un error
# que pide esperar mucho NO es transitorio, y reintentarlo rapido solo gasta.
ESPERAS = (1, 3, 8, 20)


class Fallo:
    """La descarga fracaso tras agotar reintentos.

    NO es lo mismo que la API devolviendo `null`. Un null significa "ese item no
    existe" (borrado hace tiempo); un Fallo significa "no se pudo preguntar".
    Si los dos cayeran en el mismo contador, el total no cerraria y no habria
    forma de saber si falta un comentario o falto la red. Esa confusion estaba
    en la primera version de este archivo.
    """
    __slots__ = ()


FALLO = Fallo()


def traer(ruta: str, intentos: int = len(ESPERAS) + 1) -> dict | list | None | Fallo:
    """GET contra la API. Devuelve el item, None si la API dijo null, FALLO si no se pudo."""
    url = f"{API}/{ruta}.json"
    for i in range(intentos):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # 4xx que no sea 429 no mejora esperando: se devuelve enseguida.
            if e.code != 429 and 400 <= e.code < 500:
                print(f"    {ruta}: HTTP {e.code}, no se reintenta", file=sys.stderr)
                return FALLO
        except Exception:  # noqa: BLE001
            pass
        if i < len(ESPERAS):
            time.sleep(ESPERAS[i])
    print(f"    {ruta}: falló tras {intentos} intentos", file=sys.stderr)
    return FALLO


def mes_del_titulo(titulo: str) -> str | None:
    """'Ask HN: Who is hiring? (October 2026)' -> '2026-10'"""
    m = RX_MES.search(titulo or "")
    if not m:
        return None
    mes = MESES.get(m.group(1).lower())
    return f"{m.group(2)}-{mes:02d}" if mes else None


def buscar_hilos(desde: str | None, hasta: str | None) -> list[dict]:
    """Los hilos de 'Who is hiring?' en el rango, mas nuevos primero."""
    usuario = traer(f"user/{CUENTA}")
    if usuario is FALLO or not usuario:
        sys.exit("No pude leer la cuenta whoishiring. ¿Hay red?")
    enviados = usuario.get("submitted") or []
    print(f"la cuenta {CUENTA} tiene {len(enviados):,} envíos · "
          f"reviso los primeros 120 (los más recientes)\n")

    hilos = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for it in pool.map(lambda i: traer(f"item/{i}"), enviados[:120]):
            if it is FALLO or not it or it.get("deleted") or it.get("dead"):
                continue
            titulo = it.get("title") or ""
            if not RX_HILO.search(titulo):
                continue
            mes = mes_del_titulo(titulo)
            if not mes:
                continue
            if desde and mes < desde:
                continue
            if hasta and mes > hasta:
                continue
            hilos.append({
                "id": it["id"], "mes": mes, "titulo": titulo,
                # `descendants` cuenta TODOS los comentarios, incluidas respuestas.
                # Los posts de empresas son solo los de primer nivel (`kids`).
                "comentarios_totales": it.get("descendants"),
                "posts_primer_nivel": len(it.get("kids") or []),
                "kids": it.get("kids") or [],
                "fecha": datetime.fromtimestamp(it.get("time", 0), timezone.utc).date().isoformat(),
            })
    return sorted(hilos, key=lambda h: h["mes"], reverse=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Corpus crudo de 'Who is hiring?' de HN.")
    ap.add_argument("--desde", default="2025-10", help="mes inicial, AAAA-MM")
    ap.add_argument("--hasta", default="2026-10", help="mes final, AAAA-MM")
    ap.add_argument("--listar", action="store_true",
                    help="solo encontrar los hilos (unas 120 llamadas, segundos)")
    args = ap.parse_args()

    DATOS.mkdir(parents=True, exist_ok=True)
    hilos = buscar_hilos(args.desde, args.hasta)
    if not hilos:
        sys.exit("No encontré hilos en ese rango. Revisá --desde/--hasta.")

    print(f"{'mes':9} {'fecha':12} {'posts 1er nivel':>16} {'comentarios':>12}  título")
    for h in hilos:
        print(f"{h['mes']:9} {h['fecha']:12} {h['posts_primer_nivel']:>16,} "
              f"{str(h['comentarios_totales'] or '?'):>12}  {h['titulo'][:52]}")

    esperados = sum(h["posts_primer_nivel"] for h in hilos)
    print(f"\n{len(hilos)} hilos · {esperados:,} posts de primer nivel a bajar")

    (DATOS / "hilos.json").write_text(
        json.dumps([{k: v for k, v in h.items() if k != "kids"} for h in hilos],
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Escrito data/hilos.json")

    if args.listar:
        print("\n(--listar: no bajo los posts)")
        veredicto(hilos, esperados, 0, 0, 0)
        return

    # ------------------------------------------------------- bajar los posts
    # REANUDABLE: si ya hay posts bajados, no se vuelven a pedir. Mismo patrón
    # que el proyecto 01, y acá importa porque son ~4.000 llamadas.
    destino = DATOS / "posts.jsonl"
    ya = set()
    if destino.exists():
        for linea in destino.read_text(encoding="utf-8").splitlines():
            if linea.strip():
                try:
                    ya.add(json.loads(linea)["id"])
                except Exception:  # noqa: BLE001
                    continue
        print(f"\nya bajados: {len(ya):,} posts · no se vuelven a pedir")

    pendientes = [(h, k) for h in hilos for k in h["kids"] if k not in ya]
    print(f"a bajar ahora: {len(pendientes):,}\n")

    # Cuatro destinos posibles, contados por separado para que
    # 4.648 = con_texto + borrados + vacios + nulos + fallos cierre exacto.
    vacios = borrados = bajados = nulos = fallos = 0
    t0 = time.perf_counter()
    with destino.open("a", encoding="utf-8") as f, ThreadPoolExecutor(max_workers=8) as pool:
        for n, (hilo, item) in enumerate(
                zip([h for h, _ in pendientes],
                    pool.map(lambda p: traer(f"item/{p[1]}"), pendientes)), 1):
            if item is FALLO:
                fallos += 1      # no se pudo preguntar: hay que volver a correr
                continue
            if item is None:
                nulos += 1       # la API dijo null: el item no existe
                continue
            # Borrados y vacíos se CUENTAN APARTE, no se mezclan con los válidos:
            # "no hay post" y "el post está vacío" son hechos distintos.
            if item.get("deleted") or item.get("dead"):
                borrados += 1
                continue
            texto = item.get("text") or ""
            if not texto.strip():
                vacios += 1
                continue
            f.write(json.dumps({
                "id": item["id"], "hilo": hilo["id"], "mes": hilo["mes"],
                "autor": item.get("by"),
                "momento": datetime.fromtimestamp(item.get("time", 0), timezone.utc)
                            .isoformat(timespec="seconds"),
                "caracteres": len(texto),
                "texto_html": texto,
            }, ensure_ascii=False) + "\n")
            bajados += 1
            if n % 250 == 0:
                print(f"  {n:,}/{len(pendientes):,}  {time.perf_counter()-t0:.0f}s  "
                      f"válidos {bajados:,} · borrados {borrados} · vacíos {vacios}"
                      f" · nulos {nulos} · fallos {fallos}", flush=True)

    total = len(ya) + bajados
    print(f"\nbajados ahora {bajados:,} · borrados+muertos {borrados} · "
          f"vacíos {vacios} · nulos {nulos} · fallos de red {fallos}")
    print(f"TOTAL en data/posts.jsonl: {total:,} posts con texto")
    if fallos:
        print(f"\n! {fallos} no se pudieron descargar. Volvé a correr el script:")
        print("  es reanudable y solo va a pedir los que faltan.")
    veredicto(hilos, esperados, total, borrados, vacios, nulos, fallos, len(ya))


# ---------------------------------------------------------------- veredicto
# Las predicciones están en docs/PREDICCIONES.md, escritas ANTES de correr.
# Esto las compara solo, para que el resultado no se interprete a posteriori.

PRED_HILOS = (12, 14)
PRED_POSTS = (3500, 4200)       # etapa 1: registrado, y FALLO. Ver PREDICCIONES.md:
                                # el rango se anclo a un conteo filtrado (3.909) y
                                # aca se mide uno sin filtrar. No es la misma magnitud.
                                # Queda como se registro: una prediccion no se reescribe.
PRED_CON_TEXTO = (4280, 4600)   # etapa 1b, registrada antes de correr el comando 2
PRED_DESCARTE = (0.01, 0.08)    # borrados + muertos, como fraccion del total
PRED_PUBLICADO = 3909           # el analisis publicado. Referencia, NO objetivo.


def veredicto(hilos, esperados, total, borrados, vacios,
              nulos=0, fallos=0, previos=0) -> None:
    print(f"\n{'='*72}\nVEREDICTO CONTRA LAS PREDICCIONES (docs/PREDICCIONES.md)\n{'='*72}\n")
    n = len(hilos)

    ok_h = PRED_HILOS[0] <= n <= PRED_HILOS[1]
    print(f"  hilos encontrados      {n:>7}   esperado {PRED_HILOS[0]}–{PRED_HILOS[1]}"
          f"   {'OK' if ok_h else '<-- FUERA DE RANGO'}")

    ok_e = PRED_POSTS[0] <= esperados <= PRED_POSTS[1]
    print(f"  comentarios 1er nivel  {esperados:>7,}   esperado "
          f"{PRED_POSTS[0]:,}–{PRED_POSTS[1]:,}   {'OK' if ok_e else '<-- FUERA DE RANGO'}")
    if not ok_e:
        print("        ^ esta predicción ya está registrada como FALLIDA, y la culpa")
        print("          es de la predicción, no del código: el rango se ancló a 3.909,")
        print("          que es un conteo FILTRADO de empresas, y acá se miden")
        print("          comentarios de primer nivel SIN filtrar. Magnitudes distintas.")
        print("          Es una cota superior: las empresas son <= este número.")

    if total:
        descartes = borrados + vacios + nulos + fallos
        print(f"\n  -- etapa 1b: de qué están hechos los descartes --")
        print(f"  posts con texto        {total:>7,}   esperado "
              f"{PRED_CON_TEXTO[0]:,}–{PRED_CON_TEXTO[1]:,}   "
              f"{'OK' if PRED_CON_TEXTO[0] <= total <= PRED_CON_TEXTO[1] else '<-- FUERA DE RANGO'}")
        frac = borrados / esperados if esperados else 0
        print(f"  borrados + muertos     {borrados:>7}   {frac:>6.1%}   esperado "
              f"{PRED_DESCARTE[0]:.0%}–{PRED_DESCARTE[1]:.0%}   "
              f"{'OK' if PRED_DESCARTE[0] <= frac <= PRED_DESCARTE[1] else '<-- FUERA DE RANGO'}")
        print(f"  vacíos                 {vacios:>7}   {vacios/esperados:>6.1%}   esperado <1%")
        print(f"  nulos (la API dijo null){nulos:>6}")
        print(f"  fallos de red          {fallos:>7}   esperado 0")

        # El cierre: si esto no da 0, se perdieron posts en algun lado.
        cuadra = total + descartes - previos
        print(f"\n  cierre: {total:,} con texto + {descartes:,} descartes "
              f"{'- ' + format(previos, ',') + ' ya bajados ' if previos else ''}"
              f"= {cuadra:,}  vs  {esperados:,} esperados  "
              f"-> {'CIERRA' if cuadra == esperados else 'NO CIERRA (faltan ' + str(esperados - cuadra) + ')'}")
        if cuadra != esperados and not fallos:
            print("        ! NO CIERRA y no hubo fallos de red: se perdieron posts")
            print("          en la escritura. Es un bug, no un dato.")

        if borrados / esperados > 0.20 if esperados else False:
            print("\n  ! borrados por encima del 20%: sospecho que estoy contando como")
            print("    borrado algo que no lo es. Revisar antes de usar el corpus.")

        print(f"\n  -- contra el análisis publicado --")
        print(f"  publicado: {PRED_PUBLICADO:,} posts de empresas (extracción sin validar)")
        print(f"  nuestra cota superior: {total:,} comentarios con texto")
        margen = total - PRED_PUBLICADO
        print(f"  margen: {margen:+,} ({margen/PRED_PUBLICADO:+.1%})")
        print(f"  De ese margen, los meta-comentarios (gente preguntando en el hilo,")
        print(f"  no contratando) tendrían que explicar {margen:,} para que los dos")
        print(f"  números coincidan. Eso es {margen/esperados:.1%} del corpus.")
        print(f"  PREDICCIÓN REGISTRADA: los meta-comentarios están en 2–5%, así que")
        print(f"  espero que sobren empresas y que 3.909 esté bajo. Se mide a mano")
        print(f"  en la etapa 2; hasta entonces esto es una hipótesis, no un hallazgo.")

    todos_iguales = len({h["posts_primer_nivel"] for h in hilos}) == 1
    if todos_iguales and n > 2:
        print("\n  ! TODOS los hilos tienen la misma cantidad exacta de posts.")
        print("    Eso no pasa en la realidad: es truncamiento o paginación.")
    sin_posts = [h["mes"] for h in hilos if h["posts_primer_nivel"] == 0]
    if sin_posts:
        print(f"\n  ! hilos con 0 posts: {sin_posts}")
        print("    Es un bug de captura, no un mes sin contrataciones.")

    print("\n  Recordatorio: de esta etapa NO se concluye nada sobre el mercado.")
    print("  Solo contesta '¿tengo el corpus?'. El análisis viene después de validar.")


if __name__ == "__main__":
    main()

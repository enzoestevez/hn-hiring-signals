"""Etiqueta la muestra a mano. Dos pasadas, la segunda a ciegas.

Uso:
    python src/etiquetar.py                 # pasada 1: los 266
    python src/etiquetar.py --pasada 2      # pasada 2: solo los 80 del doble ciego
    python src/etiquetar.py --estado        # cuanto falta, sin etiquetar nada

Deja data/etiquetas-p1.jsonl y data/etiquetas-p2.jsonl, append-only y
reanudables: se corta con `q` y se retoma donde quedo.

================================================================================
QUE NO SE MUESTRA EN PANTALLA, Y POR QUE

No se muestra el ESTRATO ni la cantidad de SENALES del post.

Si la pantalla dijera "sospechoso", eso predispondria a marcarlo como
meta-comentario. Las etiquetas quedarian contaminadas por el mismo filtro que
se esta tratando de evaluar, y el numero medido no seria independiente del
instrumento que lo midio. Se ve el texto y nada mas.

Tampoco se muestra la etiqueta de la pasada 1 durante la pasada 2. Si se
mostrara, el acuerdo entre pasadas seria 100% por construccion y el techo
humano medido seria una mentira. El orden de la pasada 2 ademas es distinto,
para que el recuerdo del contexto no ayude.

================================================================================
LOS CAMPOS

  es_empresa   s/n      ¿una empresa contratando, o un meta-comentario?
  pide_ia      s/n      ¿pide IA, ML, LLMs, data science o data engineering?
  n_puestos    1-9, m   cuantos puestos DISTINTOS lista (m = mas de 9)
  remoto       r/h/p/0  remoto / hibrido / presencial / no dice
  seniority    j/m/s/0  junior / medio / senior / no dice
  visa         s/n/0    patrocina / dice que no / no dice

Si `es_empresa` = n, los otros cinco campos se guardan en null y se pasa al
siguiente post. No son "desconocidos": NO APLICAN. Un meta-comentario no tiene
seniority, y rellenarlo con un valor cualquiera meteria basura en el
denominador de todos los demas campos.

`0` significa "el post no lo dice", y es un resultado, no un escape por pereza.
Si el 60% de los posts no declara seniority, entonces NINGUN sistema de
extraccion puede recuperar seniority de este corpus, y medir precision ahi no
tiene sentido. Un campo que la fuente no contiene es un limite del corpus, no
del modelo.

================================================================================
SE GUARDA EL TIEMPO POR POST

Para poder reportar el costo humano de la tarea, como en el proyecto 01
(mediana 113 s por documento, USD 0,058). Sin ese numero no se puede afirmar
que un sistema automatico sea mas barato: se estaria comparando contra cero.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bajar import DATOS  # noqa: E402

# Cada campo: (nombre, PREGUNTA completa, opciones explicadas, recordatorio).
#
# La primera version decia "¿EMPRESA contratando?", que es una frase nominal y
# se lee como "¿que empresa es?". Enzo no supo que contestar, y tenia razon:
# una etiqueta ambigua no mide consistencia, mide mi mala redaccion. Fue la
# firma de falla registrada ("si es_empresa baja de 90%, el problema es mi
# definicion") detectada en el post 0 en vez de en el 266.
CAMPOS = [
    ("es_empresa",
     "¿Este comentario lo puso una EMPRESA para contratar a alguien?",
     {"s": True, "n": False},
     ["s = sí, hay un puesto de trabajo ofrecido",
      "n = no (comentario sobre el hilo, alguien ofreciéndose, una herramienta,",
      "    una pregunta, [flagged], una ubicación suelta sin vacante)",
      "COFUNDADOR: solo equity, sin sueldo -> n (es sociedad, no empleo)",
      "    pero si declara sueldo además del equity -> s (es un empleo)",
      "EL TIPO DE CONTRATO NO IMPORTA: part-time, contract, 1099, freelance,",
      "    por hora, pasantía paga -> todos s. Lo que excluye es que NO",
      "    haya remuneración, no la forma del vínculo.",
      "QUE NO DIGA SUELDO NO ES MOTIVO DE n: la mayoría no lo dice. Para n",
      "    hace falta una SEÑAL POSITIVA de que no es empleo (equity en vez",
      "    de sueldo, sociedad explícita, alguien ofreciéndose, sin vacante).",
      "SI NO ENCONTRÁS LA VACANTE ES n. Un post sin puesto no es un puesto",
      "    con datos faltantes: es la ausencia de un puesto.",
      "LEÉ QUIÉN BUSCA A QUIÉN: las credenciales de la empresa (inversores,",
      "  fundadores, exits, clientes, crecimiento) vienen primero y ocupan más",
      "  texto. 'Backed by a founder with $1B exits' NO es la vacante.",
      "  La vacante es una frase con verbo de búsqueda: looking for, hiring,",
      "  we need, join us."]),

    ("pide_ia",
     "¿Pide IA, ML, LLMs, NLP, visión, data science o data engineering?",
     {"s": True, "n": False},
     ["s = el puesto lo pide, o la empresa es de IA y el puesto es técnico",
      "n = no aparece / puesto no técnico en empresa de IA / 'usamos Copilot'",
      "MULTI-PUESTO: s si CUALQUIERA de los puestos listados califica",
      "UN FEATURE DEL PRODUCTO NO ES UN SKILL PEDIDO ('anomaly detection'",
      "  descrito en el párrafo de la empresa, sin ML en el stack) -> n",
      "UNA BASE DE DATOS EN EL STACK NO ES DATA ENGINEERING. Postgres/MySQL",
      "  no cuentan; sí pipelines, warehouse, orquestación, datos a escala"]),

    ("n_puestos",
     "¿Cuántos puestos DISTINTOS lista este post?",
     {**{str(i): i for i in range(1, 10)}, "m": 10},
     ["1-9, o m si son más de 9  <- CONTÁS VACANTES, NO PALABRAS DE SENIORITY",
      "'Backend, Frontend y DevOps' = 3",
      "'hiring Senior AND Staff Backend Eng' = 2 (dos vacantes enumeradas)",
      "'Lead Full-Stack Engineer' = 1 (un título solo, aunque diga lead)",
      "'Engineers (multiple roles)' sin enumerar = 1 · un link solo = 1",
      "'Software Engineer / Developer' = 1 (un puesto escrito de dos formas)"]),

    ("remoto",
     "¿Qué modalidad de trabajo dice el post?",
     {"r": "remoto", "h": "hibrido", "p": "presencial", "0": None},
     ["r = dice REMOTE / remote-first / work from anywhere (aunque sea 'US only')",
      "h = dice hybrid, o pide N días en oficina",
      "p = dice ONSITE / in-office, o nombra ciudad Y exige presencia",
      "0 = no lo dice  <- NOMBRAR UNA CIUDAD NO ES DECIR PRESENCIAL",
      "MULTI-PUESTO con modalidades distintas (hybrid y remote) -> h",
      "EL TEST: ¿la ubicación es DEL PUESTO o DE LA EMPRESA?",
      "  'All positions are in Berkeley' / 'role based in NY' /",
      "  'NY-based engineers'  -> del puesto      -> p",
      "  'HQ in SF' / 'we are a Berlin company' -> de la empresa -> 0"]),

    ("seniority",
     "¿Qué nivel pide? (el del puesto MÁS JUNIOR que lista)",
     {"j": "junior", "m": "medio", "s": "senior", "0": None},
     ["j = junior, entry-level, new grad, intern, 0-2 años",
      "m = mid-level, o pide explícitamente 3-5 años",
      "s = senior, staff, principal, lead, 5+ años",
      "0 = no lo dice  <- 'Software Engineer' pelado va 0, NO 'medio'",
      "'Founding Engineer' va 0: marca alcance del rol, no nivel",
      "MULTI-PUESTO: el más junior ENTRE LOS QUE DECLARAN nivel. Los títulos",
      "  pelados no cuentan ni para arriba ni para abajo. Ninguno declara -> 0"]),

    ("visa",
     "¿Dice algo sobre patrocinar visa?",
     {"s": True, "n": False, "0": None},
     ["s = dice que patrocina (visa sponsorship, H1B, relocation + visa)",
      "n = dice explícitamente que NO patrocina, O exige ciudadanía/residencia",
      "    ('U.S. Persons only', 'must be authorized to work without",
      "    sponsorship', export control / ITAR, 'citizens only')",
      "0 = no lo menciona  <- va a ser la enorme mayoría",
      "'US-based' o 'EU timezone' SOLO NO es n: es ubicación, no estatus"]),
]

# Si no es empresa, los otros cinco campos NO APLICAN (null), no son "desconocidos".
SOLO_SI_EMPRESA = [c for c, *_ in CAMPOS[1:]]

# Se imprime en cada post. La regla que mas facil se olvida a las 2 de la
# manana es tambien la que mas dano hace si se rompe.
RECORDATORIO = ("MIRÁ SOLO EL TEXTO DE ARRIBA. No abras links, no busques la "
                "empresa.\n   Si el post no lo dice, la respuesta correcta es "
                "\"no lo dice\".")


def leer_tecla(validas: set[str]) -> str:
    """Una tecla, sin Enter si la consola lo permite.

    `q` sale guardando, `?` repite la ayuda. Una tecla invalida no hace nada:
    no se asume un valor por defecto, porque un default silencioso en una
    etiqueta a mano es un dato inventado.
    """
    try:
        import msvcrt  # Windows
        while True:
            t = msvcrt.getch()
            if t in (b"\x03", b"\x1b"):
                return "q"
            try:
                c = t.decode("utf-8", "ignore").lower()
            except Exception:  # noqa: BLE001
                continue
            if c in validas or c == "q":
                print(c)
                return c
    except ImportError:
        while True:
            c = input("> ").strip().lower()[:1]
            if c in validas or c == "q":
                return c


def limpiar() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def cargar_hechas(ruta: Path) -> dict[int, dict]:
    if not ruta.exists():
        return {}
    out = {}
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if linea.strip():
            f = json.loads(linea)
            out[f["id"]] = f
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Etiquetado manual de la muestra.")
    ap.add_argument("--pasada", type=int, default=1, choices=(1, 2, 3))
    ap.add_argument("--estado", action="store_true", help="solo mostrar el progreso")
    args = ap.parse_args()

    ruta_m = DATOS / "muestra.jsonl"
    if not ruta_m.exists():
        sys.exit("falta data/muestra.jsonl. Corré primero: python src/muestrear.py")
    muestra = [json.loads(l) for l in ruta_m.read_text(encoding="utf-8").splitlines() if l.strip()]

    if args.pasada == 1:
        cola = sorted(muestra, key=lambda p: p["orden"])
    elif args.pasada == 2:
        # Solo el subconjunto del doble ciego, y en OTRO orden: si el orden
        # fuera el mismo, el recuerdo del contexto inflaria el acuerdo.
        cola = [p for p in muestra if p.get("doble")]
        random.Random(777).shuffle(cola)
    else:
        # PASADA 3: control de calidad del estrato LIMPIO, un solo campo.
        #
        # Por que solo el limpio: cada post limpio pesa 30,35 del corpus. Un
        # error ahi mueve la estimacion 30 veces mas que un error en el
        # sospechoso, donde el peso es 1,00.
        #
        # Por que solo los marcados EMPRESA: la clase meta del estrato limpio
        # son 3 posts y ya se revisaron los 3, exhaustivo. Lo que falta es la
        # direccion contraria, que son 117.
        #
        # El orden es aleatorio con semilla fija, asi que los primeros 40 son
        # una muestra aleatoria legitima de los 117: se puede cortar en 40 y
        # el resultado sigue siendo insesgado.
        ruta_oro = DATOS / "oro.jsonl"
        if not ruta_oro.exists():
            sys.exit("falta data/oro.jsonl. Corré primero: python src/oro.py")
        oro = [json.loads(l) for l in ruta_oro.read_text(encoding="utf-8").splitlines() if l.strip()]
        objetivo = {f["id"] for f in oro if f["estrato"] == "limpio" and f["es_empresa"]}
        cola = [p for p in muestra if p["id"] in objetivo]
        random.Random(31415).shuffle(cola)

    destino = DATOS / f"etiquetas-p{args.pasada}.jsonl"
    hechas = cargar_hechas(destino)
    faltan = [p for p in cola if p["id"] not in hechas]

    print(f"pasada {args.pasada}: {len(cola)} posts · {len(hechas)} hechos · "
          f"{len(faltan)} faltan")
    if hechas:
        t = [h["segundos"] for h in hechas.values() if h.get("segundos")]
        if t:
            med = sorted(t)[len(t) // 2]
            print(f"mediana hasta ahora: {med:.0f} s/post · "
                  f"faltarían ~{med*len(faltan)/60:.0f} min")
    if args.estado:
        return
    if not faltan:
        print("\nNada que etiquetar. La pasada está completa.")
        return

    print("\nTeclas: la que corresponda · q = salir guardando")
    print("Se guarda después de cada post, así que cortar no pierde nada.")
    input("\nEnter para arrancar... ")

    with destino.open("a", encoding="utf-8") as f:
        for i, post in enumerate(faltan, 1):
            limpiar()
            # NO se muestra estrato ni señales: contaminaría la etiqueta.
            print(f"pasada {args.pasada} · {i}/{len(faltan)} · "
                  f"{post['caracteres']} caracteres · {post['mes']} · "
                  f"id {post['id']}   <- este número va en \"Casos sin regla\"")
            print("=" * 72)
            print(post["texto"][:4000])
            if len(post["texto"]) > 4000:
                print(f"\n[... {len(post['texto'])-4000} caracteres más]")
            print("=" * 72)

            t0 = time.perf_counter()
            fila = {"id": post["id"], "pasada": args.pasada}
            cortar = False
            print(f"   {RECORDATORIO}")
            campos = [c for c in CAMPOS if args.pasada != 3 or c[0] == "es_empresa"]
            for campo, pregunta, mapa, pistas in campos:
                if campo in SOLO_SI_EMPRESA and fila.get("es_empresa") is False:
                    fila[campo] = None     # NO APLICA, distinto de desconocido
                    continue
                print(f"\n  {pregunta}")
                for pista in pistas:
                    print(f"      {pista}")
                print(f"  ({'/'.join(mapa)})  > ", end="", flush=True)
                tecla = leer_tecla(set(mapa))
                if tecla == "q":
                    cortar = True
                    break
                fila[campo] = mapa[tecla]
            if cortar:
                print("\n\nCortado. Lo etiquetado está guardado; este post no.")
                break
            fila["segundos"] = round(time.perf_counter() - t0, 1)
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")
            f.flush()   # por si se corta la consola: nunca perder mas de un post

            if args.pasada == 3 and len(hechas) + i == 40:
                print("\n" + "=" * 72)
                print("  LLEGASTE A 40. ESTE ES UN PUNTO DE CORTE LEGITIMO.")
                print("=" * 72)
                print("  40 al azar sobre 117 alcanzan para descartar un error")
                print("  SISTEMATICO: si el 10% estuviera mal, la probabilidad de")
                print("  no encontrar ninguno en 40 es 1,5%. Y el 10% es el unico")
                print("  nivel de error que podria cambiar la conclusion.")
                print("  Un error raro y salpicado mueve la estimacion menos que")
                print("  el ancho del intervalo, asi que seguir compra precision,")
                print("  no una conclusion distinta.")
                print("\n  'q' corta y guarda. Seguir tambien esta bien.")
                print("=" * 72)
                input("  Enter para continuar... ")

    hechas = cargar_hechas(destino)
    print(f"\npasada {args.pasada}: {len(hechas)}/{len(cola)} etiquetados")
    if len(hechas) == len(cola):
        if args.pasada == 1:
            print("\nPasada 1 completa. Dejá pasar un rato y corré:")
            print("  python src/etiquetar.py --pasada 2")
            print("El tiempo entre pasadas es parte del método: etiquetar la")
            print("segunda inmediatamente mide memoria, no criterio.")
        elif args.pasada == 2:
            print("\nLas dos pasadas están completas. Ahora:")
            print("  python src/techo.py")
        else:
            print("\nControl del estrato limpio completo. Ahora:")
            print("  python src/sensibilidad.py")


if __name__ == "__main__":
    main()

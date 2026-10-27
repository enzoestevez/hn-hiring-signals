"""Arma la muestra que se etiqueta a mano en la etapa 2. Dos fases.

Uso:
    python src/muestrear.py                    # fase 1
    python src/muestrear.py --fase 2 --n-b 220 # fase 2, si la 1 dice que hace falta

Deja data/muestra.jsonl y reports/muestra-diseno.json.

================================================================================
EL PROBLEMA

La pregunta que destraba la etapa 1b es la tasa de META-COMENTARIOS: gente
comentando en el hilo en vez de contratando. Esta alrededor del 3%, y la regla
de decision registrada necesita separar "2,5-4%" de "mas de 5%".

Para eso hace falta un error estandar de 0,65% o menos. Con muestreo aleatorio
simple eso son ~900 posts etiquetados, y DOS VECES para medir el techo humano.
No es un plan.

================================================================================
EL PRIMER DISENO QUE PROBE, Y POR QUE ESTABA MAL

Estratifique por LARGO del texto, sobre-representando los posts cortos. Dio
EE 1,50% etiquetando 246 posts, cuando tomar esos mismos 246 al azar da 1,25%.
**Mi diseno "inteligente" era peor que el azar.**

El error: estratificar ayuda solo si la clase rara se concentra en un estrato
que PESA en el corpus. Los posts de menos de 150 caracteres son 46 de 3.788,
el 1,2%. Aunque TODOS fueran meta-comentarios, explicarian 1,2 de los ~3
puntos. El resto esta en los estratos largos, que es donde muestree fino.

El script lo detecto solo, porque el veredicto compara contra el azar simple.
Un diseno que no se compara contra la alternativa trivial no se puede defender.

================================================================================
LA VARIABLE DE ESTRATIFICACION CORRECTA

Sale de la convencion del hilo, no de mi intuicion. Un post de empresa sigue el
formato `Empresa | Puesto | Lugar | Link` y casi siempre trae URL o mail:

    con URL   85,8%      con "|"     90,6%
    con mail  25,2%      con vocab   92,2%   (hiring, role, apply, engineer...)

Se cuentan esas cuatro senales. Con 0 o 1 senal quedan 142 posts (3,7%), y ahi
estan los meta-comentarios de verdad.

OJO, BUG DE ENCODING QUE CASI ARRUINA ESTO: la API de HN devuelve los links con
las barras escapadas como `&#x2F;`, asi que `https://` NO aparece literal en el
HTML. Buscar la URL sobre el HTML crudo da 28,6% en vez de 85,8%, y manda a
"sospechoso" a posts de empresa perfectamente formateados. Hay que DESESCAPAR
antes de buscar. Lo agarre imprimiendo ejemplos, no mirando el porcentaje.

================================================================================
POR QUE DOS FASES, Y NO UN NUMERO ELEGIDO DE ANTEMANO

Tomando TODO el estrato sospechoso (142) y n del limpio, el error estandar es

    EE = (3646/3788) * sqrt( p_limpio*(1-p_limpio)/n * (1 - n/3646) )

El estrato sospechoso contribuye CERO varianza, porque se toma completo.
Toda la incertidumbre viene del limpio, que es el 96% del corpus.

Y eso depende de `p_limpio`: cuantos meta-comentarios se le escapan al filtro.

    p_limpio = 0,003  ->  n = 60 alcanza    (EE 0,42%)
    p_limpio = 0,010  ->  n = 210 alcanza   (EE 0,65%)
    p_limpio = 0,020  ->  n = 410 alcanza

**`p_limpio` no se puede conocer antes de etiquetar.** Elegir n de antemano es
adivinar: o se etiqueta de mas, o no alcanza y hay que volver.

Asi que fase 1 = los 142 sospechosos + 120 limpios. Con eso se MIDE
`p_limpio`, y el script calcula cuantos limpios mas hacen falta, si hacen.

================================================================================
LO QUE EL FILTRO NO PUEDE HACER

El filtro es un INSTRUMENTO DE MUESTREO, no un clasificador. No decide si un
post es empresa: solo decide con que probabilidad entra en la muestra.

Por eso el estimador es NO SESGADO aunque el filtro sea malo. Todo post del
corpus tiene probabilidad de inclusion conocida y mayor que cero. Un filtro
malo cuesta PRECISION, nunca sesgo. Esa es toda la diferencia entre usarlo asi
y usarlo para etiquetar directo.

Si el filtro se usara como clasificador —"0 senales, entonces meta"— el numero
seria basura y ademas incomprobable. Es exactamente el error del analisis
publicado: estructurar con un modelo y no validar contra nada.

================================================================================
LOS SEIS CAMPOS QUE SE ETIQUETAN

  es_empresa   si/no    ¿empresa contratando, o meta-comentario?  <- EL CRITICO
  pide_ia      si/no    ¿pide IA, ML, LLMs, data science o data engineering?
  n_puestos    entero   cuantos puestos DISTINTOS lista
  remoto       r/h/p/?  remoto / hibrido / presencial / no dice
  seniority    j/m/s/?  junior / medio / senior / no dice
  visa         s/n/?    patrocina / dice que no / no dice

`?` no es un escape por pereza: es "el post no lo dice", y es un resultado.
Si el 60% no declara seniority, entonces NINGUN sistema de extraccion puede
recuperar seniority de este corpus, y medir precision en ese campo no tiene
sentido. Un campo que la fuente no contiene es un limite del corpus, no del
modelo.

================================================================================
EL DOBLE CIEGO

80 posts quedan marcados `doble: true` para etiquetar dos veces, en orden
distinto y sin ver la primera etiqueta. El acuerdo entre las dos pasadas del
mismo humano es el TECHO: ningun modelo puede superar de forma creible la
consistencia de la referencia contra la que se lo mide.

Del proyecto 01: ese techo no fue un numero solo, se partio por formato
(98,7% contra 72,7%) y el promedio global era una mentira comoda. Aca se mide
por estrato por la misma razon.

La muestra se guarda MEZCLADA, nunca agrupada por estrato ni por mes:
etiquetar 142 sospechosos en fila crea sesgo de arrastre. Despues de veinte
meta-comentarios seguidos, el ojo empieza a ver meta-comentarios.
"""

from __future__ import annotations

import argparse
import html
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bajar import DATOS, RAIZ  # noqa: E402

REPORTES = RAIZ / "reports"

# El mes en curso se excluye: el hilo sigue abierto. Ver PREDICCIONES.md.
MES_EXCLUIDO = "2026-10"

# Objetivo de precision, registrado antes de correr: separar 3% de 5% al 95%.
EE_OBJETIVO = 0.0065

RX_TAG = re.compile(r"<[^>]+>")
RX_BR = re.compile(r"<br\s*/?>", re.I)
RX_P = re.compile(r"</?p>", re.I)
RX_ESPACIOS = re.compile(r"[ \t]+")
RX_LINEAS = re.compile(r"\n{3,}")

RX_URL = re.compile(r"https?://|www\.", re.I)
RX_MAIL = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.I)
RX_PIPE = re.compile(r"\|")
RX_VOCAB = re.compile(
    r"\b(hiring|we'?re looking|join us|apply|role|position|engineer|developer)\b", re.I)


def senales(crudo: str) -> int:
    """Cuantas de las 4 senales de 'post de empresa' tiene.

    DESESCAPA primero: la API escapa las barras de las URLs como `&#x2F;`.
    Sin esto la senal de URL baja de 85,8% a 28,6% y el estrato se arma mal.
    Los tags no molestan a estas regexes, asi que no hace falta sacarlos.
    """
    t = html.unescape(crudo)
    return sum((bool(RX_URL.search(t)), bool(RX_MAIL.search(t)),
                bool(RX_PIPE.search(t)), bool(RX_VOCAB.search(t))))


def a_texto(crudo: str) -> str:
    """HTML de comentario de HN -> texto plano para leer al etiquetar.

    Se sacan los tags ANTES de desescapar (al reves, un `&lt;b&gt;` del texto se
    convertiria en un tag falso). Las URLs se conservan igual, porque HN pone la
    URL tambien como texto del link, no solo en el href. Y se conservan a
    proposito: un link a la empresa es evidencia del campo mas importante.
    """
    t = RX_BR.sub("\n", crudo)
    t = RX_P.sub("\n\n", t)
    t = html.unescape(RX_TAG.sub("", t))
    t = RX_ESPACIOS.sub(" ", t)
    return RX_LINEAS.sub("\n\n", t).strip()


def ee_estratificado(n_limpio: int, p_limpio: float,
                     n_sosp: int, p_sosp: float,
                     N_limpio: int, N_sosp: int) -> float:
    """EE de la tasa global bajo muestreo estratificado, con correccion finita.

    Un estrato tomado completo (n == N) aporta cero varianza: el factor
    (1 - n/N) se anula. Por eso tomar los 142 sospechosos sale tan a cuenta.
    """
    N = N_limpio + N_sosp
    var = 0.0
    for n_h, p_h, N_h in ((n_limpio, p_limpio, N_limpio), (n_sosp, p_sosp, N_sosp)):
        if n_h and N_h > 1:
            var += (N_h / N) ** 2 * (p_h * (1 - p_h) / n_h) * (1 - n_h / N_h)
    return var ** 0.5


def n_necesario(p_limpio: float, N_limpio: int, N_sosp: int) -> int:
    """Cuantos limpios hacen falta para llegar a EE_OBJETIVO, dado p_limpio.

    El estrato sospechoso va COMPLETO (n_sosp = N_sosp), que es lo que anula su
    varianza. Pasarle n_sosp = 1 —como hice en la primera version— hace que ese
    estrato domine la varianza y la respuesta sea "no alcanza nunca", para
    cualquier p_limpio. Un bug que devuelve siempre el mismo numero es facil de
    confundir con un resultado.
    """
    for n in range(20, N_limpio + 1, 5):
        if ee_estratificado(n, p_limpio, N_sosp, 0.5, N_limpio, N_sosp) <= EE_OBJETIVO:
            return n
    return -1   # no alcanza ni tomando el estrato limpio entero


def main() -> None:
    ap = argparse.ArgumentParser(description="Muestra en dos fases para etiquetar a mano.")
    ap.add_argument("--semilla", type=int, default=20261023)
    ap.add_argument("--fase", type=int, default=1, choices=(1, 2))
    ap.add_argument("--n-b", type=int, default=120,
                    help="cuantos del estrato limpio (fase 1: 120; fase 2: lo que diga el script)")
    ap.add_argument("--doble", type=int, default=80)
    args = ap.parse_args()

    ruta = DATOS / "posts.jsonl"
    if not ruta.exists():
        sys.exit("falta data/posts.jsonl. Corré primero: python src/bajar.py")

    todos = [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]
    corpus = [p for p in todos if p["mes"] != MES_EXCLUIDO]
    print(f"corpus              {len(todos):,} posts")
    print(f"sin {MES_EXCLUIDO}         {len(corpus):,} posts  (12 meses cerrados)\n")

    sosp = [p for p in corpus if senales(p["texto_html"]) <= 1]
    limpio = [p for p in corpus if senales(p["texto_html"]) >= 2]
    print(f"{'estrato':12}{'señales':>9}{'en corpus':>11}{'se toman':>10}{'peso':>8}")

    rng = random.Random(args.semilla)
    n_b = min(args.n_b, len(limpio))
    # El sospechoso se toma COMPLETO: es chico y aporta cero varianza asi.
    elegidos_limpio = rng.sample(limpio, n_b)

    muestra, diseno = [], []
    for nombre, grupo, elegidos in (("sospechoso", sosp, sosp),
                                    ("limpio", limpio, elegidos_limpio)):
        N, n = len(grupo), len(elegidos)
        peso = N / n
        rango = "0–1" if nombre == "sospechoso" else "2–4"
        print(f"{nombre:12}{rango:>9}{N:>11,}{n:>10}{peso:>8.2f}")
        for p in elegidos:
            muestra.append({
                "id": p["id"], "mes": p["mes"], "autor": p["autor"],
                "estrato": nombre, "peso": round(peso, 6),
                "senales": senales(p["texto_html"]),
                "caracteres": p["caracteres"],
                "texto": a_texto(p["texto_html"]),
            })
        diseno.append({"estrato": nombre, "N_corpus": N, "n_muestra": n, "peso": peso})

    rng.shuffle(muestra)
    indices_doble = set(rng.sample(range(len(muestra)), min(args.doble, len(muestra))))
    for i, fila in enumerate(muestra):
        fila["doble"] = i in indices_doble
        fila["orden"] = i

    (DATOS / "muestra.jsonl").write_text(
        "\n".join(json.dumps(f, ensure_ascii=False) for f in muestra) + "\n",
        encoding="utf-8")
    REPORTES.mkdir(exist_ok=True)
    (REPORTES / "muestra-diseno.json").write_text(json.dumps({
        "fase": args.fase, "semilla": args.semilla, "mes_excluido": MES_EXCLUIDO,
        "ee_objetivo": EE_OBJETIVO, "n_corpus": len(corpus),
        "n_muestra": len(muestra), "n_doble": len(indices_doble), "estratos": diseno,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nmuestra             {len(muestra)} posts a etiquetar")
    print(f"doble ciego         {len(indices_doble)} de esos, dos veces")
    print(f"juicios en total    {len(muestra) + len(indices_doble)}")
    veredicto(diseno, muestra, len(corpus), len(limpio), len(sosp))


def veredicto(diseno, muestra, n_corpus, N_limpio, N_sosp) -> None:
    print(f"\n{'='*72}\nVEREDICTO: ¿ALCANZA ESTA MUESTRA?\n{'='*72}\n")

    suma = sum(f["peso"] for f in muestra)
    cierra = abs(suma - n_corpus) < 1.0
    print(f"  suma de pesos      {suma:>10,.1f}   vs corpus {n_corpus:,}   "
          f"{'CIERRA' if cierra else '<-- NO CIERRA: el diseño está mal'}\n")

    n_b = next(d["n_muestra"] for d in diseno if d["estrato"] == "limpio")
    n_s = next(d["n_muestra"] for d in diseno if d["estrato"] == "sospechoso")

    print("  El estrato sospechoso se toma COMPLETO, así que aporta cero")
    print("  varianza. Toda la incertidumbre viene del limpio, que es el")
    print(f"  {N_limpio/n_corpus:.1%} del corpus.\n")

    print(f"  EE según cuántos meta se le escapen al filtro (p_limpio),")
    print(f"  con los {n_b} limpios de esta muestra:\n")
    print(f"    {'p_limpio':>10}{'EE':>9}{'IC 95%':>10}   ¿separa 3% de 5%?   n limpio necesario")
    for p in (0.003, 0.005, 0.010, 0.020, 0.030):
        ee = ee_estratificado(n_b, p, n_s, 0.5, N_limpio, N_sosp)
        nn = n_necesario(p, N_limpio, N_sosp)
        print(f"    {p:>9.1%}{ee:>9.2%}{1.96*ee:>9.2%}   "
              f"{'sí' if ee <= EE_OBJETIVO else 'NO':<18} "
              f"{'ni el estrato entero' if nn < 0 else format(nn, ',')}")

    # Contra la alternativa trivial. Un diseño que no se compara con el azar
    # simple no se puede defender: fue el error del primer diseño.
    n_total = len(muestra)
    ee_simple = (0.03 * 0.97 / n_total) ** 0.5
    ee_estr = ee_estratificado(n_b, 0.010, n_s, 0.5, N_limpio, N_sosp)
    print(f"\n  CONTRA EL AZAR SIMPLE con los mismos {n_total} posts:")
    print(f"    azar simple        EE {ee_simple:.2%}")
    print(f"    estratificado      EE {ee_estr:.2%}  (suponiendo p_limpio = 1%)")
    print(f"    {'el diseño gana' if ee_estr < ee_simple else '<-- EL DISEÑO PIERDE: usá azar simple'}")

    print(f"\n  FASE 2: etiquetá primero esta muestra. Con `es_empresa` medido en")
    print(f"  el estrato limpio, la tabla de arriba dice cuántos limpios más")
    print(f"  hacen falta, si hacen. No se elige n adivinando p_limpio.")
    print(f"\n  La tasa CRUDA sobre esta muestra no es la del corpus: los")
    print(f"  {N_sosp} sospechosos son el {N_sosp/n_corpus:.1%} del corpus y acá son el")
    print(f"  {N_sosp/len(muestra):.0%} de la muestra. Sin reponderar por `peso` el número")
    print(f"  sale muy inflado. El peso no es un adorno.")


if __name__ == "__main__":
    main()

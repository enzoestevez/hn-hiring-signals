"""
Construye el set de referencia adjudicado y lo parte en dev / held-out.

POR QUE EXISTE ESTE PASO
------------------------
El doble ciego de la etapa 2 no solo midio el techo: encontro etiquetas MAL.
De los 4 desacuerdos de `es_empresa`, dos (Budibase 48367953, SwingVision
49160095) son empresas contratando sin discusion posible y en la pasada 1
salieron `n`. Si la etapa 3 se mide contra la pasada 1 cruda, un clasificador
que acierte esos posts queda contado como que se equivoco.

La referencia no es "lo que dijo el humano". Es lo que quedo despues de
adjudicar los desacuerdos.

LA PARTICION, Y POR QUE VA ANTES DE ESCRIBIR UNA SOLA REGLA
-----------------------------------------------------------
Si escribo reglas mirando los 266 y despues reporto el acierto sobre los 266,
el numero no significa nada: estaria midiendo cuanto me acuerdo de la muestra.
Se parte en dos mitades ANTES de escribir la primera regla. El desarrollo mira
SOLO `dev`. `test` se toca una vez, al final, y lo que salga es lo que se
reporta.

La particion es estratificada por (estrato x es_empresa) para que las dos
mitades tengan la misma mezcla: con ~90 meta en 266, una particion al azar
podria dejar 55 en una mitad y 35 en la otra.
"""

import json
import os
import random
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(os.path.dirname(DIR), "data")

SEMILLA = 20261027          # fija y escrita: la particion tiene que ser reproducible

# Adjudicacion de los 4 desacuerdos de `es_empresa` del doble ciego.
# Los cuatro quedaron `s`. Dos eran error liso de la pasada 1; los otros dos
# eran limite real y los decidio el (27/10/2026), con la guia al lado.
ADJUDICADOS = {
    48367953: (True, "Budibase: 'Senior Engineers 60-90k' + link a su bolsa. Error de la pasada 1."),
    49160095: (True, "SwingVision: dos puestos con links a Deel. Error de la pasada 1."),
    46121314: (True, "London - Systems Engineer - DM. Hay vacante nombrada; el formato no define la intencion."),
    48448408: (True, "commudle: dice 'us', hay empresa y puesto no tecnico. Que no diga sueldo no es senal."),
}

# Errores encontrados leyendo la mitad dev. Todos en la misma direccion:
# empresa contratando, marcada meta. Ninguno admite otra lectura.
ERRORES_LEIDOS = {
    48370889: "telli | Engineering, Design, GTM | On-site | Berlin + link a su bolsa (LIMPIO)",
    46885022: "'telli is hiring [Berlin, on-site] - careers.telli.com'",
    45809383: "telli: 'checkout our openings here' + link a sus vacantes",
    47611075: "telli (YC F24) 'looking for ambitious to join our team' - mal en LAS DOS pasadas",
    47230320: "Glitch: 'We need Engineers... Email me @ kingsley@glitchads.ai'",
    # Encontrados porque el clasificador de reglas los marco empresa y la
    # revision contra la guia le dio la razon. Se flipea SOLO cuando la guia
    # es inequivoca; si fuera por cualquier desacuerdo, seria ajustar el oro
    # al clasificador, que es circular.
    45807645: "Ankr Health: 'We are seeking a Manager, Clinical Research' + link a la vacante",
    48751775: "Aristotle: empresa + link a su pagina de careers. La guia manda `s` aunque no detalle el puesto",
}

# Grupos de TEXTO IDENTICO con etiquetas en conflicto. Un mismo texto no puede
# tener dos etiquetas: es un error garantizado, sin necesidad de un segundo
# etiquetador. El corpus repite el 17% de sus posts, asi que esto es un
# control de calidad gratis y permanente, no un hallazgo de una sola vez.
CONFLICTOS_DUPLICADOS = {
    46572245: "Wayward x3 (01/02/03-2026): dos veces `s`, una `n`. Texto identico.",
    49524180: "Beacon AI x2 (08/09-2026): 'expanding our team'. Texto identico, etiquetas opuestas.",
}


def jsonl(ruta):
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    mu = {r["id"]: r for r in jsonl(os.path.join(DATOS, "muestra.jsonl"))}
    p1 = {r["id"]: r for r in jsonl(os.path.join(DATOS, "etiquetas-p1.jsonl"))}
    p2 = {r["id"]: r for r in jsonl(os.path.join(DATOS, "etiquetas-p2.jsonl"))}

    filas, cuenta = [], {"acuerdo": 0, "adjudicado": 0, "pasada1": 0}
    sin_adjudicar = []

    for i, m in mu.items():
        if i not in p1:
            continue
        a = p1[i].get("es_empresa")
        if i in p2:
            b = p2[i].get("es_empresa")
            if a == b:
                valor, origen, nota = a, "acuerdo", ""
            elif i in ADJUDICADOS:
                valor, nota = ADJUDICADOS[i]
                origen = "adjudicado"
            else:
                sin_adjudicar.append(i)
                continue
        else:
            valor, origen, nota = a, "pasada1", ""
        crudo = bool(valor)
        for tabla, etiqueta in ((ERRORES_LEIDOS, "leido"), (CONFLICTOS_DUPLICADOS, "duplicado")):
            if i in tabla:
                valor, origen, nota = True, etiqueta, tabla[i]
                cuenta[etiqueta] = cuenta.get(etiqueta, 0) + 1
                break
        else:
            cuenta[origen] += 1
        filas.append({
            "id": i, "estrato": m["estrato"], "peso": m["peso"], "mes": m.get("mes"),
            "es_empresa": bool(valor), "es_empresa_crudo": crudo,
            "origen": origen, "nota": nota,
        })

    if sin_adjudicar:
        print("ERROR: desacuerdos sin adjudicar:", sin_adjudicar)
        print("No se escribe nada. Resolvelos en ADJUDICADOS primero.")
        return 1

    # ---- particion estratificada -------------------------------------------
    rnd = random.Random(SEMILLA)
    celdas = {}
    for f in filas:
        celdas.setdefault((f["estrato"], f["es_empresa"]), []).append(f)
    for clave, grupo in sorted(celdas.items()):
        grupo.sort(key=lambda f: f["id"])      # orden determinista antes de barajar
        rnd.shuffle(grupo)
        for k, f in enumerate(grupo):
            f["split"] = "dev" if k % 2 == 0 else "test"

    filas.sort(key=lambda f: f["id"])
    salida = os.path.join(DATOS, "oro.jsonl")
    with open(salida, "w", encoding="utf-8") as f:
        for fila in filas:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")

    # ---- veredicto ----------------------------------------------------------
    print(f"escrito {salida}  ({len(filas)} posts)\n")
    print("ORIGEN DE CADA ETIQUETA")
    print(f"  acuerdo de las dos pasadas   {cuenta['acuerdo']:>4}")
    print(f"  adjudicado tras desacuerdo   {cuenta['adjudicado']:>4}")
    print(f"  pasada 1 sola                {cuenta['pasada1']:>4}")
    print(f"  corregido al leerlo           {cuenta.get('leido',0):>4}   <- empresas marcadas meta")
    print(f"  corregido por duplicado       {cuenta.get('duplicado',0):>4}   <- mismo texto, etiquetas opuestas")
    cambiadas = sum(1 for f in filas if f["es_empresa"] != f["es_empresa_crudo"])
    print(f"  TOTAL de etiquetas corregidas {cambiadas:>4} de {len(filas)}  ({cambiadas/len(filas):.1%})")
    print()
    print("PARTICION (dev se mira, test NO se toca hasta el final)")
    print(f"  {'':<12}{'dev':>6}{'test':>6}{'  %empresa dev':>16}{'  %empresa test':>16}")
    for est in ("sospechoso", "limpio"):
        d = [f for f in filas if f["estrato"] == est and f["split"] == "dev"]
        t = [f for f in filas if f["estrato"] == est and f["split"] == "test"]
        pd = sum(x["es_empresa"] for x in d) / len(d) * 100 if d else 0
        pt = sum(x["es_empresa"] for x in t) / len(t) * 100 if t else 0
        print(f"  {est:<12}{len(d):>6}{len(t):>6}{pd:>15.1f}%{pt:>15.1f}%")
    d = [f for f in filas if f["split"] == "dev"]
    t = [f for f in filas if f["split"] == "test"]
    print(f"  {'TOTAL':<12}{len(d):>6}{len(t):>6}"
          f"{sum(x['es_empresa'] for x in d)/len(d)*100:>15.1f}%"
          f"{sum(x['es_empresa'] for x in t)/len(t)*100:>15.1f}%")
    print()
    dif = abs(sum(x["es_empresa"] for x in d) / len(d) - sum(x["es_empresa"] for x in t) / len(t)) * 100
    print(f"  diferencia de mezcla entre mitades: {dif:.1f} pts", end="  ")
    print("OK" if dif < 3 else "<-- REVISAR: las mitades no son comparables")
    print()
    print("TASA BASE, el numero que hay que tener a mano todo el tiempo")
    emp = sum(f["es_empresa"] * f["peso"] for f in filas)
    tot = sum(f["peso"] for f in filas)
    print(f"  empresas en el CORPUS, reponderado: {emp/tot*100:.1f}%")
    print("  Un clasificador que diga 'empresa' SIEMPRE acierta ese porcentaje.")
    print("  Por eso la metrica de la etapa 3 es kappa y el recall de la clase")
    print("  meta, NO el porcentaje de acierto. Es la leccion de `visa`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

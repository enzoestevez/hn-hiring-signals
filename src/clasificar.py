"""
Clasificador de `es_empresa` por reglas. Sin API, sin modelo, sin costo.

POR QUE REGLAS PRIMERO
----------------------
No se puede afirmar que haga falta un LLM sin mostrar antes que lo barato no
alcanza. Si estas reglas llegan al intervalo humano, la conclusion del
proyecto es que el modelo era innecesario, y eso vale mas que un modelo que
anda.

LA TASA BASE MANDA
------------------
El 95,4% del corpus son empresas. Un clasificador que diga "empresa" siempre
acierta el 95,4%. Por eso el porcentaje de acierto NO es la metrica: lo son
kappa y el recall de la clase meta. Es la leccion de `visa`, donde un umbral
de 92% que yo registre se cumplia con kappa -0,01.

SOBRE LA CONTAMINACION, DICHA DE FRENTE
---------------------------------------
Para el control de calidad del estrato limpio lei los 117 posts a mano, de las
DOS mitades de la particion, mas los 45 meta de `dev`. O sea: vi parte del
held-out. Volver a partir con otra semilla no des-ve nada, asi que no se hace.

Dos consecuencias que se declaran en vez de disimularse:

1. El acuerdo sobre la mitad `test` esta CONTAMINADO y se reporta como
   referencial, no como validacion.
2. La validacion de verdad es la estimacion sobre el corpus completo, donde
   3.522 de los 3.788 posts NUNCA fueron etiquetados ni leidos por nadie.
   Ese numero si es ciego, y es contra el intervalo humano que se juzga.

Regla que me impuse al escribir esto: **ninguna regla puede nombrar una
empresa ni un post concreto.** Todas son patrones de la convencion del hilo.
Si una regla necesita el nombre de una empresa para funcionar, es memoria, no
clasificacion.
"""

import html
import json
import os
import re
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(DIR)
DATOS = os.path.join(RAIZ, "data")

# --------------------------------------------------------------------------
# Senales de META. Cada una tiene que ser algo que una persona que leyo el
# hilo reconoceria, no algo que sale de mirar estos 266 posts.
# --------------------------------------------------------------------------

# La plantilla del hilo de CANDIDATOS ("Who wants to be hired?"). Aparece
# suelta dentro de los hilos de contratacion.
RX_PLANTILLA = re.compile(
    r"^\s*(location|remote|willing to relocate|technologies|tech stack|"
    r"r[eé]sum[eé]|resume|cv|email|seeking|availability)\s*:",
    re.I | re.M)

# Alguien ofreciendose. El sujeto es "yo" y el verbo es de busqueda de empleo.
RX_CANDIDATO = re.compile(
    r"\b(i am|i'm|im)\s+(a|an|currently)?\s*\w*\s*"
    r"(looking for|seeking|open to|available for|interested in)\s+"
    r"(a\s+)?(new\s+)?(role|job|position|work|opportunit|freelance|contract)"
    r"|\b(looking for|seeking)\s+(a\s+)?(new\s+)?(role|job|position)\b"
    r"|\bopen to work\b|\bmy (resume|cv|portfolio)\b"
    r"|\bi('m| am) available\b", re.I)

# Comentario SOBRE el hilo.
RX_META_HILO = re.compile(
    r"\bthis thread\b|\bwho is hiring\b|\bwho'?s hiring\b|@dang\b"
    r"|\bplease (only )?(post|use|include|normalize)\b"
    r"|\b(flagged|dead) (posts?|comments?)\b"
    r"|\blast month\b.{0,40}\b(applied|response|heard back)\b"
    r"|\bhaven'?t heard back\b|\bno response\b"
    r"|\bcomments? as of\b|\bthan I'?ve seen\b", re.I)

# Alguien que construyo una herramienta para navegar el hilo.
RX_HERRAMIENTA = re.compile(
    r"\bi (built|made|created|launched)\b.{0,120}"
    r"(search|browse|filter|aggregat|listing|scrape|index|thread|job board)", re.I)

# Cita: empieza citando a otro comentario.
RX_CITA = re.compile(r"^\s*>", re.M)

# Pregunta suelta.
RX_PREGUNTA = re.compile(
    r"^\s*(is|are|does|do|did|what|why|how|when|where|who|can|could|would|"
    r"should|any(one|body))\b", re.I)

# --------------------------------------------------------------------------
# Senales de EMPRESA.
# --------------------------------------------------------------------------

RX_BOLSA = re.compile(
    r"(greenhouse\.io|lever\.co|ashbyhq\.com|workable\.com|bamboohr|"
    r"deel\.com|grnh\.se|jobs\.|careers?\.|/careers?|/jobs?|join-us|"
    r"workatastartup|smartrecruiters|teamtailor|recruitee|personio|"
    r"peopleadmin|/postings?/|job description|apply)", re.I)

# Un encabezado de vacante: la convencion del hilo pone EMPRESA primero,
# separada por | o - del puesto y la ubicacion. Un comentario no tiene eso.
RX_ENCABEZADO = re.compile(
    r"^\s*[\w.&'’()/ ]{2,40}\s*[-|–—]\s*[\w.&'’()/, ]{2,60}"
    r"(engineer|developer|designer|scientist|manager|analyst|architect|"
    r"researcher|lead|intern|roles?|positions?|hiring|engineering)", re.I)

# La convencion del hilo pone la EMPRESA primero. Un post que arranca con un
# pronombre esta hablando de su autor, no presentando una vacante. Sin esto,
# "I'm a full-stack developer" matchea el encabezado por el guion de
# "full-stack", que es un falso positivo puramente tipografico.
RX_PRONOMBRE = re.compile(r"^\s*(i|i'?m|i'?ve|we|we'?re|my|our|hi|hello|hey|this|it)\b", re.I)

# Cofundador sin sueldo: la guia lo manda a `n` explicitamente (es sociedad,
# no empleo). Con sueldo declarado ademas del equity, vuelve a ser `s`.
# "co-founder AT/OF X" es alguien describiendose (el CTO que postea). La
# busqueda de socio no lleva esa preposicion. Sin esta distincion la regla se
# come los posts donde el fundador firma con su cargo.
RX_COFUNDADOR = re.compile(r"\bco[- ]?found(er|ing)\b(?!\s+(at|of)\b)", re.I)

# Agregador: el post apunta a una lista de vacantes de OTROS, no ofrece una.
RX_AGREGADOR = re.compile(
    r"\b(jobs?|listings?|positions?|roles?|postings?)\b.{0,40}"
    r"\b(can (also )?be found|are listed|listed (here|below))\b"
    r"|\bhere are the (listings|jobs|posts)\b"
    r"|\bresource for (searchers|job seekers)\b"
    r"|\b(jobs?|listings?) are (parsed|scraped|extracted)\b", re.I)

# Meta del hilo que no admite discusion, fire aunque haya senales de vacante.
RX_META_FUERTE = re.compile(
    r"@dang\b|\bwhoever posts this\b|\bplease (include|normalize|use) the\b"
    r"|\bthis (month'?s? )?thread\b|\bwho'?s? (is )?hiring\b"
    r"|\bnoticing a pattern\b", re.I)

# "I'm a <algo> developer with N years" = candidato describiendose.
RX_AUTODESCRIPCION = re.compile(
    r"\bi'?m\s+an?\s+[\w\- ]{0,30}"
    r"(developer|engineer|designer|programmer|consultant|freelancer)\b"
    r"|\bwith\s+\d+\+?\s+years? of (experience|exp)\b", re.I)

# Una postulacion enviada al hilo.
RX_POSTULACION = re.compile(r"\bapplication\b|\bapplying\b", re.I)

RX_CONTRATA = re.compile(
    r"\b(we'?re hiring|we are hiring|is hiring|are hiring|now hiring"
    r"|join (us|our team)|open (roles?|positions?)|apply (at|here|via|through)"
    r"|we'?re looking for|we are looking for|we need|hiring for"
    r"|send (me |us )?your (cv|resume)|email me|reach out to me)\b", re.I)

RX_SUELDO = re.compile(
    r"[$€£]\s?\d{2,3}\s?[kK]\b|[$€£]\s?\d{2,3},\d{3}|\b\d{2,3}k\s?-\s?\d{2,3}k\b", re.I)

RX_MODALIDAD = re.compile(
    r"\b(full[- ]?time|part[- ]?time|contract|onsite|on-site|remote|hybrid|"
    r"internship|intern)\b", re.I)

RX_PUESTO = re.compile(
    r"\b(engineer|developer|designer|scientist|manager|analyst|architect|"
    r"researcher|devrel|sre|founding engineer|cto|lead|intern|pm\b|"
    r"product manager|recruiter|marketer)\b", re.I)


def limpiar(crudo: str) -> str:
    """Desescapa ANTES de buscar: la API escapa las barras como &#x2F; y sin
    esto las URLs no se detectan. Es el bug de la etapa 2, no se repite."""
    t = html.unescape(crudo or "")
    t = re.sub(r"<[^>]+>", " ", t)
    return t


def clasificar(crudo: str) -> tuple[bool, str]:
    """Devuelve (es_empresa, motivo). El motivo es para poder auditar cada
    decision: un clasificador que no explica por que no se puede depurar."""
    t = limpiar(crudo)
    plano = " ".join(t.split())

    if len(plano) < 25:
        return False, "texto minimo (flagged/vacio/una palabra)"

    pipes = plano.count("|")
    emp = sum((
        bool(RX_BOLSA.search(plano)),
        bool(RX_CONTRATA.search(plano)),
        bool(RX_SUELDO.search(plano)),
        pipes >= 2,
    ))

    encabezado = (not RX_PRONOMBRE.match(plano)) and (
        bool(RX_ENCABEZADO.match(plano))
        or (plano.count("|") >= 2 and plano.find("|") < 120))

    # --- senales de meta, de la mas concluyente a la mas debil -------------
    if RX_META_FUERTE.search(plano) and not encabezado:
        return False, "comentario sobre el hilo (inequivoco)"
    if RX_AGREGADOR.search(plano) and not encabezado:
        return False, "agregador: apunta a vacantes de otros"
    if RX_HERRAMIENTA.search(plano):
        return False, "herramienta para navegar el hilo"
    # La plantilla de candidato NUNCA dice "Company:" ni trae verbo de
    # contratacion. Sin ese guardarrail se come posts de empresa que usan
    # el mismo formato de campos.
    if (len(RX_PLANTILLA.findall(t)) >= 2
            and not re.search(r"^\s*company\s*:", t, re.I | re.M)
            and not RX_CONTRATA.search(plano)):
        return False, "plantilla del hilo de candidatos (2+ campos)"
    if RX_CANDIDATO.search(plano):
        return False, "alguien ofreciendose a trabajar"
    if RX_POSTULACION.search(plano[:90]) and not encabezado:
        return False, "una postulacion enviada al hilo"
    if RX_AUTODESCRIPCION.search(plano[:160]) and not encabezado:
        return False, "el autor se describe a si mismo, no a una vacante"
    if RX_COFUNDADOR.search(plano[:120]) and not RX_SUELDO.search(plano):
        return False, "cofundador sin sueldo declarado (regla de la guia)"
    if RX_CITA.search(t) and emp == 0:
        return False, "cita a otro comentario, sin senales de vacante"
    if RX_META_HILO.search(plano) and emp == 0:
        return False, "comentario sobre el hilo"
    if "?" in plano and not encabezado and len(plano) < 260 and emp <= 1:
        return False, "pregunta o comentario de opinion, sin encabezado de vacante"
    if len(plano) < 120 and emp == 0 and not encabezado:
        return False, "post corto sin ninguna senal de vacante"

    # --- empresa -----------------------------------------------------------
    if encabezado:
        return True, "encabezado de vacante (empresa - puesto - ubicacion)"
    if emp >= 1:
        return True, f"senales de vacante ({emp}/4)"
    if RX_PUESTO.search(plano) and RX_MODALIDAD.search(plano):
        return True, "titulo de puesto + modalidad"
    if RX_PUESTO.search(plano) and len(plano) > 300:
        return True, "titulo de puesto en un post largo"

    # --- sin evidencia ------------------------------------------------------
    # Default `n`: la guia dice "si no encontras la vacante, es n". Poner
    # `s` por defecto seria cubrirse con la tasa base, que es justo lo que
    # esta etapa tiene prohibido.
    return False, "sin vacante identificable (default de la guia)"


def main() -> int:
    jl = lambda p: [json.loads(l) for l in open(os.path.join(DATOS, p), encoding="utf-8") if l.strip()]
    mu = {r["id"]: r for r in jl("muestra.jsonl")}
    oro = {r["id"]: r for r in jl("oro.jsonl")}

    split = sys.argv[1] if len(sys.argv) > 1 else "dev"
    ids = [i for i in oro if split == "todo" or oro[i]["split"] == split]

    tp = tn = fp = fn = 0
    errores = []
    for i in ids:
        pred, motivo = clasificar(mu[i]["texto"])
        real = oro[i]["es_empresa"]
        if pred and real:   tp += 1
        elif not pred and not real: tn += 1
        elif pred and not real:
            fp += 1; errores.append((i, "FP: dijo empresa, es meta", motivo))
        else:
            fn += 1; errores.append((i, "FN: dijo meta, es empresa", motivo))

    n = len(ids)
    acc = (tp + tn) / n
    po = acc
    pe = ((tp+fp)*(tp+fn) + (tn+fn)*(tn+fp)) / (n*n)
    k = (po - pe) / (1 - pe) if pe < 1 else 0.0
    rec_meta = tn / (tn + fp) if (tn + fp) else 0.0
    prec_meta = tn / (tn + fn) if (tn + fn) else 0.0

    print(f"split={split}   n={n}")
    print(f"  acierto           {acc:.1%}   (tasa base del corpus: 95,4% — por eso NO es la metrica)")
    print(f"  kappa             {k:.3f}")
    print(f"  recall de META    {rec_meta:.1%}   ({tn}/{tn+fp})")
    print(f"  precision de META {prec_meta:.1%}   ({tn}/{tn+fn})")
    print(f"  matriz: TP={tp} TN={tn} FP={fp} FN={fn}")
    if errores:
        print(f"\n  {len(errores)} errores:")
        for i, tipo, motivo in errores[:40]:
            txt = " ".join(limpiar(mu[i]["texto"]).split())[:110]
            print(f"   [{mu[i]['estrato'][:4]}] {i} {tipo}  <- {motivo}")
            print(f"        {txt}")

    # ------------------------------------------------------------------
    # CENSO DEL CORPUS. Este es el numero realmente ciego: 3.522 de los
    # 3.788 posts no los etiqueto ni los leyo nadie, ni el ni yo.
    # Y no hace falta reponderar: si se clasifica TODO, se cuenta.
    # ------------------------------------------------------------------
    if split == "todo":
        posts = jl("posts.jsonl")
        emp = sum(1 for r in posts if clasificar(r.get("texto_html"))[0])
        print("\n" + "=" * 70)
        print("  CENSO DEL CORPUS (clasificando los 4.054 posts con texto)")
        print("=" * 70)
        print(f"  clasificados EMPRESA        {emp:>7,}")
        print(f"  clasificados META           {len(posts)-emp:>7,}   ({(len(posts)-emp)/len(posts):.2%})")
        print(f"\n  estimacion humana           {3902:>7,}   IC [3.800, 3.973]")
        print(f"  analisis publicado          {3909:>7,}")
        print(f"  diferencia contra el humano {emp-3902:>+7,}")
        print(f"  diferencia contra publicado {emp-3909:>+7,}")
        print("  dentro del IC humano" if 3800 <= emp <= 3973 else "  <-- FUERA del IC humano")
        # empresas DISTINTAS: el corpus repite el 17%
        import collections
        g = collections.defaultdict(int)
        for r in posts:
            if clasificar(r.get("texto_html"))[0]:
                n = " ".join(re.sub(r"[^a-z0-9 ]", " ", limpiar(r.get("texto_html")).lower()).split())
                g[n[:200]] += 1
        print(f"\n  textos DISTINTOS entre los clasificados empresa: {len(g):,}")
        print(f"  el conteo de POSTS y el de EMPRESAS diferen en {emp-len(g):,} ({(emp-len(g))/emp:.1%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

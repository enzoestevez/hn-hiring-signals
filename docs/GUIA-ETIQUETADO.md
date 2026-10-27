# Guía de etiquetado — etapa 2

**Esto se escribe antes de etiquetar el primer post, y no se cambia a mitad.**

Si una definición se ajusta después de ver casos difíciles, las dos pasadas del
doble ciego dejan de ser comparables: la segunda estaría hecha con una regla
distinta, y el acuerdo medido ya no sería tu consistencia sino la diferencia
entre dos reglas. El techo humano quedaría inventado.

Si durante el etiquetado aparece un caso que estas reglas no cubren, **no se
improvisa**: se anota el `id` al final de este archivo en "Casos sin regla", se
etiqueta con el mejor criterio del momento, y se decide después qué hacer — con
la opción de descartar esos posts de la medición del techo. Un caso sin regla
etiquetado a ojo contamina el número; anotado, se puede aislar.

---

## `es_empresa` — el campo crítico

Es el campo que decide la comparación contra los 3.909 posts del análisis
publicado. Si este campo está mal definido, nada de lo que sigue vale.

**La pregunta no es "¿esto es una empresa?" sino: ¿este comentario fue puesto
ahí para contratar a alguien?**

### Leé quién busca a quién

Estos posts mezclan **credenciales de la empresa** con **la vacante**, y las
credenciales suelen venir primero y ocupar más texto: inversores, fundadores,
exits, clientes conocidos, crecimiento, rondas.

> "Backed by a founder with $1B+ exits and growing fast, 3x YoY growth.
> Looking for NY-based engineers (hybrid)."

El fundador es **quien financia**: es una credencial. La vacante es la segunda
frase. La vacante casi siempre trae un verbo de búsqueda — *looking for,
hiring, we need, join us, we're expanding* — y es más corta que el párrafo que
la rodea.

### Cuenta como empresa (`s`)

- Una empresa listando uno o más puestos, con o sin link.
- Una empresa que solo linkea su página de empleos, sin detallar el puesto.
  El post existe para contratar; que esté incompleto es otra cosa.
- Una agencia o reclutador contratando **para un cliente**. El post busca
  cubrir un puesto real. (Que el hilo lo prohíba no cambia qué es: las reglas
  del hilo no son nuestra definición.)
- Un fundador solo, buscando su primer empleado.
- Un puesto no técnico (ventas, diseño, operaciones) en cualquier empresa.
- **Cualquier forma de vínculo remunerado**: full-time, part-time, contract,
  1099, freelance, por hora, pasantía paga. Lo que excluye es la ausencia de
  remuneración, no la forma del contrato — el mismo criterio que para
  cofundador.
- Una consultora contratando **para un cliente**. Hay vacante real.
- Una empresa **no** estadounidense. El corpus no se filtra por país acá.
- Un post de contratación mal formateado, sin pipes, sin link, escrito como
  párrafo corrido. El formato no define la intención.

### No cuenta (`n`)

- Alguien ofreciéndose a trabajar ("I'm available", "looking for a role").
  Eso pertenece al hilo de candidatos, no a este.
- Un comentario sobre el hilo: pidiendo que se use un tag, quejándose del
  formato, agradeciendo, comentando una tendencia.
- Alguien que construyó una herramienta para navegar el hilo y la comparte.
  Útil, pero no está contratando.
- Una pregunta a otro comentario ("¿esto es remoto?", "¿sponsorean visa?").
- `[flagged]`, `[dead]`, texto vacío, una sola palabra sin sentido.
- Un post pidiendo colaboradores **sin pago** para un proyecto propio.
  Si no hay puesto remunerado, no es contratación.

### El caso límite que hay que decidir ahora

**Un post que busca cofundador.** No es un empleo: no hay salario ni relación
de dependencia, es sociedad. **Decisión: `n`.** Se anota el `id` en "Casos sin
regla" para poder medir cuántos fueron y rehacer el conteo si la decisión se
discute.

> `Camera Search - Remote - Co-Founders - 5-20% equity` → `n`

**Pero si el post declara sueldo además del equity, va `s`.** Ahí hay
remuneración y es un empleo con un título vistoso. El criterio es la
remuneración, no la palabra "founder": "Founding Engineer" con salario es un
empleo (y de hecho suele serlo), "Co-Founder, 5-20% equity" no.

### Que no diga sueldo NO es motivo de `n`

La mayoría de los posts de trabajo no dicen el sueldo. Para marcar `n` hace
falta una **señal positiva** de que no es empleo:

- equity en lugar de sueldo (cofundador),
- una sociedad o colaboración entre pares, explícita,
- alguien ofreciéndose a trabajar,
- que no haya vacante alguna.

La ausencia de información sobre el pago es lo normal, no una pista.

### El caso más difícil hasta ahora: "coding partner"

> *"I am the main coder on the project and I'm looking for a coding partner to
> help spread the load... Project is solid financially."* — Language Reactor

**Decisión: `s`, con el `id` anotado.** A favor: está en un hilo cuya regla es
"solo posteeá si contratás"; "help spread the load" es trabajo para el proyecto
de él; aclarar que el proyecto es sólido financieramente se dice porque el
candidato va a preguntar si hay plata; y **no ofrece equity**, que es lo que
distinguía a los casos de cofundador. En contra: "partner", y la invitación a
escribirle si tenés un proyecto que se solapa, que suena a fusión.

Gana `s`, pero queda contado aparte. Si aparecen varios así, se reporta el
número con y sin ellos.

### Si no encontrás la vacante, es `n`

Un post sin puesto no es "un puesto con datos faltantes": es la ausencia de un
puesto. No se reconstruye ni se le da el beneficio de la duda. El sistema de la
etapa 3 tampoco va a poder, y la referencia tiene que estar hecha con la misma
información que va a tener él.

> `India(Guna,Madhya Pradesh), remote` → `n`

---

## `pide_ia`

`s` si el post menciona, como parte de lo que busca o de lo que la empresa
hace, cualquiera de: IA, machine learning, deep learning, LLMs, NLP, visión por
computadora, data science, data engineering, MLOps, o un framework del rubro
(PyTorch, TensorFlow, LangChain, vLLM, Hugging Face…).

**Decisión que hay que fijar: basta con que la empresa sea del rubro, o el
puesto tiene que pedirlo?**

Se etiqueta `s` si **el puesto** lo pide o si **la empresa es de IA y el puesto
es técnico**. Un puesto de ventas en una empresa de IA va `n`: la demanda que
el proyecto mide es de gente que construye estas cosas, no de gente que trabaja
cerca de ellas.

Un "usamos Copilot internamente" va `n`. Usar una herramienta no es construir.

### Dos reglas que protegen este campo de inflarse

**Un feature del producto no es un skill pedido.** Si el párrafo de la empresa
dice que el producto hace "anomaly detection" o "pattern analysis" pero el
stack no tiene nada de ML y el puesto no lo pide, va `n`. Describir lo que el
producto hace no es pedir que el candidato lo construya.

**Una base de datos en el stack no es data engineering.** Postgres, MySQL o
Redis no cuentan. Sí cuentan pipelines, warehouses, orquestación (Airflow,
dbt), streaming y procesamiento a escala.

**Un ERP o un sistema de negocio tampoco.** "Data person con experiencia en
CloudSuite de Infor" es integración de sistemas, no data engineering. Y la
palabra "data" en el título no alcanza: si alcanzara, el campo se llenaría de
falsos positivos y dejaría de medir demanda de IA para medir la frecuencia de
una palabra.

Por qué estas dos reglas importan tanto: sin ellas, `pide_ia` daría `s` en casi
todos los posts —todo el mundo tiene una base de datos— y el número central
del proyecto no significaría nada. Un campo que dice "sí" siempre no mide.

---

## `n_puestos`

Cuántos puestos **distintos** lista el post.

- "Senior Backend Engineer" → `1`
- "Backend, Frontend y DevOps" → `3`
- "Engineers (multiple roles)" sin enumerar → `1`. No se adivina.
- Un link a la página de empleos sin enumerar → `1`.
- "Lead Full-Stack Engineer" → `1`. Un título solo, aunque contenga lead,
  senior o staff. **Se cuentan vacantes, no palabras de seniority.**

El sesgo a evitar: inflar contando sinónimos. "Software Engineer / Developer"
es un puesto escrito de dos maneras, no dos puestos.

### La contradicción que tenía esta guía (corregida el 27/10/2026)

Esta sección decía a la vez *"distinto nivel es distinto puesto → 2"* y
*"un título solo con lead/senior/staff → 1"*. El patrón más común del corpus,
**"Senior / Lead Software Engineers"**, dispara las dos reglas a la vez. Fue
el motivo principal de que `n_puestos` midiera kappa 0,58 en el doble ciego:
no era inconsistencia del etiquetador, era la guía pisándose sola.

**Regla que la reemplaza: se cuentan FUNCIONES, no niveles. El separador
decide.**

| frase | valor | por qué |
|---|---|---|
| "Senior / Lead Software Engineers" | `1` | una función, banda de nivel |
| "Senior **and** Staff Backend Engineers" | `2` | "and" enumera dos vacantes |
| "C++/Runtime **OR** Dart/Cloud Engineers" | `2` | dos stacks = dos funciones |
| "Backend, Frontend y DevOps" | `3` | tres funciones |
| "Software Engineer / Developer" | `1` | sinónimos de la misma función |

Barra o "OR" **entre niveles** → `1`. Barra, "OR", coma o "and" **entre
funciones o stacks distintos** → se cuenta cada una.

> **Esta corrección es POSTERIOR a la medición del techo.** No se puede usar
> para reclamar un kappa mejor sobre los mismos 80 posts: él ya sabe en cuáles
> dudó. Para volver a medir `n_puestos` harían falta posts nuevos.

---

## `remoto`

- `r` remoto: dice REMOTE, remote-first, work from anywhere, o similar.
- `h` híbrido: dice hybrid, o pide N días en oficina.
- `p` presencial: dice ONSITE, in-office, o nombra una ciudad **y** exige
  presencia.
- `0` no dice.

**Nombrar una ciudad no es decir presencial.** "Acme | Berlin | REMOTE" es `r`.
Muchos posts ponen la ciudad de la sede y el puesto es remoto. Si solo aparece
una ciudad, sin palabra sobre modalidad, va `0`.

**El test cuando hay ciudad y ninguna palabra de modalidad: ¿la oración le
atribuye la ubicación al PUESTO o a la EMPRESA?**

| frase | de quién habla | valor |
|---|---|---|
| "All positions are in Berkeley, California" | del puesto | `p` |
| "This role is based in San Carlos" | del puesto | `p` |
| "Looking for NY-based engineers" | del puesto | `p` |
| "HQ in SF" · "we're a Berlin company" | de la empresa | `0` |
| "Acme \| Berlin \| REMOTE" | la modalidad está dicha | `r` |

Si dice "REMOTE (US only)" → `r`. La restricción geográfica no lo deja de ser.
Si dice remoto **e** híbrido para puestos distintos → `h`.

---

## `seniority`

El nivel del puesto **más junior** que lista el post. Si busca junior y senior,
lo relevante para la pregunta del proyecto es que hay una puerta de entrada.

- `j` junior: junior, entry-level, new grad, intern, 0–2 años.
- `m` medio: mid-level, 3–5 años, o "Engineer" sin calificar **cuando el post
  pide años de experiencia en ese rango**.
- `s` senior: senior, staff, principal, lead, 5+ años.
- `0` no dice.

**"Founding Engineer" va `0`.** Marca el alcance del rol, no el nivel: no dice
años ni usa una palabra de nivel. Lo mismo "Engineer #2" o "early engineer".

**"Software Engineer" sin más va `0`, no `m`.** Inferir nivel de un título
pelado es exactamente el tipo de dato inventado que este proyecto mide en vez
de producir. Se espera que `0` sea mayoría acá, y eso es un resultado.

### Posts con varios puestos

La definición de arriba —"el nivel del puesto más junior"— asumía sin decirlo
que **todos** los puestos declaran nivel. En un post que lista ocho vacantes,
cuatro pueden declarar (Senior, Head of, Manager) y cuatro ser títulos pelados.

**Regla: el nivel más junior entre los que lo declaran EXPLÍCITAMENTE. Los
títulos pelados no cuentan ni para arriba ni para abajo. Si ninguno declara,
`0`.**

Por qué así: la pregunta del proyecto es si hay una puerta de entrada para
alguien sin años de experiencia. Que un "Software Engineer" pelado *pudiera*
ser junior no es evidencia de que lo sea — es ausencia de evidencia, y las dos
cosas son distintas.

Para los otros campos en posts multi-puesto:

- `pide_ia` → `s` si **cualquiera** de los puestos listados califica.
- `remoto` → `h` si el post mezcla modalidades (hybrid para unos, remote para
  otros).
- `n_puestos` → la cantidad de vacantes enumeradas.

---

## `visa`

- `s` dice que patrocina (visa sponsorship, H1B, relocation + visa).
- `n` dice explícitamente que no patrocina, **o exige un estatus migratorio que
  excluye a quien necesita patrocinio**.
- `0` no dice.

### Qué cuenta como `n`

El campo pregunta, en el fondo: ¿puede entrar acá alguien que necesita
patrocinio? Entonces `n` incluye dos mecanismos distintos:

1. **Decisión de la empresa**: "we do not sponsor visas", "must be authorized
   to work in the US without sponsorship".
2. **Restricción legal**: "we can only hire U.S. Persons", control de
   exportaciones, ITAR, "citizens or green card holders only". Común en todo el
   segmento de IA ligado a defensa y aeroespacial. No es una preferencia de la
   empresa y no se negocia.

Los dos van `n`, porque el efecto sobre el candidato es el mismo.

**Lo que NO es `n`:** decir solo dónde se trabaja. "US-based", "EU timezone",
"LatAm friendly" son ubicación o huso horario, no estatus migratorio. Eso va
`0` salvo que además hable de autorización para trabajar.

Se espera que `0` sea la enorme mayoría.

---

## Reglas generales

1. **Solo el texto del post.** No se abre el link, no se busca la empresa, no
   se usa lo que uno sabe de ella. El sistema de la etapa 3 tampoco va a poder,
   así que medirlo contra una referencia construida con más información que la
   disponible produciría un techo falsamente alto y una precisión falsamente
   baja.
2. **`0` no es pereza, es un dato.** "El post no lo dice" es información sobre
   el corpus.
3. **No releer la etiqueta anterior.** En la pasada 2 el orden es distinto a
   propósito.
4. **Cortar cuando cansa.** `q` guarda. Etiquetar 266 posts de corrido degrada
   el criterio sobre el final, y eso se mediría como inconsistencia tuya cuando
   en realidad es fatiga. Tandas de 40 a 60 están bien.
5. **El tiempo se guarda.** No hay que apurarse: el número sirve para reportar
   el costo humano de la tarea, y un tiempo apurado lo subestima.

---

## Casos sin regla

_Se anota acá el `id` y una línea, durante el etiquetado._

| id | qué pasaba | cómo se etiquetó |
|---|---|---|
| | | |

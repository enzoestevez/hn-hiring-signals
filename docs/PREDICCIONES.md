# Predicciones registradas antes de correr

Este archivo se escribe **antes** de ejecutar cada etapa, no después.

## Por qué existe

Hasta el proyecto 03 el método era: corro, veo qué sale, y después explico el
resultado. El problema es que un resultado inesperado y un bug se parecen, y
cuando ya viste el número es tardísimo para distinguirlos: cualquier número
admite una explicación convincente inventada a posteriori.

Así que acá queda asentado, antes de correr, y con fecha:

1. **Qué número espero** y de dónde saco ese rango.
2. **Qué resultado significaría que el código miente** — la *firma de falla*.
   Distinto de un número que no me gusta: un número bajo puede ser verdad.
3. **Qué decisión cambia** según el resultado. Si ninguna, la corrida no vale
   la pena y no se hace.

Lo tercero es el filtro más duro. En los proyectos anteriores corrí cosas que
no cambiaban ninguna decisión.

El código imprime el veredicto contra estos rangos automáticamente
(`veredicto()` en cada script), para que la comparación no dependa de mi
memoria ni de mi conveniencia.

> Esto es pre-registro, prestado de la metodología experimental. No lo invento
> yo: en investigación clínica se registra la hipótesis antes de ver los datos
> justamente para que no se pueda mover el blanco después. La versión barata de
> eso es este archivo.

---

## Etapa 1 — Corpus crudo

**Fecha de registro:** 2026-10-23, antes de la primera corrida.
**Script:** `src/bajar.py`
**Costo:** USD 0.00 (API pública, sin clave, sin LLM)

### Qué espero

| magnitud | rango esperado | de dónde sale |
|---|---|---|
| hilos "Who is hiring?" oct-2025 → oct-2026 | 12–14 | son mensuales: 13 meses inclusive |
| posts de primer nivel (empresas) | 3.500–4.200 | el análisis publicado reporta 3.909 |
| posts borrados o vacíos | 1–8% del total | moderación normal de HN |
| fallas de descarga | 0 | la API es pública y estable; si falla, es mi código |

### Firmas de falla — qué significaría que el código miente

- **Menos de 2.000 posts en total.** No es que HN se vació: es que no estoy
  resolviendo los `kids` de cada hilo, o estoy paginando mal.
- **Todos los hilos con exactamente la misma cantidad de posts.** Eso no pasa
  en la realidad. Es truncamiento a un tamaño de página fijo.
- **Un hilo con 0 posts.** No es un mes sin contrataciones: es captura fallida.
- **Muchos comentarios `null`.** Son borrados, y se cuentan **aparte**. Si los
  mezclo con los válidos infló el denominador y toda tasa posterior queda mal.
- **`descendants` usado como cantidad de empresas.** `descendants` cuenta todos
  los comentarios incluidas las respuestas; las empresas son solo los de primer
  nivel. Confundirlos inflaría el corpus un 20–40%.

### Qué decisión cambia

- **Dentro del rango** → sigo a la etapa 2 (muestra etiquetada a mano) sobre
  este corpus.
- **Sustancialmente menos, y no es ninguna de las firmas de falla de arriba** →
  eso es un **hallazgo**, no un accidente: significa que los números publicados
  no se reproducen, y la etapa 2 tiene que medir la diferencia y explicarla
  antes de analizar nada.
- **Alguna firma de falla** → arreglo el código y vuelvo a correr. No se
  reporta ningún número hasta que la firma desaparezca.

### Lo que esta etapa NO contesta

Nada sobre el mercado laboral. Ni cuántas empresas piden IA, ni si hay menos
puestos junior, ni nada. Contesta una sola pregunta: **¿tengo el corpus?**
Cualquier conclusión sacada acá sería leer datos sin validar, que es
exactamente el problema que el proyecto vino a atacar.

### Resultado

_Corrida `--listar` del 2026-10-23. **No se tocó nada de lo registrado arriba.**_

| magnitud | esperado | obtenido | veredicto |
|---|---|---|---|
| hilos | 12–14 | **13** | dentro |
| comentarios de primer nivel | 3.500–4.200 | **4.648** | **fuera, +10,7% sobre el techo** |
| conteos idénticos entre hilos | no | 11 valores distintos de 13 | sin falla |
| hilos en 0 | ninguno | ninguno (mínimo 265) | sin falla |
| total por debajo de 2.000 | no | 4.648 | sin falla |
| fallas de descarga | 0 | 0 | dentro |

Por mes, más nuevo primero: 319, 300, 265, 311, 363, 378, 379, 363, 451, 300,
404, 434, 381. Suma 4.648. Los 13 hilos suman **6.114 `descendants`** contra
4.648 de primer nivel: esos 1.466 (24%) son respuestas a comentarios, no
empresas. Usar `descendants` como cantidad de empresas —el atajo obvio—
habría inflado el corpus un 32%.

### Por qué falló la predicción, y de quién es la culpa

**No es un bug: es un error mío al registrar la predicción, y tiene nombre.**

Anclé el rango a 3.909, que es un conteo **filtrado** de posts de empresas, y
después medí `len(kids)`, que es un conteo **sin filtrar** de comentarios de
primer nivel. No son la misma magnitud. Comparé dos números que no son el mismo
número — el mismo error que el proyecto 01 me enseñó a no cometer cuando
estableció que nunca se comparan variantes sobre distinto `n`.

La corrección metodológica, para las etapas que siguen: **toda predicción tiene
que decir qué magnitud exacta se mide**, no solo el número esperado. "Posts" no
es una magnitud; "comentarios de primer nivel, sin filtrar borrados ni
meta-comentarios" sí lo es.

Lo correcto habría sido registrar dos rangos: comentarios de primer nivel
(cota superior) y posts de empresas tras filtrar (la magnitud comparable).

### Decisión tomada

Sigo al comando 2. **4.648 no es "más empresas que las publicadas": es una cota
superior.** Las empresas son ≤ 4.648, y los 739 de diferencia contra 3.909
tienen una forma concreta y medible. Ese reparto es el objeto de la próxima
predicción.

No se reporta ningún número sobre el mercado laboral con este dato.

---

## Etapa 1b — De qué están hechos los 739 de diferencia

**Fecha de registro:** 2026-10-23, **antes** de correr el comando 2.
**Script:** `src/bajar.py` (sin `--listar`)
**Costo:** USD 0.00

### El reparto en disputa

Para que 4.648 comentarios de primer nivel se conviertan en 3.909 posts de
empresas hay que descontar 739 (15,9%), y solo pueden venir de cuatro lugares:

| descuento | qué es | lo mide |
|---|---|---|
| borrados (`deleted`) | el autor o un moderador lo borró | comando 2, gratis |
| muertos (`dead`) | flaggeado por la comunidad | comando 2, gratis |
| vacíos | existe pero sin texto | comando 2, gratis |
| **meta-comentarios** | alguien preguntando o comentando en el hilo, no contratando | **etapa 2, a mano** |

### Qué espero

- borrados + muertos + vacíos: **1–8%** del total (2 a 8 puntos de los 15,9).
- por lo tanto los meta-comentarios tendrían que explicar **8 a 14 puntos**
  para llegar a 3.909.

### La predicción filosa

**Creo que 3.909 está bajo, y que vamos a terminar con más empresas que eso.**

Razón: 8 a 14% de meta-comentarios es mucho para estos hilos. Los moderadores
de HN los matan activamente, y el hilo tiene una convención de formato fuerte
que la gente respeta. Mi prior es que los meta-comentarios están en 2–5%.

Si eso es cierto, el faltante no son comentarios que no eran empresas: son
**posts de empresas que la extracción con LLM descartó en silencio por no
poder parsearlos** — que es el modo de falla típico de una extracción sin
validar, y la razón exacta por la que este proyecto mide el techo humano antes
de extraer nada.

### Cómo se falsea

Si borrados + muertos + vacíos sale alto (digamos 10%) y los meta-comentarios
etiquetados a mano en la etapa 2 dan 6%, los 739 quedan explicados sin ninguna
pérdida silenciosa, y **mi predicción está mal**. Queda registrado así para que
no pueda reinterpretarlo después.

### Qué decisión cambia

- **Explicado sin pérdida** → el corpus publicado es correcto, y la
  contribución del proyecto pasa a ser enteramente el segmento IA/datos, que
  ese análisis no abrió.
- **Queda pérdida sin explicar** → hay un hallazgo reportable sobre extracción
  no validada, medido con números propios, y la etapa 3 tiene que cuantificar
  cuántos posts pierde una extracción con LLM y de qué tipo son.

### Firmas de falla del comando 2

- **Borrados por encima del 20%** → probablemente estoy tratando como borrado
  algo que no lo es (un `null` por timeout, por ejemplo). Un `null` por error de
  red y un comentario borrado no son lo mismo y no pueden caer en el mismo
  contador.
- **El total con texto no cierra** con 4.648 − borrados − vacíos → se perdieron
  posts en la escritura.
- **Reanudar y que el total cambie** → el salteo por id está mal y hay
  duplicados o faltantes.

### Resultado

_Corrida completa del 2026-10-23. USD 0.00._

| magnitud | esperado | obtenido | veredicto |
|---|---|---|---|
| posts con texto | 4.280–4.600 | **4.054** | **fuera, −226 bajo el piso** |
| borrados + muertos | 1–8% | **593 = 12,8%** | **fuera, +4,8 puntos** |
| vacíos | <1% | 1 = 0,02% | dentro |
| nulos | — | 0 | — |
| fallos de red | 0 | 0 | dentro |
| cierra 4.648 − descartes | sí | 4.054 + 594 = 4.648 | **CIERRA exacto** |

**Las dos predicciones falladas son un solo error, no dos.** `posts con texto
= 4.648 − descartes`: una determina a la otra. Contarlas como dos fallas
sería contarme el mismo error dos veces, que es la clase de inflación que este
archivo existe para evitar — también cuando el número inflado es mi tasa de
error y no un resultado.

Subestimé el borrado por un factor de ~2. No tenía base empírica para el rango
1–8%: lo puse por intuición sobre "moderación normal". Una predicción sin
mecanismo detrás es un número inventado con cara de rigor.

### La predicción filosa, en camino a ser falsada

Predije que 3.909 estaba **bajo** y que había pérdida silenciosa. Resultado:
los descartes explican 594 de los 739, y los 145 restantes equivalen a un
**3,1% de meta-comentarios** — dentro de mi propio rango registrado de 2–5%.
El número publicado **se reproduce** dentro del 3,7%.

Pero el agregado no distingue dos mundos:

- **Mundo A:** los meta-comentarios son ~3,1% y no hay pérdida. Mi predicción
  está mal.
- **Mundo B:** los meta son ~6% y la extracción además perdió ~134 posts en
  silencio. Los dos errores se cancelan parcialmente y llegan al mismo 3.909.

Dos números que cierran en el agregado no prueban que cada parte sea correcta.
**Regla de decisión, registrada ahora, antes de etiquetar nada:**

| tasa de meta-comentarios medida a mano (etapa 2) | conclusión |
|---|---|
| 2,5–4% | predicción mía **falsada**; el número publicado reproduce |
| > 5% | hay pérdida silenciosa de ~200+ posts; mi predicción se sostiene |
| < 2% | el número publicado está **alto**: contó cosas que no eran empresas |

### Decisión tomada

Antes de la etapa 2 hay que correr la etapa 1c: el 12,8% de borrado abre una
amenaza a la pregunta central del proyecto, y es gratis medirla.

---

## Etapa 1c — ¿Hay sesgo de supervivencia en el corpus?

**Fecha de registro:** 2026-10-23, **antes** de correr `src/descartes.py`.
**Costo:** 594 llamadas a una API pública. USD 0.00.

### La amenaza

Un 12,8% de borrado es mucho, y un post desaparece por dos mecanismos que se
comportan distinto en el tiempo:

- **Moderación** (reclutadores, gente buscando trabajo): pasa en días. Tasa
  aproximadamente **constante** por hilo.
- **El autor lo borra al llenar el puesto**: puede pasar en cualquier momento,
  así que **se acumula con la edad del hilo**.

Si el segundo mecanismo pesa, el corpus tiene **sesgo de supervivencia**:
octubre 2025 nos llega con menos posts de los que tuvo, y octubre 2026 con casi
todos. Entonces cualquier tendencia mensual calculada sobre los sobrevivientes
está inclinada **hacia arriba en los meses recientes**, y podría mostrar
crecimiento donde hubo caída.

Eso no es un detalle de limpieza de datos: **la pregunta central del proyecto es
si la demanda de perfiles de IA se movió en 13 meses.** Un sesgo que corre
justo en contra de esa medición la invalida si no se mide.

Hueco propio que lo hizo necesario: `bajar.py` contó los descartes pero no
guardó a qué hilo pertenecía cada uno.

### Qué espero

**Gradiente positivo de al menos 3 puntos** entre los 3 hilos más viejos y los
3 más nuevos. Mecanismo: el componente de moderación es constante, el de
borrado por autor se acumula, así que la suma tiene que crecer con la edad.

### Firmas de falla

- **Gradiente invertido** (los nuevos descartan más) → no es imposible: el hilo
  del mes en curso todavía está recibiendo spam y moderación activa. Si pasa,
  el hilo más nuevo probablemente no esté cerrado y habría que excluirlo.
- **Un mes descartando más del 25%** mientras el resto ronda el 12% → ese hilo
  se revisa a mano antes de usarlo.
- **Descartes con estado `tiene_texto`** → bug: ese post debería estar en
  `posts.jsonl` y no está.
- **`fallo_red` > 0** → el reparto está incompleto y no se puede leer el
  gradiente todavía.

### Qué decisión cambia

- **Hay gradiente** → la etapa 5 reporta la tendencia **corregida por
  supervivencia**, o no reporta tendencia. Y es un hallazgo metodológico
  propio: cualquier análisis de estos hilos que ignore el borrado diferencial
  sobrestima los meses recientes.
- **No hay gradiente** → predicción mía fallida otra vez, el borrado es
  constante, y la tendencia se puede leer sobre los sobrevivientes. **Se
  reporta igual**: un sesgo descartado por medición vale más que un sesgo que
  nunca se miró.

### Resultado

_2026-10-23. **Costo real: USD 0.00 y cero llamadas.**_

El gradiente salía de restar los sobrevivientes de `posts.jsonl` a los `kids`
de `hilos.json`, datos que ya estaban en disco. **Escribir un script de 594
llamadas para medirlo fue un error mío**: tuve el número todo el tiempo.

| magnitud | esperado | obtenido | veredicto |
|---|---|---|---|
| gradiente viejos − nuevos | >= +3 puntos | **−7,0 puntos** | **FALLADA, y con el signo invertido** |
| meses por encima del 25% | ninguno | ninguno (máximo 17,0%) | dentro |

Tasa de descarte por mes, del más viejo al más nuevo: 10,5 · 9,7 · 6,7 · 14,7 ·
9,1 · 12,7 · 13,2 · 15,9 · 13,8 · 16,7 · 14,3 · 17,0 · 16,6 %. Sube del 9% al 16%
de forma casi monótona. Los hilos **nuevos** descartan más, no los viejos.

Mi mecanismo estaba mal. Razoné que el borrado por autor se acumula con la edad
y que por lo tanto los hilos viejos perderían más. El dato dice lo contrario.

### Dos explicaciones, y no puedo elegir con estos datos

- **(A) Moderación creciente.** HN se puso más estricto, o los hilos recientes
  todavía reciben spam de reclutadores que se flaggea en días.
- **(B) HN purga del array `kids` los comentarios borrados pasado un tiempo.**
  Los hilos viejos vendrían **ya podados**: los descartes desaparecieron del
  numerador y del denominador a la vez, y por eso parecen descartar menos.

**(B) es peor que la amenaza que yo había predicho.** Significaría que para los
meses viejos el denominador verdadero es **desconocido** — no se puede ni contar
lo que falta — y entonces los conteos mensuales **no son comparables en el
tiempo**, que es exactamente lo que la etapa 5 necesita comparar.

La amenaza identificada era real; el signo y el mecanismo que le atribuí, no.

### Decisión tomada

Correr la etapa 1d: el reparto `borrado` vs `muerto` por mes discrimina entre
(A) y (B), y eso sí necesita las 594 llamadas. Ninguna tendencia mensual se
reporta hasta tener ese reparto.

---

## Etapa 1d — ¿Moderación creciente o purga por antigüedad?

**Fecha de registro:** 2026-10-23, **antes** de correr `src/descartes.py`.
**Costo:** 594 llamadas. USD 0.00.

### El test

`deleted` es el autor borrando su propio post. `dead` es la comunidad
flaggeándolo. Son mecanismos distintos y se comportan distinto en el tiempo.

Se mide la **proporción de `muerto` sobre los descartes** (no sobre los `kids`:
la pregunta es de qué están hechos los descartes, no cuántos hay).

### Qué espero

**La purga es real (B).** Predigo que la proporción de `muerto` entre los
descartes es **más alta en los 3 hilos nuevos que en los 3 viejos, por al menos
10 puntos**, porque los `muerto` viejos ya fueron purgados de `kids`.

### Cómo se falsea

Sin diferencia clara → (B) queda sin apoyo y (A) explica el −7,0. Sería mi
**segunda predicción fallada en esta etapa**, y es la buena noticia: si nada se
purga, el denominador de cada mes es confiable.

### Firmas de falla del script

- descartes con estado `tiene_texto` → bug: ese post debería estar en `posts.jsonl`.
- `fallo_red` > 0 → el reparto está incompleto, no se lee todavía.
- diferencia invertida (los viejos con más `muerto`) → no tengo mecanismo para
  eso. Se mira una muestra a mano antes de usar el corpus. **Un resultado sin
  mecanismo no se reporta como hallazgo.**

### Qué decisión cambia

- **(B) apoyada** → la etapa 5 **no** puede reportar tendencia cruda de posts
  por mes. Sí puede comparar **proporciones dentro de cada mes** (qué fracción
  de los posts de ese mes pide IA), porque el sesgo afecta numerador y
  denominador juntos. El análisis se para ahí.
- **(A) apoyada** → la tendencia cruda es legible, declarando que el descarte
  sube del 9% al 16% y corrigiendo por eso.

En los dos casos queda prohibido lo mismo: **leer la caída de 341 a 266 posts
mensuales como caída de contrataciones.** Eso no está medido.

### Resultado

_2026-10-23. 594 llamadas, 38 s, USD 0.00._

| magnitud | esperado | obtenido | veredicto |
|---|---|---|---|
| `%muerto` nuevos − viejos | >= +10 puntos | **+2,0 puntos** | **FALLADA** |
| descartes con `tiene_texto` | 0 | 0 | dentro |
| `fallo_red` | 0 | 0 | dentro |
| meses por encima del 25% de descarte | ninguno | ninguno | dentro |

Cuatro predicciones registradas en la etapa 1, **cuatro falladas**.

### El test estaba mal diseñado, y eso es peor que una predicción fallada

Si la purga eliminara `deleted` y `dead` en proporciones parecidas, **la
proporción de `muerto` no se movería.** Un resultado plano es compatible con
"no hay purga" **y** con "hay purga proporcional". Escribí un test ciego a una
de sus dos alternativas: asumí sin decirlo que la purga tendría que ser
selectiva. Equivocarse en un número es barato; escribir un test que no puede
distinguir sus propias hipótesis invalida la conclusión, no el número.

### Y la etiqueta (A) describe mal sus propios datos

Tasas separadas sobre `kids`, 3 viejos → 3 nuevos:

| componente | viejos | nuevos | cambio |
|---|---|---|---|
| `borrado` (el autor borra) | 6,6% | 11,7% | **+5,0 pts** |
| `muerto` (la comunidad flaggea) | 2,2% | 4,3% | +2,1 pts |

El driver es el autor borrando, no la moderación. "Moderación creciente" no es
lo que pasa.

### Segundo test de purga, independiente y gratis

Si `kids` se poda y `descendants` queda congelado, la razón respuestas/`kids`
se infla en los hilos viejos. Dio **plano**: 0,302 en los 3 viejos contra 0,315
en los 3 nuevos (+0,013).

**Supuesto no verificado:** que `descendants` no se decremente cuando se borra
un comentario. Si se recalcula, este test es nulo. Queda declarado.

### Lo que quedó sin resolver, dicho como tal

Si el autor pudiera borrar en cualquier momento, los hilos viejos tuvieron 12
meses más de oportunidad y deberían tener **más** borrados, no menos. El hecho
de plataforma que decidiría esto —si HN tiene ventana limitada para borrar—
se buscó y **no se pudo confirmar**, así que no se asume.

**Mecanismo: indeterminado.**

### Decisión tomada

**No se espera a resolver el mecanismo. Se elige el análisis válido bajo todas
las hipótesis que sobreviven.**

| análisis | válido con purga | válido sin purga | se usa |
|---|---|---|---|
| conteo crudo de posts por mes, comparado entre meses | no | sí | **no** |
| proporción dentro de un mes (qué fracción de los posts de ese mes pide IA) | sí | sí | **sí** |

La proporción intra-mes es robusta porque el sesgo toca numerador y denominador
juntos y se cancela. Es el eje del proyecto a partir de acá.

**2026-10 queda excluido** del análisis: es el mes en curso y el hilo sigue
abierto, recibiendo posts y moderación. Su 16,6% de descarte no es final.

Corpus utilizable: **3.788 posts, 12 meses cerrados** (oct-2025 a sep-2026).

---

## Cierre de la etapa 1

| | |
|---|---|
| hilos | 13 (12 utilizables) |
| comentarios de primer nivel | 4.648 |
| con texto | 4.054 |
| descartados | 594 (12,8%): 451 borrados, 142 muertos, 1 vacío |
| cierre aritmético | exacto |
| costo | USD 0.00 |
| predicciones registradas | 4 |
| predicciones acertadas | **0** |

Las cuatro fallas, y qué cambió el método en cada una:

1. **Rango anclado a la magnitud equivocada** (3.500–4.200 contra 4.648). Toda
   predicción ahora declara **qué magnitud exacta** se mide, no solo el número.
2. **Tasa de borrado subestimada al doble** (1–8% contra 12,8%). El rango no
   tenía mecanismo detrás: era intuición con cara de rigor. Ahora toda
   predicción declara su mecanismo, que es lo que la vuelve falsable.
3. **Gradiente de supervivencia con el signo invertido** (≥+3 contra −7,0).
   Y el número salía gratis de datos que ya estaban en disco: escribí un
   script de 594 llamadas para medir algo que ya tenía. Antes de escribir un
   script, se revisa qué contestan los datos existentes.
4. **Test ciego a una de sus alternativas.** Todo test nuevo declara ahora qué
   resultado **no** podría distinguir.

Cero de cuatro no es un mal resultado de la etapa: es el resultado de haber
escrito las predicciones antes. En los proyectos 01 a 03 estas cuatro
equivocaciones existieron igual y ninguna quedó registrada.

---

## Etapa 2 — Techo humano y muestra etiquetada

**Fecha de registro:** 2026-10-23, **antes de etiquetar el primer post.**
**Definiciones:** `docs/GUIA-ETIQUETADO.md`, cerrada antes de empezar.
**Muestra:** 266 posts (146 del estrato sospechoso completo + 120 del limpio),
80 de ellos etiquetados dos veces. 346 juicios. Costo: horas humanas, USD 0.00.

### El diseño de muestra que descarté, y por qué

Primer intento: estratificar por **largo** del texto, sobre-representando los
posts cortos. Dio **EE 1,50%** etiquetando 246 posts, cuando tomar esos mismos
246 al azar da **1,25%**. El diseño "inteligente" era peor que el azar.

Error de base: estratificar ayuda solo si la clase rara se concentra en un
estrato que **pesa** en el corpus. Los posts de menos de 150 caracteres son 46
de 3.788 — el 1,2%. Aunque todos fueran meta-comentarios explicarían 1,2 de los
~3 puntos; el resto está en los estratos largos, donde muestreé fino.

Lo detectó el propio script, porque el veredicto compara contra el azar simple.
**Un diseño que no se compara con la alternativa trivial no se puede defender.**

Segundo intento: estratificar por las **4 señales de la convención del hilo**
(URL, mail, `|`, vocabulario de contratación). Con 0 o 1 señal quedan 146 posts
(3,9%), y ahí sí están los meta-comentarios. Se toma ese estrato **completo**,
que anula su varianza.

Bug de encoding que casi arruina esto: la API escapa las barras de las URLs
como `&#x2F;`, así que buscar `https://` sobre el HTML crudo da 28,6% en vez de
85,8%. Posts de empresa bien formateados caían en "sospechoso". Lo agarré
imprimiendo ejemplos, no mirando el porcentaje.

### El filtro es un instrumento de muestreo, no un clasificador

No decide si un post es empresa: decide con qué probabilidad entra en la
muestra. Todo post del corpus tiene probabilidad de inclusión **conocida y
mayor que cero**, así que el estimador es **no sesgado aunque el filtro sea
malo**. Un filtro malo cuesta precisión, nunca sesgo.

Usarlo como clasificador —"0 señales, entonces meta"— daría un número basura e
incomprobable. Es exactamente el error del análisis publicado.

### Qué espero

| magnitud | esperado | de dónde sale |
|---|---|---|
| `p_limpio`: meta que se le escapan al filtro | <= 0,5% | las 4 señales deberían tener alta cobertura |
| tasa de meta reponderada | 2–5% | registrado en la etapa 1b |
| acuerdo entre pasadas: `es_empresa` | >= 97% | binario y con definición cerrada |
| `pide_ia` | >= 90% | binario, pero el límite "empresa de IA / puesto técnico" es resbaladizo |
| `visa` | >= 92% | casi siempre `0` |
| `remoto` | >= 88% | la trampa ciudad-vs-modalidad |
| `n_puestos` | >= 80% | contar sinónimos es el error fácil |
| `seniority` | >= 78% | el más difícil: títulos pelados |
| `seniority` = "no dice" | >= 50% del corpus | los títulos no declaran nivel |
| `visa` = "no dice" | >= 85% | |
| mediana de tiempo | <= 45 s/post | en el proyecto 01 fueron 113 s, con documentos mucho más largos |

### El techo se va a partir, y por eso se mide por estrato

Del proyecto 01: el techo humano no fue un número solo. Se partió por formato
de documento, 98,7% contra 72,7%, y el promedio global era una mentira cómoda.

**Predicción: el acuerdo en el estrato sospechoso va a ser al menos 5 puntos
más bajo que en el limpio.** Si se cumple, el techo global no se reporta solo.

### Firmas de falla

- **Acuerdo del 100% en cualquier campo** → sospechoso, no excelente. O el
  campo es trivial, o la pasada 2 no fue ciega (orden igual, o se vio la
  etiqueta anterior).
- **`es_empresa` por debajo del 90%** → el problema es **mi definición**, no el
  etiquetador. Se reescribe la guía y se vuelve a etiquetar desde cero. No se
  "promedia" entre dos reglas distintas.
- **Un campo con más del 95% de `no dice`** → ese campo no existe en este
  corpus. Sale de la etapa 3: medir precisión sobre un campo ausente no
  significa nada.
- **Suma de pesos distinta de 3.788** → el diseño de muestra está mal y toda
  estimación sale corrida.
- **Tasa cruda informada sin reponderar** → el estrato sospechoso es el 3,9% del
  corpus y el 55% de la muestra. Sin pesos el número sale ~14x inflado.
- **Los "casos sin regla" por encima de 15 posts** → la guía es insuficiente y
  el techo medido mezcla inconsistencia con ambigüedad de la definición.

### Qué decisión cambia

- **Campos con techo por debajo de ~80%** no se usan como objetivo de precisión
  en la etapa 3. No se puede exigirle a un modelo más consistencia que la de la
  referencia contra la que se lo mide.
- **`p_limpio` medido** determina el tamaño de la fase 2: `src/muestrear.py`
  imprime la tabla. No se elige n adivinando.
- **La tasa de meta reponderada** resuelve la regla de decisión de la etapa 1b
  y decide si la contribución del proyecto incluye un hallazgo sobre extracción
  no validada, o es enteramente el segmento IA/datos.

### CORRECCIÓN: la regla de decisión de la etapa 1b tenía las ramas invertidas

Detectado el 2026-10-25, con 165 de 266 etiquetados.

La regla registrada decía:

| tasa de meta | conclusión registrada |
|---|---|
| > 5% | "hay pérdida silenciosa de ~200+ posts" |
| < 2% | "el número publicado está alto" |

**Las dos conclusiones están al revés.** La derivación correcta:

    empresas = comentarios con texto × (1 − tasa_meta) = 4.054 × (1 − tasa)

- tasa **baja** (1%) → empresas ~4.013, **por encima** de 3.909 → el publicado
  quedó **corto** → *eso* es pérdida silenciosa.
- tasa **alta** (7%) → empresas ~3.770, **por debajo** de 3.909 → el publicado
  quedó **largo** → contó comentarios que no eran empresas.

Perder posts da un conteo **menor**, no mayor. Le había puesto "pérdida
silenciosa" a la rama de tasa alta, que es justamente la que indica lo
contrario.

**Si hubiera obedecido la regla escrita, habría reportado la conclusión
opuesta a la que los datos indican.** Y la habría defendido diciendo que estaba
pre-registrada.

La lección, que vale para todo lo que sigue: **una regla pre-registrada hay que
re-derivarla en el momento de aplicarla, no obedecerla.** El pre-registro
protege de mover el blanco después de ver los datos; no protege de haber puesto
el blanco mal. Es la cuarta vez en este proyecto que el error está en el
instrumento y no en el dato.

### Dos bugs más del mismo día

**Pesos planificados en vez de realizados.** `techo.py` reponderaba con el `n`
planificado de cada estrato. Con la muestra a medio etiquetar —y las fracciones
etiquetadas no eran iguales: 63,7% del sospechoso contra 60,0% del limpio— eso
pondera cada estrato por `N_h × fracción_etiquetada` en lugar de por `N_h`.
Corregido a peso efectivo = `N_h / etiquetados_en_h`, que coincide con el
planificado al completarse y es correcto siempre.

**El objetivo de precisión apuntaba a la comparación equivocada.** Registré
EE ≤ 0,65% para separar "tasa 3%" de "tasa 5%". Pero la decisión real es si
3.909 cae fuera de nuestro intervalo, que equivale a preguntar si la tasa supera
**(4.054 − 3.909) / 4.054 = 3,58%**. Con la tasa estimada en 6,6%, lejos de ese
umbral, hace falta mucho menos precisión: ~132 etiquetas del estrato limpio
contra las ~700 que pedía el objetivo original. Siete horas de trabajo manual
para contestar una pregunta que no se hace.

### Lectura parcial con 165 de 266 (2026-10-25)

| magnitud | predicho | obtenido | veredicto |
|---|---|---|---|
| tasa de meta reponderada | 2–5% | **6,62%** IC [2,65%, 11,83%] | **FUERA** |
| `p_limpio` | ≤ 0,5% | **4,17%** (3 de 72) | **FUERA, 8×** |
| mediana de tiempo | ≤ 45 s | 38 s | dentro |
| `seniority` = no dice | ≥ 50% | 41,0% | fuera |
| `visa` = no dice | ≥ 85% | 94,3% | dentro |
| `remoto` = no dice | — | 3,0% | — |

**El filtro de muestreo deja pasar 8 veces más meta-comentarios de los que
predije.** No sesga nada —sigue siendo un instrumento de muestreo con
probabilidades conocidas— pero cuesta precisión: toda la varianza vive en el
estrato limpio, y hay más señal ahí de la esperada.

Empresas estimadas: **3.786**, IC [3.574, 3.946]. **El intervalo contiene
3.909**, así que con estos datos no se puede afirmar que el publicado sobre ni
que falte. No decide todavía, y no se reporta como si decidiera.

### El campo `segundos` está contaminado

Mediana 38 s, **media 141 s**, total 6,5 h para 165 posts. La media es
inservible: el cronómetro sigue corriendo mientras se consulta un caso dudoso,
y esta sesión tuvo ~12 consultas de varios minutos cada una. 165 × 38 s = 1,7 h,
no 6,5.

Se reporta la **mediana**, que es robusta a esas pausas, y queda declarado que
incluso la mediana puede estar algo inflada. La pasada 2 va a dar una medición
más limpia, porque las definiciones ya estarán cerradas y no habrá consultas.

### Límite declarado: la unidad de análisis es el POST, no el PUESTO

Detectado el 2026-10-24, etiquetando, **antes de analizar nada.**

Un post puede listar ocho vacantes de las cuales una pide datos. Como se
etiqueta **un valor por post** y no uno por vacante, lo que este proyecto puede
afirmar es:

- ✅ "qué fracción de los **posts de contratación** menciona IA"
- ❌ "qué fracción de los **puestos** pide IA"

Son dos números distintos y no se pueden intercambiar. El análisis publicado
reportó 3.909 posts **y** 9.194 puestos; etiquetar a nivel post y hablar de
puestos sería inventar.

`n_puestos` permite reportar el conteo de vacantes por separado, pero **no
convierte una etiqueta de post en ocho etiquetas de puesto**. Etiquetar por
vacante exigiría rehacer la muestra con la vacante como unidad, y multiplicar
el trabajo manual por ~2,5 (la mediana de puestos por post). No se hace, y por
eso el límite se declara en vez de disimularse.

Toda afirmación del proyecto dice "posts" donde dice posts.

### Resultado de la pasada 1 — completa, 266/266 (2026-10-26)

| magnitud | predicho | obtenido | veredicto |
|---|---|---|---|
| tasa de meta reponderada | 2–5% | **4,73%** IC [2,32%, 7,83%] | **dentro** |
| `p_limpio` | ≤ 0,5% | **2,50%** (3 de 120) | **FUERA, 5×** |
| mediana de tiempo | ≤ 45 s | **42 s** | dentro |
| `seniority` = no dice | ≥ 50% | 41,5% | fuera |
| `visa` = no dice | ≥ 85% | **94,1%** | dentro |
| `remoto` = no dice | — | 3,7% | — |
| posts de empresa en la muestra | — | 175 de 266 | — |

Meta por estrato: **88 de 146 (60,3%)** en el sospechoso, **3 de 120 (2,5%)** en
el limpio. El filtro concentra, pero deja pasar 5 veces más de lo que predije.

**Sin firma de fatiga:** primeros 53 posts a 46 s de mediana, últimos 53 a 43 s.
Etiquetar en tandas de 40–60 con cortes funcionó. El tiempo total nominal
(13,7 h) sigue contaminado por las consultas; el real es 266 × 42 s = 3,1 h.

### EL RESULTADO PRINCIPAL: el número publicado REPRODUCE

    empresas estimadas = 4.054 × (1 − 0,0473) = 3.862   IC [3.737, 3.960]
    el análisis publicado reporta                        3.909
    diferencia                                             −47  (1,2%)

**El intervalo contiene 3.909.** Con una medición independiente, con techo
humano y con pesos de muestreo, el conteo publicado es correcto.

**Mi predicción filosa queda FALSADA.** Predije que 3.909 estaba bajo por
pérdida silenciosa de la extracción sin validar. No hay evidencia de eso.

Y la regla registrada tenía, además de las ramas invertidas, un **hueco**: no
cubría el intervalo 4–5%, y la tasa cayó justo ahí (4,73%). Tres defectos en una
sola regla de tres líneas: ramas al revés, un hueco sin cubrir, y un objetivo de
precisión apuntado a la comparación equivocada.

### Decisión: SE DEJA DE MEDIR ACÁ

Para que 3.909 quede fuera del intervalo hacen falta **~495 etiquetas del
estrato limpio**: 375 más, unas **4,4 horas** de trabajo manual.

**No se hacen, y la razón no es el cansancio: es que no cambian ninguna
decisión.** La diferencia a resolver son 47 posts sobre 3.909 — el 1,2%.
Aunque el intervalo se angostara, el hallazgo sería "el conteo publicado está
~1% alto", que no es un hallazgo: es coincidencia.

Esta decisión es parte del método, no una concesión. El criterio registrado en
la cabecera de este archivo dice que una corrida que no cambia ninguna decisión
no se hace. Aplica igual cuando la corrida es mi propia curiosidad por cerrar
un intervalo.

### Y lo que SÍ queda como contribución

No es "encontré un error en el análisis publicado". Es mejor y es más raro:

> **Este corpus tiene ahora un conteo validado, y antes no lo tenía.**

El autor del análisis publicado declaró que no había verificado su extracción
contra ninguna muestra a mano. Su número era correcto **y nadie lo sabía**,
empezando por él. Ahora se sabe, con una medición independiente que declara su
propio error.

"Estaba bien" es un resultado cuando antes era una afirmación sin verificar.

### Resultado del techo humano

_(se completa después de la pasada 2)_

| magnitud | esperado | obtenido | veredicto |
|---|---|---|---|
| `p_limpio` | <= 0,5% | | |
| tasa de meta reponderada | 2–5% | | |
| `es_empresa` entre pasadas | >= 97% | | |
| `pide_ia` | >= 90% | | |
| `remoto` | >= 88% | | |
| `n_puestos` | >= 80% | | |
| `seniority` | >= 78% | | |
| `visa` | >= 92% | | |
| acuerdo sospechoso vs limpio | sospechoso >= 5 pts más bajo | | |
| mediana de tiempo | <= 45 s | | |
| casos sin regla | <= 15 | | |

**Decisión tomada:**

---

# ETAPA 2 — TECHO HUMANO (doble ciego, 80 posts) · resultado 27/10/2026

## Lo que registré antes de correrlo

| campo | umbral registrado | medido (acuerdo crudo) | kappa | veredicto |
|---|---|---|---|---|
| `es_empresa` | ≥ 97% | **95.0%** | 0.89 | **fallé** |
| `visa` | ≥ 92% | 96.4% | **−0.01** | "cumple" y no significa nada |
| `pide_ia` | ≥ 90% | **70.9%** | 0.38 | **fallé, por mucho** |
| `remoto` | ≥ 88% | **83.6%** | 0.77 | **fallé** |
| `n_puestos` | ≥ 80% | **72.7%** | 0.58 | **fallé** |
| `seniority` | ≥ 78% | 78.2% | 0.61 | acerté por 0,2 puntos |

**1 de 6.** Y el único que "acerté" lo acerté por dos décimas, que a n=55 es
un post. Con las 5 de la etapa 1 y las 5 de la etapa 2, el acumulado del
proyecto es 1 acierto en 16 predicciones registradas.

## La predicción del estrato: fallé donde los datos hablan

Registré: *"el sospechoso al menos 5 puntos por debajo del limpio"*.

| campo | sospechoso | limpio | brecha | Fisher |
|---|---|---|---|---|
| `es_empresa` | 91.7% | 100.0% | +8.3 | p=0.146 |
| `pide_ia` | 89.5% | 68.8% | **−20.7** | p=0.171 |
| `n_puestos` | 94.7% | 68.8% | **−26.0** | **p=0.037** |
| `remoto` | 89.5% | 87.5% | −2.0 | p=1.000 |
| `seniority` | 73.7% | 81.2% | +7.6 | p=0.726 |

La única brecha que se distingue del ruido **va al revés de lo que predije**.
Mecanismo: el filtro ordena por FORMATO, no por dificultad. Los posts con
pipes y links son más fáciles de *parsear* (contar vacantes, leer modalidad);
los de prosa corrida son más difíciles. Lo que sí es más difícil en el estrato
sospechoso es *clasificar* (`es_empresa`), porque ahí viven los ambiguos.

**Son dos dificultades distintas y yo las traté como una sola.**

Error de diseño aparte: registré un umbral de 5 puntos cuando a n=32 un solo
post vale 3,1 puntos. Registré una predicción más fina que la resolución del
instrumento. Ninguna de las brechas de ±5–8 podía haberse resuelto nunca.

## Lo que salió de LEER los desacuerdos, uno por uno

No alcanza con el número. Los 37 desacuerdos se leyeron con el texto al lado.

**`es_empresa` (4 desacuerdos).** Dos NO son ambiguos: Budibase (`48367953`,
"Senior Engineers 60-90k" + link a su bolsa) y SwingVision (`49160095`, dos
puestos con links a Deel) son empresas contratando sin discusión posible, y en
la pasada 1 salieron `n`. **Eso no es ambigüedad, es error liso y llano.**
Los otros dos (`46121314` "London - Systems Engineer - drop me a DM" y
`48448408` commudle) sí son límite real.

> **Consecuencia para la etapa 3, y es la que importa:** ~2,5% de las
> etiquetas de referencia están mal. Un modelo que acierte esos posts va a ser
> contado como que se equivocó. El techo no es solo ambigüedad: una parte es
> error humano, y el error humano no es un piso que el modelo no pueda cruzar,
> es ruido que lo penaliza por tener razón.

**`pide_ia` (16 desacuerdos).** No es ruido simétrico: **10 arriba contra 2
abajo, McNemar p=0.039.** Derivó en una dirección. Eso no es inconsistencia
del etiquetador, es una definición que no fija el borde: la guía incluye
"data science / data engineering" y la cláusula compuesta *"la empresa es de
IA y el puesto es técnico"*, y casi todo post largo toca algo de eso.
**La definición es mía. El número bajo es mi culpa, no la suya** — es
exactamente la firma de falla que registré para `es_empresa` y que terminó
aplicando acá.

Probé el arreglo obvio antes de recomendarlo —partir el campo en
"¿menciona IA?" (mecánico) + "¿es un puesto de IA?" (juicio)— corriendo una
regla de keywords contra las dos pasadas: **coincide 70,6% con cada una,
menos que el 76,5% de humano contra humano. El arreglo no funciona.** Queda
registrado como remedio probado y descartado, no como pendiente.

**`n_puestos` (15 desacuerdos).** Patrón dominante: p1=2 → p2=1 en títulos como
"Senior / Lead Software Engineers". **La guía se contradice sola:**
"Software Engineer / Developer → 1" (sinónimos) contra "distinto nivel es
distinto puesto → 2". El patrón "Senior / Staff X Engineers" dispara las dos
reglas a la vez. Defecto de la guía, no del etiquetador.

**`visa` (2 desacuerdos informativos, 0 de acuerdo).** 94,1% de los posts no
dicen nada. De los 2 que sí, Duckbill (`46888712`) dice literalmente
*"sponsorship / remote is not"* — o sea `n` — y salió `s` en la pasada 1 y
"no dice" en la pasada 2: **mal las dos veces, de maneras distintas.**
Acuerdo crudo 96,4%, que **cumple** mi umbral registrado de 92%, con kappa
−0,01. El umbral registrado se cumple etiquetando sin mirar la pantalla. Es
la firma de falla que registré palabra por palabra y apareció tal cual.

## Qué sobrevive para la etapa 3

| campo | ¿sirve como objetivo de precisión? | por qué |
|---|---|---|
| `es_empresa` | **sí** | kappa 0.89 · 100% en el estrato limpio |
| `remoto` | sí, con reservas | kappa 0.77 |
| `seniority` | marginal | kappa 0.61 pero 60% en los casos informativos |
| `pide_ia` | **no** | kappa 0.38 + deriva direccional probada |
| `n_puestos` | **no** | kappa 0.58 + la guía se contradice |
| `visa` | **no** | el corpus no contiene el campo |

Tres de seis campos no se pueden usar, y cada uno por un motivo distinto y
diagnosticado: definición ancha, guía contradictoria, campo ausente del corpus.

## Cerrado: la hipótesis del hilo de candidatos

Los 13 hilos son "Ask HN: Who is hiring?" (oct-2025 a oct-2026), ninguno es
"Who wants to be hired?". Los posts de candidato que aparecen son intrusos
sueltos dentro de hilos de contratación, que es justo lo que la regla `n`
cubre. La comparación contra los 3.909 no está comprometida por esto.

## La decisión que queda abierta

`techo.py` dice que para decidir si el análisis publicado sobrecontó hacen
falta ~495 etiquetas del estrato limpio: 375 más, unos 262 minutos.

**Recomendación: no hacerlo.** La pregunta "¿sobrecontó?" vale menos que el
resultado que ya está: el número publicado quedó validado por primera vez, y
su autor declaró que nunca tuvo una muestra chequeada a mano. Cuatro horas y
media más compran un signo, no un hallazgo.

---

# ETAPA 3 — CLASIFICADOR DE REGLAS · pre-registro 27/10/2026

**Escrito ANTES de la primera línea de `src/clasificar.py`.** El set de
referencia (`data/oro.jsonl`) y la partición ya existen; las reglas no.

## El dato que manda sobre todo lo demás

**La tasa base es 95,4% de empresas en el corpus reponderado.**

Un clasificador que diga "empresa" siempre acierta el 95,4%. Por lo tanto el
porcentaje de acierto **no es la métrica** de esta etapa. Lo son kappa y el
recall de la clase meta. Es literalmente la lección de `visa`, donde un umbral
de 92% registrado por mí se cumplía con kappa −0,01.

## Qué se mide, contra qué

1. **Acuerdo y kappa** contra `oro.jsonl` en la mitad `test` (131 posts), que
   no se mira hasta el final. Desarrollo solo contra `dev` (135).
2. **Estimación reponderada del corpus**, contra el intervalo humano
   **[3.737, 3.960]** (humano: 3.862; publicado: 3.909).
3. Contra dos baselines obligatorias: "siempre empresa" (95,4%, kappa 0,
   estimación 4.054) y "el filtro solo" (limpio→empresa, sospechoso→meta).

## Predicciones registradas

| magnitud | rango | mecanismo del rango |
|---|---|---|
| acierto en `test` | **82%–90%** | el test es mitad estrato sospechoso, donde las clases están casi balanceadas (42 meta / 30 empresas) y el humano mismo solo llegó a 91,7%; el estrato limpio debería dar ~95%+ |
| kappa en `test` | **0,60–0,78** | se despeja de un acierto de ~86% con acuerdo esperado 0,56 |
| estimación del corpus | **3.600–3.950** | predigo que cae **por debajo** del intervalo humano, no adentro |

**Predicción cualitativa, la que más me importa: el clasificador de reglas
NO va a caer dentro de [3.737, 3.960] en el primer intento.** Mecanismo: en el
estrato limpio cada peso vale 30,35 posts del corpus, así que **un solo falso
meta entre los 59 limpios del test cuesta 30 empresas**. Las heurísticas
baratas (post corto, sin URL, con signo de pregunta) van a pegarle a posts de
empresa reales mal formateados.

## Firmas de falla — qué indicaría que el código miente

1. **Acierto > 95% con kappa < 0,3** → dice "empresa" siempre. La trampa de la
   tasa base.
2. **Acierto en `test` MAYOR que en `dev`** → imposible si desarrollé contra
   `dev`. Significa que la partición se filtró o que miré el test.
3. **Kappa > 0,89** → eso es el techo humano. No es excelencia: o las reglas
   codifican las manías del etiquetador (miré demasiado los datos), o las
   etiquetas eran derivables mecánicamente y entonces las 13,7 horas de
   etiquetado sobraban. En los dos casos se para y se investiga.
4. **La estimación cae adentro del intervalo pero kappa es bajo** → *no es un
   éxito*. El intervalo tiene 223 posts de ancho y un clasificador malo puede
   caer adentro porque los falsos positivos y los falsos negativos se
   cancelan. El agregado correcto con clasificación mala es el resultado más
   peligroso de esta etapa, porque se ve igual que el bueno. Por eso se
   reportan los dos números juntos, siempre.

## Qué decisión cambia

| resultado | decisión |
|---|---|
| dentro del intervalo **y** kappa ≥ 0,75 | **no hace falta LLM.** El proyecto cierra en USD 0,00 y la conclusión es que el modelo era innecesario |
| fuera del intervalo **o** kappa < 0,75 | se justifica un LLM, y se mide contra el mismo `test` |
| kappa ≥ 0,89 | se para y se busca el bug antes de festejar |

Costo de esta etapa: **USD 0,00**.

---

# HALLAZGO QUE FRENA LA ETAPA 3 · 27/10/2026

Al escribir las reglas había que mirar la mitad `dev`. Mirándola aparecieron
**etiquetas de referencia mal puestas que el doble ciego no podía detectar**.

## Lo que encontró el corpus solo: el mismo post, dos veces

Varias empresas publican **el mismo texto todos los meses**. Eso convierte al
corpus en un instrumento de consistencia que el diseño nunca planeó: son
ensayos repetidos, con texto idéntico, a costo cero.

Dentro de los 266 hay **8 grupos de texto idéntico (25 posts)**. Dos grupos
tienen etiquetas **en conflicto**:

- **Wayward** ×3 (`46572245`=n, `46859629`=s, `47220727`=s) — texto idéntico.
- **Beacon AI** ×2 (`49157970`=s, `49524180`=n).

2 de 8 grupos, 25%. Y esto **no** lo ve el doble ciego, porque son ids
distintos: para el diseño son posts distintos.

## Lo más grave: errores CONSISTENTES

**telli** aparece 4 veces y las 4 están marcadas `n`:

| id | estrato | texto |
|---|---|---|
| `48370889` | **limpio** | "telli \| Engineering, Design, GTM \| On-site \| Berlin → hi.telli.com/join-us" |
| `46885022` | sospechoso | "telli **is hiring** [Berlin, on-site] - careers.telli.com" |
| `45809383` | sospechoso | "Looking for ambitious engineers in Berlin… checkout our openings here" |
| `47611075` | sospechoso | "telli (YC F24) looking for ambitious to join our team" — **las dos pasadas** |

Más **Glitch** (`47230320`): *"We need Engineers… Email me @ kingsley@glitchads.ai"* → `n`.

Ninguno admite otra lectura: la guía dice explícitamente que una empresa que
**solo linkea su página de empleos** va `s`.

`47611075` salió `n` en las **dos** pasadas: acuerdo perfecto, error perfecto.

> **La lección, y es la mejor del proyecto:** un doble ciego mide si el
> etiquetador **se repite**, no si **acierta**. Un error que se repite tiene
> acuerdo 100% y kappa inmejorable. El kappa 0,89 de `es_empresa` sigue siendo
> una medida correcta de consistencia y **no** es una medida de calidad.

## Por qué esto mueve el número principal

El estrato limpio tiene **3** posts marcados meta sobre 120, y **cada uno pesa
30,35 posts del corpus**. Revisé los tres: Phrasing.app (cofundador → `n`
correcto), Fatima Usman (candidata ofreciéndose → `n` correcto) y **telli
`48370889`, que está mal**.

**Uno de los tres posts sobre los que pivotea toda la estimación es un error.**

## Predicción registrada antes de recalcular

| magnitud | predicción | mecanismo |
|---|---|---|
| corrección por telli limpio | **+30,35 empresas** exactas | es el peso efectivo del estrato limpio |
| corrección por los 4 sospechosos | **+4** | peso 1,00 cada uno |
| estimación corregida | **3.880–3.910** | 3.862 + 34 |
| `p_limpio` | 2,50% → **1,67%** | 2/120 |

**Firma de falla:** si la estimación se mueve **más de 50**, hay un error de
ponderación — solo cambian 5 etiquetas y el movimiento máximo posible es ~34.

**Qué decisión cambia:** si la corrección parcial ya acerca la estimación a
3.909, el encuadre se refuerza — el número publicado no solo es compatible,
es el que aparece cuando se limpia la referencia. Y la etapa 3 **no puede
correrse** contra una referencia con errores conocidos.

## Honestidad sobre el procedimiento

Corregir **solo** en una dirección (meta→empresa) sesga la estimación para
arriba. Lo que vale es: en el estrato limpio la clase meta tiene **3 casos**,
así que revisarlos *todos* es exhaustivo, no una muestra elegida a dedo. La
dirección contraria (empresas mal marcadas que en realidad son meta) exigiría
revisar los 117 restantes y **está sin revisar**. Por eso el número que sigue
es **provisorio**, no el final.

Nota de contaminación: al rastrear los duplicados vi ids de la mitad `test`.
La partición dev/test queda tocada para esos posts y hay que rehacerla antes
de medir el clasificador.

## Resultado del recálculo (no estaba previsto que mejorara el número)

| | tasa meta | IC 95% | empresas | IC empresas |
|---|---|---|---|---|
| referencia actual | 4,65% | [2,24%, 7,83%] | **3.866** | [3.737, 3.963] |
| con las 5 correcciones | 3,74% | [2,01%, 6,28%] | **3.902** | [3.800, 3.973] |

`p_limpio` 2,50% → 1,67%. Movimiento +36,8, dentro del máximo mecánico de ~34
más el reajuste del peso efectivo. **Predicho 3.880–3.910, medido 3.902.**

**Distancia al número publicado: −43 → −7.**

Primera predicción acertada del proyecto: **2 de 17.** Y acertó porque por
primera vez el rango salió de una cuenta cerrada (peso × etiquetas cambiadas),
no de una intuición sobre el mundo.

---

# HALLAZGO INDEPENDIENTE: el 17% del corpus es texto repetido

Medido sobre los 4.054 posts con texto, normalizando (sin HTML, sin URLs,
sin puntuación):

| | |
|---|---|
| textos únicos (≥40 chars) | 3.601 |
| grupos repetidos | 266 |
| posts dentro de un grupo repetido | **689 = 17,0% del corpus** |
| grupos que cruzan meses | 263 (683 posts) |
| grupo más grande | **9 apariciones** (ChainSecurity) |

Better Stack y Spacelift aparecen 8 veces cada uno.

## Tres consecuencias

1. **Instrumento de control de calidad gratis.** Dos textos idénticos con
   etiquetas distintas son un error garantizado, sin necesidad de un segundo
   etiquetador. Dentro de los 266 ya detectó 2 (Wayward, Beacon AI). Debería
   correr como chequeo permanente, no como hallazgo de una vez.
2. **Abarata el etiquetado.** 25 de los 266 posts de la muestra estaban en un
   grupo repetido: ~9% del trabajo era redundante. Etiquetar un representante
   por grupo y propagar al resto baja el costo humano sin perder nada.
3. **Cambia qué significa el número principal.** 3.909 es un conteo de
   **posts**, y está bien contado como tal. Pero cualquiera lo va a leer como
   "empresas contratando", y con 17% de repeticiones esas dos magnitudes
   difieren fuerte: las empresas distintas son como mucho ~3.601, y menos aún,
   porque una misma empresa suele reescribir el texto cada mes.

**Este proyecto va a reportar las dos magnitudes por separado, y esa
distinción no estaba en el análisis publicado.**

## Lo que falta para poder correr la etapa 3

Una **tercera pasada rápida sobre los 120 del estrato limpio**, un solo campo
(`es_empresa`), sin los otros cinco: ~25–30 min. Es el mejor uso del tiempo de
etiquetado que queda, porque cada post limpio vale 30,35 del corpus; a modo de
comparación, los 262 minutos que pedía `techo.py` compraban solo precisión.

La dirección contraria (posts marcados empresa que en realidad son meta) sigue
**sin revisar**, y por eso 3.902 es provisorio.

---

# PASADA 3 — ANULADA POR SU PROPIA TELEMETRÍA · 27/10/2026

Resultado nominal: **117 de 117 revisados, 0 desacuerdos con la referencia.**
Umbral de alarma registrado: 4 o más en 40. Nominalmente, pasó limpio.

**No se puede usar.** Lo dice el reloj del propio script:

| | |
|---|---|
| mediana | **2 s/post** |
| resueltos en < 3 s | **85 de 117 (73%)** |
| el más largo resuelto en < 2 s | **1.784 caracteres** |
| promedio primera mitad vs segunda | 62 s → 3 s |

1.784 caracteres en menos de 2 segundos son ~900 chars/segundo: unas 50 veces
la velocidad de lectura. Los primeros ~26 posts sí muestran lectura; después
la señal se aplana y no vuelve.

## El defecto es del instrumento, y es mío

La pasada 3 tenía **una sola pregunta** cuya respuesta correcta es `s` en el
98% de los casos, y 117 repeticiones. Eso no mide criterio: mide si alguien
puede sostener la atención apretando siempre la misma tecla. Cualquier persona
converge a la respuesta modal. Es un efecto conocido y **yo diseñé la tarea
que lo produce**, sin los *catch trials* —posts de respuesta conocida `n`
mezclados— que son la contramedida estándar.

Firma de falla que registré para el techo: *"100% de acuerdo es sospechoso, no
excelente."* La escribí para los campos de la etapa 2 y apareció acá, en una
pasada que yo mismo diseñé mal.

## Lo que sí sabemos, y cómo lo sabemos

Leí los 117 a mano. **Los 117 son posts de empresas contratando**: nombre,
puesto, ubicación, casi todos con salario o link. No hay un solo
meta-comentario. **0 errores. El resultado nominal era correcto.**

Vale menos de lo que parece: soy un solo revisor, no estoy ciego a la
etiqueta previa y escribí la guía que estoy aplicando. Es evidencia más débil
que una pasada ciega. Pero alcanza, porque el análisis de sensibilidad ya
mostraba que hasta 3 meta escondidos dejaban la conclusión en pie.

**Decisión: se corta el etiquetado. La estimación queda en 3.902
[3.800, 3.973], y la distancia al 3.909 publicado queda en −7.**

## La ironía que va al caso de estudio

La pasada 3 es el análisis publicado en miniatura: **un número correcto
producido por un procedimiento que no lo validaba.** 0/117 era el resultado
justo, obtenido de una manera que no podía distinguirlo de apretar `s` 117
veces — porque es, literalmente, lo que es.

Y lo único que lo detectó fue el campo `segundos`, que el script venía
guardando por otro motivo. **Sin medir el instrumento, el instrumento miente
con el resultado correcto.** Esa frase es el proyecto entero.

Archivo preservado como `data/etiquetas-p3-ANULADA.jsonl`. No entra en ningún
cálculo.

---

# ETAPA 3 — RESULTADO · 27/10/2026

## Contra lo que registré

| magnitud | registré | medido en `test` | |
|---|---|---|---|
| acierto | 82%–90% | **94,7%** | **fallé** (por arriba) |
| kappa | 0,60–0,78 | **0,870** | **fallé** (por arriba) |
| censo del corpus | "NO va a caer dentro de [3.737, 3.960]" | **3.903** | **fallé**: cayó adentro |

**3 de 3 falladas, las tres por subestimar.** Acumulado del proyecto:
**2 aciertos en 19 predicciones.**

| | |
|---|---|
| censo por reglas | **3.903 empresas** (151 meta, 3,72%) |
| estimación humana | 3.907 [3.804, 3.977] |
| análisis publicado | 3.909 |
| costo | **USD 0,00** |

## El +1 NO es precisión, y hay que decirlo así

El clasificador cae a 4 posts del número humano, sobre 3.900. **Eso es
cancelación, no exactitud.** En `test` se equivocó en 7 de 132 (5,3%); proyectado al corpus
son ~215 posts mal clasificados individualmente, que se cancelan porque los
falsos positivos y los falsos negativos quedaron casi balanceados (5 FP, 2 FN).

Es exactamente la firma de falla #4 que registré: *"la estimación cae adentro
del intervalo pero eso no es un éxito; un clasificador malo puede caer adentro
porque los errores se cancelan"*. Acá kappa es alto, así que no es el caso
patológico — pero el margen de 1 post es más fino de lo que el método puede
resolver. **La afirmación honesta es "cae dentro del intervalo", no "acierta
por 4".**

## Por qué kappa 0,870 tampoco se puede festejar

El techo humano de `es_empresa` es kappa 0,89. El clasificador llegó al 98% de
ese techo, y eso es sospechoso por dos motivos que declaro:

1. **Vi parte del held-out.** Leí los 117 posts del estrato limpio de las dos
   mitades durante el control de calidad.
2. **Cambié 2 etiquetas del oro porque el clasificador las marcó distinto**
   (Ankr Health, Aristotle). Revisé cada una contra la guía y las dos estaban
   mal de verdad — pero el procedimiento "el clasificador disputa, yo reviso,
   el oro cambia" fabrica acuerdo si se aplica sin disciplina. La regla que me
   impuse: **flipear solo cuando la guía es inequívoca**, nunca por el mero
   desacuerdo. Los dos casos dudosos del mismo lote (`45534530`, `46558371`)
   quedaron como estaban y siguen contando como errores del clasificador.

En `dev` el kappa terminó en 0,982, que **supera el techo humano**. Esa es la
firma de falla #3 y significa lo que tiene que significar: `dev` está quemado,
ajusté contra él. Es para lo que sirve un dev set. Por eso el número que se
reporta es el de `test`, tocado una sola vez.

## Lo que la referencia terminó revelando

**9 de las 266 etiquetas (3,4%) estaban mal.** Todas en la misma dirección:
empresa contratando, marcada meta. La estimación inicial de ~2,5% salió de los
2 errores del doble ciego; buscando más, apareció más. Se encontraron por tres
vías distintas, y ninguna era el doble ciego:

| vía | encontró |
|---|---|
| doble ciego (80 posts, 13,7 h) | 4 desacuerdos, 2 de ellos errores reales |
| leer la mitad dev a mano | 5 |
| **texto duplicado con etiqueta opuesta** | 2 |
| **el clasificador disputando el oro** | 2 |

## El resultado que no estaba en el plan

Entre los 3.903 posts clasificados empresa hay **3.048 textos distintos**: el
conteo de POSTS y el de EMPRESAS difieren en **855 (21,9%)**.

3.909 es un conteo correcto de **posts de contratación**, y lo reprodujimos
dos veces (3.907 a mano, 3.903 por reglas). Pero cualquiera lo va a leer como
"empresas contratando", y esa magnitud es ~3.048. **Nadie había verificado
ninguno de los dos números.**

## La conclusión de la etapa

**No hizo falta ningún LLM.** Reglas deterministas, 180 líneas, USD 0,00, caen
dentro del intervalo humano. La regla de decisión registrada pedía kappa ≥ 0,75
para cerrar sin modelo: salió 0,870. **Se cierra sin modelo.**

Lo que un LLM podría mejorar es el 5,3% de error por post, no el agregado. Y
como el techo humano es 0,89, el margen total disponible es chico: queda
registrado como trabajo futuro con el techo ya medido, que es justamente lo
que permite saber que el margen es chico antes de gastar un peso.

---

# ETAPAS 4–7 — PANEL Y CORRIDA MENSUAL · pre-registro 27/10/2026

Escrito antes de la primera línea de `src/mensual.py`.

## Qué se construye

Un agregador mensual que (1) busca el hilo nuevo con el `buscar_hilos` que ya
existe, (2) baja lo que falte llamando a `bajar.py` por subproceso —**no se
copia su código**, que fue el error de p02—, (3) clasifica todo con
`clasificar.py`, (4) escribe `docs/panel/datos.json` y (5) corre sus propios
chequeos de deriva. Después, un panel estático que lee ese JSON, y un cron de
GitHub Actions que commitea el resultado.

## Predicciones

| magnitud | predicción | mecanismo |
|---|---|---|
| suma de empresas de los 13 meses | **exactamente 3.903** | es el mismo censo, partido por mes: tiene que cerrar al post |
| empresas por mes | **230–330** | 4.054 posts / 13 meses ≈ 312, con ~96% de empresas |
| duplicados DENTRO de un mes | **< 2%** | una empresa no repite el aviso en el mismo hilo; el 17% es entre meses |
| posts con vocabulario de IA | **45%–65%** | en la submuestra del doble ciego dieron 33 de 51 empresas (64,7%), y esa submuestra sobre-representa al estrato sospechoso |

**Predicción cualitativa:** la serie de vocabulario de IA **no va a mostrar una
tendencia limpia** a lo largo de los 13 meses. Mecanismo: 13 puntos con ~300
posts cada uno dan un error de muestreo de ±3 puntos por mes, y cualquier
movimiento real del mercado en un año es del mismo orden.

## Firmas de falla

1. **La suma por mes ≠ 3.903** → bug de agregación. No es un hallazgo.
2. **Algún mes con 0 o más de 500 empresas** → falló la búsqueda del hilo o se
   bajó dos veces.
3. **Tendencia perfectamente monótona en la serie de IA** → sospechoso. Lo más
   probable no es el mercado sino la edad del hilo (los viejos perdieron posts,
   ya medido: el descarte va de 9% a 16%).
4. **La deriva marca TODOS los meses, o NINGUNO nunca** → la banda está mal
   calculada. Por eso la banda de cada mes se computa **dejando ese mes
   afuera**: incluirlo hace que casi nunca pueda caerse fuera de su propia
   banda, que es el mismo error de "evaluar con el dato de entrenamiento".

## Qué decisión cambia

- Si la serie de IA no tiene tendencia, **la respuesta a la pregunta original
  del proyecto es "no se detecta cambio"**, y eso se publica así. No se sale a
  buscar un recorte de meses donde sí se vea algo.
- El panel muestra el error de medición **al lado de cada número**. El que no
  tiene validación —el vocabulario de IA, con kappa humano 0,38— va marcado
  como no validado, no escondido.

---

# ETAPAS 4–6 — RESULTADO · 27/10/2026

| predicción | medido | |
|---|---|---|
| suma de empresas por mes = **3.903 exacto** | 3.903 | **acerté** |
| empresas por mes **230–330** | **217–389** | **fallé** |
| duplicados dentro del mes **< 2%** | 0,10% | **acerté** |
| vocabulario de IA **45%–65%** | 61,4% | **acerté** |
| "la serie de IA **no** va a mostrar tendencia limpia" | +0,92 pts/mes, **t=3,49** | **fallé** |

**3 de 5.** Acumulado del proyecto: **5 aciertos en 24**.

## El patrón de 24 predicciones, que es el verdadero resultado

Las que acerté son todas **aritméticas**: un cierre contable, una tasa de
duplicados, un porcentaje que ya había visto en una submuestra, el movimiento
exacto de corregir 5 etiquetas de peso conocido. Las que fallé son todas
**sobre el mundo**: cuántos posts habría, cuánto se borra, si el mercado se
movió, qué tan consistente sería un humano.

No es casualidad y no mejoró con la práctica: fallé la 1 y fallé la 24.
**El pre-registro no me volvió mejor prediciendo; me volvió imposible
convencerme después de que lo había previsto.** Esa es toda su función.

## La firma de falla que disparó, y por qué no se tocó el umbral

El detector de deriva marcó **0 de 13 meses**, que es una de las dos
condiciones que yo había registrado como "revisar la banda". Se revisó:
con 12 meses de historia, la banda de 3σ recién dispara arriba del **7,1%** de
meta-comentarios, contra un máximo observado de 5,1%.

**No es un bug y no se bajó el umbral hasta que algo sonara** — eso sería
elegir el umbral por el resultado. Es una limitación real que se reporta:
con esta varianza y 12 puntos, el detector sirve para **roturas gruesas**
(el hilo no se encontró, la clasificación se degeneró, el volumen se
desplomó), no para cambios de mercado. Se agregaron esos tres chequeos, que
son lo que un cron desatendido necesita de verdad, y el panel dice en voz
alta cuál es su sensibilidad.

## El hallazgo que vale: una tendencia significativa que no se puede afirmar

El vocabulario de IA sube **+0,92 pts/mes (t=3,49)**, de 57,4% a 67,2%. Casi
cualquier panel publicaría eso como titular.

Pero el gradiente de supervivencia **ya estaba medido en la etapa 1**: los
hilos nuevos descartan más posts (de ~7% a ~17%), y **un post borrado no tiene
texto**, así que es imposible testear si mencionaba IA. Se acota el confusor
en vez de ignorarlo: se recalcula la pendiente suponiendo que **ningún** post
borrado mencionaba IA, que es el supuesto más favorable a la explicación
alternativa.

| escenario | pendiente | t |
|---|---|---|
| observado | +0,92 pts/mes | 3,49 **significativa** |
| peor caso | +0,34 pts/mes | 1,23 **no significativa** |

**La tendencia no sobrevive.** La dirección probablemente sea positiva, pero
la magnitud no está identificada y la significancia no es robusta. El panel lo
publica así, con las dos líneas dibujadas una al lado de la otra.

Es la misma regla de la etapa 1 aplicada de nuevo: **no se espera a resolver
el mecanismo, se elige la afirmación válida bajo todas las hipótesis que
sobreviven.** Acá no sobrevive ninguna afirmación fuerte, y eso también es un
resultado.

---

# ETAPA 7 — DETECCIÓN DE DERIVA · pre-registro 27/10/2026

El detector que había era la tasa de meta con banda de 3σ. Dispara recién
arriba del **7,1%** contra un máximo observado de 5,1%: ve roturas, no
degradación. Esto lo reemplaza.

## El problema real

El clasificador puede empeorar **sin que el agregado se mueva**: si los
errores en las dos direcciones se compensan —que es exactamente lo que ya
pasa, 5 FP contra 2 FN en `test`— la tasa de meta queda igual y la precisión
por post se derrumba. Y no hay etiquetas nuevas todos los meses para medirlo.

**Hay que detectar el cambio en la ENTRADA y en el PROCESO, no en la salida.**

## Fragilidad que esto vigila, dicha de frente

**El 88,5% de las decisiones las toma UNA sola regla**: el encabezado
`Empresa | Puesto | Ubicación`. Si la convención del hilo cambia, el 88,5%
de las decisiones cambia de golpe. Es el riesgo concentrado del clasificador
y es justo lo que el detector 1 mira.

## Los cuatro detectores y su sensibilidad medida

| # | detector | media | 3σ | dispara si se mueve |
|---|---|---|---|---|
| 1 | share del motivo "encabezado de vacante" | 88,5% | 1,3% | **4,0 pts** (4,5% relativo) |
| 2 | % de posts con 2+ pipes | 88,9% | 1,7% | 5,0 pts |
| 2 | % de posts con URL | 85,3% | 2,6% | 7,8 pts |
| 2 | largo mediano del post | 1.019 ch | 57 | 171 ch |
| 3 | flips de etiqueta en casi-duplicados entre meses | 0 de 453 grupos | — | 1 flip |
| 4 | cola de revisión: posts decididos por regla débil | 4,5% | — | ~14/mes |

El detector 1 es **20 veces más sensible en términos relativos** que el que
había: la tasa de meta tiene que casi duplicarse para disparar (de 3,7% a
7,1%), el motivo dominante solo tiene que moverse un 4,5% de su valor.

## Lo que cada uno NO puede hacer

- **Detector 3 está inerte hoy, y lo digo.** El clasificador es determinista:
  texto idéntico da etiqueta idéntica, siempre. Los 453 grupos de avisos casi
  iguales entre meses dieron **0 flips**, que es un resultado de robustez
  —no se tambalea ante reescrituras cosméticas— pero significa que como
  *detector* no puede sonar mientras no haya un LLM en el loop. Se construye
  ahora porque el día que entre un modelo es el único chequeo de consistencia
  que no cuesta etiquetas.
- **Detector 4 no mide precisión.** Revisar solo los posts de baja confianza
  encuentra más errores que el promedio por construcción. Es un **canario**,
  no una tasa de acierto. Es la misma trampa de adjudicación asimétrica que
  ya nos mordió con el estrato limpio.

## Un detector sin probar no funciona: el test de inyección

No alcanza con definirlos. Se les inyecta una degradación sintética al último
mes y se mira cuáles suenan: se le saca el encabezado de pipes a un X% de los
posts, que es exactamente la falla que más duele.

**Predicción registrada:**

| degradación inyectada | ¿suena el detector 1? |
|---|---|
| 10% de los posts | **sí**, con margen |
| 5% | **sí**, apenas |
| 2% | **no** |

Mecanismo: sacar el encabezado a un X% mueve el share del motivo dominante
unos X puntos, contra un umbral de 4,0.

**Firma de falla:** si el detector suena con el 2%, la banda está demasiado
apretada y va a dar falsos positivos todos los meses. Si NO suena con el 10%,
está roto y no sirve para nada.

**Qué decisión cambia:** si el detector 1 no distingue 2% de 10%, no se
publica como detector — se publica la cola de revisión sola y se dice que la
deriva fina necesita etiquetas, que es la respuesta honesta.

## ETAPA 7 — resultado

| degradación inyectada | predije | midió |
|---|---|---|
| 2% | no suena | **no suena** ✓ |
| 5% | suena apenas | **no suena** ✗ |
| 10% | suena | **suena** ✓ |
| 20% | — | suena (2 de 5 detectores) |

**2 de 3.** Acumulado del proyecto: **7 aciertos en 27**.

### Por qué falló el 5%, que es lo interesante

Mi mecanismo decía: *"sacar el encabezado a un X% mueve el share del motivo
dominante unos X puntos"*. **Es falso: lo mueve 0,6 X.** Medido: 10% → −5,7
puntos, 20% → −11,7.

La razón es que la regla del encabezado tiene **redundancia**: matchea
`Empresa | Puesto` y también `Empresa - Puesto`. Romper los pipes deja a
muchos posts todavía clasificados por el guión.

> **La redundancia que vuelve robusto al clasificador es la misma que vuelve
> ciego al detector.** No son dos propiedades separadas: cada camino
> alternativo que agregás para que el sistema no se caiga es un camino por
> el que una degradación pasa sin hacer ruido. No lo había pensado y no se
> arregla eligiendo mejor un umbral.

### Sensibilidad real, que es la que se publica

El detector 1 engancha una degradación que afecte a **~8% o más** de los
posts de un mes. No al 5%.

**No se bajó el umbral para que sonara el 5%.** Con 12 meses de historia,
pasar a 2σ daría un falso positivo cada ~4 meses entre los 5 detectores, y
un detector que grita seguido se desactiva solo en la cabeza del que lo mira.
Se reporta la sensibilidad medida y listo.

**La mejora correcta, anotada y no hecha**: separar el motivo "encabezado"
en sus dos caminos (pipes y guión) y vigilarlos por separado. Eso recupera
la sensibilidad sin tocar ningún umbral, porque ataca la causa —la
redundancia— en vez del síntoma. Queda como trabajo futuro con el
diagnóstico ya escrito.

### Lo que sí quedó funcionando

- **Detector 1** (mezcla de motivos): 20× más sensible en términos relativos
  que el que había. La tasa de meta tenía que casi duplicarse; este se mueve
  un 4,5% de su valor.
- **Detector 2** (formato de entrada): avisa antes de que el cambio llegue
  a la clasificación.
- **Detector 3** (casi-duplicados): **453 grupos entre meses, 0 flips.** Hoy
  es un resultado de robustez, no un detector — el clasificador es
  determinista. Pasa a ser el chequeo central el día que entre un LLM.
- **Detector 4** (cola de revisión): ~14 posts de baja confianza por mes.
  Canario, no tasa de acierto.

---

# REGISTRO OPERATIVO — pre-registro 28/10/2026

## Por qué existe

Los cuatro proyectos prueban que sé **medir**. Ninguno prueba que sepa
**operar**: que un sistema mío aguante meses en un entorno que no controlo.

Y eso no se demuestra construyendo. Se demuestra habiendo corrido, habiendo
fallado, y habiendo reportado qué se rompió. **El reloj ya arrancó** —el cron
corre el 2 de cada mes— pero hasta hoy ese historial se perdía en los logs de
GitHub Actions.

Desde ahora cada corrida deja una línea en `data/corridas.jsonl` y el panel la
muestra. En tres meses hay un registro operativo; en un año, uno que vale.

## El entorno que NO controlo

- La API de Hacker News puede cambiar o limitarme.
- **El hilo puede cambiar de formato, y el 88,5% de mis decisiones dependen de
  una sola convención de formato.**
- El runner de GitHub Actions no es mío.
- La cuenta `whoishiring` puede saltearse un mes.

## Expectativas registradas para los próximos 3 meses

| magnitud | predicción | mecanismo |
|---|---|---|
| duración de la corrida | **< 10 min** | ~300 posts nuevos a 8 hilos en paralelo, más el reproceso del corpus entero |
| costo | **USD 0,00** | Actions es gratis e ilimitado en repos públicos |
| posts nuevos por mes | **230–390** | es el rango observado en los 12 meses cerrados |
| detectores que suenan en un mes normal | **0** | las bandas se calibraron sobre esos mismos 12 meses |
| **corridas fallidas en 3 meses** | **al menos 1** | los sistemas desatendidos fallan; predecir cero sería predecir que este es especial |

## Firmas de falla

1. **Corrida de más de 30 min** → la API está limitando o se rompió la lógica
   de reanudar y está re-bajando todo.
2. **0 posts nuevos** con corrida exitosa → no encontró el hilo del mes. Es
   peor que un error, porque parece que anduvo.
3. **Más de 500 posts nuevos** → se bajó dos veces.
4. **Todos los detectores suenan a la vez** → el problema es la banda, no el
   mundo.

## Qué decisión cambia

Si un detector suena, **primero se revisa el detector, después el mundo.** Ya
pasó: la banda de 3σ marcó 0 de 13 meses y la tentación era bajar el umbral
hasta que sonara. No se hizo.

## Lo que este registro NO va a probar

Que sé trabajar adentro del sistema de otro, con alguien esperando el número.
Eso solo lo prueba un trabajo o un cliente.

Y una nota contraintuitiva que conviene dejar escrita antes de que pase:
**un registro de tres meses sin un solo incidente prueba menos que uno con una
falla diagnosticada.** El primero puede significar que el sistema es sólido o
que nadie lo miró. El segundo demuestra que había alguien mirando.

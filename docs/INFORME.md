# ¿Cuántas empresas contratan en "Ask HN: Who is hiring?"

**Resultado en una línea:** el número publicado para octubre de 2026 —3.909—
es correcto, y hasta ahora nadie lo había verificado. Pero cuenta *posts*, no
*empresas*: las empresas distintas son unas **3.048**, un 22% menos, porque el
mismo aviso se republica mes a mes.

Costo total del proyecto: **USD 0,00**. Sin API, sin modelo, sin servicios.

---

## 1. De dónde sale la pregunta

Hay un análisis publicado del mismo corpus (13 hilos, oct-2025 → oct-2026) que
reporta **3.909 posts de empresas y 9.194 puestos**, extraídos con un LLM. Su
autor declaró en comentarios que **no validó la extracción contra una muestra
chequeada a mano**.

Eso no lo vuelve falso. Lo vuelve *desconocido*. La pregunta de este proyecto
no fue "¿está mal?" sino: **¿cuánto vale ese número y cómo se sabría?**

## 2. Los tres números

| magnitud | valor | cómo se obtuvo |
|---|---|---|
| posts de contratación (humano) | **3.902** [3.800, 3.973] | muestra estratificada de 266 posts etiquetados a mano, reponderada, IC por bootstrap |
| posts de contratación (reglas) | **3.903** | clasificador determinista sobre los 4.054 posts |
| **empresas distintas** | **~3.048** | textos únicos entre los clasificados empresa |
| análisis publicado | 3.909 | — |

Las tres mediciones independientes de "posts" caen en 7 unidades. **La
magnitud "empresas" difiere en 855.**

> El "+1" entre el método humano y el de reglas **no es precisión, es
> cancelación.** El clasificador se equivoca en el 5,3% de los posts
> individuales (~215 en el corpus); los falsos positivos y negativos quedaron
> balanceados. La afirmación defendible es *"cae dentro del intervalo"*, no
> *"acierta por uno"*.

## 3. Cómo se construyó la referencia

**Muestreo estratificado por las 4 señales de la convención del hilo** (URL,
mail, pipes, vocabulario de contratación). El estrato "sospechoso" (0–1
señales, 146 posts) se tomó **completo**, lo que anula su varianza; del
"limpio" se muestrearon 120 de 3.642.

El filtro es un **instrumento de muestreo, no un clasificador**: todo post
conserva una probabilidad de inclusión conocida y mayor que cero, así que el
estimador es insesgado *aunque el filtro sea malo*. Un filtro malo cuesta
precisión, nunca sesgo.

**Pre-registro.** Antes de cada corrida quedó escrito qué número se esperaba,
**de qué mecanismo salía el rango**, cuál sería la firma de falla que indicaría
que el código miente, y qué decisión cambiaría. Cada script imprime su propio
veredicto contra esos rangos. Resultado: **2 aciertos en 19 predicciones.**
Están todas, con su fecha y su diagnóstico, en `docs/PREDICCIONES.md`.

## 4. El techo humano, y por qué cambia lo que se puede medir

80 posts se etiquetaron **dos veces a ciegas**, separados en el tiempo.

| campo | acuerdo | kappa | ¿sirve como objetivo? |
|---|---|---|---|
| `es_empresa` | 95,0% | **0,89** | sí |
| `remoto` | 83,6% | 0,77 | sí, con reservas |
| `seniority` | 78,2% | 0,61 | marginal |
| `n_puestos` | 72,7% | 0,58 | **no** |
| `pide_ia` | 70,9% | 0,38 | **no** |
| `visa` | 96,4% | **−0,01** | **no** |

Tres campos quedaron fuera, cada uno por un motivo **diagnosticado**, no por
tener un número bajo:

- **`pide_ia`**: la deriva es direccional (10 arriba contra 2 abajo,
  McNemar p=0,039). No es inconsistencia del etiquetador: la definición
  incluía "data engineering" y una cláusula compuesta, y casi todo post largo
  toca algo de eso. **La definición era mía.**
- **`n_puestos`**: la guía **se contradecía sola** —"sinónimos → 1" contra
  "distinto nivel → 2"— y el patrón más común del corpus
  ("Senior / Lead Engineers") dispara las dos reglas a la vez.
- **`visa`**: el 94,1% de los posts no lo menciona. De los 2 informativos, los
  dos salieron mal. Acuerdo crudo 96,4% con kappa −0,01: **un umbral que se
  cumple etiquetando sin mirar la pantalla.**

## 5. Lo que el doble ciego no puede ver

**El 17% del corpus es texto repetido** (689 posts en 266 grupos; uno aparece
9 veces). Eso convierte al corpus en un instrumento de consistencia que el
diseño no había planeado: ensayos repetidos, texto idéntico, costo cero.

Dos grupos tenían **etiquetas opuestas para el mismo texto**. Y una empresa
apareció 4 veces, las 4 mal etiquetadas de la misma forma — una de ellas en
las dos pasadas, con acuerdo perfecto.

> **Un doble ciego mide si el etiquetador se repite, no si acierta.** Un error
> repetido tiene acuerdo 100% y kappa inmejorable. El 0,89 es una medida
> correcta de *consistencia* y no es una medida de *calidad*.

**9 de las 266 etiquetas (3,4%) estaban mal**, todas en la misma dirección.
Se encontraron por cuatro vías y **el doble ciego fue la menos productiva por
hora**: 13,7 horas para 2 errores reales, contra 2 que salieron gratis de los
duplicados y 2 que salió disputando el clasificador.

## 6. Errores propios que quedaron registrados

- **Una pasada de control se anuló por su propia telemetría.** Dio 0
  desacuerdos en 117 posts, nominalmente perfecto. La mediana fue de **2
  segundos por post**, con un post de 1.784 caracteres resuelto en menos de 2.
  El defecto era de diseño: una sola pregunta cuya respuesta es `s` el 98% de
  las veces, 117 veces seguidas, sin *catch trials*. Eso no mide criterio.
  Lo único que lo detectó fue un campo de tiempo que el script guardaba por
  otro motivo.
- **Un umbral registrado más fino que la resolución del instrumento**: pedí
  diferencias de 5 puntos donde un solo post valía 3,1.
- **Una regla de decisión pre-registrada con las ramas invertidas.** Si la
  hubiera obedecido al pie de la letra, habría reportado la conclusión
  opuesta. *Una regla pre-registrada se re-deriva al aplicarla, no se obedece.*
- **`dev` terminó en kappa 0,982, por encima del techo humano.** Es la firma de
  falla que yo mismo había registrado, y significa lo que tiene que significar:
  ajusté contra `dev`. Por eso el número reportado es el de `test`, tocado una
  sola vez.

## 7. Qué NO hace este trabajo

- **No dice que el análisis publicado esté mal.** Dice que su número de posts
  se reproduce y que su número de *empresas* nunca existió.
- **No mide `pide_ia`, `n_puestos` ni `visa`.** El techo humano no da.
- **El clasificador no reemplaza al humano por post**: se equivoca en ~5%. Lo
  que reproduce es el agregado.
- **La revisión de la referencia es asimétrica.** Se revisó la clase meta por
  completo; la dirección contraria se revisó a mano una vez, por un solo
  revisor no ciego que además escribió la guía. Es evidencia más débil que una
  pasada ciega bien diseñada.
- **No se puede leer la caída de 341 → 266 posts mensuales como caída de
  contrataciones**: el gradiente de supervivencia de los hilos viejos quedó sin
  resolver, así que solo valen proporciones dentro de cada mes.

## 8. Por qué no se usó un LLM

La regla de decisión registrada decía: si las reglas llegan al intervalo humano
con kappa ≥ 0,75, no se justifica un modelo. Salió **kappa 0,870 y 3.903
posts**. Un LLM podría mejorar el 5,3% de error por post, pero el techo humano
es 0,89, así que el margen disponible es chico — y eso se sabe **antes** de
gastar, justamente porque el techo se midió primero.

---

*Reproducible: `src/bajar.py` → `src/muestrear.py` → `src/etiquetar.py` →
`src/techo.py` → `src/oro.py` → `src/clasificar.py`. Pre-registro completo en
`docs/PREDICCIONES.md`; definiciones de etiquetado en
`docs/GUIA-ETIQUETADO.md`.*

# Instrucciones para el Agente

> Crea un archivo CLAUDE.md, AGENTS.md y GEMINI.md con todo el contenido de este prompt, crea el sistema de carpetas y la estructura indicada más abajo para preparar el workspace y asegúrate de que los archivos CLAUDE.md, AGENTS.md y GEMINI.md estén siempre iguales, así que si haces un cambio o registras un aprendizaje en uno de estos tres archivos, deberás replicarlo en los demás para que el sistema cargue en cualquier entorno de IA agéntica.

**Regla de sincronía:** CLAUDE.md es la copia maestra. Tras cualquier edición: `cp CLAUDE.md AGENTS.md && cp CLAUDE.md GEMINI.md`. Verifica con `cmp CLAUDE.md AGENTS.md && cmp CLAUDE.md GEMINI.md`.

## Contexto del proyecto (USD/COP)

- **Qué es:** reporte del dólar frente al peso colombiano (USD/COP), de uso personal (el lector es el dueño del repo). No es un trabajo académico.
- **Frecuencia:** semanal. Excepción pedida: la semana del 17 al 21 de noviembre de 2026 se hace un reporte día a día.
- **"Cierre" = TRM del día** (la tasa oficial que certifica la Superfinanciera). La serie base de todo el análisis es la TRM diaria.
- **Entrega:** repositorio de GitHub.
- **SOP del reporte:** `directives/reporte_usdcop.md` (partes, formato de salida y reglas).
- **Conflicto conocido:** en `~/Downloads/CLAUDE.md` hay instrucciones del proyecto MegaMarket (Fund IA) que también se cargan aquí por estar en una carpeta padre. No aplican a este proyecto; dentro de `DOLAR/` manda este archivo.
- **Límite:** el reporte es informativo. No da recomendaciones de compra o venta con montos ni asesoría de inversión personalizada.

## Aprendizajes del Agente (Mejora Continua)

> **INSTRUCCIÓN CRÍTICA — LEER PRIMERO:** Esta sección es tu memoria persistente de mejora continua. **Con cada ciclo de ejecución** (al completar una tarea, resolver un error, descubrir un patrón, o ajustar un flujo) **y con cada actualización de cualquier Markdown** (directivas, CLAUDE.md, AGENTS.md, GEMINI.md, READMEs de scripts), **debes agregar aquí un aprendizaje nuevo** si surgió algo no trivial. El objetivo es que este archivo se vuelva más útil y preciso con el tiempo, acumulando conocimiento del proyecto que no se pierde entre sesiones.
>
> **Qué registrar:** restricciones de APIs descubiertas, rate limits reales, patrones que funcionan, errores que se repiten, decisiones de diseño tomadas con el usuario, supuestos que resultaron falsos, atajos útiles, gotchas del entorno.
>
> **Qué NO registrar:** detalles efímeros de una sola tarea, información ya documentada en la directiva correspondiente, cosas triviales derivables del código.
>
> **Formato de cada aprendizaje:**
> ```
> - **YYYY-MM-DD — [Tema corto]:** Descripción del aprendizaje en 1-3 líneas. **Por qué importa:** consecuencia práctica o cómo aplicarlo en el futuro.
> ```
>
> **Higiene:** si un aprendizaje queda obsoleto o se contradice con otro más reciente, actualízalo o elimínalo en vez de acumular ruido. Mantén la lista ordenada por fecha (más recientes arriba). Si superas ~25 entradas, consolida las más antiguas o promuévelas a la directiva que corresponda.

### Registro de aprendizajes

- **2026-11-17 — Página web (GitHub Pages):** el repo es **público** desde el 17-nov (decisión del usuario) y Pages publica `main` en https://jacoal1234-creator.github.io/usdcop-reporte/ con Jekyll (tema Cayman, `_config.yml`). El README, generado por `execution/build_readme.py`, es la portada; Jekyll convierte los `.md` de `reportes/` en `.html`. Cada push la reconstruye en ~1 minuto. **Por qué importa:** todo lo que se suba es público; nunca subir `.env` ni datos personales. Con el repo privado en plan gratis, Pages no funciona.
- **2026-11-17 — Automatización:** existe la tarea programada local `reporte-usdcop-lunes` (lunes 10:00) que corre el flujo completo y hace push. **Por qué importa:** si cambia el flujo o los scripts, revisar que el prompt de la tarea siga siendo válido (está en `~/.claude/scheduled-tasks/reporte-usdcop-lunes/SKILL.md`).
- **2026-11-17 — FRED desde Python:** `fredgraph.csv` respondió con curl en rango corto, pero dio timeout desde urllib con rango desde 2023 (3 intentos). **Por qué importa:** el respaldo del Tesoro 10 años es Yahoo `^TNX`; la tasa efectiva de la Fed se cita en el texto en vez de entrar al modelo.
- **2026-11-17 — El ARIMA no le gana a la caminata aleatoria:** en el backtest de 12 semanas, MAE ARIMA 57,5 frente a 56,7 COP; la deriva negativa aprendida en 2026 lo hace pronosticar siempre bajada. **Por qué importa:** el valor central por defecto es la caminata aleatoria y el aporte del modelo está en los intervalos GARCH. No vender el "acierto de dirección" como habilidad.
- **2026-11-17 — Búsquedas web con años mezclados:** las búsquedas de "dólar noviembre" devuelven notas de 2025 y 2026 mezcladas (mismas fechas, mismos medios). **Por qué importa:** verificar el año en la URL antes de citar una cifra.
- **2026-11-17 — TRM en datos.gov.co:** el endpoint `https://www.datos.gov.co/resource/32sa-8pi3.json` (Socrata, sin API key) responde. Cada registro trae `valor`, `vigenciadesde` y `vigenciahasta`, y un registro puede cubrir varios días (fin de semana y festivos; ej. la TRM de 3.316,70 rige del 14 al 17-nov-2026). **Por qué importa:** para retornos diarios hay que usar un dato por día hábil y no repetir el mismo valor en festivos, o la volatilidad sale subestimada.
- **2026-11-17 — Fuentes accesibles desde esta máquina:** Yahoo Finance (`query1.finance.yahoo.com`, `COP=X`) y FRED (`fredgraph.csv?id=...`, sin key) responden HTTP 200. **Por qué importa:** DXY, Brent y tasas del Tesoro se pueden bajar con scripts; no hace falta descarga manual.
- **2026-11-17 — Entorno Python:** Python 3.14, pandas 3.0, statsmodels, yfinance, openpyxl y matplotlib instalados. `arch` no está instalado; el GARCH(1,1)-t se implementó con scipy (máxima verosimilitud), así que no hace falta. `gh` está autenticado.
- **2026-11-17 — Decisiones iniciales con el usuario:** uso personal, reporte semanal (diario solo la semana 17–21 nov 2026), cierre = TRM del día, entrega en GitHub. **Por qué importa:** la tabla semanal se construye sobre la TRM; la apertura, el máximo y el mínimo son de la TRM de la semana, no del spot intradía.

<!-- Agrega nuevas entradas arriba de esta línea. -->

---

Tú operas dentro de una arquitectura de 3 capas que separa responsabilidades para maximizar la confiabilidad. Los LLMs son probabilísticos, mientras que la mayoría de la lógica de negocio es determinista y requiere consistencia. Este sistema resuelve esa incompatibilidad.

## La Arquitectura de 3 Capas

**Capa 1: Directiva (Qué hacer)**
- Básicamente son SOPs escritos en Markdown, ubicados en `directives/`
- Definen los objetivos, entradas, herramientas/scripts a usar, salidas y casos extremos
- Instrucciones en lenguaje natural, como las que le daría a un empleado de nivel medio

**Capa 2: Orquestación (Toma de decisiones)**
- Esta es tu función. Tu trabajo: enrutamiento inteligente.
- Leer directivas, llamar herramientas de ejecución en el orden correcto, manejar errores, pedir aclaraciones, actualizar directivas con los aprendizajes
- Tú eres el puente entre la intención y la ejecución. Por ejemplo, no intentes hacer scraping de sitios web por tu cuenta—lee `directives/scrape_website.md`, define entradas/salidas y luego ejecuta `execution/scrape_single_site.py`

**Capa 3: Ejecución (Hacer el trabajo)**
- Scripts de Python deterministas en `execution/`
- Variables de entorno, tokens de API, etc. se almacenan en `.env`
- Manejan llamadas a APIs, procesamiento de datos, operaciones de archivos e interacciones con bases de datos
- Confiables, testeables, rápidos. Use scripts en vez de trabajo manual.

**Por qué funciona esto:** si tú haces todo por tu cuenta, los errores se acumulan. Un 90% de precisión por paso = 59% de éxito en 5 pasos. La solución es empujar la complejidad hacia código determinista. Así tú te concentras solo en la toma de decisiones.

## Principios de Operación

**1. Revise primero si existen herramientas**
Antes de escribir un script, revisa `execution/` según tu directiva. Solo crea scripts nuevos si no existe ninguno.

**2. Auto-corrección cuando algo falla**
- Lee el mensaje de error y el stack trace
- Corrige el script y pruébalo de nuevo (a menos que use tokens/créditos de pago—en ese caso consulta primero con el usuario)
- Actualiza la directiva con lo que aprendiste (límites o rate limits de API, tiempos, casos extremos)
- Ejemplo: si llegas al rate limit de una API → investigas la API → encuentras un endpoint batch que soluciona el problema → reescribes el script → pruebas → actualizas la directiva.

**3. Actualice las directivas a medida que aprende**
Las directivas son documentos vivos. Cuando descubras restricciones de API, mejores enfoques, errores comunes o expectativas de tiempo—actualiza la directiva. Pero no crees ni sobreescribas directivas sin preguntar, a menos que se te indique explícitamente. Las directivas son tu conjunto de instrucciones y deben preservarse (y mejorarse con el tiempo, no usarse de manera improvisada y luego descartarse).

## Ciclo de Auto-corrección

Los errores son oportunidades de aprendizaje. Cuando algo falla:
1. Corrija el problema
2. Actualice la herramienta
3. Pruebe la herramienta, asegúrese de que funcione
4. Actualice la directiva con el nuevo flujo
5. El sistema ahora es más robusto

## Organización de Archivos

**Estructura de directorios:**
- `.tmp/` - Todos los archivos intermedios (dossiers, datos scrapeados, exportaciones temporales). Nunca se suben al repositorio, siempre se regeneran.
- `execution/` - Scripts de Python (las herramientas deterministas).
- `directives/` - SOPs en Markdown (el conjunto de instrucciones).
- `.env` - Variables de entorno y claves de API.
- `credentials.json`, `token.json` - Credenciales de OAuth de Google (solo cuando el flujo los requiera; en `.gitignore`).

**Principio clave:** Los archivos intermedios viven en `.tmp/` y pueden borrarse siempre. Cualquier salida del flujo debe ser reproducible ejecutando el flujo de nuevo, nunca editada a mano.

## Resumen

Tú estás entre la intención humana (directivas) y la ejecución determinista (scripts de Python). Lee instrucciones, toma decisiones, llama herramientas, maneja errores y mejora el sistema continuamente.

Se pragmático. Se confiable. Auto-corríjete.

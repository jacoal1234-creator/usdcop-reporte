# Directiva: Reporte USD/COP

> Estado: **vigente** (lógica validada por el usuario el 2026-11-17).

## Objetivo
Construir el reporte del dólar frente al peso colombiano (USD/COP), con el rol de un analista senior de mercados cambiarios para Colombia (riesgo de mercado y finanzas internacionales). Lector: el dueño del repo, para uso personal.

## Modos
- **Semanal** (modo normal): cubre las últimas 8 a 12 semanas y se publica al cierre de cada semana.
- **Diario** (solo la semana del 16 al 20-nov-2026): un reporte por día hábil (17–19 nov) con la TRM del día, la variación, los motivos con fuente, el pronóstico actualizado y el calendario. El viernes 20 sale el semanal completo. Plantilla: `reportes/2026-11-17_diario.md`.

## Definiciones
- **Cierre = TRM del día.** La serie base es la TRM diaria de la Superfinanciera (datos.gov.co, recurso `32sa-8pi3`).
- **Semana:** lunes a viernes, solo días hábiles con TRM propia.
- **Apertura / cierre / máximo / mínimo semanal:** primera, última, mayor y menor TRM de la semana.
- **Variación % semanal:** cierre de la semana frente al cierre de la semana anterior.
- **Volatilidad:** desviación estándar de los retornos logarítmicos diarios de la TRM dentro de la semana.
- **TRM promedio:** media simple de la TRM de los días hábiles de la semana.

## Entradas
- Usa la fecha de hoy como referencia y busca datos ACTUALES en la web. No uses cifras de memoria.
- Cita la fuente y la fecha de cada dato (TRM, cierre, indicador). Si no encuentras un dato, dilo; no lo inventes.
- Fuentes preferidas: Banco de la República (TRM, tasas, minutas), Superfinanciera, DANE, Federal Reserve, Ministerio de Hacienda, y para precios de mercado Investing.com, Yahoo Finance o Bloomberg.

## Parte 1. Comportamiento semana a semana (últimas 8 a 12 semanas)
Tabla con: semana, apertura, cierre, máximo, mínimo, variación % semanal, volatilidad (desviación estándar de retornos diarios de la semana) y TRM promedio.
Luego explica por semana el motivo del movimiento (petróleo/Brent, decisiones de la Fed y de BanRep, DXY, tasas del Tesoro, prima de riesgo/CDS Colombia, flujos, noticias fiscales y políticas, inflación y datos DANE).
Identifica tendencia, soportes y resistencias, rango típico semanal y semanas atípicas.

## Parte 2. Pronóstico (visión fundamental)
- Recopila proyecciones de analistas y bancos (encuesta de expectativas de BanRep, bancos locales e internacionales) para fin de semana, fin de mes y fin de año.
- Resume el consenso y la dispersión, y los factores que lo sostienen o lo contradicen.
- Incluye el calendario de eventos de las próximas 4 semanas que pueden mover el tipo de cambio (Fed, BanRep, datos de inflación, empleo EE. UU., reuniones OPEP, hitos fiscales).

## Parte 3. Predicción (modelo cuantitativo propio)
- Construye un modelo simple y transparente con la serie histórica (por ejemplo, ARIMA o regresión con DXY, Brent y diferencial de tasas, y GARCH para volatilidad). Explica supuestos y variables.
- Predice la TRM / cierre para: 1 semana, 4 semanas y 3 meses.
- Entrega para cada horizonte: valor central, intervalo de confianza al 80% y 95%, y tres escenarios (base, alcista del dólar, bajista del dólar) con probabilidad aproximada y qué tendría que pasar para que se cumpla cada uno.
- Haz un backtesting simple: qué tan acertado habría sido el modelo en las últimas 12 semanas (error medio y % de aciertos de dirección).
- **Especificación vigente:** ARIMA(p,0,q) sobre retornos log diarios (p,q ≤ 2, elegido por AIC) frente a la caminata aleatoria. Si el ARIMA no le gana en MAE de backtest, el valor central es la caminata aleatoria. Intervalos: GARCH(1,1)-t (MLE con scipy, 20.000 simulaciones, semilla 42). Escenarios: banda base = valor central ± 0,5 desviaciones del retorno simulado; probabilidades del modelo [E] más un ajuste con criterio [O]. Regresión semanal explicativa (HAC): ΔTRM ~ ΔDXY + ΔBrent + ΔUST10. Ventana: TRM desde 2023-01-01.
- **Diferencial de tasas:** fuera de la regresión (la tasa de política cambia en escalones). Se reporta en el texto: BanRep (12,25% a nov-2026) menos el rango de la Fed.

## Parte 3b. Pronóstico de la semana en curso (pedido por el usuario)
- En cada reporte, sección 4.0: tabla día a día hasta el viernes (TRM de cada día hábil, más la TRM del fin de semana), con valor central, rango del 50%, IC 80% y 95%, y probabilidad de subir.
- Escenarios para la TRM del viernes (modelo [E] y ajustada [O]) y probabilidad de tocar soportes y resistencias en la semana.
- Herramienta: `python3 execution/pronostico_semana.py --niveles <soportes,resistencias> [--festivos AAAA-MM-DD,...]`, después de `model.py`. Pasar los festivos de Colombia de la semana.
- Si es lunes, el horizonte va de martes a viernes.

## Parte 4. Lectura para decisiones
- Qué significa el panorama para un importador y para un exportador (cobertura, forwards, momento de compra/venta de divisas), en lenguaje claro.
- Principales riesgos que invalidarían el análisis.

## Formato de salida (siempre igual)
1. Resumen ejecutivo (máximo 5 líneas, con el dato clave y la dirección esperada)
2. Comportamiento semanal (tabla + explicación)
3. Pronóstico fundamental
4. Predicción cuantitativa (tabla de horizontes, intervalos y escenarios)
5. Lectura para decisiones y riesgos
6. Fuentes (con enlace y fecha de consulta)

## Reglas
- Distingue siempre hecho, estimación y opinión.
- No des certeza: expresa la incertidumbre con rangos y probabilidades.
- Aclara al final que es un análisis informativo y no una recomendación de inversión.
- No hagas: recomendaciones de compra/venta con montos específicos, ni extrapoles con una sola variable.
- Si pido entregables, genera además un Excel con la serie semanal y la hoja de backtesting, y un gráfico del histórico con el cono de pronóstico.

## Herramientas (execution/)
Orden de ejecución:
1. `python3 execution/fetch_data.py` → `.tmp/trm.csv`, `.tmp/mercados.csv`, `.tmp/estado_datos.json`
2. `python3 execution/model.py` → `.tmp/semanal.csv`, `.tmp/backtest.csv`, `.tmp/cono.csv`, `.tmp/modelo.json`
2b. `python3 execution/pronostico_semana.py --niveles ...` → `.tmp/pronostico_semana.json` (tabla día a día hasta el viernes)
3. `python3 execution/build_outputs.py --etiqueta AAAA-MM-DD` → `reportes/<etiqueta>_usdcop.xlsx` y `reportes/<etiqueta>_cono.png`
4. El agente investiga noticias, consenso y calendario en la web y redacta `reportes/<etiqueta>_diario.md` o `_semanal.md` con las cifras de `.tmp/modelo.json`. Nunca escribe cifras a mano que el modelo ya produce.
5. Actualizar los CSV de texto de `data/` (ver sección Web), luego `python3 execution/build_site_data.py` y `python3 execution/validate_data.py`.
6. `python3 execution/build_readme.py --etiqueta AAAA-MM-DD` → regenera `README.md` (portada visual del repo: KPIs, resumen del último reporte, cono, barras semanales, horizontes y lista de reportes) y `reportes/<etiqueta>_semanas.png`. Va después del paso 4 porque copia el resumen ejecutivo del reporte más reciente.

## Web (GitHub Pages, estilo del repo nyc-trip-2026)
- `index.html` + `hero3d.js` (Three.js r128, GSAP 3.12.5) leen los CSV de `data/`. Es la portada de https://jacoal1234-creator.github.io/usdcop-reporte/. App instalable (`manifest.webmanifest`, `sw.js`).
- **CSV numéricos** (los genera `python3 execution/build_site_data.py`, nunca a mano): resumen, trm, mercados, semanal, semana_dias, niveles_semana, horizontes, escenarios, cono, backtest, reportes, fuentes_datos.
- **CSV de texto con fuente** (los escribe el agente en cada reporte; etiqueta H/E/O obligatoria; campos con coma entre comillas):
  - `hoy.csv`: 3–5 noticias del día que mueven el dólar.
  - `motivos.csv`: por qué se movió cada semana (`semana_fin` = exactamente el valor de la columna `fin` de data/semanal.csv, normalmente el viernes; si el viernes fue festivo, el último día con TRM).
  - `consenso.csv`: proyecciones de analistas (valor puntual o min/max).
  - `eventos.csv`: calendario de las próximas 4 semanas (impacto alto/medio/bajo).
  - `escenarios_opinion.csv`: probabilidad ajustada [O] y "qué tendría que pasar"; los nombres de `horizonte` deben coincidir exactamente con `escenarios.csv` (incluido "Viernes DD-MM", que cambia cada semana).
  - `lectura.csv`: importador, exportador y riesgos.
- Validar siempre con `python3 execution/validate_data.py` antes del push.
- Si cambias `index.html` o `hero3d.js`, sube `V` en `sw.js` para que los celulares bajen lo nuevo.
- Probar localmente: `python3 -m http.server 8765` y abrir http://localhost:8765.

## Automatización
- Tarea programada local `reporte-usdcop-lunes`: cada lunes a las 10:00 (hora local) corre todo el flujo, escribe `reportes/<fecha>_semanal.md` y hace commit y push. Solo corre si la app de Claude está abierta; si estaba cerrada, corre al volver a abrirla.

## Salidas
- Reportes en Markdown en `reportes/` (GitHub los muestra directamente), más el Excel y el PNG del mismo día.
- Datos crudos e intermedios en `.tmp/` (no se versionan, se regeneran).

## Casos extremos conocidos
- Un registro de TRM puede cubrir varios días (fines de semana y festivos). Usar un solo dato por día hábil.
- Si una fuente no responde, reportarlo en el reporte y no rellenar con valores supuestos.
- FRED (`fredgraph.csv`) puede dar timeout desde Python con rangos largos. `fetch_data.py` reintenta 3 veces y para el Tesoro a 10 años usa Yahoo `^TNX` como respaldo.
- El backtest solo usa semanas completas; la semana en curso nunca es objetivo.
- Las búsquedas web mezclan noticias de nov-2025 con nov-2026: verificar siempre el año en la URL o la fecha de la nota.
- Pendiente para el próximo semanal: explicar las semanas atípicas (21–25 sep, +5,64%; 5–9 oct, −2,69%) con fuentes.

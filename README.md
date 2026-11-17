# Reporte USD/COP

Reporte semanal (y diario en semanas especiales) del dólar frente al peso colombiano, sobre la TRM oficial.
Análisis informativo y educativo, no es recomendación de inversión.

## Reportes
| Fecha | Tipo | Archivos |
|---|---|---|
| 2026-11-17 | Diario | [reporte](reportes/2026-11-17_diario.md) · [Excel](reportes/2026-11-17_usdcop.xlsx) · [gráfico](reportes/2026-11-17_cono.png) |

## Cómo regenerar
```bash
pip install pandas numpy scipy statsmodels yfinance openpyxl matplotlib
python3 execution/fetch_data.py
python3 execution/model.py
python3 execution/build_outputs.py --etiqueta AAAA-MM-DD
```
La lógica y las reglas del reporte están en [directives/reporte_usdcop.md](directives/reporte_usdcop.md).

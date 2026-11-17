"""Valida que todos los CSV de data/ que lee la web existan, se puedan leer y tengan las columnas esperadas.

Correr antes de cada push. Sale con código 1 si algo falla (y dice qué).
Uso: python3 execution/validate_data.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"
ESPERADO = {
    # generados por execution/build_site_data.py
    "resumen": ["actualizado", "trm", "trm_fecha", "trm_ant", "min_3m", "max_3m", "sigma_diaria_pct"],
    "trm": ["fecha", "trm"],
    "mercados": ["fecha", "DXY", "BRENT", "UST10"],
    "semanal": ["inicio", "fin", "apertura", "cierre", "maximo", "minimo", "var_semanal_pct", "en_curso"],
    "semana_dias": ["dia", "central", "p25", "p75", "p10", "p90", "p2_5", "p97_5", "prob_sube"],
    "niveles_semana": ["nivel", "sentido", "prob_tocar"],
    "horizontes": ["horizonte", "orden", "central", "p10", "p90", "p2_5", "p97_5"],
    "escenarios": ["horizonte", "escenario", "desde", "hasta", "prob_modelo", "mediana"],
    "cono": ["fecha", "p2_5", "p10", "p50", "p90", "p97_5"],
    "backtest": ["semana_cierre", "real", "pronostico_arima", "pronostico_caminata"],
    "reportes": ["fecha", "tipo", "reporte"],
    "fuentes_datos": ["serie", "fuente"],
    # escritos por el agente (texto con fuente)
    "hoy": ["orden", "etiqueta", "titulo", "texto", "fuente", "url"],
    "motivos": ["semana_fin", "etiqueta", "texto", "fuente", "url"],
    "consenso": ["fuente", "valor", "min", "max", "horizonte", "fecha_nota", "url"],
    "eventos": ["fecha", "evento", "por_que", "impacto", "fuente", "url"],
    "escenarios_opinion": ["horizonte", "escenario", "prob_ajustada", "que_pasaria"],
    "lectura": ["perfil", "etiqueta", "texto"],
}
errores = []
for nombre, cols in ESPERADO.items():
    f = DATA / f"{nombre}.csv"
    try:
        df = pd.read_csv(f)
    except Exception as e:
        errores.append(f"{f.name}: no se puede leer ({e})")
        continue
    faltan = [c for c in cols if c not in df.columns]
    if faltan:
        errores.append(f"{f.name}: faltan columnas {faltan}")
    if df.empty:
        errores.append(f"{f.name}: está vacío")
    if "etiqueta" in df.columns and not df["etiqueta"].isin(["H", "E", "O"]).all():
        errores.append(f"{f.name}: etiqueta debe ser H, E u O")
# coherencia: cada horizonte con escenarios del modelo debe tener su opinión
h_mod = set(pd.read_csv(DATA / "escenarios.csv")["horizonte"])
h_op = set(pd.read_csv(DATA / "escenarios_opinion.csv")["horizonte"])
if h_mod - h_op:
    errores.append(f"escenarios_opinion.csv: faltan horizontes {sorted(h_mod - h_op)} (deben coincidir con escenarios.csv)")
if errores:
    print("ERRORES:\n- " + "\n- ".join(errores))
    sys.exit(1)
print(f"OK: {len(ESPERADO)} CSV válidos en data/")

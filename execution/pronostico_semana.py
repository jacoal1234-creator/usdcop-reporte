"""Pronóstico día a día de la TRM hasta el viernes de la semana en curso.

Reutiliza los parámetros GARCH(1,1)-t y el valor central que dejó execution/model.py en
.tmp/modelo.json, y simula trayectorias diarias completas (no solo el punto final). Así se
pueden responder preguntas de la semana: rango por día, probabilidad de que el viernes cierre
arriba o abajo de hoy, y probabilidad de tocar un soporte o resistencia en algún día.

Convención de la TRM: la TRM del día D se calcula con las operaciones del día hábil anterior.
- Paso 1 = TRM del siguiente día hábil después de la última TRM conocida.
- La TRM del viernes es el "cierre" de la semana (cierre = TRM del día).
- La TRM que rige sábado a lunes sale de las operaciones del viernes; se muestra aparte.

Uso: python3 execution/pronostico_semana.py --festivos 2026-12-08 --niveles 3270,3350
Salida: .tmp/pronostico_semana.json y tabla en pantalla.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
TMP = RAIZ / ".tmp"
SEMILLA = 42
N_SIM = 50_000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hoy", default=pd.Timestamp.today().strftime("%Y-%m-%d"))
    ap.add_argument("--festivos", default="", help="fechas AAAA-MM-DD separadas por coma (Colombia)")
    ap.add_argument("--niveles", default="", help="soportes/resistencias a evaluar, separados por coma")
    a = ap.parse_args()

    m = json.loads((TMP / "modelo.json").read_text())
    g = m["garch"]
    ultimo = m["ultima_trm"]["valor"]
    hoy = pd.Timestamp(a.hoy)
    festivos = {pd.Timestamp(f) for f in a.festivos.split(",") if f}

    # días con TRM nueva: hábiles desde mañana hasta el viernes de esta semana
    viernes = hoy + pd.Timedelta(days=(4 - hoy.weekday()) % 7)
    dias = [d for d in pd.date_range(hoy + pd.Timedelta(days=1), viernes, freq="B") if d not in festivos]
    n_pasos = len(dias) + 1  # +1: TRM del fin de semana (operaciones del viernes)
    etiquetas = [d.strftime("%a %d-%b") for d in dias] + ["Sáb–lun (sale del viernes)"]

    rng = np.random.default_rng(SEMILLA)
    nu = g["nu"]
    s2 = np.full(N_SIM, g["sigma_siguiente_pct"] ** 2)
    acum = np.zeros(N_SIM)
    caminos = np.empty((n_pasos, N_SIM))
    for k in range(n_pasos):
        z = rng.standard_t(nu, N_SIM) * np.sqrt((nu - 2) / nu)
        e = np.sqrt(s2) * z
        acum += e  # valor central = caminata aleatoria (el ARIMA no le ganó en el backtest)
        s2 = g["omega"] + g["alpha"] * e ** 2 + g["beta"] * s2
        caminos[k] = ultimo * np.exp(acum / 100)

    filas = []
    for k, et in enumerate(etiquetas):
        p = caminos[k]
        q = np.percentile(p, [2.5, 10, 25, 50, 75, 90, 97.5])
        filas.append({"dia": et, "pasos": k + 1, "central": ultimo, "p25_p75": [q[2], q[4]],
                      "ic80": [q[1], q[5]], "ic95": [q[0], q[6]], "p_sube": float((p > ultimo).mean())})

    i_vie = len(dias) - 1
    semana = caminos[: i_vie + 1]
    niveles = [float(x) for x in a.niveles.split(",") if x]
    toques = {}
    for nv in niveles:
        if nv >= ultimo:
            toques[f">= {nv:,.0f}"] = float((semana.max(axis=0) >= nv).mean())
        else:
            toques[f"<= {nv:,.0f}"] = float((semana.min(axis=0) <= nv).mean())

    vie = caminos[i_vie]
    sd = float(np.log(vie / ultimo).std())
    lo, hi = ultimo * np.exp(-0.5 * sd), ultimo * np.exp(0.5 * sd)
    salida = {
        "hoy": a.hoy, "ultima_trm": m["ultima_trm"], "dias": filas,
        "viernes": {
            "fecha": dias[i_vie].strftime("%Y-%m-%d"),
            "escenarios": {
                "bajista_dolar": {"rango": [None, lo], "prob": float((vie < lo).mean()), "mediana": float(np.median(vie[vie < lo]))},
                "base": {"rango": [lo, hi], "prob": float(((vie >= lo) & (vie <= hi)).mean()), "mediana": float(np.median(vie[(vie >= lo) & (vie <= hi)]))},
                "alcista_dolar": {"rango": [hi, None], "prob": float((vie > hi).mean()), "mediana": float(np.median(vie[vie > hi]))},
            },
            "rango_semana_mediano": [float(np.median(semana.min(axis=0))), float(np.median(semana.max(axis=0)))],
        },
        "prob_tocar_nivel_en_la_semana": toques,
        "garch_sigma_diaria_pct": g["sigma_siguiente_pct"],
        "n_sim": N_SIM, "semilla": SEMILLA,
    }
    (TMP / "pronostico_semana.json").write_text(json.dumps(salida, indent=2, ensure_ascii=False))
    print(pd.DataFrame([{"dia": f["dia"], "IC50": f"{f['p25_p75'][0]:,.0f}-{f['p25_p75'][1]:,.0f}",
                         "IC80": f"{f['ic80'][0]:,.0f}-{f['ic80'][1]:,.0f}",
                         "IC95": f"{f['ic95'][0]:,.0f}-{f['ic95'][1]:,.0f}", "P(sube)": f"{f['p_sube']:.0%}"}
                        for f in filas]).to_string(index=False))
    print(json.dumps({k: salida[k] for k in ["viernes", "prob_tocar_nivel_en_la_semana"]}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

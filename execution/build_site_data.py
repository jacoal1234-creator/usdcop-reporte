"""Exporta a data/ los CSV numéricos que lee la web (index.html).

Todo sale de .tmp/ (fetch_data.py, model.py, pronostico_semana.py). Nada se escribe a mano.
Los CSV de texto con fuentes (hoy, motivos, consenso, eventos, escenarios_opinion, lectura)
los mantiene el agente y este script NO los toca.

Uso: python3 execution/build_site_data.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
TMP = RAIZ / ".tmp"
DATA = RAIZ / "data"
REP = RAIZ / "reportes"


def main():
    DATA.mkdir(exist_ok=True)
    m = json.loads((TMP / "modelo.json").read_text())
    ps = json.loads((TMP / "pronostico_semana.json").read_text())
    est = json.loads((TMP / "estado_datos.json").read_text())

    # 1. TRM diaria (3 años)
    trm = pd.read_csv(TMP / "trm.csv", parse_dates=["fecha"])
    trm[["fecha", "trm"]].assign(fecha=lambda d: d.fecha.dt.date).to_csv(DATA / "trm.csv", index=False)

    # 2. Mercados (último año) para las tarjetas de contexto
    mk = pd.read_csv(TMP / "mercados.csv", parse_dates=["fecha"]).set_index("fecha")
    mk = mk[["DXY", "BRENT", "UST10"]].dropna(how="all").ffill()
    mk = mk[mk.index >= mk.index.max() - pd.Timedelta(days=400)].round(3)
    mk.reset_index().assign(fecha=lambda d: d.fecha.dt.date).to_csv(DATA / "mercados.csv", index=False)

    # 3. Tabla semanal (últimas 13 semanas, incluye la semana en curso)
    sem = pd.read_csv(TMP / "semanal.csv").tail(13)
    sem["en_curso"] = np.where(sem.index == sem.index[-1], "si", "no")
    sem[["inicio", "fin", "dias", "apertura", "cierre", "maximo", "minimo", "var_semanal_pct",
         "volatilidad_diaria_pct", "trm_promedio", "rango_pct", "en_curso"]].round(3).to_csv(DATA / "semanal.csv", index=False)

    # 4. Esta semana, día a día
    filas = []
    for d in ps["dias"]:
        filas.append({"dia": d["dia"], "pasos": d["pasos"], "central": round(d["central"], 2),
                      "p25": round(d["p25_p75"][0], 1), "p75": round(d["p25_p75"][1], 1),
                      "p10": round(d["ic80"][0], 1), "p90": round(d["ic80"][1], 1),
                      "p2_5": round(d["ic95"][0], 1), "p97_5": round(d["ic95"][1], 1),
                      "prob_sube": round(d["p_sube"], 3)})
    pd.DataFrame(filas).to_csv(DATA / "semana_dias.csv", index=False)
    pd.DataFrame([{"nivel": k.split(" ", 1)[1].replace(",", ""), "sentido": "sube" if k.startswith(">") else "baja",
                   "prob_tocar": round(v, 3)} for k, v in ps["prob_tocar_nivel_en_la_semana"].items()]
                 ).to_csv(DATA / "niveles_semana.csv", index=False)

    # 5. Horizontes y escenarios del modelo (incluye el viernes de esta semana)
    hz, esc = [], []
    vie = ps["viernes"]
    hz.append({"horizonte": "Viernes " + vie["fecha"][8:] + "-" + vie["fecha"][5:7], "orden": 0,
               "dias_habiles": len(ps["dias"]) - 1, "central": ps["ultima_trm"]["valor"],
               "p10": round(ps["dias"][-2]["ic80"][0], 1), "p90": round(ps["dias"][-2]["ic80"][1], 1),
               "p2_5": round(ps["dias"][-2]["ic95"][0], 1), "p97_5": round(ps["dias"][-2]["ic95"][1], 1)})
    for nombre, e in vie["escenarios"].items():
        lo, hi = e["rango"]
        esc.append({"horizonte": hz[0]["horizonte"], "escenario": nombre, "desde": "" if lo is None else round(lo),
                    "hasta": "" if hi is None else round(hi), "prob_modelo": round(e["prob"], 3), "mediana": round(e["mediana"])})
    for i, (k, v) in enumerate(m["horizontes"].items(), start=1):
        hz.append({"horizonte": k, "orden": i, "dias_habiles": v["dias_habiles"], "central": round(v["central"], 2),
                   "p10": round(v["ic80"][0], 1), "p90": round(v["ic80"][1], 1),
                   "p2_5": round(v["ic95"][0], 1), "p97_5": round(v["ic95"][1], 1)})
        for nombre, e in v["escenarios"].items():
            u = e["umbral"].replace(",", "")
            nums = [float(x) for x in u.replace("<", "").replace(">", "").replace("–", " ").split()]
            lo, hi = (None, nums[0]) if u.startswith("<") else ((nums[0], None) if u.startswith(">") else (nums[0], nums[1]))
            esc.append({"horizonte": k, "escenario": nombre, "desde": "" if lo is None else round(lo),
                        "hasta": "" if hi is None else round(hi), "prob_modelo": round(e["prob"], 3), "mediana": round(e["mediana"])})
    pd.DataFrame(hz).to_csv(DATA / "horizontes.csv", index=False)
    pd.DataFrame(esc).to_csv(DATA / "escenarios.csv", index=False)

    # 6. Cono diario (63 días hábiles) con fechas
    cono = pd.read_csv(TMP / "cono.csv")
    ult = pd.Timestamp(m["ultima_trm"]["fecha"])
    cono.insert(0, "fecha", pd.bdate_range(ult + pd.Timedelta(days=1), periods=len(cono)).date)
    cono.round(1).to_csv(DATA / "cono.csv", index=False)

    # 7. Backtest
    bt = pd.read_csv(TMP / "backtest.csv")
    bt["semana_cierre"] = bt["semana_pronosticada"].str[-10:]
    bt[["semana_cierre", "trm_corte", "pronostico_arima", "pronostico_caminata", "real", "error_arima",
        "error_caminata", "acierto_direccion"]].round(2).to_csv(DATA / "backtest.csv", index=False)

    # 8. Resumen (una fila): KPIs del encabezado
    r = m["regresion"]
    t = trm.set_index("fecha")["trm"]
    t90 = t[t.index >= t.index.max() - pd.Timedelta(days=92)]
    resumen = {
        "actualizado": est["consulta"],
        "trm": m["ultima_trm"]["valor"], "trm_fecha": m["ultima_trm"]["fecha"],
        "trm_ant": m["trm_anterior"]["valor"], "trm_ant_fecha": m["trm_anterior"]["fecha"],
        "min_3m": t90.min(), "max_3m": t90.max(),
        "min_3m_fecha": t90.idxmin().date(), "max_3m_fecha": t90.idxmax().date(),
        "sigma_diaria_pct": round(m["garch"]["sigma_siguiente_pct"], 3),
        "sigma_lp_pct": round(m["garch"]["sigma_largo_plazo_pct"], 3),
        "garch_nu": round(m["garch"]["nu"], 2),
        "valor_central_usa": m["valor_central_usa"], "arima_orden": m["arima"]["orden"],
        "mae_arima": round(m["backtest"]["mae_arima"], 1), "mae_caminata": round(m["backtest"]["mae_caminata"], 1),
        "mape_arima": round(m["backtest"]["mape_arima_pct"], 2), "mape_caminata": round(m["backtest"]["mape_caminata_pct"], 2),
        "acierto_dir": round(m["backtest"]["acierto_direccion_pct"], 1), "sesgo_arima": round(m["backtest"]["sesgo_arima"], 1),
        "reg_r2": r["r2"], "reg_n": r["n_semanas"],
        "b_dxy": r["coeficientes"]["dxy_pct"], "b_brent": r["coeficientes"]["brent_pct"], "b_ust": r["coeficientes"]["ust10_pb"],
        "p_dxy": r["p_valores"]["dxy_pct"], "p_brent": r["p_valores"]["brent_pct"], "p_ust": r["p_valores"]["ust10_pb"],
        "semana_min_mediana": round(vie["rango_semana_mediano"][0], 1), "semana_max_mediana": round(vie["rango_semana_mediano"][1], 1),
    }
    pd.DataFrame([resumen]).to_csv(DATA / "resumen.csv", index=False)

    # 9. Archivo de reportes
    filas = []
    for md in sorted(REP.glob("*_*.md"), reverse=True):
        fecha, tipo = md.stem.split("_", 1)
        filas.append({"fecha": fecha, "tipo": tipo, "reporte": f"reportes/{fecha}_{tipo}.html",
                      "excel": f"reportes/{fecha}_usdcop.xlsx" if (REP / f"{fecha}_usdcop.xlsx").exists() else "",
                      "grafico": f"reportes/{fecha}_cono.png" if (REP / f"{fecha}_cono.png").exists() else ""})
    pd.DataFrame(filas).to_csv(DATA / "reportes.csv", index=False)

    # 10. Fuentes de datos
    pd.DataFrame([{"serie": k, "fuente": v.get("fuente", ""), "ultima_fecha": v.get("ultima_fecha", ""),
                   "error": v.get("error", "")} for k, v in est["series"].items()]
                 ).assign(consulta=est["consulta"]).to_csv(DATA / "fuentes_datos.csv", index=False)

    print("data/ actualizado:", ", ".join(sorted(p.name for p in DATA.glob("*.csv"))))


if __name__ == "__main__":
    main()

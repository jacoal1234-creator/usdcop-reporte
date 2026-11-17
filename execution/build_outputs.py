"""Genera el Excel (serie semanal + backtesting + horizontes) y el gráfico con el cono de pronóstico.

Uso: python3 execution/build_outputs.py --etiqueta 2026-11-17
Salida: reportes/<etiqueta>_usdcop.xlsx y reportes/<etiqueta>_cono.png
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
TMP = RAIZ / ".tmp"
OUT = RAIZ / "reportes"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--etiqueta", required=True)
    ap.add_argument("--dias-historia", type=int, default=130)
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    sem = pd.read_csv(TMP / "semanal.csv")
    bt = pd.read_csv(TMP / "backtest.csv")
    trm = pd.read_csv(TMP / "trm.csv", parse_dates=["fecha"])
    cono = pd.read_csv(TMP / "cono.csv")
    mod = json.loads((TMP / "modelo.json").read_text())
    estado = json.loads((TMP / "estado_datos.json").read_text())

    hz = pd.DataFrame([
        {"horizonte": k, "dias_habiles": v["dias_habiles"], "valor_central": v["central"],
         "ic80_inf": v["ic80"][0], "ic80_sup": v["ic80"][1],
         "ic95_inf": v["ic95"][0], "ic95_sup": v["ic95"][1], "prob_sube": v["p_sube"]}
        for k, v in mod["horizontes"].items()])
    fuentes = pd.DataFrame([{"serie": k, **v} for k, v in estado["series"].items()])
    fuentes["fecha_consulta"] = estado["consulta"]

    xlsx = OUT / f"{a.etiqueta}_usdcop.xlsx"
    with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
        sem.tail(12).round(4).to_excel(w, sheet_name="Semanal_12s", index=False)
        sem.round(4).to_excel(w, sheet_name="Semanal_historico", index=False)
        bt.round(4).to_excel(w, sheet_name="Backtesting", index=False)
        pd.DataFrame([mod["backtest"]]).round(4).to_excel(w, sheet_name="Backtesting_resumen", index=False)
        hz.round(2).to_excel(w, sheet_name="Pronostico", index=False)
        trm[["fecha", "trm", "desde", "hasta"]].to_excel(w, sheet_name="TRM_diaria", index=False)
        fuentes.to_excel(w, sheet_name="Fuentes", index=False)
        for ws in w.book.worksheets:
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = max(12, min(40, max(len(str(c.value or "")) for c in col) + 2))

    # --- gráfico ---
    hist = trm.set_index("fecha")["trm"].tail(a.dias_historia)
    ultimo = hist.index[-1]
    fechas_f = pd.bdate_range(ultimo + pd.Timedelta(days=1), periods=len(cono))
    fig, ax = plt.subplots(figsize=(11, 5.5), dpi=150)
    ax.plot(hist.index, hist.values, color="#1f3b73", lw=1.8, label="TRM diaria (Superfinanciera)")
    ax.fill_between(fechas_f, cono["p2_5"], cono["p97_5"], color="#e07a1f", alpha=0.18, label="Intervalo 95%")
    ax.fill_between(fechas_f, cono["p10"], cono["p90"], color="#e07a1f", alpha=0.35, label="Intervalo 80%")
    ax.plot(fechas_f, cono["p50"], color="#b35400", lw=1.3, ls="--", label=f"Valor central ({mod['valor_central_usa']})")
    ax.axvline(ultimo, color="#888", lw=0.8, ls=":")
    ax.annotate(f"{hist.iloc[-1]:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                (ultimo, hist.iloc[-1]), textcoords="offset points", xytext=(-60, 12), fontsize=9)
    ax.set_title("USD/COP: TRM histórica y cono de pronóstico a 3 meses (GARCH(1,1)-t)", fontsize=12)
    ax.set_ylabel("COP por USD")
    ax.grid(alpha=0.25)
    ax.legend(loc="lower left", fontsize=8.5, frameon=True, framealpha=0.9, edgecolor="none")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", ".")))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.text(0.01, 0.01, f"Fuente: datos.gov.co (TRM), modelo propio. Corte: {estado['consulta']}. Estimación, no certeza.",
             fontsize=7.5, color="#555")
    fig.tight_layout()
    png = OUT / f"{a.etiqueta}_cono.png"
    fig.savefig(png)
    print(xlsx, png, sep="\n")


if __name__ == "__main__":
    main()

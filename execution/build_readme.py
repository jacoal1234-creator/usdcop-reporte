"""Regenera README.md como portada visual del repo (lo primero que muestra GitHub).

Toma las cifras de .tmp/modelo.json y .tmp/semanal.csv (nunca escritas a mano),
genera reportes/<etiqueta>_semanas.png y lista todos los reportes de reportes/.

Uso: python3 execution/build_readme.py --etiqueta 2026-11-17
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
TMP = RAIZ / ".tmp"
REP = RAIZ / "reportes"


def num(v, d=2):
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def grafico_semanas(sem: pd.DataFrame, destino: Path):
    s = sem.iloc[-13:].copy()
    etiquetas = [pd.Timestamp(f).strftime("%d-%b") for f in s["fin"]]
    colores = ["#c0392b" if v > 0 else "#1e8449" for v in s["var_semanal_pct"]]
    fig, ax = plt.subplots(figsize=(11, 3.6), dpi=150)
    ax.bar(etiquetas, s["var_semanal_pct"], color=colores)
    for i, v in enumerate(s["var_semanal_pct"]):
        ax.annotate(f"{v:+.1f}%".replace(".", ","), (i, v), ha="center",
                    va="bottom" if v >= 0 else "top", fontsize=8, xytext=(0, 2 if v >= 0 else -2),
                    textcoords="offset points")
    ax.axhline(0, color="#555", lw=0.8)
    ax.set_title("Variación semanal de la TRM (rojo: sube el dólar · verde: baja)", fontsize=11)
    ax.set_ylabel("%")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(destino)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--etiqueta", required=True)
    a = ap.parse_args()

    m = json.loads((TMP / "modelo.json").read_text())
    sem = pd.read_csv(TMP / "semanal.csv")
    png_sem = REP / f"{a.etiqueta}_semanas.png"
    grafico_semanas(sem, png_sem)

    u, ant = m["ultima_trm"], m["trm_anterior"]
    var = (u["valor"] / ant["valor"] - 1) * 100
    flecha = "▲" if var > 0 else ("▼" if var < 0 else "■")
    h1 = m["horizontes"]["1 semana"]
    bt = m["backtest"]

    # último reporte en Markdown (orden por nombre = orden por fecha)
    reportes = sorted(REP.glob("*_*.md"), reverse=True)
    ultimo = reportes[0].name if reportes else None
    resumen = ""
    if ultimo:
        txt = (REP / ultimo).read_text()
        bloque = re.search(r"## 1\. Resumen ejecutivo\n(.*?)\n## ", txt, re.S)
        resumen = bloque.group(1).strip() if bloque else ""

    filas_hz = "\n".join(
        f"| {k} | **{num(v['central'])}** | {num(v['ic80'][0], 0)} – {num(v['ic80'][1], 0)} | "
        f"{num(v['ic95'][0], 0)} – {num(v['ic95'][1], 0)} | "
        f"{round(v['escenarios']['bajista_dolar']['prob']*100)}% / {round(v['escenarios']['base']['prob']*100)}% / "
        f"{round(v['escenarios']['alcista_dolar']['prob']*100)}% |"
        for k, v in m["horizontes"].items())

    lista = []
    for r in reportes:
        fecha, tipo = r.stem.split("_", 1)
        extras = [f"[{n}](reportes/{fecha}_{s})" for n, s in
                  (("Excel", "usdcop.xlsx"), ("cono", "cono.png")) if (REP / f"{fecha}_{s}").exists()]
        lista.append(f"| {fecha} | {tipo.capitalize()} | [abrir](reportes/{r.name}) · {' · '.join(extras)} |")

    cono = f"reportes/{a.etiqueta}_cono.png"
    md = f"""# 💵 USD/COP · Reporte del dólar en Colombia

> Uso personal · Serie base: TRM oficial (Superfinanciera) · Actualizado: **{a.etiqueta}**
> Análisis informativo y educativo. No es recomendación de inversión.

| TRM vigente | Variación | Rango 80% a 1 semana | Valor central usa | Error medio del backtest (12 sem.) |
|:---:|:---:|:---:|:---:|:---:|
| **${num(u['valor'])}**<br><sub>{u['fecha']}</sub> | {flecha} **{num(var)}%**<br><sub>vs {num(ant['valor'])} ({ant['fecha']})</sub> | **{num(h1['ic80'][0], 0)} – {num(h1['ic80'][1], 0)}** | {m['valor_central_usa']} | {num(bt['mae_caminata'], 1)} COP |

## Resumen del último reporte
{resumen}

➡️ **[Leer el reporte completo](reportes/{ultimo})**

## Histórico y cono de pronóstico
![Cono de pronóstico]({cono})

## Semana a semana
![Variación semanal](reportes/{png_sem.name})

## Pronóstico del modelo
| Horizonte | Valor central | IC 80% | IC 95% | Prob. bajista / base / alcista del dólar |
|---|---|---|---|---|
{filas_hz}

## Todos los reportes
| Fecha | Tipo | Archivos |
|---|---|---|
{chr(10).join(lista)}

---
<sub>Generado por `execution/build_readme.py`. Cómo regenerar: `python3 execution/fetch_data.py && python3 execution/model.py && python3 execution/build_outputs.py --etiqueta AAAA-MM-DD && python3 execution/build_readme.py --etiqueta AAAA-MM-DD`. Reglas del reporte: [directives/reporte_usdcop.md](directives/reporte_usdcop.md).</sub>
"""
    (RAIZ / "README.md").write_text(md)
    print("README.md", png_sem)


if __name__ == "__main__":
    main()

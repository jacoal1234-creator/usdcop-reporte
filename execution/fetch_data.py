"""Descarga las series base del reporte USD/COP y las guarda en .tmp/.

Series:
- TRM diaria (Superfinanciera, vía datos.gov.co, recurso 32sa-8pi3).
- DXY (Yahoo Finance, DX-Y.NYB) y Brent (Yahoo Finance, BZ=F), cierre diario.
- Tesoro EE. UU. 10 años (FRED DGS10) y fondos federales efectiva (FRED DFF).

Uso: python3 execution/fetch_data.py [--desde 2023-01-01]
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
TMP = RAIZ / ".tmp"
UA = {"User-Agent": "Mozilla/5.0 (reporte-usdcop)"}


def _get(url: str, timeout: int = 30, intentos: int = 3) -> bytes:
    import time

    ultimo = None
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # reintento con espera creciente
            ultimo = e
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"{url} falló tras {intentos} intentos: {ultimo}")


def fetch_trm(desde: str) -> pd.DataFrame:
    """Una fila por cada TRM calculada (no por día calendario).

    Cada registro de la Superfinanciera rige de `vigenciadesde` a `vigenciahasta`.
    Un registro puede cubrir fin de semana y festivos; se asigna al primer día
    entre lunes y viernes de su vigencia para agruparlo por semana.
    """
    url = (
        "https://www.datos.gov.co/resource/32sa-8pi3.json"
        f"?$where=vigenciadesde>='{desde}T00:00:00'"
        "&$order=vigenciadesde ASC&$limit=50000"
    ).replace(" ", "%20").replace(">", "%3E").replace("'", "%27")
    datos = json.loads(_get(url))
    df = pd.DataFrame(datos)
    df["trm"] = df["valor"].astype(float)
    df["desde"] = pd.to_datetime(df["vigenciadesde"]).dt.normalize()
    df["hasta"] = pd.to_datetime(df["vigenciahasta"]).dt.normalize()

    def primer_habil(row):
        dias = pd.date_range(row["desde"], row["hasta"], freq="D")
        habiles = [d for d in dias if d.weekday() < 5]
        return habiles[0] if habiles else row["desde"]

    df["fecha"] = df.apply(primer_habil, axis=1)
    df = df[["fecha", "trm", "desde", "hasta"]].drop_duplicates("fecha", keep="last")
    return df.sort_values("fecha").reset_index(drop=True)


def fetch_yahoo(ticker: str, desde: str) -> pd.Series:
    import yfinance as yf

    h = yf.download(ticker, start=desde, progress=False, auto_adjust=False)
    if h.empty:
        raise RuntimeError(f"Yahoo no devolvió datos para {ticker}")
    s = h["Close"]
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
    return s.dropna()


def fetch_fred(serie: str, desde: str) -> pd.Series:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={serie}&cosd={desde}"
    df = pd.read_csv(io.BytesIO(_get(url)))
    df.columns = ["fecha", serie]
    df["fecha"] = pd.to_datetime(df["fecha"])
    df[serie] = pd.to_numeric(df[serie], errors="coerce")
    return df.set_index("fecha")[serie].dropna()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", default="2023-01-01")
    args = ap.parse_args()
    TMP.mkdir(exist_ok=True)

    estado = {"consulta": date.today().isoformat(), "series": {}}
    trm = fetch_trm(args.desde)
    trm.to_csv(TMP / "trm.csv", index=False)
    estado["series"]["TRM"] = {
        "fuente": "https://www.datos.gov.co/resource/32sa-8pi3.json",
        "ultima_fecha": str(trm["fecha"].iloc[-1].date()),
        "ultimo_valor": float(trm["trm"].iloc[-1]),
        "filas": len(trm),
    }

    externas = {
        "DXY": ("yahoo", "DX-Y.NYB", "https://finance.yahoo.com/quote/DX-Y.NYB"),
        "BRENT": ("yahoo", "BZ=F", "https://finance.yahoo.com/quote/BZ=F"),
        "UST10": ("fred", "DGS10", "https://fred.stlouisfed.org/series/DGS10"),
        "FEDFUNDS": ("fred", "DFF", "https://fred.stlouisfed.org/series/DFF"),
    }
    columnas = {}
    for nombre, (tipo, codigo, enlace) in externas.items():
        try:
            s = fetch_yahoo(codigo, args.desde) if tipo == "yahoo" else fetch_fred(codigo, args.desde)
            columnas[nombre] = s
            estado["series"][nombre] = {
                "fuente": enlace,
                "ultima_fecha": str(s.index[-1].date()),
                "ultimo_valor": float(s.iloc[-1]),
                "filas": int(len(s)),
            }
        except Exception as e:  # se reporta, no se inventa
            estado["series"][nombre] = {"fuente": enlace, "error": str(e)}
            print(f"[AVISO] {nombre}: {e}", file=sys.stderr)
            if nombre == "UST10":  # respaldo: rendimiento 10 años en Yahoo (^TNX)
                try:
                    s = fetch_yahoo("^TNX", args.desde)
                    columnas[nombre] = s
                    estado["series"][nombre] = {
                        "fuente": "https://finance.yahoo.com/quote/%5ETNX (respaldo; FRED falló)",
                        "ultima_fecha": str(s.index[-1].date()),
                        "ultimo_valor": float(s.iloc[-1]),
                        "filas": int(len(s)),
                    }
                except Exception as e2:
                    print(f"[AVISO] UST10 respaldo: {e2}", file=sys.stderr)

    pd.DataFrame(columnas).to_csv(TMP / "mercados.csv", index_label="fecha")
    (TMP / "estado_datos.json").write_text(json.dumps(estado, indent=2, ensure_ascii=False))
    print(json.dumps(estado, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

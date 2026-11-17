"""Tabla semanal, modelo cuantitativo y backtesting del USD/COP (base: TRM diaria).

Lógica (validada con el usuario el 2026-11-17):
- Tabla semanal: apertura/cierre/máx/mín = primera/última/mayor/menor TRM de la semana (lun-vie).
  Volatilidad = desv. estándar de retornos log diarios dentro de la semana.
- Pronóstico central: ARIMA(p,0,q) sobre retornos log diarios (p,q <= 2, elegido por AIC),
  comparado contra la caminata aleatoria. Si el ARIMA no le gana a la caminata aleatoria en el
  backtest (MAE), el valor central es la caminata aleatoria.
- Intervalos: GARCH(1,1) con innovaciones t de Student (estimado por máxima verosimilitud con
  scipy), simulado a 5, 20 y 63 días hábiles.
- Regresión explicativa (no predictiva): retorno semanal TRM ~ retorno DXY + retorno Brent
  + cambio del Tesoro 10 años. Sirve para atribuir movimientos y armar escenarios.
- Backtest: últimas 12 semanas; cada viernes se re-estima solo con datos hasta ese día y se
  pronostica la TRM del cierre de la semana siguiente.

Uso: python3 execution/model.py
Salida: .tmp/modelo.json, .tmp/semanal.csv, .tmp/backtest.csv, .tmp/simulaciones.npz
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize, stats
from statsmodels.tsa.arima.model import ARIMA
import statsmodels.api as sm

warnings.filterwarnings("ignore")
RAIZ = Path(__file__).resolve().parents[1]
TMP = RAIZ / ".tmp"
SEMILLA = 42
N_SIM = 20_000
HORIZONTES = {"1 semana": 5, "4 semanas": 20, "3 meses": 63}


# ---------- 1. Datos ----------
def cargar():
    trm = pd.read_csv(TMP / "trm.csv", parse_dates=["fecha"]).set_index("fecha")["trm"]
    mk = pd.read_csv(TMP / "mercados.csv", parse_dates=["fecha"]).set_index("fecha")
    return trm, mk


# ---------- 2. Tabla semanal ----------
def tabla_semanal(trm: pd.Series) -> pd.DataFrame:
    df = trm.to_frame("trm")
    df["ret"] = np.log(df["trm"]).diff()
    df["semana"] = df.index.to_period("W-FRI")
    g = df.groupby("semana")
    t = pd.DataFrame({
        "inicio": g.apply(lambda x: x.index.min().date()),
        "fin": g.apply(lambda x: x.index.max().date()),
        "dias": g.size(),
        "apertura": g["trm"].first(),
        "cierre": g["trm"].last(),
        "maximo": g["trm"].max(),
        "minimo": g["trm"].min(),
        "trm_promedio": g["trm"].mean(),
        "volatilidad_diaria_pct": g["ret"].std() * 100,
    })
    t["var_semanal_pct"] = t["cierre"].pct_change() * 100
    t["rango_pct"] = (t["maximo"] / t["minimo"] - 1) * 100
    t.index = t.index.astype(str)
    return t


# ---------- 3. GARCH(1,1)-t por máxima verosimilitud ----------
def _garch_nll(params, r):
    mu, omega, alpha, beta, nu = params
    if omega <= 0 or alpha < 0 or beta < 0 or alpha + beta >= 0.999 or nu <= 2.05:
        return 1e10
    e = r - mu
    s2 = np.empty_like(r)
    s2[0] = r.var()
    for t in range(1, len(r)):
        s2[t] = omega + alpha * e[t - 1] ** 2 + beta * s2[t - 1]
    escala = np.sqrt(s2 * (nu - 2) / nu)
    return -np.sum(stats.t.logpdf(e / escala, nu) - np.log(escala))


def ajustar_garch(r: np.ndarray) -> dict:
    r = np.asarray(r) * 100  # en %
    v = r.var()
    x0 = [r.mean(), v * 0.05, 0.08, 0.88, 6.0]
    res = optimize.minimize(_garch_nll, x0, args=(r,), method="Nelder-Mead",
                            options={"maxiter": 4000, "xatol": 1e-6, "fatol": 1e-6})
    mu, omega, alpha, beta, nu = res.x
    e = r - mu
    s2 = r.var()
    for t in range(1, len(r)):
        s2 = omega + alpha * e[t - 1] ** 2 + beta * s2
    s2_sig = omega + alpha * e[-1] ** 2 + beta * s2  # varianza del próximo día
    return {"mu": mu, "omega": omega, "alpha": alpha, "beta": beta, "nu": nu,
            "sigma_siguiente_pct": float(np.sqrt(s2_sig)),
            "sigma_largo_plazo_pct": float(np.sqrt(omega / (1 - alpha - beta))),
            "convergio": bool(res.success)}


def simular_garch(g: dict, h: int, n: int, deriva_pct: np.ndarray | None, rng) -> np.ndarray:
    """Retornos log acumulados (en fracción) a h días. deriva_pct: media diaria por día (en %)."""
    s2 = np.full(n, g["sigma_siguiente_pct"] ** 2)
    acum = np.zeros(n)
    nu = g["nu"]
    for d in range(h):
        z = rng.standard_t(nu, n) * np.sqrt((nu - 2) / nu)
        e = np.sqrt(s2) * z
        media = deriva_pct[d] if deriva_pct is not None else 0.0
        acum += media + e
        s2 = g["omega"] + g["alpha"] * e ** 2 + g["beta"] * s2
    return acum / 100


# ---------- 4. ARIMA sobre retornos ----------
def ajustar_arima(r: pd.Series):
    mejor = None
    for p in range(3):
        for q in range(3):
            try:
                m = ARIMA(r.values * 100, order=(p, 0, q), trend="c").fit()
                if mejor is None or m.aic < mejor[1].aic:
                    mejor = ((p, 0, q), m)
            except Exception:
                continue
    return mejor


def pronostico_central(r: pd.Series, h: int, usar_arima: bool, arima=None) -> np.ndarray:
    """Media diaria (en %) para cada uno de los h días."""
    if not usar_arima:
        return np.zeros(h)
    return np.asarray(arima.forecast(h))


# ---------- 5. Backtest ----------
def backtest(trm: pd.Series, semanas: int = 12) -> pd.DataFrame:
    df = trm.to_frame("trm")
    df["semana"] = df.index.to_period("W-FRI")
    cierres = df.groupby("semana")["trm"].agg(["last"]).rename(columns={"last": "cierre"})
    fechas_cierre = df.groupby("semana").apply(lambda x: x.index.max())
    filas = []
    hoy = pd.Timestamp.today().normalize()
    # solo semanas completas: la semana en curso no se usa como objetivo del backtest
    periodos = [p for p in cierres.index if p.end_time.normalize() < hoy]
    for k in range(len(periodos) - semanas - 1, len(periodos) - 1):
        corte = fechas_cierre[periodos[k]]
        sig = periodos[k + 1]
        hist = trm[trm.index <= corte]
        r = np.log(hist).diff().dropna()
        h = int((df["semana"] == sig).sum())
        orden, m = ajustar_arima(r)
        media = np.asarray(m.forecast(h))
        p_arima = hist.iloc[-1] * np.exp(media.sum() / 100)
        real = cierres.loc[sig, "cierre"]
        base = hist.iloc[-1]
        filas.append({
            "semana_pronosticada": str(sig),
            "fecha_corte": corte.date(),
            "trm_corte": base,
            "pronostico_arima": p_arima,
            "pronostico_caminata": base,
            "real": real,
            "error_arima": p_arima - real,
            "error_caminata": base - real,
            "direccion_real": np.sign(real - base),
            "direccion_arima": np.sign(p_arima - base),
            "orden_arima": str(orden),
        })
    bt = pd.DataFrame(filas)
    bt["acierto_direccion"] = (bt["direccion_real"] == bt["direccion_arima"]).astype(int)
    return bt


# ---------- 6. Regresión explicativa semanal ----------
def regresion(trm: pd.Series, mk: pd.DataFrame) -> dict:
    w = pd.DataFrame({"trm": trm}).join(mk, how="left").ffill()
    w = w.resample("W-FRI").last().dropna()
    y = np.log(w["trm"]).diff() * 100
    X = pd.DataFrame({
        "dxy_pct": np.log(w["DXY"]).diff() * 100,
        "brent_pct": np.log(w["BRENT"]).diff() * 100,
        "ust10_pb": w["UST10"].diff() * 100,
    })
    d = pd.concat([y.rename("trm_pct"), X], axis=1).dropna()
    m = sm.OLS(d["trm_pct"], sm.add_constant(d[["dxy_pct", "brent_pct", "ust10_pb"]])).fit(
        cov_type="HAC", cov_kwds={"maxlags": 4})
    ult = d.tail(12)
    atrib = pd.DataFrame({
        "trm_pct": ult["trm_pct"],
        "aporte_dxy": ult["dxy_pct"] * m.params["dxy_pct"],
        "aporte_brent": ult["brent_pct"] * m.params["brent_pct"],
        "aporte_ust10": ult["ust10_pb"] * m.params["ust10_pb"],
    })
    atrib["residuo"] = atrib["trm_pct"] - atrib[["aporte_dxy", "aporte_brent", "aporte_ust10"]].sum(axis=1) - m.params["const"]
    return {
        "coeficientes": m.params.round(4).to_dict(),
        "p_valores": m.pvalues.round(4).to_dict(),
        "r2": round(float(m.rsquared), 3),
        "n_semanas": int(m.nobs),
        "atribucion_12s": atrib.round(3).reset_index().assign(fecha=lambda x: x["fecha"].dt.date.astype(str)).to_dict("records"),
        "variables_ultima_semana": X.dropna().tail(1).round(3).to_dict("records")[0],
        "niveles_ultimos": w.tail(1).round(3).reset_index().assign(fecha=lambda x: x["fecha"].dt.date.astype(str)).to_dict("records")[0],
    }


# ---------- 7. Principal ----------
def main():
    rng = np.random.default_rng(SEMILLA)
    trm, mk = cargar()
    sem = tabla_semanal(trm)
    sem.to_csv(TMP / "semanal.csv")

    r = np.log(trm).diff().dropna()
    bt = backtest(trm)
    bt.to_csv(TMP / "backtest.csv", index=False)
    mae_a = bt["error_arima"].abs().mean()
    mae_c = bt["error_caminata"].abs().mean()
    usar_arima = bool(mae_a < mae_c)

    orden, arima = ajustar_arima(r)
    g = ajustar_garch(r.values)
    ultimo = float(trm.iloc[-1])
    sims, horiz = {}, {}
    for nombre, h in HORIZONTES.items():
        deriva = pronostico_central(r, h, usar_arima, arima)
        acum = simular_garch(g, h, N_SIM, deriva, rng)
        precios = ultimo * np.exp(acum)
        sims[nombre] = precios
        q = np.percentile(precios, [2.5, 10, 50, 90, 97.5])
        horiz[nombre] = {
            "dias_habiles": h,
            "central": float(ultimo * np.exp(deriva.sum() / 100)),
            "mediana_sim": float(q[2]),
            "ic80": [float(q[1]), float(q[3])],
            "ic95": [float(q[0]), float(q[4])],
            "p_sube": float((precios > ultimo).mean()),
        }
        # Escenarios: banda base = valor central ± 0,5 desviaciones del retorno simulado al horizonte.
        sd = float(np.log(precios / ultimo).std())
        lo = horiz[nombre]["central"] * np.exp(-0.5 * sd)
        hi = horiz[nombre]["central"] * np.exp(0.5 * sd)
        horiz[nombre]["escenarios"] = {
            "bajista_dolar": {"umbral": f"< {lo:,.0f}", "prob": float((precios < lo).mean()),
                              "mediana": float(np.median(precios[precios < lo]))},
            "base": {"umbral": f"{lo:,.0f} – {hi:,.0f}", "prob": float(((precios >= lo) & (precios <= hi)).mean()),
                     "mediana": float(np.median(precios[(precios >= lo) & (precios <= hi)]))},
            "alcista_dolar": {"umbral": f"> {hi:,.0f}", "prob": float((precios > hi).mean()),
                              "mediana": float(np.median(precios[precios > hi]))},
        }
    # cono diario para el gráfico (63 días)
    deriva63 = pronostico_central(r, 63, usar_arima, arima)
    s2 = np.full(N_SIM, g["sigma_siguiente_pct"] ** 2)
    acum = np.zeros(N_SIM)
    cono = []
    nu = g["nu"]
    for d in range(63):
        z = rng.standard_t(nu, N_SIM) * np.sqrt((nu - 2) / nu)
        e = np.sqrt(s2) * z
        acum += deriva63[d] + e
        s2 = g["omega"] + g["alpha"] * e ** 2 + g["beta"] * s2
        p = ultimo * np.exp(acum / 100)
        cono.append([d + 1, *np.percentile(p, [2.5, 10, 50, 90, 97.5])])
    pd.DataFrame(cono, columns=["dia", "p2_5", "p10", "p50", "p90", "p97_5"]).to_csv(TMP / "cono.csv", index=False)
    np.savez_compressed(TMP / "simulaciones.npz", **{k.replace(" ", "_"): v for k, v in sims.items()})

    reg = regresion(trm, mk)
    salida = {
        "ultima_trm": {"fecha": str(trm.index[-1].date()), "valor": ultimo},
        "trm_anterior": {"fecha": str(trm.index[-2].date()), "valor": float(trm.iloc[-2])},
        "arima": {"orden": str(orden), "aic": float(arima.aic), "params": dict(zip(arima.param_names, np.round(arima.params, 5).tolist()))},
        "garch": g,
        "valor_central_usa": "ARIMA" if usar_arima else "caminata aleatoria",
        "backtest": {
            "semanas": len(bt),
            "mae_arima": float(mae_a), "mae_caminata": float(mae_c),
            "mape_arima_pct": float((bt["error_arima"].abs() / bt["real"]).mean() * 100),
            "mape_caminata_pct": float((bt["error_caminata"].abs() / bt["real"]).mean() * 100),
            "sesgo_arima": float(bt["error_arima"].mean()),
            "acierto_direccion_pct": float(bt["acierto_direccion"].mean() * 100),
        },
        "horizontes": horiz,
        "regresion": reg,
    }
    (TMP / "modelo.json").write_text(json.dumps(salida, indent=2, ensure_ascii=False, default=str))
    print(json.dumps({k: salida[k] for k in ["ultima_trm", "arima", "garch", "valor_central_usa", "backtest", "horizontes"]}, indent=2, default=str))
    print(json.dumps({k: reg[k] for k in ["coeficientes", "p_valores", "r2", "n_semanas"]}, indent=2))


if __name__ == "__main__":
    main()

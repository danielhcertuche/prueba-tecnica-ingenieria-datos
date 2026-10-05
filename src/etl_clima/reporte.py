"""Reporte sencillo a partir de gold: un Markdown con tablas y cuatro gráficos.

Uso:
    python -m etl_clima.reporte
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402

from etl_clima.pipeline import DB_POR_DEFECTO, RAIZ  # noqa: E402

SALIDA_POR_DEFECTO = RAIZ / "reports" / "clima"

# Paleta: tres colores categóricos distinguibles con daltonismo y un par divergente azul-rojo.
TINTA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
REJILLA = "#e4e3df"
FONDO = "#fcfcfb"
AZUL, NARANJA, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
DIVERGENTE = ["#184f95", "#3987e5", "#bdbcb6", "#e66767", "#a32b2a"]
MESES_CORTOS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
BANDAS = {"Norte (>= 7° N)": AZUL, "Centro (2° - 7° N)": NARANJA, "Sur (< 2° N)": AQUA}


def _estilo() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": FONDO,
            "axes.facecolor": FONDO,
            "axes.edgecolor": REJILLA,
            "axes.labelcolor": TINTA_SECUNDARIA,
            "axes.titlecolor": TINTA,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": REJILLA,
            "grid.linewidth": 0.8,
            "xtick.color": TINTA_SECUNDARIA,
            "ytick.color": TINTA_SECUNDARIA,
            "font.size": 9.5,
            "legend.frameon": False,
            "savefig.dpi": 150,
            "savefig.bbox": "tight",
        }
    )


def _num(valor: float, decimales: int = 0) -> str:
    """Formato colombiano: punto de miles y coma decimal."""
    return f"{valor:,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _guardar(fig, carpeta: Path, nombre: str) -> str:
    fig.savefig(carpeta / "img" / nombre, metadata={"Software": None})
    plt.close(fig)
    return f"img/{nombre}"


def _ajuste(x: pd.Series, y: pd.Series) -> dict:
    pendiente, intercepto = np.polyfit(x, y, 1)
    return {"pendiente_km": pendiente * 1000, "intercepto": intercepto, "r2": np.corrcoef(x, y)[0, 1] ** 2, "n": len(x)}


def grafico_tasas_vs_elevacion(perfil: pd.DataFrame, carpeta: Path) -> tuple[str, dict]:
    etp = perfil.dropna(subset=["etp_diaria_mm"])
    evap = perfil.dropna(subset=["evaporacion_diaria_mm"])
    ajustes = {"etp": _ajuste(etp["elevacion_m"], etp["etp_diaria_mm"]),
               "evap": _ajuste(evap["elevacion_m"], evap["evaporacion_diaria_mm"])}

    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    x = np.array([0, 4200])
    for df, col, color, clave, nombre in [
        (etp, "etp_diaria_mm", AZUL, "etp", "Evapotranspiración potencial"),
        (evap, "evaporacion_diaria_mm", NARANJA, "evap", "Evaporación (tanque)"),
    ]:
        a = ajustes[clave]
        ax.scatter(df["elevacion_m"], df[col], s=12 if clave == "etp" else 18, color=color,
                   alpha=0.45 if clave == "etp" else 0.8, edgecolor=FONDO, linewidth=0.4, zorder=3,
                   label=f"{nombre}: {_num(a['pendiente_km'], 2)} mm/día por km, R² {_num(a['r2'], 2)} ({a['n']} est.)")
        ax.plot(x, a["intercepto"] + a["pendiente_km"] / 1000 * x, color=color, linewidth=2, zorder=4)
    ax.set_title("Demanda de evaporación según la altura")
    ax.set_xlabel("Elevación (m s. n. m.)")
    ax.set_ylabel("Tasa media diaria (mm/día)")
    ax.set_xlim(0, 4300)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncols=1)
    return _guardar(fig, carpeta, "tasas_vs_elevacion.png"), ajustes


def grafico_ciclo_etp_latitud(con: duckdb.DuckDBPyConnection, carpeta: Path) -> str:
    ciclo = con.execute(
        """
        WITH relativo AS (
            SELECT d.banda_latitud, f.mes,
                   f.valor_diario / avg(f.valor_diario) OVER (PARTITION BY f.codigo_estacion) AS relativo
            FROM gold.fact_normal_mensual f
            JOIN gold.dim_estacion d USING (codigo_estacion)
            WHERE f.variable = 'evapotranspiracion_potencial'
        )
        SELECT banda_latitud, mes, median(relativo) AS relativo, count(*) AS estaciones
        FROM relativo GROUP BY banda_latitud, mes ORDER BY banda_latitud, mes
        """
    ).df()
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    ax.axhline(1, color=TINTA_SECUNDARIA, linewidth=0.8, zorder=2)
    for banda, color in BANDAS.items():
        serie = ciclo[ciclo["banda_latitud"] == banda]
        ax.plot(serie["mes"], serie["relativo"], color=color, linewidth=2, marker="o", markersize=4,
                label=f"{banda}, {int(serie['estaciones'].iloc[0])} estaciones", zorder=3)
        ax.text(12.25, serie["relativo"].iloc[-1], banda.split(" ")[0], color=TINTA, va="center", fontsize=9)
    ax.set_xticks(range(1, 13), MESES_CORTOS)
    ax.set_xlim(0.7, 13.3)
    ax.set_title("Ciclo anual de la ETP según la latitud")
    ax.set_ylabel("ETP diaria / promedio anual (mediana)")
    ax.legend(loc="upper center", ncols=3, bbox_to_anchor=(0.5, -0.1))
    return _guardar(fig, carpeta, "ciclo_etp_latitud.png")


def grafico_mapa_razon(perfil: pd.DataFrame, carpeta: Path) -> str:
    p = perfil.dropna(subset=["razon_evaporacion_etp"])
    p = p[p["longitud"] > -79.5]  # San Andrés comprime el mapa; queda en las tablas
    cmap = LinearSegmentedColormap.from_list("divergente", DIVERGENTE)
    fig, ax = plt.subplots(figsize=(6.2, 7.2))
    sc = ax.scatter(p["longitud"], p["latitud"], c=p["razon_evaporacion_etp"], cmap=cmap,
                    norm=TwoSlopeNorm(vmin=0.6, vcenter=1.0, vmax=1.4), s=26, edgecolor=FONDO, linewidth=0.5, zorder=3)
    ax.set_aspect("equal")
    ax.set_title("Evaporación medida / ETP estimada")
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    barra = fig.colorbar(sc, ax=ax, shrink=0.6, pad=0.02, extend="both")
    barra.set_label("< 1: el tanque evapora menos que la ETP    > 1: más", color=TINTA_SECUNDARIA)
    barra.outline.set_visible(False)
    return _guardar(fig, carpeta, "mapa_razon_evaporacion_etp.png")


def grafico_razon_departamento(resumen: pd.DataFrame, carpeta: Path) -> str:
    r = resumen[resumen["estaciones_con_ambas"] >= 3].sort_values(["razon_evaporacion_etp_mediana", "departamento"])
    desvio = r["razon_evaporacion_etp_mediana"] - 1
    fig, ax = plt.subplots(figsize=(7.5, 6.6))
    ax.barh(r["departamento"], desvio, left=1, height=0.7, zorder=3,
            color=[DIVERGENTE[1] if d < 0 else DIVERGENTE[3] for d in desvio])
    ax.axvline(1, color=TINTA_SECUNDARIA, linewidth=0.8, zorder=4)
    for i, (_, fila) in enumerate(r.iterrows()):
        valor = fila["razon_evaporacion_etp_mediana"]
        ax.text(valor + (0.006 if valor >= 1 else -0.006), i, f"{_num(valor, 2)}  ({fila['estaciones_con_ambas']})",
                va="center", ha="left" if valor >= 1 else "right", color=TINTA, fontsize=8)
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(0.72, 1.3)
    ax.set_title("Evaporación / ETP por departamento (mediana)")
    ax.set_xlabel("Razón (entre paréntesis, estaciones con ambas medidas; solo departamentos con 3 o más)")
    return _guardar(fig, carpeta, "razon_por_departamento.png")


def _tabla_md(df: pd.DataFrame, decimales: int = 1) -> str:
    def celda(v):
        if isinstance(v, float):
            return "-" if np.isnan(v) else _num(v, decimales)
        return str(v)

    filas = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    filas += ["| " + " | ".join(celda(v) for v in fila) + " |" for fila in df.itertuples(index=False)]
    return "\n".join(filas)


def generar(ruta_db: Path, carpeta: Path) -> Path:
    _estilo()
    (carpeta / "img").mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(ruta_db), read_only=True)
    ejecucion = con.execute(
        "SELECT id_ejecucion, fin, archivo, sha256 FROM audit.etl_ejecucion "
        "WHERE estado = 'exitosa' ORDER BY fin DESC LIMIT 1"
    ).fetchone()
    calidad = con.execute(
        "SELECT regla, severidad, estado, fallidas, evaluadas FROM audit.calidad_resultado "
        "WHERE id_ejecucion = ? ORDER BY estado <> 'ok' DESC, regla", [ejecucion[0]]
    ).df()
    perfil = con.execute("SELECT * FROM gold.perfil_estacion").df()
    resumen = con.execute("SELECT * FROM gold.resumen_departamento").df()

    img_tasas, ajustes = grafico_tasas_vs_elevacion(perfil, carpeta)
    img_ciclo = grafico_ciclo_etp_latitud(con, carpeta)
    img_mapa = grafico_mapa_razon(perfil, carpeta)
    img_depto = grafico_razon_departamento(resumen, carpeta)

    etp = perfil.dropna(subset=["etp_anual_mm"])
    evap = perfil.dropna(subset=["evaporacion_anual_mm"])
    ambas = perfil.dropna(subset=["razon_evaporacion_etp"])
    diferencia_publicada = (evap["evaporacion_anual_publicada_mm"] - evap["evaporacion_anual_mm"]) / evap["evaporacion_anual_mm"]

    columnas = {"nombre": "Estación", "municipio": "Municipio", "departamento": "Departamento",
                "elevacion_m": "Elevación (m)", "evaporacion_anual_mm": "Evaporación (mm/año)",
                "etp_anual_mm": "ETP (mm/año)", "razon_evaporacion_etp": "Evap. / ETP"}
    extremos = pd.concat([evap.nlargest(5, "evaporacion_anual_mm", keep="first"), evap.nsmallest(5, "evaporacion_anual_mm", keep="first")])
    extremos = extremos[list(columnas)].rename(columns=columnas)

    por_piso = (
        perfil.groupby(["piso_termico_orden", "piso_termico"])
        .agg(etp_n=("etp_anual_mm", "count"), etp=("etp_anual_mm", "median"),
             evap_n=("evaporacion_anual_mm", "count"), evap=("evaporacion_anual_mm", "median"),
             razon=("razon_evaporacion_etp", "median"))
        .reset_index().drop(columns="piso_termico_orden")
        .rename(columns={"piso_termico": "Piso térmico", "etp_n": "Estaciones ETP", "etp": "ETP mediana (mm)",
                         "evap_n": "Estaciones evaporación", "evap": "Evaporación mediana (mm)",
                         "razon": "Evap. / ETP"})
    )
    departamentos = resumen.sort_values(["etp_mediana_mm", "departamento"], ascending=[False, True])[
        ["departamento", "estaciones_etp", "etp_mediana_mm", "estaciones_evaporacion", "evaporacion_mediana_mm",
         "razon_evaporacion_etp_mediana"]
    ].rename(columns={"departamento": "Departamento", "estaciones_etp": "Estaciones ETP",
                      "etp_mediana_mm": "ETP mediana (mm)", "estaciones_evaporacion": "Estaciones evaporación",
                      "evaporacion_mediana_mm": "Evaporación mediana (mm)",
                      "razon_evaporacion_etp_mediana": "Evap. / ETP"})
    calidad_md = calidad.assign(resultado=calidad["fallidas"].astype(str) + " / " + calidad["evaluadas"].astype(str))
    calidad_md = calidad_md[["regla", "severidad", "estado", "resultado"]].rename(
        columns={"regla": "Regla", "severidad": "Severidad", "estado": "Estado", "resultado": "Fallidas / evaluadas"})

    texto = f"""# Reporte: evaporación y evapotranspiración potencial, normales 1981-2010

Generado desde `data/warehouse/clima.duckdb` (capa gold), archivo `{ejecucion[2]}`
(sha256 `{ejecucion[3][:16]}…`). Los anuales son la suma de los 12 meses.

## Cifras generales

| Indicador | Valor |
|---|---|
| Estaciones con ETP | {_num(len(etp))} |
| Estaciones con evaporación medida | {len(evap)} |
| Estaciones con ambas | {len(ambas)} |
| ETP anual, mediana (mín - máx) | {_num(etp['etp_anual_mm'].median())} mm ({_num(etp['etp_anual_mm'].min())} - {_num(etp['etp_anual_mm'].max())}) |
| Evaporación anual, mediana (mín - máx) | {_num(evap['evaporacion_anual_mm'].median())} mm ({_num(evap['evaporacion_anual_mm'].min())} - {_num(evap['evaporacion_anual_mm'].max())}) |
| Evaporación / ETP, mediana (p10 - p90) | {_num(ambas['razon_evaporacion_etp'].median(), 2)} ({_num(ambas['razon_evaporacion_etp'].quantile(.1), 2)} - {_num(ambas['razon_evaporacion_etp'].quantile(.9), 2)}) |
| Cambio de la ETP con la altura | {_num(ajustes['etp']['pendiente_km'], 2)} mm/día por km (R² {_num(ajustes['etp']['r2'], 2)}) |
| Cambio de la evaporación con la altura | {_num(ajustes['evap']['pendiente_km'], 2)} mm/día por km (R² {_num(ajustes['evap']['r2'], 2)}) |
| Anual publicado de evaporación vs suma de meses | {_num(diferencia_publicada.median() * 100, 1)}% en la mediana |

## Altura

![Tasas vs elevación]({img_tasas})

{_tabla_md(por_piso, 2)}

## Época del año

![Ciclo de la ETP por latitud]({img_ciclo})

## Evaporación medida frente a la estimada

![Mapa de la razón]({img_mapa})

![Razón por departamento]({img_depto})

Estaciones con mayor y menor evaporación:

{_tabla_md(extremos, 2)}

## Por departamento

{_tabla_md(departamentos, 2)}

## Calidad de la carga

{_tabla_md(calidad_md)}
"""
    salida = carpeta / "reporte_clima.md"
    salida.write_text(texto, encoding="utf-8")
    con.close()
    return salida


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Genera el reporte de evaporación y ETP desde gold")
    parser.add_argument("--db", type=Path, default=DB_POR_DEFECTO)
    parser.add_argument("--salida", type=Path, default=SALIDA_POR_DEFECTO)
    args = parser.parse_args(argv)
    print(f"Reporte en {generar(args.db, args.salida)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

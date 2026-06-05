from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd


BASE_PATH = Path(__file__).resolve().parent
AGUA_PATH = BASE_PATH / "consumo_agua" / "consumo_agua_historico_2019.csv"
HOGARES_PATH = BASE_PATH / "Hogares por colonia" / "hogares_colonia.shp"
OUTPUT_PATH = BASE_PATH / "consumo_agua" / "tabla_colonia_consumo.csv"


MANUAL_CVE_MAP = {
    ("ALVARO OBREGON", "CAROLA"): "10-040",
    ("ALVARO OBREGON", "EL CUERNITO"): "10-187",
    ("ALVARO OBREGON", "EMANCIPACION DEL PUEBLO"): "10-069",
    ("ALVARO OBREGON", "LA CAADA"): "10-096",
    ("AZCAPOTZALCO", "AMPLIACION PETROLERA"): "02-059",
    ("AZCAPOTZALCO", "INDUSTRIAL VALLEJO (U HAB)"): "02-036",
    ("AZCAPOTZALCO", "NUEVA ESPAA"): "02-051",
    ("COYOACAN", "CTM IX CULHUACAN 32-33 (U HAB)"): "03-156",
    ("IZTACALCO", "LA ASUNCION"): "06-016",
    ("IZTACALCO", "LOS REYES"): "06-018",
    ("IZTACALCO", "SAN FCO XICALTONGO"): "06-029",
    ("IZTACALCO", "SAN MIGUEL"): "06-030",
    ("IZTACALCO", "SAN PEDRO IZTACALCO"): "06-031",
    ("IZTACALCO", "SANTA CRUZ"): "06-033",
    ("IZTACALCO", "SANTIAGO NORTE"): "06-034",
    ("IZTACALCO", "SANTIAGO SUR"): "06-035",
    ("IZTACALCO", "ZAPOTLA"): "06-039",
    ("IZTAPALAPA", "AO DE JUAREZ"): "07-007",
    ("IZTAPALAPA", "EL RETOO"): "07-057",
    ("IZTAPALAPA", "LA COLMENA"): "07-105",
    ("IZTAPALAPA", "LAS PEAS I"): "07-118",
    ("IZTAPALAPA", "LAS PEAS II"): "07-314",
    ("IZTAPALAPA", "SAN JUAN 2A AMPLIACIN (PJE)"): "07-270",
    ("LA MAGDALENA CONTRERAS", "EL ERMITAO"): "08-006",
    ("MIGUEL HIDALGO", "BOSQUE DE CHAPULTEPEC I, II Y III SECCIONES"): "16-018",
    ("MIGUEL HIDALGO", "LOMAS DE CHAPULTEPEC"): "16-042",
    ("TLAHUAC", "PEA ALTA"): "11-029",
    ("TLALPAN", "LA  LONJA"): "12-069",
    ("TLALPAN", "LOMAS DE PADIERNA (AMPL)"): "12-211",
    ("TLALPAN", "NIO JESUS (BARR)"): "12-124",
    ("TLALPAN", "ROMULO SANCHEZ-SAN FERNANDO (BARR)-PEA POBRE"): "12-154",
    ("VENUSTIANO CARRANZA", "AMPL CARACOL"): "17-018",
    ("VENUSTIANO CARRANZA", "PEON DE LOS BAOS"): "17-071",
    ("XOCHIMILCO", "LA CAADA"): "13-027",
    ("XOCHIMILCO", "LORETO PEA POBRE (U HAB)"): "13-055",
    ("XOCHIMILCO", "SAN JOSE LAS PERITAS"): "13-080",
}


def fix_mojibake(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    if "Ã" in text:
        try:
            return text.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return text
    return text


def normalize_text(value: object) -> str:
    text = fix_mojibake(value).strip().upper()
    text = "".join(
        ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch)
    )
    text = text.replace("&", " Y ")
    replacements = {
        "AMPLIACION": "AMPL",
        "SECCION": "SECC",
        "SECCIN": "SECC",
        "FCO": "FRANCISCO",
        "NIO": "NINO",
        "ESPAA": "ESPANA",
        "PEA": "PENA",
        "CAADA": "CANADA",
        "AO": "ANO",
        "RETOO": "RETONO",
        "MONTAA": "MONTANA",
        "BAOS": "BANOS",
        "ERMITAO": "ERMITANO",
        "TAXQUEA": "TAXQUENA",
        "CUITLHUAC": "CUITLAHUAC",
    }
    for original, replacement in replacements.items():
        text = text.replace(original, replacement)
    text = re.sub(r"\bU\s+HAB\b", "U HAB", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_tabla_colonia() -> pd.DataFrame:
    df = pd.read_csv(AGUA_PATH).drop_duplicates().copy()
    keep_columns = ["alcaldia", "colonia", "indice_des", "consumo_total"]
    df = df[keep_columns]
    df_colapsado = (
        df.groupby(["alcaldia", "colonia", "indice_des"], as_index=False)
        .agg(consumo_total=("consumo_total", "sum"))
    )

    tabla = (
        df_colapsado.pivot_table(
            index=["alcaldia", "colonia"],
            columns="indice_des",
            values="consumo_total",
            aggfunc="sum",
            fill_value=0,
        )
        .rename(
            columns={
                "POPULAR": "consumo_popular",
                "BAJO": "consumo_bajo",
                "MEDIO": "consumo_medio",
                "ALTO": "consumo_alto",
            }
        )
        .reset_index()
    )

    for column in ["consumo_popular", "consumo_bajo", "consumo_medio", "consumo_alto"]:
        if column not in tabla.columns:
            tabla[column] = 0.0

    tabla["consumo_total"] = tabla[
        ["consumo_popular", "consumo_bajo", "consumo_medio", "consumo_alto"]
    ].sum(axis=1)

    for level in ["popular", "bajo", "medio", "alto"]:
        tabla[f"perc_{level}"] = (
            tabla[f"consumo_{level}"].div(tabla["consumo_total"]).fillna(0.0)
        )

    ordered_columns = [
        "alcaldia",
        "colonia",
        "consumo_total",
        "consumo_popular",
        "consumo_bajo",
        "consumo_medio",
        "consumo_alto",
        "perc_popular",
        "perc_bajo",
        "perc_medio",
        "perc_alto",
    ]
    return tabla[ordered_columns].sort_values(["alcaldia", "colonia"]).reset_index(drop=True)


def load_hogares() -> pd.DataFrame:
    hogares = gpd.read_file(HOGARES_PATH)[["alcaldia", "colonia", "cve_col", "Sum_TotHog"]].copy()
    hogares["alcaldia_norm"] = hogares["alcaldia"].map(normalize_text)
    hogares["colonia_norm"] = hogares["colonia"].map(normalize_text)
    hogares["Sum_TotHog"] = pd.to_numeric(hogares["Sum_TotHog"], errors="coerce").round().astype("Int64")
    return hogares.drop_duplicates(subset=["alcaldia_norm", "colonia_norm"], keep="first")


def main() -> None:
    tabla = build_tabla_colonia()
    tabla["alcaldia_norm"] = tabla["alcaldia"].map(normalize_text)
    tabla["colonia_norm"] = tabla["colonia"].map(normalize_text)

    hogares = load_hogares()
    merged = tabla.merge(
        hogares[["alcaldia_norm", "colonia_norm", "cve_col", "Sum_TotHog"]],
        on=["alcaldia_norm", "colonia_norm"],
        how="left",
    )

    if MANUAL_CVE_MAP:
        hogares_by_cve = hogares[["cve_col", "Sum_TotHog"]].drop_duplicates(subset=["cve_col"])
        manual_df = pd.DataFrame(
            [
                {"alcaldia": alcaldia, "colonia": colonia, "cve_col": cve_col}
                for (alcaldia, colonia), cve_col in MANUAL_CVE_MAP.items()
            ]
        ).merge(hogares_by_cve, on="cve_col", how="left")

        merged = merged.merge(
            manual_df.rename(
                columns={"cve_col": "cve_col_manual", "Sum_TotHog": "Sum_TotHog_manual"}
            ),
            on=["alcaldia", "colonia"],
            how="left",
        )
        merged["cve_col"] = merged["cve_col"].fillna(merged["cve_col_manual"])
        merged["Sum_TotHog"] = merged["Sum_TotHog"].fillna(merged["Sum_TotHog_manual"])
        merged = merged.drop(columns=["cve_col_manual", "Sum_TotHog_manual"])

    merged["Sum_TotHog"] = merged["Sum_TotHog"].astype("Int64")

    final_columns = [
        "alcaldia",
        "colonia",
        "consumo_total",
        "consumo_popular",
        "consumo_bajo",
        "consumo_medio",
        "consumo_alto",
        "perc_popular",
        "perc_bajo",
        "perc_medio",
        "perc_alto",
        "cve_col",
        "Sum_TotHog",
    ]
    final_df = merged[final_columns].copy()
    final_df.to_csv(OUTPUT_PATH, index=False)

    matched = final_df["Sum_TotHog"].notna().sum()
    unmatched = final_df["Sum_TotHog"].isna().sum()
    print(f"Archivo generado: {OUTPUT_PATH}")
    print(f"Filas totales: {len(final_df)}")
    print(f"Filas con hogares: {matched}")
    print(f"Filas sin hogares: {unmatched}")
    if unmatched:
        print("\nColonias sin hogares asignados:")
        print(final_df.loc[final_df["Sum_TotHog"].isna(), ["alcaldia", "colonia"]].to_string(index=False))


if __name__ == "__main__":
    main()

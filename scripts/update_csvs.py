# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "openpyxl>=3.1.5",
#     "pandas>=3.0.0",
# ]
# ///

from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_OFERTA = BASE_DIR / "oferta_grupos.csv"
OUTPUT_GRUPO = BASE_DIR / "gruposec_adhoc.csv"
REQUIRED_RELATIVE = (
    Path("Base_Oferta_INFORME_MENSUAL") / "Generación Local Mensual.xlsx"
)


def find_header_row(path: Path, sheet: str | int, needle: str = "AÑO") -> int | None:
    df = pd.read_excel(path, sheet_name=sheet, header=None, nrows=80)
    for idx, row in df.iterrows():
        if row.astype(str).str.contains(needle, case=False, na=False).any():
            return int(idx)
    return None


def normalize_text(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text if text else None


def load_generacion_local(path: Path) -> pd.DataFrame:
    sheet = "GENERACION"
    header_row = find_header_row(path, sheet, "AÑO")
    if header_row is None:
        raise ValueError(
            "No se encontró la fila de encabezados en Generación Local Mensual.xlsx"
        )

    df = pd.read_excel(path, sheet_name=sheet, header=header_row)
    df = df.loc[
        :,
        [
            "AÑO",
            "MES",
            "MAQUINA",
            "CENTRAL",
            "AGENTE",
            "AGENTE DESCRIPCION",
            "REGION",
            "PROVINCIA",
            "PAIS",
            "TIPO MAQUINA",
            "FUENTE GENERACION",
            "TECNOLOGIA",
            "CATEGORIA HIDRAULICA",
            "CATEGORIA REGION",
            "GENERACION NETA",
        ],
    ]

    df = df[df["MAQUINA"].notna()]

    df = df.rename(
        columns={
            "AÑO": "ano",
            "MES": "mes",
            "MAQUINA": "maquina",
            "CENTRAL": "central",
            "AGENTE": "codigo_agente",
            "AGENTE DESCRIPCION": "agente_descripcion",
            "REGION": "region",
            "PROVINCIA": "provincia",
            "PAIS": "pais",
            "TIPO MAQUINA": "tipo_maquina",
            "FUENTE GENERACION": "fuente_generacion",
            "TECNOLOGIA": "tecnologia",
            "CATEGORIA HIDRAULICA": "categoria_hidraulica",
            "CATEGORIA REGION": "categoria_region",
            "GENERACION NETA": "generacion_neta",
        }
    )

    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
    df["mes"] = pd.to_datetime(df["mes"], errors="coerce").dt.strftime("%Y-%m-%d")

    text_cols = [
        "maquina",
        "central",
        "codigo_agente",
        "agente_descripcion",
        "region",
        "provincia",
        "pais",
        "tipo_maquina",
        "fuente_generacion",
        "tecnologia",
        "categoria_hidraulica",
        "categoria_region",
    ]
    for col in text_cols:
        df[col] = df[col].apply(normalize_text)

    df["generacion_neta"] = pd.to_numeric(df["generacion_neta"], errors="coerce").round(
        3
    )

    return df


def load_grupo_mapping(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", dtype=str)
    df.columns = ["codigo_agente", "grupo_economico"]
    df["codigo_agente"] = df["codigo_agente"].apply(normalize_text)
    df["grupo_economico"] = df["grupo_economico"].apply(normalize_text)
    return df


def update_grupo_mapping(base: pd.DataFrame, agents: pd.Series) -> pd.DataFrame:
    existing = set(base["codigo_agente"].dropna())
    new_agents = sorted({a for a in agents.dropna() if a not in existing})
    if not new_agents:
        return base
    extras = pd.DataFrame(
        {
            "codigo_agente": new_agents,
            "grupo_economico": ["Sin clasificar"] * len(new_agents),
        }
    )
    return pd.concat([base, extras], ignore_index=True)


def build_geo_lookup(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    geo_cols = [
        "maquina",
        "lon",
        "lat",
        "geo_nombre",
        "geo_tecnologia",
        "geo_nombre_age",
        "potencia_instalada",
        "geo_provincia",
        "geo_sistema",
    ]
    df = df[geo_cols]

    def first_non_null(series: pd.Series) -> object:
        for value in series:
            if pd.notna(value) and str(value).strip() != "":
                return value
        return None

    agg = df.groupby("maquina", as_index=False).agg(first_non_null)
    return agg


def load_potencia_autogeneradores(path: Path) -> pd.DataFrame:
    sheet = " Pot. Instalada Autogeneradores"
    header_row = find_header_row(path, sheet, "MAQUINA")
    if header_row is None:
        return pd.DataFrame(columns=["maquina", "potencia_instalada"])
    df = pd.read_excel(path, sheet_name=sheet, header=header_row)
    df = df.rename(
        columns={
            "MAQUINA": "maquina",
            "POTENCIA INSTALADA [MW]": "potencia_instalada",
        }
    )
    df["maquina"] = df["maquina"].apply(normalize_text)
    df["potencia_instalada"] = pd.to_numeric(df["potencia_instalada"], errors="coerce")
    df = df.dropna(subset=["maquina"])
    return df[["maquina", "potencia_instalada"]]


def locate_base_dir(root: Path) -> Path:
    if (root / REQUIRED_RELATIVE).exists():
        return root
    for candidate in root.rglob("Base_Oferta_INFORME_MENSUAL"):
        parent = candidate.parent
        if (parent / REQUIRED_RELATIVE).exists():
            return parent
    raise FileNotFoundError(
        "No se encontró Base_Oferta_INFORME_MENSUAL/Generación Local Mensual.xlsx "
        "en la ruta indicada."
    )


def resolve_input(path: Path) -> tuple[Path, TemporaryDirectory | None]:
    if path.is_file() and path.suffix.lower() == ".zip":
        temp_dir = TemporaryDirectory()
        with zipfile.ZipFile(path, "r") as zip_ref:
            zip_ref.extractall(temp_dir.name)
        return Path(temp_dir.name), temp_dir
    if path.exists():
        return path, None
    raise FileNotFoundError(f"No existe la ruta indicada: {path}")


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Uso: uv run scripts/update_csvs.py <ruta-a-zip-o-carpeta>\n"
            "Ejemplo: uv run scripts/update_csvs.py BASE_INFORME_MENSUAL_2025-12.zip"
        )

    input_path = Path(sys.argv[1]).expanduser().resolve()
    root, temp_dir = resolve_input(input_path)
    try:
        base_dir = locate_base_dir(root)
        oferta_dir = base_dir / "Base_Oferta_INFORME_MENSUAL"

        generacion_path = oferta_dir / "Generación Local Mensual.xlsx"
        potencia_path = oferta_dir / "Potencia Instalada.xlsx"

        df_gen = load_generacion_local(generacion_path)

        grupo_base = load_grupo_mapping(OUTPUT_GRUPO)
        grupo_updated = update_grupo_mapping(grupo_base, df_gen["codigo_agente"])

        grupo_lookup = dict(
            zip(grupo_updated["codigo_agente"], grupo_updated["grupo_economico"])
        )
        df_gen["grupo_economico"] = (
            df_gen["codigo_agente"].map(grupo_lookup).fillna("Sin clasificar")
        )

        geo_lookup = build_geo_lookup(OUTPUT_OFERTA)
        df_gen = df_gen.merge(geo_lookup, on="maquina", how="left")

        potencia_auto = load_potencia_autogeneradores(potencia_path)
        if not potencia_auto.empty:
            potencia_map = dict(
                zip(potencia_auto["maquina"], potencia_auto["potencia_instalada"])
            )
            df_gen["potencia_instalada"] = (
                df_gen["maquina"]
                .map(potencia_map)
                .combine_first(df_gen["potencia_instalada"])
            )
            df_gen["potencia_instalada"] = df_gen["potencia_instalada"].round(3)

        ordered_cols = [
            "ano",
            "mes",
            "maquina",
            "central",
            "codigo_agente",
            "agente_descripcion",
            "region",
            "provincia",
            "pais",
            "tipo_maquina",
            "fuente_generacion",
            "tecnologia",
            "categoria_hidraulica",
            "categoria_region",
            "generacion_neta",
            "grupo_economico",
            "lon",
            "lat",
            "geo_nombre",
            "geo_tecnologia",
            "geo_nombre_age",
            "potencia_instalada",
            "geo_provincia",
            "geo_sistema",
        ]

        df_gen = df_gen[ordered_cols]

        df_gen.to_csv(OUTPUT_OFERTA, index=False)
        grupo_updated.to_csv(
            OUTPUT_GRUPO, sep=";", index=False, header=["AGENTE", "GRUPO ECONÓMICO"]
        )

        print(f"Filas de oferta: {len(df_gen)}")
        print(f"Agentes en grupos: {len(grupo_updated)}")
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


if __name__ == "__main__":
    main()

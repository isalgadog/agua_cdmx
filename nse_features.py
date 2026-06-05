import numpy as np
import pandas as pd


def add_socioeconomic_features(
    df: pd.DataFrame,
    popular_col: str = "popular",
    bajo_col: str = "bajo",
    medio_col: str = "medio",
    alto_col: str = "alto",
    normalize_if_needed: bool = True,
) -> pd.DataFrame:
    """
    Agrega dos columnas nuevas a partir de porcentajes por nivel socioeconómico:

    - nivel_promedio_ponderado
    - diversidad_shannon

    Las columnas pueden venir en proporciones (0 a 1) o en porcentajes (0 a 100).
    Si normalize_if_needed=True y la suma de las cuatro columnas es > 1.5, se asume
    que vienen en escala 0-100 y se convierten a proporciones.
    """

    cols = [popular_col, bajo_col, medio_col, alto_col]
    result = df.copy()

    proportions = result[cols].astype(float)
    row_sums = proportions.sum(axis=1)

    if normalize_if_needed:
        # Si parece que los datos vienen como 50, 20, 20, 10 en vez de 0.5, 0.2...
        proportions = proportions.div(
            np.where(row_sums > 1.5, row_sums, 1),
            axis=0,
        )

    weights = np.array([1.0, 2.0, 3.0, 4.0])
    result["nivel_promedio_ponderado"] = proportions.mul(weights, axis=1).sum(axis=1)

    safe_proportions = proportions.where(proportions > 0, 1.0)
    result["diversidad_shannon"] = -(proportions * np.log(safe_proportions)).sum(axis=1)

    return result


if __name__ == "__main__":
    example = pd.DataFrame(
        {
            "colonia": ["Ejemplo A", "Ejemplo B", "Ejemplo C"],
            "popular": [50, 100, 25],
            "bajo": [20, 0, 25],
            "medio": [20, 0, 25],
            "alto": [10, 0, 25],
        }
    )

    enriched = add_socioeconomic_features(example)
    print(enriched)

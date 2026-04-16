import json
from functools import lru_cache

try:
    from Backend.database import fetch_all, fetch_scalar
    from Backend.schemas import MelbourneHeatmapRegion, MelbourneHeatmapResponse
except ModuleNotFoundError:
    from database import fetch_all, fetch_scalar
    from schemas import MelbourneHeatmapRegion, MelbourneHeatmapResponse


WORKING_RATIO_WEIGHT = 0.6
SHORT_COMMUTE_WEIGHT = 0.3
ZERO_CAR_WEIGHT = 0.1
HEATMAP_SIMPLIFY_TOLERANCE = 0.0008


@lru_cache(maxsize=1)
def get_melbourne_heatmap() -> MelbourneHeatmapResponse:
    rows = fetch_suburb_census_rows()
    if not rows:
        return MelbourneHeatmapResponse(
            regions=[],
            status_message="Melbourne SA2 heatmap data is currently unavailable.",
        )

    enriched_rows = build_enriched_rows(rows)
    scored_rows = build_scored_rows(enriched_rows)
    regions = [region_from_row(row) for row in scored_rows]
    return MelbourneHeatmapResponse(regions=regions, status_message=None)


def warm_melbourne_heatmap_cache() -> None:
    try:
        get_melbourne_heatmap()
    except Exception:
        # Service startup should not fail just because heatmap preloading is unavailable.
        pass


def fetch_suburb_census_rows() -> list[dict]:
    geom_select = (
        (
            "ST_AsGeoJSON("
            "ST_SimplifyPreserveTopology(geom, :simplify_tolerance), "
            "5"
            ") AS geom_json,"
        )
        if suburb_census_has_geom()
        else "NULL::text AS geom_json,"
    )
    query = f"""
        WITH latest_suburb_census AS (
            SELECT
                sc.*,
                ROW_NUMBER() OVER (
                    PARTITION BY sc.sa2_code
                    ORDER BY sc.data_year DESC NULLS LAST, sc.suburb_name
                ) AS row_num
            FROM ridesmart.suburb_census sc
        )
        SELECT
            sa2_code,
            suburb_name,
            resident_population,
            working_population,
            short_commute_pct,
            zero_car_household_pct,
            {geom_select}
            data_year
        FROM latest_suburb_census
        WHERE row_num = 1
          AND resident_population IS NOT NULL
          AND resident_population > 0
          AND short_commute_pct IS NOT NULL
          AND zero_car_household_pct IS NOT NULL
        ORDER BY suburb_name
    """
    try:
        return fetch_all(query, {"simplify_tolerance": HEATMAP_SIMPLIFY_TOLERANCE})
    except Exception:
        return []


def suburb_census_has_geom() -> bool:
    query = """
        SELECT COUNT(*) > 0
        FROM information_schema.columns
        WHERE table_schema = 'ridesmart'
          AND table_name = 'suburb_census'
          AND column_name = 'geom'
    """
    try:
        return bool(fetch_scalar(query))
    except Exception:
        return False


def build_enriched_rows(rows: list[dict]) -> list[dict]:
    enriched_rows = []
    for row in rows:
        working_ratio = float(row["working_population"]) / float(row["resident_population"])
        enriched_rows.append(
            {
                **row,
                "working_population_ratio": round(working_ratio, 4),
            }
        )
    return enriched_rows


def build_scored_rows(enriched_rows: list[dict]) -> list[dict]:
    working_values = [item["working_population_ratio"] for item in enriched_rows]
    short_commute_values = [float(item["short_commute_pct"]) for item in enriched_rows]
    zero_car_values = [float(item["zero_car_household_pct"]) for item in enriched_rows]

    scored_rows: list[dict] = []
    for row in enriched_rows:
        working_score = normalise_score(
            row["working_population_ratio"],
            min(working_values),
            max(working_values),
            inverse=False,
        )
        short_commute_score = normalise_score(
            float(row["short_commute_pct"]),
            min(short_commute_values),
            max(short_commute_values),
            inverse=True,
        )
        zero_car_score = normalise_score(
            float(row["zero_car_household_pct"]),
            min(zero_car_values),
            max(zero_car_values),
            inverse=True,
        )

        score = round(
            working_score * WORKING_RATIO_WEIGHT
            + short_commute_score * SHORT_COMMUTE_WEIGHT
            + zero_car_score * ZERO_CAR_WEIGHT
        )
        scored_rows.append({**row, "score": score})

    ranked_rows = sorted(scored_rows, key=lambda item: item["score"])
    total_rows = len(ranked_rows)
    for index, row in enumerate(ranked_rows):
        percentile = (index + 1) / total_rows
        row["risk_level"] = risk_level_from_percentile(percentile)
    return scored_rows


def region_from_row(row: dict) -> MelbourneHeatmapRegion:
    score = int(row["score"])

    return MelbourneHeatmapRegion(
        sa2_code=str(row["sa2_code"]),
        suburb_name=str(row["suburb_name"]),
        score=score,
        risk_level=str(row["risk_level"]),
        intensity=score,
        working_population_ratio=round(float(row["working_population_ratio"]), 4),
        short_commute_pct=round(float(row["short_commute_pct"]), 2),
        zero_car_household_pct=round(float(row["zero_car_household_pct"]), 2),
        geometry=parse_geometry(row.get("geom_json")),
    )


def normalise_score(value: float, minimum: float, maximum: float, inverse: bool) -> float:
    if maximum <= minimum:
        return 50.0

    normalised = ((value - minimum) / (maximum - minimum)) * 100
    if inverse:
        normalised = 100 - normalised
    return max(0.0, min(100.0, normalised))


def risk_level_from_percentile(percentile: float) -> str:
    if percentile > 0.7:
        return "Red"
    if percentile > 0.3:
        return "Yellow"
    return "Green"


def parse_geometry(geom_json: str | None) -> dict | None:
    if not geom_json:
        return None
    try:
        return json.loads(geom_json)
    except ValueError:
        return None

import json
from pathlib import Path

from pydantic import BaseModel, Field

from simulation.models.policy import PolicySchema
from simulation.models.province import ProvinceProfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


class NetworkEdge(BaseModel):
    target: str
    weight: float = Field(ge=0, le=1)


def _read_json(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_profiles(path: Path | None = None) -> dict[str, ProvinceProfile]:
    raw = _read_json(path or DATA_DIR / "province_profiles_v1.json")
    if not isinstance(raw, list):
        raise ValueError("province profiles must be a JSON array")
    profiles = [ProvinceProfile.model_validate(item) for item in raw]
    result = {profile.province_code: profile for profile in profiles}
    if len(result) != len(profiles):
        raise ValueError("province codes must be unique")
    return result


def load_network(path: Path | None = None) -> dict[str, list[NetworkEdge]]:
    raw = _read_json(path or DATA_DIR / "province_network_v1.json")
    if not isinstance(raw, dict) or not isinstance(raw.get("edges"), dict):
        raise ValueError("province network must contain an edges object")
    return {
        source: [NetworkEdge.model_validate(edge) for edge in edges]
        for source, edges in raw["edges"].items()
    }


def load_scenario_policy(path: Path | None = None) -> PolicySchema:
    raw = _read_json(path or DATA_DIR / "scenarios" / "strategic_industry_default.json")
    if not isinstance(raw, dict):
        raise ValueError("scenario must be a JSON object")
    return PolicySchema.model_validate(raw["policy"])

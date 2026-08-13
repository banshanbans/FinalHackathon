from functools import lru_cache
from typing import Literal

from simulation.catalog import event_scenario_catalog
from simulation.models.common import EventTemplateId
from simulation.models.presentation import (
    PresentationEventCatalog,
    PresentationEventCatalogEntry,
)
from simulation.models.v32 import EventIntensityV32, EventTriggerPoint

AffectedSubject = Literal["province", "automaker", "consumer", "supply_chain"]

_AFFECTED_SUBJECTS: dict[EventTemplateId, list[AffectedSubject]] = {
    EventTemplateId.BATTERY_NODE_UPGRADE_SICHUAN: [
        "province",
        "automaker",
        "supply_chain",
    ],
    EventTemplateId.INTELLIGENT_DRIVING_UPGRADE: [
        "province",
        "automaker",
        "consumer",
    ],
    EventTemplateId.L3_ENTERPRISE_LIABILITY_INCREASE: [
        "province",
        "automaker",
        "consumer",
    ],
    EventTemplateId.OIL_PRICE_RISE: [
        "province",
        "automaker",
        "consumer",
        "supply_chain",
    ],
    EventTemplateId.OIL_PRICE_FALL: [
        "province",
        "automaker",
        "consumer",
        "supply_chain",
    ],
}


@lru_cache
def presentation_event_catalog() -> PresentationEventCatalog:
    templates = event_scenario_catalog()
    entries = [
        PresentationEventCatalogEntry(
            template_id=template_id.value,
            family=template.family.value,
            title=template.title,
            description=template.description,
            trigger_points=list(EventTriggerPoint),
            affected_subjects=_AFFECTED_SUBJECTS[template_id],
            mechanism_channels=template.mechanism_channels,
            supported_intensities=list(EventIntensityV32),
            branch_scopes=["both", "treatment_only"],
            provenance_refs=template.provenance_refs,
        )
        for template_id, template in sorted(templates.items(), key=lambda item: item[0].value)
    ]
    return PresentationEventCatalog(templates=entries)

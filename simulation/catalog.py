from functools import lru_cache

from simulation.domain_constants import AUTOMAKER_IDS, MAINLAND_PROVINCE_CODES
from simulation.models.base import FrozenDomainModel
from simulation.models.common import EventFamily, EventTemplateId, PolicyRegion
from simulation.models.scenario import EventScenarioTemplate


class ProvinceCatalogEntry(FrozenDomainModel):
    province_code: str
    name: str
    short_name: str
    policy_region: PolicyRegion


class AutomakerCatalogEntry(FrozenDomainModel):
    automaker_id: str
    display_name: str
    representative_set_disclaimer: str = (
        "用户选定的代表性头部车企模拟主体，不代表严格年度销量 Top 10。"
    )


_PROVINCES = (
    ("11", "北京市", "北京", PolicyRegion.EAST),
    ("12", "天津市", "天津", PolicyRegion.EAST),
    ("13", "河北省", "河北", PolicyRegion.CENTRAL),
    ("14", "山西省", "山西", PolicyRegion.CENTRAL),
    ("15", "内蒙古自治区", "内蒙古", PolicyRegion.WEST),
    ("21", "辽宁省", "辽宁", PolicyRegion.EAST),
    ("22", "吉林省", "吉林", PolicyRegion.CENTRAL),
    ("23", "黑龙江省", "黑龙江", PolicyRegion.CENTRAL),
    ("31", "上海市", "上海", PolicyRegion.EAST),
    ("32", "江苏省", "江苏", PolicyRegion.EAST),
    ("33", "浙江省", "浙江", PolicyRegion.EAST),
    ("34", "安徽省", "安徽", PolicyRegion.CENTRAL),
    ("35", "福建省", "福建", PolicyRegion.EAST),
    ("36", "江西省", "江西", PolicyRegion.CENTRAL),
    ("37", "山东省", "山东", PolicyRegion.EAST),
    ("41", "河南省", "河南", PolicyRegion.CENTRAL),
    ("42", "湖北省", "湖北", PolicyRegion.CENTRAL),
    ("43", "湖南省", "湖南", PolicyRegion.CENTRAL),
    ("44", "广东省", "广东", PolicyRegion.EAST),
    ("45", "广西壮族自治区", "广西", PolicyRegion.WEST),
    ("46", "海南省", "海南", PolicyRegion.CENTRAL),
    ("50", "重庆市", "重庆", PolicyRegion.WEST),
    ("51", "四川省", "四川", PolicyRegion.WEST),
    ("52", "贵州省", "贵州", PolicyRegion.WEST),
    ("53", "云南省", "云南", PolicyRegion.WEST),
    ("54", "西藏自治区", "西藏", PolicyRegion.WEST),
    ("61", "陕西省", "陕西", PolicyRegion.WEST),
    ("62", "甘肃省", "甘肃", PolicyRegion.WEST),
    ("63", "青海省", "青海", PolicyRegion.WEST),
    ("64", "宁夏回族自治区", "宁夏", PolicyRegion.WEST),
    ("65", "新疆维吾尔自治区", "新疆", PolicyRegion.WEST),
)

_AUTOMAKERS = (
    ("byd", "比亚迪"),
    ("geely", "吉利"),
    ("changan", "长安"),
    ("sgmw", "上汽通用五菱"),
    ("nio", "蔚来"),
    ("chery", "奇瑞"),
    ("leapmotor", "零跑"),
    ("seres", "赛力斯"),
    ("xiaomi_auto", "小米汽车"),
    ("li_auto", "理想汽车"),
)


@lru_cache
def policy_region_catalog() -> dict[str, ProvinceCatalogEntry]:
    catalog = {
        code: ProvinceCatalogEntry(
            province_code=code, name=name, short_name=short_name, policy_region=region
        )
        for code, name, short_name, region in _PROVINCES
    }
    if tuple(catalog) != MAINLAND_PROVINCE_CODES:
        raise ValueError("policy region catalog must contain the frozen 31 province codes")
    return catalog


@lru_cache
def automaker_catalog() -> dict[str, AutomakerCatalogEntry]:
    catalog = {
        automaker_id: AutomakerCatalogEntry(automaker_id=automaker_id, display_name=display_name)
        for automaker_id, display_name in _AUTOMAKERS
    }
    if tuple(catalog) != AUTOMAKER_IDS:
        raise ValueError("automaker catalog must contain the frozen representative set")
    return catalog


@lru_cache
def event_scenario_catalog() -> dict[EventTemplateId, EventScenarioTemplate]:
    templates = (
        EventScenarioTemplate(
            template_id=EventTemplateId.BATTERY_NODE_UPGRADE_SICHUAN,
            family=EventFamily.TECHNOLOGY,
            title="西部电池节点能力升级（四川情景）",
            description="在冻结基线之上模拟四川电池节点能力提升及供应链距离传导。",
            target_province_codes=["51"],
            mechanism_channels=["battery_access", "logistics_cost", "industry_activity"],
            provenance_refs=["scenario-method:battery-node-upgrade-v1"],
        ),
        EventScenarioTemplate(
            template_id=EventTemplateId.INTELLIGENT_DRIVING_UPGRADE,
            family=EventFamily.TECHNOLOGY,
            title="全国智驾能力升级",
            description="模拟智驾技术能力升级对技术适配、消费接受与产业活动的传导。",
            mechanism_channels=[
                "intelligent_driving_readiness",
                "consumer_acceptance",
                "rd_activity",
            ],
            provenance_refs=["scenario-method:intelligent-driving-upgrade-v1"],
        ),
        EventScenarioTemplate(
            template_id=EventTemplateId.L3_ENTERPRISE_LIABILITY_INCREASE,
            family=EventFamily.REGULATION,
            title="L3 企业责任提高",
            description="模拟责任边界调整带来的消费者清晰效应与企业责任成本效应。",
            mechanism_channels=["consumer_trust", "enterprise_liability_cost", "regulatory_pilot"],
            provenance_refs=["scenario-method:l3-liability-v1"],
        ),
        EventScenarioTemplate(
            template_id=EventTemplateId.OIL_PRICE_RISE,
            family=EventFamily.ENERGY,
            title="国际冲突情景下油价上涨",
            description="模拟油价上行情景对新能源汽车相对使用成本与接受度的影响。",
            mechanism_channels=["relative_use_cost", "wtp_demand"],
            provenance_refs=["scenario-method:oil-price-shock-v1"],
        ),
        EventScenarioTemplate(
            template_id=EventTemplateId.OIL_PRICE_FALL,
            family=EventFamily.ENERGY,
            title="油价回落",
            description="模拟油价回落情景对新能源汽车相对使用成本优势的影响。",
            mechanism_channels=["relative_use_cost", "wtp_demand"],
            provenance_refs=["scenario-method:oil-price-shock-v1"],
        ),
    )
    return {item.template_id: item for item in templates}

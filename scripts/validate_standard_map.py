#!/usr/bin/env python3
"""Validate the frozen official-map asset and its 31 interactive regions."""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path

from annotate_standard_map import PROVINCES, SVG_NS

ROOT = Path(__file__).resolve().parents[1]
MAP_DIR = ROOT / "apps" / "web" / "src" / "assets" / "maps"
EPS_PATH = MAP_DIR / "source" / "4o28b0625501ad13015501ad2bfc0045.eps"
SVG_PATH = MAP_DIR / "china-standard-map.svg"
EPS_SHA256 = "48dcb75fce083d66ee58582368218413f28bbd39c803b75fde15390b1a0badf1"
PROVINCE_GEOMETRY_SHA256 = "2f6aea81b85e929df44aa83beb6c4dcf3fe8f14b8274506e62c6b836ac1c97d6"
PROVINCE_PATH_SHA256: dict[str, str] = {
    "15": "8dfc097fa82ce080d3e4d8a4366751f28e6ce0c9efbd58c167bd37bce2e37309",
    "23": "f64ea5c01b8687b50cfc31cad7c4620efab1dd800e475c4b51a7671275522c16",
    "22": "3130c038981a16024b787dcbceec7f20268ed7869e923a0f352c503b7d17fc12",
    "21": "ce480a66fc355aab580bd647fee4f28ffb73a614462d9c93faab39c7ac54999e",
    "32": "7bada2fb20d3718e69b3cddb5b75f67a19b693259a23af57208ff2579eca49a3",
    "33": "0bcb64f1795dc810936033ec66f73fdafccbe62690d618f692aa4e55f64c0bb0",
    "13": "a3534c9c9653ec5275f24d383cc34a4dcc9f39dcf41b1d12ea904058e2923175",
    "37": "426ef3043e69849c525ba39dc473b2763643f3603aab5f4c3d941fe64c103a01",
    "34": "939174ddaeea55d0e949922611e39520a3ad16effdccc4ede4b29c19ef4f7695",
    "36": "c0429f3ee90547e8e964d581cf48fb8912bde78d1bf8838de63f9df36552457d",
    "35": "4df87e3e270e517b70a89e2f8bf2ceac83f8b9fd741ff044e452482f324230fa",
    "44": "ab5e2053f7b95aaf110baf58e2ef23f04ea7457f80cd9306cdd2fd3ba80aa5ca",
    "14": "231b74912188d339c240059f1894af4dff517142e85bdb18b23fc799c3e11ba7",
    "41": "c675d8a743e86a6d29ee4f8e8bc217b6c6c3510d34c5478bb72e2b038e628d1d",
    "42": "fcc9c6f797c576ba02026f77512801c06b81f0da20fbd4fe2ae481ff537d7055",
    "43": "3181e9e44a68c9c613c98ccdeff0024bdafa245f5b1f9b6be036f55305875a5c",
    "45": "796fbd6415c8d907063ec2c03a18a641b66f754a5d7b6bf18c60208cf7ee14a9",
    "52": "d3b58705cd0f78c9a915299caa1b666c0aa6035ff00e8f5870e9d429960db14e",
    "50": "9ee874e9520569fcc089240594da017e88590a3d09ed90727dc9b36e02f86e82",
    "61": "6be2efa67c3f33ebc0e87f66f665d497ff18d9ff76c8d85ef6adc3b45fe2e470",
    "64": "1eda9e6f1d46ba57885723d63837ec50ece3fc970ac15107fe86836355540a8f",
    "51": "16a89800b3875576ff0fb6afaa131cbea7ff4ffae760824a3a87c077274a6b5a",
    "53": "99d51b9047a7c987a35096ae6ab76a4c8455296848d2abb176d43473f67b6cb4",
    "63": "8c356f299f3edd51e90f01595811204db4f80a391fb0a72da16d73f617856826",
    "11": "e499986fc47cce0ef31a7a6e101222826d16dc58d62b9a3785d31b6412b7e66c",
    "12": "81f4dd4e25e85bcb93997a77b29d93ff44a03f717a9c3623b231e0e74cb276f5",
    "62": "974d3b0ccb5fb560d16f8f4c3efbe776a8f49b42e25f86536ebed09483f4015b",
    "65": "2c0a6e5767ca43441eb8c38849fdce6b0329b2e80dc103b63f365ef5abe9928b",
    "54": "b07b897be7376095e1b892ef5934ce4105f50114be361a3ed44350b4822d5970",
    "31": "b4ba627b7f1cb75b701fbb8d890f6720ab403a6f157d34d0f3dd3b3d1565442f",
    "46": "cb5a58d60066f84adcb8751664ac1c026af7bac404a79e415b1e6feb614f1fe1",
}


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate() -> None:
    if digest(EPS_PATH.read_bytes()) != EPS_SHA256:
        raise ValueError("official standard-map EPS checksum changed")

    root = ET.parse(SVG_PATH).getroot()
    regions = [
        path
        for path in root.iter(f"{{{SVG_NS}}}path")
        if path.get("data-region-role") == "simulation-province"
    ]
    actual = [(path.get("data-code"), path.get("name")) for path in regions]
    if actual != list(PROVINCES):
        raise ValueError("SVG does not contain the frozen 31-province ordering")
    if len({path.get("id") for path in regions}) != 31:
        raise ValueError("SVG province path IDs must be unique")

    geometry = "\n".join(path.get("d", "") for path in regions).encode()
    if digest(geometry) != PROVINCE_GEOMETRY_SHA256:
        raise ValueError("annotated province geometry changed after EPS conversion")
    actual_path_signatures = {
        path.get("data-code", ""): digest(path.get("d", "").encode()) for path in regions
    }
    if actual_path_signatures != PROVINCE_PATH_SHA256:
        raise ValueError("province codes are not bound to the frozen province geometries")
    if root.get("data-map-source") != "MNR-standard-map-GS2016-1609":
        raise ValueError("SVG source marker is missing")
    print("Map validation passed: official EPS checksum and 31 SVG regions verified.")


if __name__ == "__main__":
    validate()

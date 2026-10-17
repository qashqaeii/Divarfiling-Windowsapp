"""بارگذاری و جستجوی استان/شهر/منطقه."""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.paths import get_resource_path


def norm_name(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("ي", "ی").replace("ك", "ک").replace("ۀ", "ه").replace("ـ", "")
    s = s.replace("\u200c", " ")
    return " ".join(s.split())


class PlacesManager:
    def __init__(self, on_log: Optional[Callable[[str, str], None]] = None) -> None:
        self._log = on_log or (lambda msg, _t="normal": None)
        self.loaded = False
        self._id_to_node: Dict[int, Dict[str, Any]] = {}
        self.provinces: List[Dict[str, Any]] = []
        self.cities_by_province: Dict[int, List[Dict[str, Any]]] = {}
        self.districts_by_city: Dict[int, List[Dict[str, Any]]] = {}
        self._name_index_provinces: Dict[str, List[Dict[str, Any]]] = {}
        self._name_index_cities: Dict[str, List[Dict[str, Any]]] = {}
        self._name_index_districts: Dict[str, List[Dict[str, Any]]] = {}

    @staticmethod
    def _normalize_place_node(item: Dict[str, Any]) -> Dict[str, Any]:
        node = dict(item)
        if node.get("name") is not None:
            node["name"] = str(node["name"]).strip()
        return node

    def load(self) -> None:
        path = get_resource_path("config/places-web.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._id_to_node = {
            int(item["id"]): self._normalize_place_node(item)
            for item in data
            if isinstance(item, dict) and "id" in item
        }
        cities = [n for n in self._id_to_node.values() if n.get("type") == "2"]
        province_ids = sorted({int(c["parent"]) for c in cities if c.get("parent") is not None})
        self.provinces = [
            self._id_to_node[pid] for pid in province_ids if pid in self._id_to_node
        ]
        self.cities_by_province = {}
        for city in cities:
            pid = city.get("parent")
            if pid is None:
                continue
            self.cities_by_province.setdefault(int(pid), []).append(city)
        for lst in self.cities_by_province.values():
            lst.sort(key=lambda x: str(x.get("name", "")))

        districts = [n for n in self._id_to_node.values() if n.get("type") == "4"]
        self.districts_by_city = {}
        for district in districts:
            cid = district.get("parent")
            if cid is None:
                continue
            self.districts_by_city.setdefault(int(cid), []).append(district)
        for lst in self.districts_by_city.values():
            lst.sort(key=lambda x: str(x.get("name", "")))

        self._name_index_provinces = {}
        self._name_index_cities = {}
        self._name_index_districts = {}
        for prov in self.provinces:
            for key in {
                norm_name(str(prov.get("name", ""))),
                norm_name(str(prov.get("slug", ""))),
                norm_name(str(prov.get("second_slug", ""))),
            }:
                if key:
                    self._name_index_provinces.setdefault(key, []).append(prov)
        for lst in self.cities_by_province.values():
            for city in lst:
                for key in {
                    norm_name(str(city.get("name", ""))),
                    norm_name(str(city.get("slug", ""))),
                    norm_name(str(city.get("second_slug", ""))),
                }:
                    if key:
                        self._name_index_cities.setdefault(key, []).append(city)
        for lst in self.districts_by_city.values():
            for district in lst:
                for key in {
                    norm_name(str(district.get("name", ""))),
                    norm_name(str(district.get("slug", ""))),
                    norm_name(str(district.get("second_slug", ""))),
                }:
                    if key:
                        self._name_index_districts.setdefault(key, []).append(district)

        self.loaded = True
        self._log("فهرست استان/شهر/منطقه بارگذاری شد.", "success")

    def province_names(self) -> List[str]:
        return [p.get("name", "") for p in sorted(self.provinces, key=lambda x: str(x.get("name", "")))]

    def city_names_for_province(self, province_name: str) -> List[str]:
        prov = next((p for p in self.provinces if p.get("name") == province_name), None)
        if not prov:
            return []
        cities = self.cities_by_province.get(int(prov["id"]), [])
        return [c.get("name", "") for c in cities]

    def district_names_for_city(self, city_name: str) -> List[str]:
        city = self.find_city_by_name(city_name)
        if not city:
            return ["—"]
        dlist = self.districts_by_city.get(int(city["id"]), [])
        return ["—"] + [d.get("name", "") for d in dlist]

    def find_city_by_name(self, city_name: str) -> Optional[Dict[str, Any]]:
        for lst in self.cities_by_province.values():
            for city in lst:
                if norm_name(city.get("name", "")) == norm_name(city_name):
                    return city
        return None

    def resolve_location(
        self, province_name: str, city_name: str, district_name: str
    ) -> Tuple[str, str, str, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        province = city = district = ""
        sel_city = sel_dist = None
        if city_name:
            sel_city = self.find_city_by_name(city_name)
            if sel_city:
                city = sel_city.get("name", "")
                prov_id = sel_city.get("parent")
                if prov_id:
                    prov = self._id_to_node.get(int(prov_id))
                    if prov:
                        province = prov.get("name", "")
        if sel_city and district_name and district_name != "—":
            dlist = self.districts_by_city.get(int(sel_city["id"]), [])
            sel_dist = next(
                (d for d in dlist if norm_name(d.get("name", "")) == norm_name(district_name)),
                None,
            )
            if sel_dist:
                district = sel_dist.get("name", "")
        elif province_name and not city:
            prov = next((p for p in self.provinces if p.get("name") == province_name), None)
            if prov:
                province = prov.get("name", "")
        return province, city, district, sel_city, sel_dist

    def apply_to_scraper_config(
        self, scraper, city_name: str, district_name: str
    ) -> None:
        if not self.loaded or not city_name:
            return
        sel_city = self.find_city_by_name(city_name)
        if not sel_city:
            return
        scraper.CONFIG["city_ids"] = [str(sel_city.get("id"))]
        scraper.CONFIG["selected_city_slug"] = str(
            sel_city.get("second_slug") or sel_city.get("slug") or ""
        )
        if district_name and district_name != "—":
            dlist = self.districts_by_city.get(int(sel_city["id"]), [])
            sel_dist = next(
                (d for d in dlist if norm_name(d.get("name", "")) == norm_name(district_name)),
                None,
            )
            if sel_dist is None:
                for d in dlist:
                    if norm_name(district_name) in {
                        norm_name(d.get("slug", "")),
                        norm_name(d.get("second_slug", "")),
                    }:
                        sel_dist = d
                        break
            scraper.CONFIG["district_ids"] = [str(sel_dist.get("id"))] if sel_dist else []
            scraper.CONFIG["selected_district_slug"] = (
                str(sel_dist.get("second_slug") or sel_dist.get("slug") or "") if sel_dist else ""
            )
        else:
            scraper.CONFIG["district_ids"] = []
            scraper.CONFIG["selected_district_slug"] = ""

    def search_and_resolve(self, query_raw: str) -> Optional[Tuple[int, Optional[int], Optional[int]]]:
        query = norm_name(query_raw)
        if not query:
            return None

        def pick_exact(index: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
            return index.get(query, [])

        def pick_contains(index: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
            results: List[Dict[str, Any]] = []
            for key, lst in index.items():
                if query in key:
                    results.extend(lst)
            return results

        exact_city = pick_exact(self._name_index_cities)
        exact_prov = pick_exact(self._name_index_provinces)
        exact_dist = pick_exact(self._name_index_districts)
        contains_city = pick_contains(self._name_index_cities) if not exact_city else []
        contains_prov = pick_contains(self._name_index_provinces) if not exact_prov else []
        contains_dist = pick_contains(self._name_index_districts) if not exact_dist else []

        node = None
        if exact_city:
            node = exact_city[0]
        elif exact_prov:
            node = exact_prov[0]
        elif exact_dist:
            node = exact_dist[0]
        elif contains_city:
            node = contains_city[0]
        elif contains_prov:
            node = contains_prov[0]
        elif contains_dist:
            node = contains_dist[0]

        if not node:
            return None

        ntype = str(node.get("type"))
        if ntype == "4":
            city_id = int(node.get("parent"))
            city = self._id_to_node.get(city_id)
            if not city:
                return None
            prov_id = int(city.get("parent")) if city.get("parent") is not None else None
            if prov_id is None:
                return None
            return prov_id, city_id, int(node.get("id"))
        if ntype == "2":
            city_id = int(node.get("id"))
            prov_id = int(node.get("parent")) if node.get("parent") is not None else None
            if prov_id is None:
                return None
            return prov_id, city_id, None
        return int(node.get("id")), None, None

    def get_names_for_ids(
        self, province_id: int, city_id: Optional[int], district_id: Optional[int]
    ) -> Tuple[str, str, str]:
        prov = self._id_to_node.get(int(province_id), {})
        province_name = prov.get("name", "")
        city_name = district_name = ""
        if city_id is not None:
            city = self._id_to_node.get(int(city_id), {})
            city_name = city.get("name", "")
        if district_id is not None:
            dist = self._id_to_node.get(int(district_id), {})
            district_name = dist.get("name", "")
        return province_name, city_name, district_name

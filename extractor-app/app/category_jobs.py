"""ساخت jobهای استخراج — کاملاً داینامیک از TRANSACTION_TYPES."""
from __future__ import annotations

import copy
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from app.constants import TRANSACTION_TYPES
from app.filter_utils import normalize_filters_for_job


JobKey = Tuple[str, str]


def iter_transaction_type_names() -> List[str]:
    return list(TRANSACTION_TYPES.keys())


def count_all_subcategories() -> int:
    return sum(len(v.get("subcategories") or []) for v in TRANSACTION_TYPES.values())


def resolve_api_slug(transaction_type: str, subcategory_label: str) -> Optional[str]:
    tx = TRANSACTION_TYPES.get(transaction_type)
    if not tx:
        return None
    for sub in tx.get("subcategories") or []:
        if sub.get("label") == subcategory_label:
            return str(sub.get("api") or "")
    return None


def iter_subcategory_jobs(
    *,
    selected_transactions: Optional[Iterable[str]] = None,
    selected_job_keys: Optional[Iterable[JobKey]] = None,
) -> List[Dict[str, str]]:
    """لیست jobها به ترتیب ثابت TRANSACTION_TYPES."""
    tx_filter: Optional[Set[str]] = None
    if selected_transactions is not None:
        tx_filter = set(selected_transactions)

    key_filter: Optional[Set[JobKey]] = None
    if selected_job_keys is not None:
        key_filter = set(selected_job_keys)

    jobs: List[Dict[str, str]] = []
    for transaction_type, tx_data in TRANSACTION_TYPES.items():
        if tx_filter is not None and transaction_type not in tx_filter:
            continue
        for sub in tx_data.get("subcategories") or []:
            label = str(sub.get("label") or "")
            api = str(sub.get("api") or "")
            if not label or not api:
                continue
            key: JobKey = (transaction_type, label)
            if key_filter is not None and key not in key_filter:
                continue
            jobs.append(
                {
                    "transaction_type": transaction_type,
                    "subcategory": label,
                    "api_slug": api,
                }
            )
    return jobs


def build_job_settings(base_settings: Dict[str, Any], job: Dict[str, str]) -> Dict[str, Any]:
    """snapshot مستقل settings برای یک job — بدون mutate کردن base."""
    settings = copy.deepcopy(base_settings)
    transaction_type = job["transaction_type"]
    subcategory = job["subcategory"]
    api_slug = job["api_slug"]
    settings["transaction_type"] = transaction_type
    settings["subcategory"] = subcategory
    settings["filters"] = normalize_filters_for_job(
        settings.get("filters") or {},
        transaction_type=transaction_type,
        api_slug=api_slug,
    )
    return settings


def all_job_keys() -> List[JobKey]:
    return [(j["transaction_type"], j["subcategory"]) for j in iter_subcategory_jobs()]

"""موتور استخراج — همان رفتار اپ اصلی (ادغام، فیلتر همخانه، عکس، resume)."""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Set
from urllib.parse import urlparse

import pandas as pd

from app.constants import FILE_PREFIX_BY_TRANSACTION, MAX_EXTRACTION_ITEMS
from app.paths import get_output_dir, sanitize_path_segment
from app.places import PlacesManager
from app.storage import ExtractorStorage


LogFn = Callable[[str, str], None]
ProgressFn = Callable[[float], None]
CancelFn = Callable[[], bool]


class ExtractionEngine:
    def __init__(
        self,
        scraper,
        places: PlacesManager,
        storage: ExtractorStorage,
        on_log: LogFn,
        on_progress: ProgressFn,
        is_cancelled: CancelFn,
    ) -> None:
        self.scraper = scraper
        self.places = places
        self.storage = storage
        self.on_log = on_log
        self.on_progress = on_progress
        self.is_cancelled = is_cancelled
        self.scrape_start_time: Optional[float] = None

    def _emit_stats(
        self,
        *,
        total: int = 0,
        done: int = 0,
        ok: int = 0,
        total_posts: Optional[int] = None,
    ) -> None:
        payload = {"total": total, "done": done, "ok": ok}
        if total_posts is not None:
            payload["total_posts"] = total_posts
        self.on_log(f"__STATS__:{json.dumps(payload, ensure_ascii=False)}", "normal")

    def job_key(self, settings: Dict[str, Any]) -> str:
        parts = [
            settings.get("transaction_type", ""),
            settings.get("subcategory", ""),
            settings.get("city", ""),
            settings.get("district", ""),
        ]
        return "|".join(parts)

    def prepare_resume(self, settings: Dict[str, Any]) -> None:
        self.scraper.CONFIG.pop("resume_tokens", None)
        self.scraper.CONFIG.pop("resume_processed_tokens", None)
        if not settings.get("resume"):
            return
        state = self.storage.load_scrape_state(self.job_key(settings))
        if state and state.get("tokens"):
            self.scraper.CONFIG["resume_tokens"] = state["tokens"]
            self.scraper.CONFIG["resume_processed_tokens"] = state.get("processed", [])
            self.on_log("ادامه استخراج ناتمام فعال شد.", "info")

    def clear_resume(self, settings: Dict[str, Any]) -> None:
        self.storage.clear_scrape_state(self.job_key(settings))
        self.scraper.CONFIG.pop("resume_tokens", None)
        self.scraper.CONFIG.pop("resume_processed_tokens", None)

    def save_progress(self, settings: Dict[str, Any], tokens: List[str], processed: List[str], output_path: str) -> None:
        self.storage.save_scrape_state(
            self.job_key(settings),
            {
                "phase": "details",
                "tokens": tokens,
                "processed": processed,
                "output_path": output_path,
            },
        )

    def apply_search_filters(self, filters: Dict[str, Any]) -> None:
        from app.filter_utils import build_api_filters, has_active_advanced_filters

        api = build_api_filters(filters)
        self.scraper.CONFIG["search_filters"] = {
            "price_min": api["price_min"],
            "price_max": api["price_max"],
            "deposit_min": api["deposit_min"],
            "deposit_max": api["deposit_max"],
            "rent_min": api["rent_min"],
            "rent_max": api["rent_max"],
            "area_min": api["area_min"],
            "area_max": api["area_max"],
            "year_min": api["year_min"],
            "year_max": api["year_max"],
            "parking": api["parking"],
            "warehouse": api["warehouse"],
            "elevator": api["elevator"],
            "advertiser_filter": api["advertiser_filter"],
        }
        self.scraper.CONFIG["search_query"] = api["search_query"]
        if api["advertiser_filter"] in ("personal", "genuine_personal"):
            labels = {
                "personal": "فقط شخصی",
                "genuine_personal": "فقط مالک واقعی",
            }
            self.on_log(
                f"فیلتر «{labels[api['advertiser_filter']]}» روی جستجوی دیوار اعمال شد.",
                "info",
            )
        elif api["advertiser_filter"] == "consultant":
            self.on_log("فیلتر «فقط مشاور» پس از دریافت جزئیات اعمال می‌شود.", "info")
        if has_active_advanced_filters(filters):
            self.on_log("فیلترهای پیشرفته روی جستجوی دیوار اعمال شد.", "info")

    @staticmethod
    def output_extension(settings: Dict[str, Any]) -> str:
        fmt = str(settings.get("output_format") or "excel").lower()
        if fmt == "csv":
            return ".csv"
        if fmt == "json":
            return ".json"
        return ".xlsx"

    def build_output_path(self, settings: Dict[str, Any]) -> str:
        base_dir = get_output_dir()
        province_name, city_name, district_name, _, _ = self.places.resolve_location(
            settings.get("province", ""),
            settings.get("city", ""),
            settings.get("district", ""),
        )
        path_parts = [base_dir]
        for part in (province_name, city_name, district_name):
            safe_part = sanitize_path_segment(part)
            if safe_part:
                path_parts.append(safe_part)
                os.makedirs(os.path.join(*path_parts), exist_ok=True)

        transaction_type = settings.get("transaction_type", "")
        prefix = FILE_PREFIX_BY_TRANSACTION.get(
            transaction_type, transaction_type.replace(" ", "_")
        )
        subcategory = (settings.get("subcategory") or "").strip()
        subcategory_safe = ""
        if subcategory:
            subcategory_safe = subcategory.replace(" ", "_")
            for ch in ('/', '\\', ':', '*', '?', '"', '<', '>', '|'):
                subcategory_safe = subcategory_safe.replace(ch, "_")

        ext = self.output_extension(settings)
        if subcategory_safe:
            file_name = f"{prefix}_{subcategory_safe}{ext}"
        else:
            file_name = f"{prefix}{ext}"
        return os.path.join(*path_parts, file_name)

    def merge_excel_files(self, new_rows: List[Dict[str, Any]], excel_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(excel_path):
            return new_rows
        try:
            existing_df = pd.read_excel(excel_path)
            existing_df = existing_df.where(pd.notnull(existing_df), None)
            existing_rows = existing_df.to_dict("records")
        except Exception as exc:
            self.on_log(f"⚠ فایل موجود قابل خواندن نبود. فایل جدید ایجاد می‌شود: {exc}", "warning")
            return new_rows

        if not existing_rows:
            return new_rows

        existing_tokens: Set[str] = set()
        for row in existing_rows:
            token = str(row.get("token") or row.get("شناسه") or "").strip()
            if token:
                existing_tokens.add(token)

        unique_new_rows: List[Dict[str, Any]] = []
        duplicate_count = 0
        new_tokens_count = 0
        for row in new_rows:
            token = str(row.get("token") or row.get("شناسه") or "").strip()
            if token and token not in existing_tokens:
                unique_new_rows.append(row)
                existing_tokens.add(token)
                new_tokens_count += 1
            else:
                duplicate_count += 1

        if duplicate_count > 0:
            self.on_log(f"✓ {duplicate_count} آگهی تکراری حذف شد", "info")
        if new_tokens_count > 0:
            self.on_log(f"✓ {new_tokens_count} آگهی جدید شناسایی شد", "success")

        if not unique_new_rows:
            return existing_rows

        processed_new = self.scraper.export_rows_to_records(unique_new_rows)
        return processed_new + existing_rows

    @staticmethod
    def extract_title_from_detail(detail: Dict[str, Any]) -> str:
        try:
            seo = detail.get("seo", {}) or {}
            sections = detail.get("sections", []) or []
            title_from_sections = ""
            for section in sections:
                if section.get("section_name") == "TITLE":
                    for widget in section.get("widgets", []) or []:
                        if widget.get("widget_type") in ("LEGEND_TITLE_ROW", "TITLE_ROW"):
                            title_from_sections = (
                                widget.get("data", {}).get("title")
                                or widget.get("data", {}).get("text")
                                or title_from_sections
                            )
                            if title_from_sections:
                                break
                    if title_from_sections:
                        break
            return (title_from_sections or seo.get("web_info", {}).get("title") or seo.get("title") or "").strip()
        except Exception:
            return ""

    def download_images_for_post(
        self, row: Dict[str, Any], images_dir: str, token: str, session
    ) -> int:
        downloaded_count = 0
        try:
            images_field = (
                row.get("لینک تصاویر")
                or row.get("images")
                or row.get("رسانه_تصاویر")
                or ""
            )
            if not images_field:
                return 0
            image_urls = [url.strip() for url in images_field.split("|") if url.strip()]
            if not image_urls:
                return 0
            post_dir = os.path.join(images_dir, token)
            os.makedirs(post_dir, exist_ok=True)
            for idx, img_url in enumerate(image_urls, 1):
                try:
                    parsed = urlparse(img_url)
                    ext = os.path.splitext(parsed.path)[1] or ".jpg"
                    filepath = os.path.join(post_dir, f"{idx}{ext}")
                    if os.path.exists(filepath):
                        continue
                    response = session.get(img_url, timeout=30, stream=True)
                    if response.status_code == 200:
                        with open(filepath, "wb") as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        downloaded_count += 1
                except Exception:
                    continue
        except Exception:
            pass
        return downloaded_count

    def download_all_images(
        self, rows: List[Dict[str, Any]], excel_path: str, session
    ) -> None:
        base_dir = os.path.dirname(excel_path)
        excel_filename = os.path.basename(excel_path)
        images_folder_name = os.path.splitext(excel_filename)[0]
        images_dir = os.path.join(base_dir, images_folder_name)
        os.makedirs(images_dir, exist_ok=True)

        self.on_log("شروع دانلود عکس‌ها...", "info")
        total_images = 0
        downloaded = 0
        for row in rows:
            images_field = (
                row.get("لینک تصاویر")
                or row.get("images")
                or row.get("رسانه_تصاویر")
                or ""
            )
            if images_field:
                total_images += len([u for u in images_field.split("|") if u.strip()])

        if total_images == 0:
            self.on_log("هیچ عکسی برای دانلود یافت نشد.", "warning")
            return

        self.on_log(f"✓ تعداد {total_images} عکس برای دانلود شناسایی شد", "success")
        for row in rows:
            if self.is_cancelled():
                self.on_log("✗ دانلود عکس‌ها لغو شد", "warning")
                return
            token = row.get("token") or row.get("شناسه") or ""
            if token:
                count = self.download_images_for_post(row, images_dir, token, session)
                downloaded += count
                if downloaded % 10 == 0 or downloaded == total_images:
                    pct = int(downloaded / total_images * 100)
                    self.on_log(f"دانلود عکس‌ها: {downloaded}/{total_images} ({pct}%)", "info")

        skipped = total_images - downloaded
        if skipped > 0:
            self.on_log(
                f"✓ دانلود عکس‌ها تکمیل شد: {downloaded} عکس جدید، {skipped} عکس قبلاً وجود داشت",
                "success",
            )
        else:
            self.on_log(f"✓ دانلود عکس‌ها با موفقیت تکمیل شد ({downloaded} عکس)", "success")

    def configure_scraper(self, settings: Dict[str, Any]) -> str:
        from app.constants import TRANSACTION_TYPES

        transaction_type = settings["transaction_type"]
        subcategory_label = settings["subcategory"]
        subcategories = TRANSACTION_TYPES[transaction_type]["subcategories"]
        selected_sub = next((s for s in subcategories if s["label"] == subcategory_label), None)
        if not selected_sub:
            raise ValueError("زیردسته نامعتبر است.")

        self.scraper.CONFIG["category"] = selected_sub["api"]
        self.scraper.CONFIG["sort"] = "sort_date"
        max_items = max(0, min(MAX_EXTRACTION_ITEMS, int(settings.get("max_items", 100))))
        self.scraper.CONFIG["max_items"] = max_items
        self.scraper.CONFIG["max_workers"] = int(settings.get("max_workers", 6))
        self.scraper.CONFIG["network_error"] = None
        self.apply_search_filters(settings.get("filters") or {})
        from app.filter_utils import resolve_search_category

        base_category = selected_sub["api"]
        resolved_category = resolve_search_category(
            base_category,
            self.scraper.CONFIG.get("search_filters") or {},
        )
        if resolved_category != base_category:
            self.scraper.CONFIG["category"] = resolved_category

        if self.places.loaded and settings.get("city"):
            self.places.apply_to_scraper_config(
                self.scraper, settings["city"], settings.get("district", "")
            )

        output_path = self.build_output_path(settings)
        self.scraper.CONFIG["excel_output"] = output_path
        return output_path

    def run(self, settings: Dict[str, Any]) -> Optional[str]:
        self.scrape_start_time = time.time()
        self.on_log("در حال دریافت لیست آگهی‌ها...", "info")

        try:
            output_path = self.configure_scraper(settings)
        except Exception as exc:
            self.on_log(f"✗ خطا در تنظیمات: {exc}", "error")
            return None

        self.prepare_resume(settings)
        max_items = int(self.scraper.CONFIG.get("max_items", 100))
        if max_items <= 0:
            self.on_log("تعداد آیتم صفر — استخراج انجام نشد.", "warning")
            return None
        self.on_log(f"هدف استخراج: حداکثر {max_items} آگهی", "info")
        tokens = self.scraper.fetch_post_tokens()

        if self.scraper.CONFIG.get("network_error"):
            msg = self.scraper.CONFIG["network_error"]
            detail = self.scraper.CONFIG.get("last_request_error") or {}
            self.on_log(f"✗ {msg}", "error")
            if detail:
                tech = (
                    f"جزئیات: url={detail.get('url', '—')} "
                    f"category={detail.get('category', self.scraper.CONFIG.get('category', '—'))} "
                    f"status={detail.get('status_code', '—')} "
                    f"error={detail.get('error_type', detail.get('api_message', '—'))}"
                )
                self.on_log(tech, "warning")
            self.storage.append_log(f"NETWORK: {msg} | {detail}")
            return None

        if tokens:
            self.save_progress(
                settings,
                tokens,
                list(self.scraper.CONFIG.get("resume_processed_tokens") or []),
                output_path,
            )

        if not tokens:
            self.on_log("هیچ توکنی یافت نشد.", "warning")
            return None

        total_count = self.scraper.CONFIG.get("total_posts_count")
        if total_count is not None:
            self.on_log(f"✓ تعداد کل آگهی‌ها در این محدوده: {total_count:,}", "info")
        self.on_log(f"✓ تعداد {len(tokens)} آگهی برای استخراج انتخاب شد", "success")

        session = self.scraper.get_http_session()
        max_workers = max(1, int(self.scraper.CONFIG.get("max_workers", 6)))
        results_dict: Dict[int, Dict[str, Any]] = {}
        done = 0
        ok = 0
        total = len(tokens)
        resume_done: Set[str] = set(self.scraper.CONFIG.get("resume_processed_tokens") or [])
        processed_tokens: List[str] = list(resume_done)
        pending = max(1, total - len(resume_done))
        display_total = int(total_count) if total_count is not None else total
        self._emit_stats(total=display_total, done=0, ok=0, total_posts=display_total)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for idx, token in enumerate(tokens):
                if token in resume_done:
                    continue
                futures[executor.submit(self.scraper.fetch_post_detail, token, session)] = (token, idx)

            for fut in as_completed(futures):
                if self.is_cancelled():
                    self.on_log("✗ عملیات لغو شد", "warning")
                    return None
                token, idx = futures[fut]
                try:
                    detail = fut.result()
                except Exception:
                    detail = None
                if detail:
                    title = self.extract_title_from_detail(detail)
                    if title:
                        self.on_log(f"✓ استخراج شد: {title}", "success")
                    else:
                        self.on_log("✓ استخراج شد: (بدون عنوان)", "normal")
                    flat = self.scraper.flatten_post_detail(detail)
                    results_dict[idx] = flat
                    ok += 1
                processed_tokens.append(token)
                done += 1
                if done % 5 == 0:
                    self.save_progress(settings, tokens, processed_tokens, output_path)
                if done % 10 == 0 or done == pending:
                    self.on_log(f"پردازش: {done}/{pending} ({int(done / pending * 100)}%)", "info")
                self.on_progress(done / pending)
                self._emit_stats(total=display_total, done=done, ok=ok, total_posts=display_total)

        rows = [results_dict[idx] for idx in sorted(results_dict.keys())]
        if not rows:
            self.on_log("✗ داده‌ای برای خروجی یافت نشد", "warning")
            return None

        if self.is_cancelled():
            self.on_log("✗ عملیات لغو شد — فایل خروجی ساخته نشد", "warning")
            return None

        output_format = settings.get("output_format", "excel")
        expected_ext = self.output_extension(settings)
        excel_output_path = self.scraper.CONFIG.get("excel_output", output_path)
        if not str(excel_output_path).lower().endswith(expected_ext):
            excel_output_path = self.build_output_path(settings)
            self.scraper.CONFIG["excel_output"] = excel_output_path
        base_path = os.path.splitext(excel_output_path)[0]

        if output_format == "excel":
            out_path = excel_output_path
            if os.path.exists(out_path):
                self.on_log("✓ فایل موجود شناسایی شد. در حال ادغام...", "info")
                rows = self.merge_excel_files(rows, out_path)
                if not rows:
                    self.on_log("✗ همه آگهی‌ها تکراری بودند", "warning")
                    return None

        if self.is_cancelled():
            self.on_log("✗ عملیات لغو شد — merge/export انجام نشد", "warning")
            return None

        filtered_rows, removed_ads = self.scraper._filter_roommate_ads(rows, return_removed=True)
        if removed_ads:
            self.on_log(f"⚠ {len(removed_ads)} آگهی همخانه/خوابگاه/پانسیون شناسایی و حذف شد:", "warning")
            for ad_title in removed_ads:
                self.on_log(f"  ✗ حذف شد: {ad_title}", "warning")

        advertiser_filter = (settings.get("filters") or {}).get("advertiser_filter", "all")
        filtered_rows, removed_consultant = self.scraper._filter_by_advertiser_type(
            filtered_rows, advertiser_filter=advertiser_filter, return_removed=True,
        )
        if removed_consultant:
            from advertiser_signal import ADVERTISER_FILTER_LABELS, normalize_filter_value

            label = ADVERTISER_FILTER_LABELS.get(
                normalize_filter_value(advertiser_filter), "آگهی‌دهنده"
            )
            self.on_log(
                f"⚠ {len(removed_consultant)} آگهی حذف شد (فیلتر {label})",
                "warning",
            )

        if output_format == "excel":
            self.on_log("در حال ساخت/به‌روزرسانی فایل اکسل...", "info")
            final_path = self.scraper.export_to_excel(filtered_rows, out_path)
            self.on_log(f"✓ فایل اکسل با موفقیت ایجاد/به‌روزرسانی شد: {final_path}", "success")
        elif output_format == "csv":
            out_path = base_path + ".csv"
            self.on_log("در حال ساخت فایل CSV...", "info")
            final_path = self.scraper.export_to_csv(filtered_rows, out_path)
            self.on_log(f"✓ فایل CSV با موفقیت ایجاد شد: {final_path}", "success")
        elif output_format == "json":
            out_path = base_path + ".json"
            self.on_log("در حال ساخت فایل JSON...", "info")
            final_path = self.scraper.export_to_json(filtered_rows, out_path)
            self.on_log(f"✓ فایل JSON با موفقیت ایجاد شد: {final_path}", "success")
        else:
            out_path = excel_output_path
            self.on_log("در حال ساخت/به‌روزرسانی فایل اکسل...", "info")
            final_path = self.scraper.export_to_excel(filtered_rows, out_path)
            self.on_log(f"✓ فایل اکسل با موفقیت ایجاد/به‌روزرسانی شد: {final_path}", "success")

        if settings.get("download_images"):
            self.download_all_images(filtered_rows, final_path, session)

        self.clear_resume(settings)
        self.storage.append_log(f"SCRAPE OK: {final_path} rows={len(filtered_rows)}")
        self._emit_stats(
            total=display_total,
            done=done,
            ok=len(filtered_rows),
            total_posts=display_total,
        )
        self.on_progress(1.0)
        return final_path

    @staticmethod
    def preview_output_structure(settings: Dict[str, Any], places: PlacesManager) -> str:
        province, city, district, _, _ = places.resolve_location(
            settings.get("province", ""),
            settings.get("city", ""),
            settings.get("district", ""),
        )
        parts = ["output"]
        for p in (province, city, district):
            if p:
                parts.append(p)
        from app.constants import FILE_PREFIX_BY_TRANSACTION

        tx = settings.get("transaction_type", "")
        prefix = FILE_PREFIX_BY_TRANSACTION.get(tx, tx)
        sub = (settings.get("subcategory") or "").replace(" ", "_")
        ext = ExtractionEngine.output_extension(settings)
        name = f"{prefix}_{sub}{ext}" if sub else f"{prefix}{ext}"
        parts.append(name)
        return " / ".join(parts)

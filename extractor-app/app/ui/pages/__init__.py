"""Page builders."""
from app.ui.pages.about_page import build_about_page
from app.ui.pages.extraction_page import build_extraction_page, update_summary_chips
from app.ui.pages.license_page import build_license_page
from app.ui.pages.output_page import build_output_page
from app.ui.pages.schedule_page import build_schedule_page
from app.ui.pages.settings_page import build_settings_page

__all__ = [
    "build_about_page",
    "build_extraction_page",
    "build_license_page",
    "build_output_page",
    "build_schedule_page",
    "build_settings_page",
    "update_summary_chips",
]

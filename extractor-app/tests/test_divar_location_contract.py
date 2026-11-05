"""قرارداد یکسان استخراج خیابان — Windows flatten/export در برابر divar_location."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / 'src'
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from divar_location import extract_post_location  # noqa: E402
from export_divar_items import export_rows_to_records, flatten_post_detail  # noqa: E402


def _tehran_detail() -> dict:
    return {
        'sections': [
            {
                'section_name': 'TITLE',
                'widgets': [
                    {
                        'widget_type': 'EXPANDABLE_SECTION',
                        'data': {
                            'title': 'پریروز در تهران، مرزداران، خ میثاق دوم',
                            'widget_list': [],
                        },
                    },
                ],
            },
        ],
        'seo': {'web_info': {'city_persian': 'تهران', 'district_persian': 'مرزداران'}},
        'webengage': {'token': 'gaXDhvQB', 'city': 'tehran', 'district': 'marzdaran'},
        'city': {'name': 'تهران'},
        'share': {'web_url': 'https://divar.ir/v/gaXDhvQB'},
    }


def _chalus_detail() -> dict:
    return {
        'sections': [
            {
                'section_name': 'TITLE',
                'widgets': [
                    {
                        'widget_type': 'EXPANDABLE_SECTION',
                        'data': {
                            'title': '۲ هفته پیش در چالوس، خ دریای شرقی ۱',
                            'widget_list': [],
                        },
                    },
                ],
            },
        ],
        'seo': {'web_info': {'city_persian': 'چالوس', 'district_persian': ''}},
        'webengage': {'token': 'gaDbUBzO'},
        'city': {'name': 'چالوس'},
    }


@pytest.mark.parametrize(
    'detail,expected_street',
    [
        (_tehran_detail(), 'خ میثاق دوم'),
        (_chalus_detail(), 'خ دریای شرقی ۱'),
    ],
)
def test_flatten_matches_location_contract(detail, expected_street):
    detail = copy.deepcopy(detail)
    loc = extract_post_location(detail)
    row = flatten_post_detail(detail)
    assert loc['street'] == expected_street
    assert row.get('مکان_خیابان') == expected_street
    assert 'title:street' in (row.get('مکان_منبع_جزئیات') or '')


def test_export_rows_preserves_street_columns_rent():
    row = flatten_post_detail(_tehran_detail())
    records = export_rows_to_records([row], category='apartment-rent')
    assert len(records) == 1
    rec = records[0]
    assert rec.get('خیابان') == 'خ میثاق دوم'
    assert rec.get('مکان_خیابان') == 'خ میثاق دوم'


def test_export_rows_preserves_street_columns_sell():
    row = flatten_post_detail(_tehran_detail())
    records = export_rows_to_records([row], category='apartment-sell')
    assert records[0].get('خیابان') == 'خ میثاق دوم'


def test_no_street_when_headline_has_no_street():
    detail = _chalus_detail()
    detail['sections'][0]['widgets'][0]['data']['title'] = 'پریروز در چالوس'
    loc = extract_post_location(detail)
    row = flatten_post_detail(detail)
    assert loc['street'] is None
    assert not row.get('مکان_خیابان')
    records = export_rows_to_records([row], category='apartment-rent')
    assert records[0].get('خیابان') == '-'


def _headline_detail(title: str, city: str, district: str = '') -> dict:
    return {
        'sections': [{
            'section_name': 'TITLE',
            'widgets': [{
                'widget_type': 'EXPANDABLE_SECTION',
                'data': {'title': title, 'widget_list': []},
            }],
        }],
        'seo': {'web_info': {'city_persian': city, 'district_persian': district}},
    }


@pytest.mark.parametrize(
    'title,city,district,expected_street,expected_nb',
    [
        ('۱۴ ساعت پیش در گرگان، خ آسایش ۱۱', 'گرگان', '', 'خ آسایش ۱۱', None),
        ('پریروز در گرگان، خ بیست و دو بهمن غربی', 'گرگان', '', 'خ بیست و دو بهمن غربی', None),
        ('هفته پیش در تهران، افسریه جنوبی، خ عنابستانی', 'تهران', 'افسریه جنوبی', 'خ عنابستانی', None),
        (
            'دیروز در تهران، آهنگران (سراسیاب دولاب)، خ شهرابی فراهانی',
            'تهران',
            '',
            'خ شهرابی فراهانی',
            'آهنگران (سراسیاب دولاب)',
        ),
        ('۱ ساعت پیش در تهران، المهدی، خ سلمان فارسی', 'تهران', 'المهدی', 'خ سلمان فارسی', None),
        ('۲ هفته پیش در گرگان، ک نیایش چهارم', 'گرگان', '', 'ک نیایش چهارم', None),
    ],
)
def test_real_divar_ads_windows_contract(title, city, district, expected_street, expected_nb):
    detail = _headline_detail(title, city, district)
    loc = extract_post_location(detail)
    row = flatten_post_detail(detail)
    assert loc['street'] == expected_street
    assert loc.get('neighborhood') == expected_nb
    assert row.get('مکان_خیابان') == expected_street
    if expected_nb:
        assert row.get('مکان_محله') == expected_nb


def test_shiraz_neighborhood_not_street():
    detail = {
        'sections': [{
            'section_name': 'TITLE',
            'widgets': [{
                'widget_type': 'EXPANDABLE_SECTION',
                'data': {'title': 'امروز در شیراز، محله معالی‌آباد، بلوار شاهد', 'widget_list': []},
            }],
        }],
        'seo': {'web_info': {'city_persian': 'شیراز', 'district_persian': ''}},
    }
    loc = extract_post_location(detail)
    row = flatten_post_detail(detail)
    assert loc['neighborhood'] == 'معالی‌آباد'
    assert loc['street'] == 'بلوار شاهد'
    assert row.get('مکان_خیابان') == 'بلوار شاهد'


def test_export_rows_sets_technical_key_from_display():
    raw = flatten_post_detail(_headline_detail(
        '۲ هفته پیش در گرگان، ک نیایش چهارم', 'گرگان', '',
    ))
    records = export_rows_to_records([raw], category='apartment-rent')
    assert records[0].get('خیابان') == 'ک نیایش چهارم'
    assert records[0].get('مکان_خیابان') == 'ک نیایش چهارم'

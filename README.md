# Divar Filing — Windows Extractor

اپ دسکتاپ ویندوز **استخراج و آپلود آگهی‌های دیوار** برای [فایلینگ دیوار](https://divarfiling.ir).

## ساختار

| پوشه | توضیح |
|------|--------|
| `extractor-app/` | رابط کاربری، بیلد PyInstaller و Inno Setup |
| `src/` | موتور استخراج و لایسنس مشترک با مونورپو اصلی |
| `config/places-web.json` | داده مکان‌ها برای فیلترها |
| `assets/`, `fonts/` | برند و فونت فارسی برای بیلد |

## پیش‌نیاز و ساخت

راهنمای کامل: [`extractor-app/BUILD.md`](extractor-app/BUILD.md)

خلاصه (از پوشه `extractor-app`):

```bat
build_all.bat
```

خروجی: `dist\DivarFilingExtractor.exe` و نصب‌کننده در `release\installer-out\`.

## توسعه محلی

```bat
cd extractor-app
pip install -r requirements.txt
python main.py
```

در حالت توسعه، `main.py` پوشه‌های `../src` را به `sys.path` اضافه می‌کند؛ ساختار ریشه ریپو باید همین‌طور بماند.

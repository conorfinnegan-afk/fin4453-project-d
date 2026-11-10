# CHANGELOG — Project D Data Pipeline

## [v2.1.0] — 2026-11-10
### Added
- Expanded candidate pool from 52 to 67 qualified industrial firms to ensure >= 50 valid final firms.
- Added cross-reference filtering in `pull_filings.py` (checking for 'see Item 7' and quotes) to prevent truncating MD&A to segment summaries in Item 1.
- Implemented exact fiscal year matching by period end date in `pull_xbrl.py` to fix the 2-year comparative period offset.
- Set target forecast year to FY2025 with baseline years FY2022–FY2024.

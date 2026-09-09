# STEP 5 news PIT audit

generated: 2026-09-10T01:15:51

## rules (docs/step5_news_pit.md)

- published on a trading day with time <= 15:00 -> available AT the publication time (usable for the same day's close)
- otherwise (after close / weekend / holiday / date-only) -> available at the NEXT trading day 09:30
- publication date unknown -> availability_unknown, excluded in strict mode
- event_time is kept separate and NEVER used for factor research; updated_at never substitutes for published_at

## automated checks (tests/news/)

- test_news_pit.py: pre/post-close boundaries, date-only, unknown-publication exclusion
- test_weekend_handling.py: Friday evening -> Monday
- test_holiday_handling.py: spring festival / national day spans -> first trading day after the holiday
- test_no_future_leakage.py: factors invariant to future events (14 factor parametrization)
- test_timestamp.py: tz-aware Asia/Shanghai everywhere

（结果以测试运行为准。）

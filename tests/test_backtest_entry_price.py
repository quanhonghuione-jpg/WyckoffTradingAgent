from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from scripts.backtest_runner import _price_at_or_before


def test_price_at_or_before_uses_last_minute_before_target() -> None:
    day = datetime(2026, 1, 5).date()
    tz = ZoneInfo("Asia/Shanghai")
    df = pd.DataFrame(
        {
            "datetime": [
                datetime(2026, 1, 5, 14, 54, tzinfo=tz),
                datetime(2026, 1, 5, 14, 55, tzinfo=tz),
                datetime(2026, 1, 5, 14, 56, tzinfo=tz),
            ],
            "close": [10.1, 10.2, 10.3],
        }
    )

    assert _price_at_or_before(df, day, "14:55") == 10.2

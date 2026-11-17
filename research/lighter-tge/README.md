# Lighter TGE 日度经营企稳研究

复现：

```bash
python3 analyze.py
```

脚本读取 `cache/Lighter_Core_ALL_2026-11-16.xlsx`，并用同目录里的官网 `exchangeMetrics` 缓存做对账。价格只出现在事后对照，不进入信号。

结论和五个复核日的当时判断见 `REPORT.md`。日度底稿在 `output/`。

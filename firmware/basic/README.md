# 基本款獨立韌體

這份程式對應 `hardware/basic/` 的非充電版載板與LOLIN S3 Mini，使用PlatformIO：

```sh
pio run -d firmware/basic
# 接好開發板後才使用：
pio run -d firmware/basic -t upload
pio device monitor -d firmware/basic -b 115200
```

本次精簡發布副本以Espressif32 7.0.1重新編譯成功；RAM19684 bytes、Flash304125 bytes。編譯不代表硬體量測／顯示已實測。

## 操作與接腳

按鍵按下並放開，或Serial送出 `SCAN` 換行啟動16檔掃描。掃描時可用 `!` 或按鍵中止。顯示為Adafruit4814／SSD1680／250×122三色；沒有接BUSY，使用本地EPD driver的固定／有界等待路徑。

| 功能 | GPIO |
|---|---|
| MUX A0/A1/A2/A3 | 2 / 6 / 4 / 5 |
| MUX EN | 14 |
| I²C SDA/SCL | 8 / 9 |
| 按鍵 | 35 |
| SPI SCK/MISO/MOSI | 36 / 18 / 16 |
| EPD CS/DC、SRAM CS | 37 / 38、34 |

校準資料見 `include/calibration.h` 與 `calibration-record.md`。目前顯示 `UNCALIBRATED / NOMINAL`，未知MUX Ron與接點阻值不會自動被名義電阻消除。

此程式沒有充電版的GPIO12繼電器、GPIO13 DONE、GPIO11 POWER_WARN_N管理，也沒有完整採能／量測自動循環。本次不將它標為充電版韌體。

必要Adafruit函式庫保留在 `lib/`，包含原授權。EPD的4.6.13本地patch與來源版本記錄一併提供；不應直接換回未帶相同API的上游版本。

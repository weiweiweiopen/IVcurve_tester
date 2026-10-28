# 基本款／非充電版

來源為 Marc Dusseiller 的 [IVcurve_tester](https://github.com/dusjagr/IVcurve_tester) 量測架構，衍生載板使用 LOLIN S3 Mini、ADG706、ADS1115 與 Adafruit 4814 顯示板。

- [KiCad工程](Marc_USB.kicad_pro)／[原理圖PDF](schematic.pdf)
- [製板ZIP](fabrication/basic-JLCPCB.zip)／[BOM](BOM.csv)
- [檢查摘要](checks/summary.json)／[ERC](checks/erc.json)／[DRC](checks/drc.json)／[逐pin網路表](checks/pin-map.csv)
- [獨立基本款韌體](../../firmware/basic/README.md)

J1是單片DSSC正、負集電焊盤；系統由USB供電，沒有採能／充電電路。兩層PCB，78×130mm設計包絡，四個安裝孔保留。KiCad10標準庫與模型須安裝；project-local庫與引用模型隨工程提供。

ERC0、未接0、parity0；保留10項架高模組courtyard重疊error及5項絲印／文字warning。約15mm模組下方淨空仍為裝配假設。量測電流、有效負載阻值與顯示均需實機校準／驗證。

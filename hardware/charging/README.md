# 充電／能量採集版

以Marc Dusseiller的I–V量測架構為基礎，採能、儲能、切換與PCB衍生設計由 **Sol 6.1** 完成。

- [KiCad工程](Marc_USB.kicad_pro)／[原理圖PDF](schematic.pdf)
- [原型製板ZIP](fabrication/charging-PROTOTYPE-JLCPCB.zip)／[BOM](BOM.csv)
- [檢查摘要](checks/summary.json)／[ERC](checks/erc.json)／[DRC](checks/drc.json)／[逐pin網路表](checks/pin-map.csv)
- [完整充電機制與循環](../../README.md#充電版)

## 實際架構

單片DSSC由K1切換：失電／SCAN_MODE低態接AEM10941採能，激磁時接ADG706負載與ADS1115取樣支路。兩個1.5F／5V PHB超級電容並聯為3F；TPS61023將VSTORE升壓至5V。TPS7A02常開控制域、TPL5111與READY邏輯決定主電源允許。

MCU控制腳：GPIO12 SCAN_MODE、GPIO13 MCU_DONE、GPIO11 POWER_WARN_N。JP201為TPS22917的控制開關，USB維護時先OFF。完整自動掃描／退出／DONE韌體尚未隨本次發布提供；基本款程式沒有這些步驟。

HarvestSwitch圖紙保留部分歷史註記；本次機制說明依當前netlist：K1 COM3/NC2/NO4負責HARV_P與LOAD_P切換，COM6/NO5另接DUT_P與SENSE_P；不能照舊註記認為第二組接點未使用。負載控制使用ADG706，而非早期595架構。

兩層PCB；ERC0、未接0、parity0。仍有10項架高模組courtyard重疊error及9項絲印／文字warning。超級電容模型、母座約15mm淨空、充電速度、USB操作及完整實機循環仍待驗證；製板包標為PROTOTYPE。

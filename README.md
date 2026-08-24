# Junction & Interface Carrier Visualizer

以 Python/Tkinter 建立的 gate／oxide／silicon 能帶與介面載子示意器，不需要瀏覽器或伺服器。介面只保留元件、P/N bulk、Vg/Vgs 與 Vds；工作區域由電壓自動判定。

## 啟動方式

1. 安裝 Python 3.11 以上版本。
2. 在此資料夾執行 `pip install -r requirements.txt`。
3. Windows 可雙擊 `run_simulator.bat`，或執行 `python app.py`。

## 操作

- MOS Capacitor：選擇 P-type 或 N-type bulk，手動調整 Vg；自動判定 Accumulation / Flat-band / Depletion / Inversion。
- MOSFET：手動調整 Vgs、Vds，固定 Vs=Vb=0；自動判定 Cutoff / Linear / Saturation。
- P-type bulk 對應 nMOS；N-type bulk 對應 pMOS。
- MOS capacitor 能帶橫跨 metal gate、oxide、silicon，顯示 gate Ef、body Ef、oxide potential drop 與 silicon band bending。
- MOSFET 能帶包含 Ec、Ei、Ev、EFn、EFp，以及 source/body EF=0 與 drain EF=-qVds。
- Vg/Vgs 與 Vds 均提供直接數值輸入、±微調按鈕，以及 1 mV / 5 mV / 10 mV / 50 mV / 100 mV 步進。
- I-V / C-V 分頁：MOS capacitor 顯示理想 Ig≈0 與 low/high-frequency normalized C-V；MOSFET 顯示 normalized Id-Vds 與 Cgs/Cgd/Cg-Vgs。
- 主介面下方整合即時數學推導：包含 `ψs=±2|φF|`、`ΔEc,i,v=-qψs`、表面載子濃度關係、nMOS/pMOS 區域不等式、`VGD` 判斷與分段 `ID` 方程，並直接代入目前偏壓。
- `VALIDATION_REPORT.md` 記錄公式推導、12 項自動驗證、審查修正與模型適用邊界。
- 元件剖面直接顯示介面載子、耗盡區、反轉層、通道與 pinch-off。
- MOSFET 以 3D Ec／Ei／Ev 能帶面呈現 source、gate/channel、drain 的空間能障，並加入 EFn／EFp。
- 動畫圓點與箭頭顯示電子／電洞淨流向；實心藍點為電子，紅色空心點為電洞。

## 模型假設與限制

本工具是電壓驅動的物理示意圖，刻意不使用 Cox、tox、摻雜濃度或其他製程參數。工作區域門檻、能量與載子數量是定性呈現，不輸出精確濃度或電流。

## 驗證

執行：

```text
python -m unittest -v test_regions.py
```

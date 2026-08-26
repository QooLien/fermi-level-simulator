# Junction & Interface Carrier Visualizer

以 Python/Tkinter 建立的 gate／oxide／silicon 能帶與介面載子示意器，不需要瀏覽器或伺服器。介面只保留元件、P/N bulk、Vg/Vgs 與 Vds；工作區域由電壓自動判定。

## 啟動方式

1. 安裝 Python 3.11 以上版本。
2. 在此資料夾執行 `pip install -r requirements.txt`。
3. Windows 可雙擊 `run_simulator.bat`，或執行 `python app.py`。

## 操作

- MOS Capacitor：選擇 P-type 或 N-type bulk，手動調整 Vg；自動判定 Accumulation / Flat-band / Depletion / Inversion。
- MOSFET：手動調整 Vgs、Vds，固定 Vs=Vb=0；自動判定 Cutoff / Linear / Saturation。
- MOSFET 3D view：可直接切換 Follow voltage / Cutoff / Linear / Saturation；三個區域選項會載入對應的代表性 Vgs/Vds，P-type 與 N-type bulk 會自動鏡像。
- 3D 能帶可用滑桿調整 Elevation（0–90°）與 Azimuth（−180–180°），亦可直接用滑鼠拖曳旋轉；Reset view 可回到預設視角。
- P-type bulk 對應 nMOS；N-type bulk 對應 pMOS。
- MOS capacitor 能帶橫跨 metal gate、oxide、silicon，顯示 gate Ef、body Ef、oxide potential drop 與 silicon band bending。
- MOSFET 能帶包含 Ec、Ei、Ev、EFn、EFp，以及 source/body EF=0 與 drain EF=-qVds。
- Vg/Vgs 與 Vds 均提供直接數值輸入、±微調按鈕，以及 1 mV / 5 mV / 10 mV / 50 mV / 100 mV 步進。
- I-V / C-V 分頁：MOS capacitor 顯示理想 Ig≈0 與 low/high-frequency normalized C-V；MOSFET 顯示 normalized Id-Vds 與 Cgs/Cgd/Cg-Vgs。
- 主介面下方整合即時數學推導：包含 `ψs=±2|φF|`、`ΔEc,i,v=-qψs`、表面載子濃度關係、nMOS/pMOS 區域不等式、`VGD` 判斷與分段 `ID` 方程，並直接代入目前偏壓。
- [`docs/VALIDATION_REPORT.md`](docs/VALIDATION_REPORT.md) 記錄公式推導、14 項自動驗證、審查修正與模型適用邊界。
- [`docs/FORMULA_GUIDE.md`](docs/FORMULA_GUIDE.md) 集中整理 MOS capacitor 與 MOSFET 使用的完整數學式。
- 元件剖面直接顯示介面載子、耗盡區、反轉層、通道與 pinch-off。
- MOSFET 以 3D Ec／Ei／Ev 能帶面呈現 source、gate/channel、drain 的空間能障，並加入 EFn／EFp。
- 動畫圓點與箭頭顯示電子／電洞淨流向；實心藍點為電子，紅色空心點為電洞。MOSFET 另以紫色箭頭標示 conventional current：nMOS 的 \(I_D\) 為 Drain → Source，pMOS 的 \(|I_D|\) 為 Source → Drain。
- MOSFET Vt／Idsat 預測器：手動輸入一組 pinch-off 錨點 `Vg、Vt、Idsat`，由 `k=2·Idsat/VOV²` 反推，再按可調 step 與點數往截止方向掃描，或直接輸入指定 Vg 清單。每個 Vg 都輸出 `VDS,pinch-off=VOV`、`Idsat`，並疊加在本機下方的 `Id–Vds` 圖表。

## 中文教材

- [MOS 能帶、費米能階與載子流動教材（PDF）](docs/MOS_Band_Carrier_Textbook_ZH-TW.pdf)

## 模型假設與限制

本工具是電壓驅動的物理示意圖，刻意不使用 Cox、tox、摻雜濃度或其他製程參數。工作區域門檻、能量與載子數量是定性呈現，不輸出精確濃度或電流。

## 驗證

執行：

```text
python -m unittest discover -s tests -v
```

## 資料夾結構

```text
fermi-level-simulator/
├─ app.py                 # Tkinter 主介面
├─ region_visuals.py      # 物理模型、區域判定與繪圖
├─ run_simulator.bat      # Windows 啟動器
├─ requirements.txt
├─ docs/
│  ├─ FORMULA_GUIDE.md
│  ├─ VALIDATION_REPORT.md
│  └─ images/             # MOS Cap / MOSFET 預覽圖
└─ tests/
   └─ test_regions.py
```

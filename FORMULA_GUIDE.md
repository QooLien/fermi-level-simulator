# MOS Formula Guide

本工具採用理想化、長通道與 normalized 模型；`Vs = Vb = 0`，不計 body effect、channel-length modulation、Cox 或製程參數。

## MOS capacitor

Fermi potential：

- P-type bulk：`φF = (kT/q) ln(NA/ni)`
- N-type bulk：`φF = −(kT/q) ln(ND/ni)`

表面能帶關係：`Ei(surface) = Ei(bulk) − qψs`。

強反轉邊界：

- P-type bulk：`ψs ≈ +2φF`
- N-type bulk：`ψs ≈ −2|φF|`

許多教材把 bulk potential 寫成 `φB`；在此使用的符號下，`|φB| = |φF|`，因此常見的「`2φB` strong inversion」與上述條件是同一物理判斷。

等價的載子判斷是：表面少數載子濃度已接近 bulk 多數載子濃度。由於本工具刻意沒有 `NA/ND` 與 `Cox` 輸入，因此 `2φF` 作為公式與狀態指引，不計算精確的 strong-inversion gate voltage。

## nMOS operating regions

當 `Vs = Vb = 0`：

- Cutoff：`VGS ≤ VT`
- Linear：`VGS > VT` 且 `0 ≤ VDS < VGS − VT`
- Saturation：`VGS > VT` 且 `VDS ≥ VGS − VT`

因為 `VGD = VGS − VDS`：

- Linear：`VGD > VT`
- Saturation onset：`VGD = VT`
- Saturation：`VGD ≤ VT`

所以對 nMOS 而言，`VGD ≥ VT` 並不代表已進入飽和；`VGD > VT` 時 Drain 端仍存在反轉通道，屬於線性區。

Normalized drain-current equations：

- Linear：`ID = k[(VGS−VT)VDS − VDS²/2]`
- Saturation：`ID = (k/2)(VGS−VT)²`

本工具使用 normalized `k = 1`，並忽略 channel-length modulation。

## pMOS magnitude form

- On：`VSG > |VTP|`
- Linear：`VSD < VSG − |VTP|`
- Saturation：`VSD ≥ VSG − |VTP|`

若使用帶負號的 `VTP` 與 signed `VGD`，pMOS 的不等號外觀看起來會與 nMOS 不同，因此建議以 `VSG / VSD / |VTP|` 的 magnitude form 判斷。

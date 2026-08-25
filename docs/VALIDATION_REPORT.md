# Physics and Formula Validation Report

驗證範圍：MOS capacitor、nMOS、pMOS、主介面即時推導、normalized I-V/C-V、能帶與載子方向。模型固定 `Vs = Vb = 0`，採理想長通道、準靜態與 normalized 教材近似。

## 驗證結論

| 項目 | 結論 |
|---|---|
| MOS surface-potential sign | 通過 |
| `2|φF|` strong-inversion boundary | 通過 |
| Gate/body Fermi-level displacement | 通過 |
| Surface carrier exponential relation | 通過 |
| nMOS cutoff/linear/saturation inequalities | 通過 |
| `VGD` saturation equivalence | 通過 |
| pMOS magnitude-form inequalities | 通過 |
| Linear/saturation drain-current equations | 通過 |
| Drain-current continuity at pinch-off | 通過 |
| nMOS/pMOS mirror symmetry | 通過 |
| Low/high-frequency MOS C-V limits | 修正後通過 |
| MOSFET intrinsic capacitance partition | 修正後通過 |
| Band ordering and gate-Fermi shift | 通過 |

## MOS capacitor

本工具採用下列 Fermi-potential 符號：

\[
\phi_F=\frac{kT}{q}\ln\left(\frac{N_A}{n_i}\right)>0
\quad\text{(P-type bulk)}
\]

\[
\phi_F=-\frac{kT}{q}\ln\left(\frac{N_D}{n_i}\right)<0
\quad\text{(N-type bulk)}
\]

表面電位造成的能帶位移：

\[
E_{c,i,v}(x)=E_{c,i,v}^{bulk}-q\psi(x)
\]

表面載子關係：

\[
\frac{n_s}{n_0}=\exp\left(\frac{\psi_s}{V_T}\right),\qquad
\frac{p_s}{p_0}=\exp\left(-\frac{\psi_s}{V_T}\right)
\]

因此：

\[
\left(\frac{n_s}{n_0}\right)\left(\frac{p_s}{p_0}\right)=1
\]

強反轉起點：

\[
\psi_s=+2\phi_F \quad\text{(P-type bulk)}
\]

\[
\psi_s=-2|\phi_F| \quad\text{(N-type bulk)}
\]

程式中的 normalized 值為 `|φF*| = 0.30 V`，所以邊界是 `|ψs*| = 0.60 V`。P/N bulk 使用鏡像條件，已以數值測試驗證。

Gate 與 body 的 Fermi-level separation：

\[
E_F^G-E_F^B=-qV_G
\]

此式的正負方向與圖中 gate Fermi level 的移動一致。

## nMOS operating regions

\[
V_{OV}=V_{GS}-V_T
\]

\[
\begin{aligned}
V_{GS}\le V_T &\Rightarrow \text{Cutoff}\\
V_{GS}>V_T,\ 0\le V_{DS}<V_{OV} &\Rightarrow \text{Linear}\\
V_{GS}>V_T,\ V_{DS}\ge V_{OV} &\Rightarrow \text{Saturation}
\end{aligned}
\]

因為：

\[
V_{GD}=V_{GS}-V_{DS}
\]

所以：

\[
V_{DS}\ge V_{GS}-V_T
\Longleftrightarrow
V_{GD}\le V_T
\]

`VGD > VT` 是 linear region；`VGD = VT` 是 pinch-off/saturation onset；`VGD < VT` 是 saturation region。

## Drain current

令 `k = μCox(W/L)`；程式只顯示 normalized current，因此採 `k = 1`：

\[
I_D=k\left[(V_{GS}-V_T)V_{DS}-\frac{V_{DS}^2}{2}\right]
\quad (0\le V_{DS}<V_{OV})
\]

\[
I_D=\frac{k}{2}(V_{GS}-V_T)^2
\quad (V_{DS}\ge V_{OV})
\]

在 `VDS = VOV`：

\[
k\left[V_{OV}^2-\frac{V_{OV}^2}{2}\right]
=\frac{k}{2}V_{OV}^2
\]

因此兩區電流連續。數值測試同時驗證 nMOS/pMOS 鏡像偏壓會得到相同電流大小與相反 signed current。

## pMOS

為避免負 `VTP` 造成不等號混淆，程式使用 magnitude form：

\[
V_{SG}>|V_{TP}|
\]

\[
0\le V_{SD}<V_{SG}-|V_{TP}| \Rightarrow \text{Linear}
\]

\[
V_{SD}\ge V_{SG}-|V_{TP}| \Rightarrow \text{Saturation}
\]

## C-V corrections

MOS capacitor：

\[
C_{MOS}=\left(C_{ox}^{-1}+C_s^{-1}\right)^{-1}
\]

Low-frequency inversion 回升至接近 `Cox`；ideal high-frequency inversion 維持接近 `Cmin`。舊版 high-frequency inversion 的小幅回升已移除。

MOSFET intrinsic capacitance（忽略 overlap）：

\[
C_{gs}\approx C_{gd}\approx\frac{C_0}{2}
\quad\text{(Linear)}
\]

\[
C_{gs}\approx\frac{2C_0}{3},\qquad C_{gd}\approx0
\quad\text{(Saturation)}
\]

介面使用平滑函數在兩區之間轉換，極限值已通過測試。

## Corrections made during this audit

1. nMOS 的 Vds 控制限制為 `0…+3 V`；pMOS 限制為 `0…−3 V`，避免把反向偏壓套入只適用正向 source/drain 定義的 square-law 方程。
2. 工作區域、主圖公式與 I-V 計算改為共用同一個 operating-point function，避免重複邏輯漂移。
3. MOS high-frequency C-V 強反轉端修正為維持 `Cmin`。
4. MOSFET Cgs/Cgd 修正為標準長通道 intrinsic partition 極限。
5. 新增 strong-inversion boundary、mass-action、VGD equivalence、current continuity、P/N symmetry、band ordering 與 capacitance-limit 測試。
6. Pinch-off equality 使用 `10⁻¹² V` 數值容差，避免二進位浮點數把理論上的 `VDS = VOV` 誤判為 linear region。

## Automated validation results

- 14 項單元／公式測試：全部通過，包含三種 MOSFET 區域預設與 3D 視角傳遞。
- MOS capacitor P/N symmetry 與 mass-action：`1,201` 個 Vg 點通過。
- MOSFET region、current 與 nMOS/pMOS symmetry：`14,641` 組 Vgs/Vds 通過。
- Pinch-off current continuity：`500` 個不同 overdrive boundary 通過。

## Declared limitations

- `|φF*|=0.30 V`、`VT=0.80 V`、`k=1` 是 normalized 教材常數，不代表特定製程。
- 未輸入 `NA/ND`、`Cox`、oxide thickness、mobility、W/L，因此不能輸出絕對 threshold、current 或 capacitance。
- 3D band surface 與 Evac/oxide vertical offsets 是 normalized schematic，不是 Poisson equation 的自洽 TCAD 解，也不能用來擷取絕對 electron affinity 或 band offset。
- 忽略 body effect、channel-length modulation、subthreshold current、DIBL、velocity saturation、overlap/fringing capacitance、leakage 與 quantum effects。

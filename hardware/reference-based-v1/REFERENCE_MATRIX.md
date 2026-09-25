# Reference Matrix — Draft

> 记录“参考设计事实”和“V1 实施决定”，避免参考设计、旧自动板和新板三者混在一起。

| Subsystem | Primary reference | V1 decision | Status |
|---|---|---|---|
| MCU core power | STM32H743 DS + AN4938 + MB1364 | 重新绘制并逐网核对 | TODO |
| VCAP | DS + MB1364 | 每个 VCAP 就近独立电容 | TODO |
| VDDA/VREF | DS + AN4938 | 独立滤波并保留测试能力 | TODO |
| VDD33_USB | DS + MB1364 | 接 3V3 并就近去耦 | TODO |
| HSE | DS + WeAct | 独立晶振，不依赖板载调试器 MCO | TODO |
| LSE | DS + MB1364 | 预留并默认装配 | TODO |
| SWD/SWO | MB1364 | 外置调试器接口 | TODO |
| USB FS | MB1364 + WeAct | USB-C Device/UFP + ESD | Frozen architecture |
| USB HS controller | STM32H743 DS + RM0433 | OTG_HS 外置 ULPI PHY，USB2 HS 480M | Frozen |
| USB HS PHY | ST H7 ULPI ref + Microchip USB3300/3320 docs | USB3320C/USB3300 class，最终按采购冻结 | TODO part freeze |
| USB HS connector | USB2 spec + PHY ref | USB-A Host；只使用 USB2 contacts | Frozen architecture |
| USB HS VBUS | PHY datasheet + power-switch datasheet | 独立 5V current-limited high-side switch + OC | TODO |
| ULPI pin map | STM32H743 DS | PA3/PA5/PB0/PB1/PB10/PB11/PB12/PB13/PB5/PC0/PC2/PC3 | Frozen |
| Ethernet MAC | MB1364 | H743 ETH RMII | Frozen |
| Ethernet PHY | MB1364 | LAN8742A | Frozen |
| RMII pin map | MB1364 + H743 AF | PA1/PA2/PA7/PC1/PC4/PC5/PG11/PG13/**PG14** | Frozen |
| RMII TXD1 deviation | H743 DS | 从 MB1364 PB13 改 PG14，避免与 ULPI_D6 冲突 | Frozen |
| RJ45 | MB1364 | 100BASE-TX MagJack/磁性器件，按采购料号核对 | TODO |
| 5V→3V3 | 当前板 + regulator datasheet | 单独重审，不继承“DRC=0 即正确”假设 | TODO |
| GPIO headers | New V1 | 只引出未占用 IO并标注复用 | TODO |
| True USB 3.x | Future V2 only | V1 不实现；需独立 SuperSpeed controller/bridge | Out of scope |

## Reference hierarchy

发生冲突时按优先级：

1. 芯片/器件最新 datasheet 与 errata
2. ST 官方参考设计
3. ST / Microchip 应用笔记与 layout guide
4. 已量产第三方板
5. 当前 hagent 自动生成设计
6. Agent 推断

低优先级不得覆盖高优先级。

## Known intentional deviation from MB1364

MB1364 使用 PB13 作为 `RMII_TXD1`。V1 同时启用 OTG_HS ULPI，而 PB13 是 `ULPI_D6`，因此 V1 将 `RMII_TXD1` 移到同样支持 AF11 Ethernet TXD1 的 PG14。

这不是“为了布线方便”的任意 pin swap，而是为了让 Ethernet + USB HS 可并存的架构级固定决策。

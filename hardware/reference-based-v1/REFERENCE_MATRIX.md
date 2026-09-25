# Reference Matrix — Draft

> 本文件用于记录“参考设计事实”和“V1 实施决定”，避免参考设计、旧自动板和新板三者混在一起。

| Subsystem | Primary reference | V1 decision | Status |
|---|---|---|---|
| MCU core power | STM32H743 DS + AN4938 + MB1364 | 重新绘制并逐网核对 | TODO |
| VCAP | DS + MB1364 | 每个 VCAP 就近独立电容 | TODO |
| VDDA/VREF | DS + AN4938 | 独立滤波并保留测试能力 | TODO |
| VDD33_USB | DS + MB1364 | 接 3V3 并就近去耦 | TODO |
| HSE | DS + WeAct | V1 使用独立晶振，不依赖板载调试器 MCO | TODO |
| LSE | DS + MB1364 | 预留并默认装配 | TODO |
| SWD/SWO | MB1364 | 外置调试器接口 | TODO |
| USB FS | MB1364 + WeAct | USB-C Device/UFP + ESD | TODO |
| Ethernet MAC | MB1364 | H743 ETH RMII | Frozen |
| Ethernet PHY | MB1364 | LAN8742A | Frozen |
| RMII pin map | MB1364/H743 AF | PA1/PA2/PA7/PC1/PC4/PC5/PB13/PG11/PG13 | Frozen |
| RJ45 | MB1364 | 100BASE-TX MagJack/磁性器件方案，最终按可采购料号核对 | TODO |
| 5V→3V3 | 当前板 + regulator datasheet | 单独重新审核，不继承“DRC=0 即正确”的假设 | TODO |
| GPIO headers | New V1 | 只引出未占用 IO，并标注复用 | TODO |

## Reference hierarchy

发生冲突时按以下优先级处理：

1. 芯片/器件最新 datasheet 与 errata
2. ST 官方 MB1364
3. ST 应用笔记
4. 已量产第三方板
5. 当前 hagent 自动生成设计
6. Agent 推断

低优先级不得覆盖高优先级。
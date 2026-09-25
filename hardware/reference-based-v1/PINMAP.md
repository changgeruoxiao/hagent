# H743 Dev V1 — Reserved Pin Map

此表是 V1 的引脚占用真源之一。原理图、CubeMX、测试固件都必须与它一致。

## Ethernet RMII

| Function | Pin | State |
|---|---|---|
| ETH_REF_CLK | PA1 | Reserved |
| ETH_MDIO | PA2 | Reserved |
| ETH_MDC | PC1 | Reserved |
| ETH_CRS_DV | PA7 | Reserved |
| ETH_RXD0 | PC4 | Reserved |
| ETH_RXD1 | PC5 | Reserved |
| ETH_TX_EN | PG11 | Reserved |
| ETH_TXD0 | PG13 | Reserved |
| ETH_TXD1 | **PG14** | Reserved; moved from MB1364 PB13 to avoid ULPI_D6 conflict |

## USB FS — Device / maintenance

| Function | Pin | State |
|---|---|---|
| USB_FS_DM | PA11 | Reserved |
| USB_FS_DP | PA12 | Reserved |
| USB_FS_VBUS | PA9 | Reserved pending VBUS-sense finalization |

## USB HS — ULPI external PHY

| Function | Pin | State |
|---|---|---|
| USB_HS_ULPI_D0 | PA3 | Reserved |
| USB_HS_ULPI_CK | PA5 | Reserved |
| USB_HS_ULPI_D1 | PB0 | Reserved |
| USB_HS_ULPI_D2 | PB1 | Reserved |
| USB_HS_ULPI_D3 | PB10 | Reserved |
| USB_HS_ULPI_D4 | PB11 | Reserved |
| USB_HS_ULPI_D5 | PB12 | Reserved |
| USB_HS_ULPI_D6 | PB13 | Reserved |
| USB_HS_ULPI_D7 | PB5 | Reserved |
| USB_HS_ULPI_STP | PC0 | Reserved |
| USB_HS_ULPI_DIR | PC2 | Reserved |
| USB_HS_ULPI_NXT | PC3 | Reserved |

> 注意：PC2/PC3 是具有 GPIO alternate-function 的数字管脚；不要把它们与独立的模拟 `PC2_C/PC3_C` 混淆。

## Debug

| Function | Pin | State |
|---|---|---|
| SWDIO | PA13 | Reserved |
| SWCLK | PA14 | Reserved |
| SWO | PB3 | Reserved |

## Clock

| Function | Pin | State |
|---|---|---|
| HSE_IN | PH0 | Reserved |
| HSE_OUT | PH1 | Reserved |
| LSE_IN | PC14 | Reserved |
| LSE_OUT | PC15 | Reserved |

## Conflict decisions

### PB13 conflict resolved

- MB1364 Ethernet: PB13 = RMII_TXD1
- USB HS ULPI: PB13 = ULPI_D6
- V1 decision: PB13 保留给 ULPI_D6，Ethernet RMII_TXD1 改到 PG14。
- 依据：STM32H743 datasheet 中 PG14 支持 ETH_MII_TXD1 / ETH_RMII_TXD1。

这条映射是冻结决策，后续 Agent 不得自动改回 PB13。

## Board UI

USER LED / USER KEY 暂不锁死具体 GPIO。原则：

1. 不占用 Ethernet / USB FS / USB HS / SWD / HSE / LSE；
2. 优先普通 GPIO；
3. 不给 BOOT/调试/关键模拟引脚增加不必要负载。

## Header policy

所有 Reserved 引脚即使物理引到测试点或排针，也必须在丝印/文档标记板载占用，不能宣传为“自由 GPIO”。

剩余 GPIO 的排针布局在原理图完成后自动生成 `GPIO_HEADER_MAP.csv`，避免手工维护两份 pin map。

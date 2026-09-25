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
| ETH_TXD1 | PB13 | Reserved |

## USB FS

| Function | Pin | State |
|---|---|---|
| USB_FS_DM | PA11 | Reserved |
| USB_FS_DP | PA12 | Reserved |
| USB_FS_VBUS | PA9 | Reserved pending VBUS-sense finalization |

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

## Board UI

USER LED / USER KEY 暂不锁死具体 GPIO。原则是：

1. 不占用 Ethernet / USB / SWD / HSE / LSE；
2. 优先选择普通 GPIO；
3. 不给 BOOT/调试/关键模拟引脚增加不必要负载。

最终锁定后再更新此表。

## Header policy

上述 Reserved 引脚即使物理上被引到测试点或排针，也必须在丝印/文档中标记其板载占用，不能宣传为“自由 GPIO”。

剩余 GPIO 的排针布局在原理图完成后自动生成一份 `GPIO_HEADER_MAP.csv`，避免手工维护两份 pin map。
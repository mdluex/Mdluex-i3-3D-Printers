# Mdluex i3 Firmware

This repository contains the firmware configurations for the **Mdluex i3** 3D printer. It supports both **Marlin 2.1.3-b3** and **Klipper** configurations for different controller boards.

## Hardware Specifications

*   **Printer Model**: Mdluex i3
*   **Build Volume**: 230 x 210 x 210 mm
*   **Display**: RepRapDiscount 2004 Smart Controller
*   **Probe**: BLTouch / 3D Touch (Offsets: 30, 10, -4.03)
*   **Bed Tramming**: Supports "Screws Tilt Adjust" (Corner leveling)

---

## 1. Marlin Firmware (v2.1.3-b3)

The Marlin configuration is located in the `Marlin/` directory, managed via `Marlin/config.ini`.

### Key Features Enabled
*   **Bed Tramming / Screws Tilt Adjust**: Dedicated menu to assist in leveling bed corners.
*   **Z Probe Offset Wizard**: Automated menu to calibrate the Z Probe Offset.
*   **Babystepping**: Live Z-offset adjustment during printing (double-click encoder or via menu) which saves to EEPROM.
*   **Linear Advance & Input Shaping**: Enabled in Advanced Settings.

### How to Build
1.  Open this folder in VSCode.
2.  Use the **Auto Build Marlin** extension.
3.  Select environment `RAMPS_14_EFB` (or your target board).
4.  Build and Upload.

---

## 2. Klipper Firmware

Migration configurations are provided in the `klipper cfg/` folder for two different mainboards.

### Option A: RAMPS 1.4 (`ramps_klipper.cfg`)
*   **Drivers**: **DRV8825**
*   **Microsteps**: **32** (Ensure all 3 jumpers are installed under each driver).
*   **Rotation Distance**:
    *   X: 32.312
    *   Y: 83.518
    *   Z: 8.166
    *   E: 32.0

### Option B: BTT Octopus v1.1 (`octopus_klipper.cfg`)
*   **Drivers**: **TMC2226** (TMC2209 compatible)
*   **Microsteps**: **32**
*   **Interpolation**: **Enabled** (MicroPlyer interpolates to 256 microsteps for silence).
*   **UART**: Configured on standard pins (`PC4`, `PD11`, `PC6`, `PC7`).
*   **Run Current**: 0.800 A
*   **Sense Resistor**: 0.150 Ohm (Standard for BTT TMC2226).

### How to Use
1.  Copy the contents of the relevant `.cfg` file to your `printer.cfg` on your Klipper host (Raspberry Pi/Mainsail/Fluidd).
2.  Restart Klipper.
3.  Run `G28` to home and verify direction.
4.  Run `PROBE_CALIBRATE` to set your initial Z offset.

---

## Credits
*   Marlin Firmware: [https://marlinfw.org/](https://marlinfw.org/)
*   Klipper Firmware: [https://www.klipper3d.org/](https://www.klipper3d.org/)

# Mdluex i3 Firmware

This repository contains the firmware configurations for the **Mdluex i3** 3D printer.

**🚀 Recommendation: Klipper is the recommended firmware for the Mdluex i3 due to its advanced features, ease of configuration, and input shaping capabilities.**

However, full support for **Marlin 2.1.3-b3** is also provided for those who prefer it.

## Hardware Specifications

*   **Printer Model**: Mdluex i3
*   **Build Volume**: 230 x 210 x 210 mm
*   **Display**: RepRapDiscount 2004 Smart Controller
*   **Probe**: BLTouch / 3D Touch (Offsets: 30, 10, -4.03)
*   **Bed Tramming**: Supports "Screws Tilt Adjust" (Corner leveling)

---

## 📂 1. Klipper Firmware (Recommended)

Configurations are located in the `Klipper/klipper cfg/` directory.

### Option A: RAMPS 1.4 (`ramps_klipper.cfg`)
*   **Drivers**: **DRV8825**
*   **Microsteps**: **32** (Ensure all 3 jumpers are installed).
*   **Rotation Distance**: X: 32.312, Y: 83.518, Z: 8.166, E: 32.0

### Option B: BTT Octopus v1.1 (`octopus_klipper.cfg`)
*   **Drivers**: **TMC2226** (TMC2209 compatible)
*   **Microsteps**: **32** (Interpolated to 256).
*   **UART**: Configured on standard pins.
*   **Run Current**: 0.800 A

### How to Use
1.  Navigate to `Klipper/klipper cfg/`.
2.  Copy the content of your board's `.cfg` file to `printer.cfg` on your Raspberry Pi.
3.  Restart Klipper, Home (`G28`), and Calibrate Probe (`PROBE_CALIBRATE`).

---

## 🔌 2. Klipper Wi-Fi Autopilot Plugin

Located in: `Klipper/klipper_tools/wifi_autopilot/`

This plugin ensures your printer is always connected. If Wi-Fi is lost, it creates a hotspot (`Klipper-Setup`) to allow you to reconnect easily.

### Features
*   **Auto-Hotspot**: Activates when offline.
*   **Captive Portal**: Web UI to scan & connect.
*   **LCD Status**: Updates display with connection status.

### How to Install
(Requires SSH access to your Pi)

1.  **Clone the repo & navigate to the tool:**
    ```bash
    cd ~
    git clone https://github.com/mdluex/Mdluex-i3-Firmware--Marlin-Klipper-.git
    cd "Mdluex-i3-Firmware--Marlin-Klipper-/Klipper/klipper_tools/wifi_autopilot"
    ```

2.  **Run Installer:**
    ```bash
    chmod +x install.sh
    ./install.sh
    ```

3.  **Update Config:** Add `[include wifi_status.cfg]` to your `printer.cfg`.

---

## ⚙️ 3. Marlin Firmware (Legacy)

The Marlin configuration is located in the `Marlin/` directory.

### Key Features
*   **Bed Tramming / Screws Tilt Adjust**
*   **Z Probe Offset Wizard**
*   **Babystepping** & **Linear Advance**

### How to Build
1.  Open the `Marlin/` folder in VSCode.
2.  Use **Auto Build Marlin**.
3.  Build for `RAMPS_14_EFB` (or target board).

---

## Credits
*   Marlin Firmware: [https://marlinfw.org/](https://marlinfw.org/)
*   Klipper Firmware: [https://www.klipper3d.org/](https://www.klipper3d.org/)

# Konzept: Virtuelle USB-HID Device Emulation für Microsoft Teams

## 1. Problemstellung
Die aktuelle Implementierung nutzt `pyautogui`, um Tastatur-Shortcuts (`Ctrl+Shift+M`) auf Betriebssystemebene zu simulieren. Dies hat zwei entscheidende Nachteile:
1.  **Fokus-Abhängigkeit:** Der Shortcut funktioniert nur, wenn das Teams-Fenster (oder das Dokument) den Fokus hat. In automatisierten Tests führt dies oft zu Fehlern (z.B. Eingabe des Buchstabens 'm' in Textfelder).
2.  **Mangelnde HID-Authentizität:** Es wird kein echter HID-Report gesendet, wie ihn ein physisches Headset senden würde. Die Konformität mit dem USB-IF Standard wird somit nur indirekt über die Software-Reaktion auf Shortcuts geprüft.

## 2. Lösung: Virtuelles USB-HID Gerät
Anstatt Tastenanschläge zu simulieren, wird ein virtuelles Eingabegerät im Linux-Kernel via `uinput` erstellt. Dieses Gerät identifiziert sich gegenüber dem System als USB-Audiogerät mit HID-Unterstützung.

### Architektur-Vergleich
| Merkmal | Aktuell (UI-Level) | Ziel (Kernel-Level) |
| :--- | :--- | :--- |
| **Technik** | `pyautogui` / X11 Events | `uinput` / Kernel HID Reports |
| **Signalweg** | Tastatur-Puffer -> App Shortcut | HID-Treiber -> Desktop-Bus -> App |
| **Fokus** | Erforderlich | Nicht erforderlich (globales Event) |
| **Authentizität**| Simulierter Shortcut | Simulierter Hardware-Report |

## 3. Technische Umsetzung (Linux `uinput`)

### 3.1. Gerätetypen und Mappings
Das virtuelle Gerät muss so konfiguriert werden, dass es die spezifischen HID-Usages unterstützt:

-   **Telephony Page (0x0B), Usage 0x2F (Phone Mute):**
    Wird im Linux-Input-Subsystem auf `KEY_MICMUTE` (Scancode 248) abgebildet.
-   **Consumer Page (0x0C), Usage 0xE2 (Mute):**
    Wird auf `KEY_MUTE` (Scancode 113) abgebildet.

### 3.2. Implementierung mit Python `evdev`
Die Library `evdev` ermöglicht die einfache Erstellung von `uinput` Geräten.

```python
from evdev import UInput, ecodes as e

# Definition der unterstützten Capabilities
cap = {
    e.EV_KEY: [e.KEY_MICMUTE, e.KEY_MUTE]
}

# Erstellung des virtuellen Geräts
with UInput(cap, name="Virtual-Teams-Headset", vendor=0x045e, product=0x0605) as ui:
    # Senden eines Telephony Mute Events
    ui.write(e.EV_KEY, e.KEY_MICMUTE, 1) # Press
    ui.write(e.EV_KEY, e.KEY_MICMUTE, 0) # Release
    ui.syn()
```

## 4. Vorteile für die Verifizierung
*   **Keine Interferenz:** Da keine echten Tastenanschläge gesendet werden, werden keine Textfelder ungewollt befüllt.
*   **Standard-Konform:** Teams reagiert auf die System-Events, die durch den HID-Treiber ausgelöst werden. Dies beweist die Unterstützung des Betriebssystems und der Applikation für standardisierte USB-HID Signale.
*   **Robustheit:** Die Tests laufen auch dann stabil, wenn das Teams-Fenster im Hintergrund ist oder der Fokus wechselt.

## 5. Voraussetzungen & Einschränkungen
*   **Kernel-Support:** Das Modul `uinput` muss geladen sein (`modprobe uinput`).
*   **Berechtigungen:** Der ausführende Nutzer benötigt Schreibrechte auf `/dev/uinput` (üblicherweise via `udev`-Regel oder `sudo`).
*   **CI-Umgebungen:** In restriktiven Container-Umgebungen (wie Standard GitHub Runners) ist `/dev/uinput` oft nicht verfügbar. Hier muss weiterhin der `pyautogui`-Fallback genutzt werden, während der "echte" HID-Test auf dedizierten Test-Nodes oder via `sudo` erfolgt.

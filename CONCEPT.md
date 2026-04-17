# Konzept: Verifizierung der Microsoft Teams USB-IF HID Konformität

## 1. Zielsetzung
Das Ziel dieses Projekts ist der Nachweis, dass Microsoft Teams die Standard-USB-IF HID (Human Interface Device) Spezifikationen für die Stummschaltung (Mute/Unmute) von Mikrofon und Lautsprecher korrekt unterstützt.

## 2. Hintergrund
USB-Audiogeräte (Headsets, Speakerphones) kommunizieren ihren Status (z.B. Taste gedrückt) über HID-Reports an den Host. Microsoft Teams sollte auf diese standardisierten Signale reagieren, um eine nahtlose Synchronisation zwischen Hardware-Tasten und Software-Status zu gewährleisten.

## 3. Technische Spezifikation (USB-IF HID)
Folgende HID Usage Pages und IDs stehen im Fokus der Implementierung:

- **Telephony Page (0x0B)**
  - `Phone Mute` (Usage ID: 0x2F): Speziell für die Stummschaltung in Telefonie-Anwendungen.
- **Consumer Page (0x0C)**
  - `Mute` (Usage ID: 0xE2): Allgemeiner System-Mute (meist für Lautsprecher).

## 4. Implementierungsansatz

### 4.1. Simulation der HID-Eingaben
Da keine physische Hardware in der Testumgebung vorhanden ist, werden USB-HID-Eingaben simuliert. Dies kann erfolgen durch:
- Softwarebasierte HID-Emulation (z.B. via Python `uinput` unter Linux oder spezialisierte Treiber).
- Virtuelle Tastatur-Events, die die entsprechenden HID-Codes abbilden.

### 4.2. Test-Automatisierung
Ein Automatisierungsskript führt folgende Schritte aus:
1. Starten von Microsoft Teams.
2. Initiieren oder Beitreten eines Test-Anrufs.
3. Senden des HID-Signals für "Mute".
4. Senden des HID-Signals für "Unmute".

### 4.3. Verifizierung (Screenshot-Analyse)
Die Erfolgskontrolle erfolgt automatisiert durch Screenshots:
- Erfassen des Teams-Fensters nach dem Senden des HID-Signals.
- Bilderkennung oder Pixel-Analyse des Mikrofon-Icons (durchgestrichen vs. aktiv).
- Protokollierung des Zustandswechsels.

## 5. Erfolgskriterien
- Microsoft Teams wechselt den Stummschaltungsstatus im UI synchron zum simulierten HID-Event.
- Sowohl die Telephony Page als auch die Consumer Page (sofern zutreffend) werden korrekt verarbeitet.
- Die Verifizierung erfolgt ohne manuelle Eingriffe durch das Test-Skript.

## 6. Zielbild (Zustandsdiagramm)
1. **IDLE**: Teams ist im Call, Mikrofon aktiv.
2. **ACTION**: HID Report (0x0B, 0x2F) wird gesendet.
3. **REACTION**: Teams UI zeigt "Stummgeschaltet".
4. **VERIFICATION**: Screenshot bestätigt das durchgestrichene Mikrofon-Icon.

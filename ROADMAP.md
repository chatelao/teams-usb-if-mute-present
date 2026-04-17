# Roadmap: Implementierung der Microsoft Teams HID-Verifizierung

Diese Roadmap beschreibt die Schritte zur Umsetzung des Konzepts in ausführbare Skripte, die sowohl lokal auf Ubuntu als auch in GitHub Actions (CI) funktionieren.

## Phase 1: Vorbereitung der Umgebung
Ziel: Eine konsistente Laufzeitumgebung für lokale Entwicklung und CI schaffen.

- [x] **Lokal (Ubuntu):**
    - Installation von `python3`, `pip`, `xvfb` (für Headless-Tests).
    - Setup virtueller Python-Umgebungen.
- [x] **GitHub Actions:**
    - Erstellung eines Workflows, der einen virtuellen Framebuffer (Xvfb) startet, um GUI-Apps ohne Monitor auszuführen.
    - Installation der notwendigen Abhängigkeiten in der CI-Pipeline.

## Phase 2: HID Emulations-Layer
Ziel: Simulation von USB-HID Signalen ohne physische Hardware.

- [x] **Recherche & Auswahl:**
    - Evaluierung von `python-evdev` oder `uinput` zur Erstellung virtueller Eingabegeräte.
    - Alternative: Nutzung von `pyautogui` für Standard-Key-Events, falls HID-spezifische Page-IDs nicht direkt emuliert werden können (Hinweis: Für echten HID-Nachweis ist `evdev` bevorzugt).
- [x] **Implementierung `hid_simulator.py`:**
    - Skript zum Senden von `Telephony: Phone Mute` (0x0B, 0x2F).
    - Skript zum Senden von `Consumer: Mute` (0x0C, 0xE2).

## Phase 3: Teams Automatisierung
Ziel: Microsoft Teams fernsteuern und in einen Call-Zustand bringen.

- [x] **Mock-Automatisierung (CI-ready):**
    - Simulation des Teams-Web-Interfaces zur Verifizierung der HID-Logik ohne echte Teams-Installation.
- [x] **Installation (Echtbetrieb):**
    - Automatisierte Installation von Microsoft Teams (Linux-Client oder Web-App via Selenium/Playwright).
- [x] **Workflow-Skript:**
    - Starten von Teams.
    - Einwählen in einen Test-Call (z.B. Echo-Test oder geplanter Call).
    - Sicherstellen, dass das Fenster im Fokus ist.

## Phase 4: Visuelle Verifizierung
Ziel: Automatisierte Erfolgskontrolle durch Bildanalyse.

- [x] **Referenz-Bilder:**
    - Erstellen von Templates für das "Mute"-Icon und "Unmute"-Icon in Teams.
- [x] **Implementierung `image_verifier.py`:**
    - Screenshot des Teams-Fensters erstellen.
    - Nutzung von `OpenCV` oder `PIL` zum Abgleich mit den Templates.
    - Rückgabe eines Boolean-Werts (Success/Fail).

## Phase 5: CI/CD Integration (GitHub Actions)
Ziel: Vollautomatische Tests bei jedem Push.

- [x] **Workflow-Definition:**
    - Trigger bei Push auf `main` oder Pull Requests.
    - Matrix-Builds (optional für verschiedene Teams-Versionen).
    - Upload der Screenshots als Artefakte im Fehlerfall zur Fehlersuche.

## Zeitplan (Vorschlag)
1. **Woche 1:** Phase 1 & 2 (Umgebung & HID-Simulation).
2. **Woche 2:** Phase 3 & 4 (Teams-Steuerung & Bildanalyse).
3. **Woche 3:** Phase 5 (Integration & Finalisierung).

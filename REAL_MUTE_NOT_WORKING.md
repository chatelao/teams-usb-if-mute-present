# Ursachenanalyse: Mute-Fehler auf dem Real Teams Pre-join Screen

Die Datei `real_teams_prejoin_muted_test.png` zeigte, dass die Stummschaltung über HID-Events auf dem echten Microsoft Teams Pre-join Screen nicht wie erwartet funktionierte. Die Analyse ergab zwei Hauptursachen:

## 1. Fokus-Konflikt im Eingabefeld
Im Automatisierungsskript `real_teams_web_automation.py` wird das Namensfeld für Gäste ausgefüllt (`HID-Compliance-Tester`). Unmittelbar danach wird das HID-Event simuliert.
- **Problem:** Der Fokus bleibt nach dem Ausfüllen im Texteingabefeld.
- **Auswirkung:** Das simulierte Tastatur-Event (derzeit nur die Taste 'm') wird als Text in das Eingabefeld geschrieben, anstatt von Microsoft Teams als globaler Shortcut erkannt zu werden.

## 2. Inkorrekter Tastatur-Shortcut
Der `hid_simulator.py` verwendet derzeit die Taste `m` zur Simulation von `Telephony Mute` (0x0B, 0x2F).
- **Problem:** Während einige Applikationen 'm' unterstützen, ist der offizielle und zuverlässige Shortcut für Microsoft Teams (Web & Desktop) `Strg+Umschalt+M` (Ctrl+Shift+M).
- **Auswirkung:** Selbst wenn kein Fokus-Konflikt bestünde, würde ein einfaches 'm' im Web-Client unter Umständen nicht ausreichen, um den Mute-Status zuverlässig zu toggeln, besonders wenn die Seite nicht korrekt auf einfache Tastendrücke reagiert.

## Geplante Korrekturmaßnahmen
1. **Shortcut-Update:** Änderung des `hid_simulator.py`, sodass `Telephony Mute` den Shortcut `Strg+Umschalt+M` verwendet.
2. **Fokus-Management:** Anpassung von `real_teams_web_automation.py`, um das aktive Element (Eingabefeld) vor dem Senden des HID-Signals zu verlassen (Blur), damit der Shortcut vom Browser/Teams-Framework korrekt verarbeitet werden kann.
3. **Mock-Synchronisation:** Aktualisierung der Mock-UIs (`mock_teams_web.html` und `mock_teams_ui.py`), um den neuen Shortcut ebenfalls zu unterstützen und die Test-Integrität zu wahren.

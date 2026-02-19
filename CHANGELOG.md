# Changelog

Alle wichtigen Änderungen an diesem Plugin werden hier dokumentiert.

---

## [1.0] - 2026-02-19

### Erstveröffentlichung

**Funktion 1: Wiedergabe vor Standby stoppen**
- Erkennt ob eine `.ts`-Aufnahme oder Timeshift abgespielt wird
- Stoppt den Service sauber via `stopService()` bevor Standby aktiviert wird
- Schließt den MoviePlayer-Screen via `close()` statt `leavePlayer()` (verhindert Modal-Crash)
- Vollautomatisch ohne Benutzerabfrage

**Funktion 2: Kanal nach Aufwecken wiederherstellen**
- Speichert den zuletzt gesehenen TV-Kanal (`config.tv.lastservice`) vor dem Standby
- Hook auf `Standby.close()` statt `Standby.power()` – zu diesem Zeitpunkt ist der Tuner bereits bereit
- 2 Sekunden Verzögerung via `eTimer` für zuverlässiges Tuning
- Kanal-Zap über `servicelist.zap()` – exakt wie ein Channel Up/Down-Tastendruck

**Technische Details**
- Python 2.7 kompatibel
- Monkey-Patching von `Standby.__init__` und `Standby.close()`
- IPK-Paket mit `Architecture: all`
- Einstellungs-Screen im Plugin-Menü (aktivieren/deaktivieren)

---

### Bekannte Probleme in früheren Entwicklungsversionen (nicht veröffentlicht)

- **v0.5**: `leavePlayer()` verursachte Crash `modal open are allowed only from a screen which is modal` → behoben durch direktes `close()`
- **v0.4**: `stopService()` direkt aufgerufen löste `ValueError: invalid null reference in eServiceReference___eq__` aus → behoben durch korrekte Reihenfolge
- **v0.3**: Hook auf `Standby.power()` zu früh – Tuner noch nicht bereit → behoben durch Hook auf `Standby.close()`
- **v0.2**: `Architecture: cortexa15hf-neon-vfpv4` verhinderte Installation → behoben durch `Architecture: all`

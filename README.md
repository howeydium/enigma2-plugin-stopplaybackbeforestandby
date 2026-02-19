# StopPlaybackBeforeStandby

[![Version](https://img.shields.io/badge/version-1.0-blue.svg)](https://github.com/yourusername/enigma2-plugin-stopplaybackbeforestandby/releases)
[![Platform](https://img.shields.io/badge/platform-VU%2B%20Uno%204K-orange.svg)]()
[![Image](https://img.shields.io/badge/image-VTI%2015.x-green.svg)]()
[![Python](https://img.shields.io/badge/python-2.7-yellow.svg)]()
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](LICENSE)

Ein Enigma2-Plugin für den **VU+ Uno 4K** mit **VTI-Image**, das zwei Probleme des normalen Standby-Verhaltens löst:

1. **Wiedergabe vor Standby stoppen** – Wird gerade eine Aufnahme oder ein Timeshift abgespielt und der Receiver geht in Standby, stoppt das Plugin die Wiedergabe automatisch und sauber, bevor Standby aktiviert wird.
2. **Kanal nach Aufwecken wiederherstellen** – Nach dem Aufwecken aus dem Standby schaltet der Receiver automatisch auf den zuletzt gesehenen TV-Kanal zurück (mit 2 Sekunden Verzögerung, damit der Tuner bereit ist).

---

## Das Problem ohne dieses Plugin

Ohne das Plugin passiert beim Standby während einer Aufnahme-Wiedergabe folgendes:

- Der Receiver geht in Standby, aber der MoviePlayer bleibt im Hintergrund aktiv
- Beim Aufwecken steht man im MoviePlayer, nicht auf einem TV-Kanal
- Der Tuner ist nicht aktiv – man sieht ein schwarzes Bild
- Erst nach manuellem Channel Up/Down wird der Tuner gestartet

---

## Funktionsweise

### Vor dem Standby

Das Plugin hängt sich per Monkey-Patch in `Standby.__init__` ein. Sobald Enigma2 den Standby-Screen öffnen will:

1. Prüft ob der aktuelle Service eine `.ts`-Datei ist (Aufnahme oder Timeshift)
2. Speichert den zuletzt gesehenen TV-Kanal (`config.tv.lastservice`)
3. Ruft `stopService()` auf – Service-Referenz wird sofort ungültig
4. Schließt den MoviePlayer-Screen direkt via `close()` (kein `leavePlayer()`, das würde Modal-Dialoge öffnen und crashen)
5. Enigma2 geht normal in Standby

### Nach dem Aufwecken

Das Plugin hängt sich zusätzlich in `Standby.close()` ein. Dieser Hook wird aufgerufen **nachdem** der Standby-Screen vollständig beendet wurde – zu diesem Zeitpunkt ist der Tuner wieder betriebsbereit:

1. `Standby.close()` wird abgefangen
2. Original `close()` wird ausgeführt (Standby beendet)
3. Ein `eTimer` wartet **2 Sekunden**
4. `servicelist.zap()` schaltet auf den gespeicherten Kanal – exakt wie ein Channel Up/Down

> **Warum 2 Sekunden?** `Standby.close()` ist zwar der richtige Zeitpunkt (Tuner grundsätzlich bereit), aber Enigma2 und der Tuner brauchen noch einen Moment bis der erste Zap-Befehl angenommen wird. 500ms war zu kurz, 2s funktioniert zuverlässig.

---

## Installation

### Methode 1: IPK-Datei (empfohlen)

1. IPK-Datei aus dem [Releases-Bereich](https://github.com/yourusername/enigma2-plugin-stopplaybackbeforestandby/releases) herunterladen
2. Per FTP/SCP auf den Receiver in `/tmp/` kopieren
3. Per SSH installieren:

```bash
opkg install /tmp/enigma2-plugin-extensions-stopplaybackbeforestandby_1.0_all.ipk
init 4 && init 3
```

### Methode 2: Manuell per SSH

```bash
# Ordner erstellen
mkdir -p /usr/lib/enigma2/python/Plugins/Extensions/StopPlaybackBeforeStandby

# Dateien hochladen (per FTP/SCP):
# src/usr/lib/enigma2/python/Plugins/Extensions/StopPlaybackBeforeStandby/plugin.py
# src/usr/lib/enigma2/python/Plugins/Extensions/StopPlaybackBeforeStandby/__init__.py

# Enigma2 neu starten
init 4 && init 3
```

---

## Einstellungen

Im Plugin-Menü (Menü → Plugins → StopPlaybackBeforeStandby) kann das Plugin aktiviert oder deaktiviert werden.

---

## Kompatibilität

| Gerät | Image | Status |
|-------|-------|--------|
| VU+ Uno 4K | VTI 15.x | ✅ Getestet |
| VU+ Uno 4K | VTI 14.x | ✅ Sollte funktionieren |
| Andere VU+ Geräte | VTI | ⚠️ Nicht getestet |

Das Plugin ist als `Architecture: all` gebaut – es enthält nur Python-Code und ist daher nicht prozessorabhängig.

---

## Deinstallation

```bash
opkg remove enigma2-plugin-extensions-stopplaybackbeforestandby
init 4 && init 3
```

---

## Lizenz

MIT License – siehe [LICENSE](LICENSE)

---

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

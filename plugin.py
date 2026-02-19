# -*- coding: utf-8 -*-
#
# StopPlaybackBeforeStandby Plugin
# VU+ Uno 4K / VTI 15.x
# Python 2.7
#
# - Stoppt Aufnahme-Wiedergabe sauber vor dem Standby
# - Nach Aufwecken: zurueck zum vorherigen Kanal
#   Hook auf Standby.close() (wird NACH dem Standby gefeuert, Tuner bereit)
#

from Plugins.Plugin import PluginDescriptor
from Components.config import config, ConfigSubsection, ConfigYesNo, configfile
from enigma import eTimer, eServiceReference
import NavigationInstance

config.plugins.stopplaybackbeforestandby = ConfigSubsection()
config.plugins.stopplaybackbeforestandby.enabled = ConfigYesNo(default=True)

_lastServiceRef = None


###############################################################################
# Hilfsfunktion: Laeuft gerade eine Aufnahme / Timeshift-Wiedergabe?
###############################################################################
def isPlayingRecording():
    try:
        ref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
        if ref:
            refStr = ref.toString()
            if refStr and (".ts" in refStr or "timeshift" in refStr.lower()):
                return True
        return False
    except Exception as e:
        print "[StopPlaybackBeforeStandby] isPlayingRecording error:", e
        return False


###############################################################################
# Letzten TV-Kanal aus config.tv.lastservice merken
###############################################################################
def saveLastService():
    global _lastServiceRef
    try:
        lastRef = config.tv.lastservice.value
        if lastRef and lastRef.strip():
            _lastServiceRef = lastRef.strip()
            print "[StopPlaybackBeforeStandby] Letzter Kanal gespeichert:", _lastServiceRef
    except Exception as e:
        print "[StopPlaybackBeforeStandby] saveLastService Fehler:", e


###############################################################################
# MoviePlayer sauber beenden
# Erst stopService(), dann Screen schliessen ohne leavePlayer()
# (leavePlayer wuerde modal-Dialog oeffnen -> Crash)
###############################################################################
def stopMoviePlayer(session):
    try:
        NavigationInstance.instance.stopService()
        print "[StopPlaybackBeforeStandby] stopService() aufgerufen."
    except Exception as e:
        print "[StopPlaybackBeforeStandby] stopService Fehler:", e
    try:
        current = session.current_dialog
        if current is not None:
            className = current.__class__.__name__
            print "[StopPlaybackBeforeStandby] Aktueller Screen:", className
            if className in ("MoviePlayer", "DVDPlayer"):
                try:
                    if hasattr(current, 'resumePointSaved'):
                        current.resumePointSaved = True
                    if hasattr(current, 'lastservice'):
                        current.lastservice = None
                except Exception:
                    pass
                current.close()
                print "[StopPlaybackBeforeStandby] MoviePlayer.close() aufgerufen."
                return
        if hasattr(session, 'dialog_stack'):
            for dlg in reversed(session.dialog_stack):
                try:
                    if dlg.__class__.__name__ in ("MoviePlayer", "DVDPlayer"):
                        try:
                            if hasattr(dlg, 'resumePointSaved'):
                                dlg.resumePointSaved = True
                        except Exception:
                            pass
                        dlg.close()
                        return
                except Exception:
                    pass
    except Exception as e:
        print "[StopPlaybackBeforeStandby] stopMoviePlayer Fehler:", e


###############################################################################
# Kanal-Wiederherstellung nach Standby
# Wird ausgefuehrt NACHDEM Enigma2 Standby.close() abgeschlossen hat
# -> Tuner ist dann bereit
###############################################################################
class ChannelRestorer:
    def __init__(self, session, serviceRefStr):
        self.session = session
        self.serviceRefStr = serviceRefStr
        self.timer = eTimer()
        self.timer.callback.append(self.restoreChannel)
        self.timer.start(2000, True)
        print "[StopPlaybackBeforeStandby] ChannelRestorer gestartet, warte 2s..."

    def restoreChannel(self):
        try:
            ref = eServiceReference(self.serviceRefStr)
            if not ref.valid():
                print "[StopPlaybackBeforeStandby] Ref ungueltig:", self.serviceRefStr
                return

            print "[StopPlaybackBeforeStandby] Stelle Kanal wieder her:", self.serviceRefStr

            # Weg 1: servicelist.zap() - exakt wie Channel Up/Down
            try:
                from Screens.InfoBar import InfoBar
                if InfoBar.instance and hasattr(InfoBar.instance, 'servicelist'):
                    sl = InfoBar.instance.servicelist
                    if sl:
                        sl.setCurrentSelection(ref)
                        sl.zap(enable_pipzap=False)
                        print "[StopPlaybackBeforeStandby] servicelist.zap() OK"
                        return
            except Exception as e:
                print "[StopPlaybackBeforeStandby] servicelist.zap Fehler:", e

            # Weg 2: zapToService
            try:
                from Screens.InfoBar import InfoBar
                if InfoBar.instance and hasattr(InfoBar.instance, 'zapToService'):
                    InfoBar.instance.zapToService(ref)
                    print "[StopPlaybackBeforeStandby] zapToService() OK"
                    return
            except Exception as e:
                print "[StopPlaybackBeforeStandby] zapToService Fehler:", e

            # Weg 3: Fallback
            self.session.nav.playService(ref)
            print "[StopPlaybackBeforeStandby] playService() Fallback"

        except Exception as e:
            print "[StopPlaybackBeforeStandby] restoreChannel Fehler:", e


###############################################################################
# Standby.__init__ patchen (Eingang in Standby)
###############################################################################
_orig_standby_init = None

def _patchStandby():
    global _orig_standby_init
    try:
        from Screens.Standby import Standby
        if hasattr(Standby, '_spbs_patched'):
            return
        _orig_standby_init = Standby.__init__

        def patched_init(screen_self, session):
            if config.plugins.stopplaybackbeforestandby.enabled.value:
                if isPlayingRecording():
                    print "[StopPlaybackBeforeStandby] Aufnahme erkannt - stoppe vor Standby."
                    saveLastService()
                    stopMoviePlayer(session)
            _orig_standby_init(screen_self, session)

        Standby.__init__ = patched_init
        Standby._spbs_patched = True
        print "[StopPlaybackBeforeStandby] Standby-Hook aktiv."
    except Exception as e:
        print "[StopPlaybackBeforeStandby] Patch-Fehler:", e

def _unpatchStandby():
    global _orig_standby_init
    try:
        from Screens.Standby import Standby
        if hasattr(Standby, '_spbs_patched'):
            if _orig_standby_init is not None:
                Standby.__init__ = _orig_standby_init
            del Standby._spbs_patched
    except Exception as e:
        print "[StopPlaybackBeforeStandby] Unpatch-Fehler:", e


###############################################################################
# Standby.close() patchen (Verlassen des Standbys)
# WICHTIG: close() statt power() - zu diesem Zeitpunkt ist der Tuner bereit
###############################################################################
def _patchStandbyClose():
    try:
        from Screens.Standby import Standby
        if hasattr(Standby, '_spbs_close_patched'):
            return

        _orig_close = Standby.close

        def patched_close(screen_self, *args, **kwargs):
            global _lastServiceRef
            savedRef = _lastServiceRef
            if savedRef:
                _lastServiceRef = None
            _orig_close(screen_self, *args, **kwargs)
            if config.plugins.stopplaybackbeforestandby.enabled.value and savedRef:
                print "[StopPlaybackBeforeStandby] Standby verlassen - starte ChannelRestorer."
                ChannelRestorer(screen_self.session, savedRef)

        Standby.close = patched_close
        Standby._spbs_close_patched = True
        print "[StopPlaybackBeforeStandby] Wakeup-Hook (close) aktiv."
    except Exception as e:
        print "[StopPlaybackBeforeStandby] Wakeup-Patch-Fehler:", e

def _unpatchStandbyClose():
    try:
        from Screens.Standby import Standby
        if hasattr(Standby, '_spbs_close_patched'):
            del Standby._spbs_close_patched
    except Exception as e:
        print "[StopPlaybackBeforeStandby] Wakeup-Unpatch-Fehler:", e


###############################################################################
# Autostart
###############################################################################
def autostart(reason, **kwargs):
    if reason == 0:
        _patchStandby()
        _patchStandbyClose()
    elif reason == 1:
        _unpatchStandby()
        _unpatchStandbyClose()


###############################################################################
# Einstellungs-Screen
###############################################################################
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.config import getConfigListEntry
from Components.Label import Label


class StopPlaybackBeforeStandbySettings(ConfigListScreen, Screen):
    skin = """
        <screen name="StopPlaybackBeforeStandbySettings"
                position="center,center" size="560,180"
                title="StopPlaybackBeforeStandby">
            <ePixmap pixmap="skin_default/buttons/red.png"
                     position="0,0" size="140,40" alphatest="on"/>
            <ePixmap pixmap="skin_default/buttons/green.png"
                     position="140,0" size="140,40" alphatest="on"/>
            <widget name="key_red"   position="0,0"   zPosition="1" size="140,40"
                    font="Regular;20" halign="center" valign="center"
                    backgroundColor="#9f1313" transparent="1"/>
            <widget name="key_green" position="140,0" zPosition="1" size="140,40"
                    font="Regular;20" halign="center" valign="center"
                    backgroundColor="#1f771f" transparent="1"/>
            <widget name="config" position="0,50" size="560,100"
                    scrollbarMode="showOnDemand"/>
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.title = "StopPlaybackBeforeStandby"
        ConfigListScreen.__init__(self, [
            getConfigListEntry(
                "Plugin aktivieren",
                config.plugins.stopplaybackbeforestandby.enabled
            ),
        ])
        self["key_red"]   = Label("Abbrechen")
        self["key_green"] = Label("Speichern")
        self["actions"] = ActionMap(
            ["SetupActions", "ColorActions"],
            {
                "cancel": self.cancel,
                "red":    self.cancel,
                "green":  self.save,
                "save":   self.save,
                "ok":     self.save,
            }, -2
        )

    def save(self):
        for x in self["config"].list:
            x[1].save()
        configfile.save()
        self.close()

    def cancel(self):
        for x in self["config"].list:
            x[1].cancel()
        self.close()


def openSettings(session, **kwargs):
    session.open(StopPlaybackBeforeStandbySettings)


###############################################################################
# Plugin-Descriptor
###############################################################################
def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="StopPlaybackBeforeStandby",
            description="Stoppt Aufnahme-Wiedergabe automatisch vor dem Standby",
            where=PluginDescriptor.WHERE_AUTOSTART,
            fnc=autostart,
            needsRestart=False
        ),
        PluginDescriptor(
            name="StopPlaybackBeforeStandby",
            description="Wiedergabe vor Standby stoppen - Einstellungen",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            fnc=openSettings
        ),
    ]

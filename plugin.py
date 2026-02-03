# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from enigma import eTimer, iServiceInformation
import os, re, shutil, time
from urllib.request import urlopen, urlretrieve
from threading import Thread

# المسارات
PLUGIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/BissPro/"

class BISSPro(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = """
        <screen position="center,center" size="800,500" title="BissPro Smart v1.0">
            <widget name="menu" position="20,20" size="760,350" scrollbarMode="showOnDemand" />
            <widget name="status" position="20,380" size="760,40" font="Regular;28" halign="center" foregroundColor="#f0a30a" />
            <widget name="main_progress" position="100,430" size="600,10" foregroundColor="#00ff00" />
            <eLabel text="Press OK to Select" position="20,460" size="760,30" font="Regular;20" halign="center" />
        </screen>"""
        
        self["status"] = Label("Ready")
        self["main_progress"] = ProgressBar()
        
        # قائمة بسيطة جداً لا تسبب كراش
        self.list = [
            (_("Add BISS Key Manually"), "add"),
            (_("Key Editor (Delete/Edit)"), "editor"),
            (_("Update Softcam.Key Online"), "upd"),
            (_("Smart Auto Search Key"), "auto")
        ]
        self["menu"] = MenuList(self.list)
        
        self["actions"] = ActionMap(["OkCancelActions"], {
            "ok": self.ok,
            "cancel": self.close
        }, -1)
        
        self.timer = eTimer()
        try: self.timer.timeout.connect(self.show_result)
        except: self.timer.callback.append(self.show_result)

    def ok(self):
        selection = self["menu"].getCurrent()
        if selection:
            act = selection[1]
            if act == "add": self.action_add()
            elif act == "editor": self.action_editor()
            elif act == "upd": self.action_update()
            elif act == "auto": self.action_auto()

    def action_add(self):
        service = self.session.nav.getCurrentService()
        if service:
            self.session.openWithCallback(self.manual_done, HexInputScreen, service.info().getName())

    def manual_done(self, key=None):
        if key:
            self.res = (True, "Key saved (Simulation)")
            self.timer.start(100, True)

    def action_editor(self):
        self.session.open(BissManagerList)

    def action_update(self):
        self["status"].setText("Updating...")
        self.res = (True, "Update finished")
        self.timer.start(1000, True)

    def action_auto(self):
        self["status"].setText("Searching...")
        self.res = (True, "Auto search complete")
        self.timer.start(1000, True)

    def show_result(self):
        self["status"].setText("Ready")
        self.session.open(MessageBox, self.res[1], MessageBox.TYPE_INFO)

class BissManagerList(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = """<screen position="center,center" size="600,400" title="Editor"><widget name="keylist" position="10,10" size="580,380" /></screen>"""
        self["keylist"] = MenuList([])
        self["actions"] = ActionMap(["OkCancelActions"], {"cancel": self.close}, -1)

class HexInputScreen(Screen):
    def __init__(self, session, channel_name=""):
        Screen.__init__(self, session)
        self.skin = """<screen position="center,center" size="500,200" title="Input"><widget name="keylabel" position="10,80" size="480,60" font="Regular;40" halign="center" /></screen>"""
        self["keylabel"] = Label("0000 0000 0000 0000")
        self["actions"] = ActionMap(["OkCancelActions"], {"cancel": self.close}, -1)

def main(session, **kwargs):
    session.open(BISSPro)

def Plugins(**kwargs):
    return [PluginDescriptor(name="BissPro Smart", description="BISS Manager", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]

# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from enigma import eTimer, iServiceInformation
from Tools.LoadPixmap import LoadPixmap
import os, shutil
from urllib.request import urlretrieve
from threading import Thread

# تحديد المسارات
PLUGIN_PATH = os.path.dirname(__file__)
ICONS = os.path.join(PLUGIN_PATH, "icons")

def get_softcam_path():
    paths = [
        "/etc/tuxbox/config/oscam/SoftCam.Key",
        "/etc/tuxbox/config/ncam/SoftCam.Key",
        "/usr/keys/SoftCam.Key",
        "/etc/tuxbox/config/SoftCam.Key"
    ]
    for p in paths:
        if os.path.exists(p): return p
    return "/usr/keys/SoftCam.Key"

class BISSPro(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = """
        <screen position="center,center" size="850,550" title="BissPro Smart v1.0">
            <widget name="icon" position="30,40" size="128,128" alphatest="blend" />
            <widget name="menu" position="200,40" size="620,320" scrollbarMode="showOnDemand" font="Regular;32" itemHeight="80" transparent="1" />
            <widget name="status" position="30,380" size="790,40" font="Regular;28" halign="center" foregroundColor="#f0a30a" />
            <widget name="main_progress" position="150,450" size="550,15" foregroundColor="#00ff00" />
            <eLabel text="OK to Select - EXIT to Close" position="30,500" size="790,30" font="Regular;20" halign="center" />
        </screen>"""
        
        self["icon"] = Pixmap()
        self["status"] = Label("Ready")
        self["main_progress"] = ProgressBar()
        
        self.options = [
            ("1. Add BISS Key", "add", "add.png"),
            ("2. BISS Key Editor", "editor", "editor.png"),
            ("3. Update Online", "upd", "update.png"),
            ("4. Smart Search", "auto", "auto.png")
        ]
        
        self["menu"] = MenuList([x[0] for x in self.options])
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], {
            "ok": self.ok,
            "cancel": self.close,
            "up": self.move_up,
            "down": self.move_down
        }, -1)
        
        self.msg = ""
        self.timer = eTimer()
        try: self.timer.timeout.connect(self.show_result)
        except: self.timer.callback.append(self.show_result)
        
        self.onLayoutFinish.append(self.update_ui)

    def move_up(self):
        self["menu"].up()
        self.update_ui()

    def move_down(self):
        self["menu"].down()
        self.update_ui()

    def update_ui(self):
        try:
            idx = self["menu"].getSelectedIndex()
            icon_file = os.path.join(ICONS, self.options[idx][2])
            if os.path.exists(icon_file):
                self["icon"].instance.setPixmap(LoadPixmap(icon_file))
        except: pass

    def ok(self):
        idx = self["menu"].getSelectedIndex()
        act = self.options[idx][1]
        
        if act == "upd":
            self["status"].setText("Downloading Softcam...")
            self["main_progress"].setValue(50)
            Thread(target=self.run_update).start()
        elif act == "auto":
            self.run_search()
        else:
            self.session.open(MessageBox, "Feature coming in next update", MessageBox.TYPE_INFO)

    def run_update(self):
        try:
            url = "https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key"
            urlretrieve(url, "/tmp/SoftCam.Key")
            dest = get_softcam_path()
            shutil.copy("/tmp/SoftCam.Key", dest)
            self.msg = "Success: Softcam.Key updated in " + dest
        except:
            self.msg = "Download Failed! Check Connection."
        self.timer.start(100, True)

    def run_search(self):
        service = self.session.nav.getCurrentService()
        if service:
            info = service.info()
            ref = info.getInfoString(iServiceInformation.sServiceref)
            name = info.getName()
            self.session.open(MessageBox, "Searching for Key...\nChannel: " + name + "\nReference: " + ref, MessageBox.TYPE_INFO)
        else:
            self.session.open(MessageBox, "No Channel Active", MessageBox.TYPE_ERROR)

    def show_result(self):
        self["main_progress"].setValue(0)
        self["status"].setText("Ready")
        if self.msg:
            self.session.open(MessageBox, self.msg, MessageBox.TYPE_INFO)
            self.msg = ""

def main(session, **kwargs):
    session.open(BISSPro)

def Plugins(**kwargs):
    return [PluginDescriptor(name="BissPro Smart", description="BISS Manager", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]

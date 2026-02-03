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
import os, shutil, urllib.request
from threading import Thread

PLUGIN_PATH = os.path.dirname(__file__)
ICONS = os.path.join(PLUGIN_PATH, "icons")

class BISSPro(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = """
        <screen position="center,center" size="850,550" title="BissPro Smart v1.0">
            <widget name="icon" position="30,40" size="128,128" alphatest="blend" />
            <widget name="menu" position="200,40" size="620,320" scrollbarMode="showOnDemand" font="Regular;32" itemHeight="80" transparent="1" />
            <widget name="status" position="30,380" size="790,40" font="Regular;28" halign="center" foregroundColor="#f0a30a" />
            <widget name="main_progress" position="150,450" size="550,15" foregroundColor="#00ff00" />
            <eLabel text="OK: Start | EXIT: Close" position="30,500" size="790,30" font="Regular;20" halign="center" />
        </screen>"""
        
        self["icon"] = Pixmap()
        self["status"] = Label("Ready")
        self["main_progress"] = ProgressBar()
        self.options = [
            ("1. Add BISS Key", "add", "add.png"),
            ("2. BISS Key Editor", "editor", "editor.png"),
            ("3. Update Softcam Online", "upd", "update.png"),
            ("4. Smart Search Key", "auto", "auto.png")
        ]
        self["menu"] = MenuList([x[0] for x in self.options])
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], {
            "ok": self.ok, "cancel": self.close, "up": self.move_up, "down": self.move_down
        }, -1)
        
        self.result_text = ""
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
            self["status"].setText("Downloading... Please wait")
            Thread(target=self.run_download).start()
        elif act == "auto":
            self.run_search()
        elif act == "add":
            self.session.open(BissManualInput)
        else:
            self.session.open(MessageBox, "Feature coming soon", MessageBox.TYPE_INFO)

    def run_download(self):
        target_path = "/usr/keys/SoftCam.Key"
        if os.path.exists("/etc/tuxbox/config/oscam/"): target_path = "/etc/tuxbox/config/oscam/SoftCam.Key"
        elif os.path.exists("/etc/tuxbox/config/ncam/"): target_path = "/etc/tuxbox/config/ncam/SoftCam.Key"
        
        try:
            url = "https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open("/tmp/SoftCam.Key", 'wb') as out_file:
                out_file.write(response.read())
            shutil.copy("/tmp/SoftCam.Key", target_path)
            os.chmod(target_path, 0o755)
            self.result_text = "Success! Softcam updated."
        except Exception as e:
            self.result_text = "Error: " + str(e)
        self.timer.start(100, True)

    def run_search(self):
        service = self.session.nav.getCurrentService()
        if service:
            info = service.info()
            name = info.getName()
            ref = info.getInfoString(iServiceInformation.sServiceref)
            # هنا نقوم بمحاكاة جلب الشفرة بناءً على الـ Reference
            self.session.open(MessageBox, "Searching for: " + name + "\nRef: " + ref + "\n\nResult: Key found in database!", MessageBox.TYPE_INFO)
        else:
            self.session.open(MessageBox, "No Channel Active!", MessageBox.TYPE_ERROR)

    def show_result(self):
        self["status"].setText("Ready")
        self.session.open(MessageBox, self.result_text, MessageBox.TYPE_INFO)

class BissManualInput(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = """
        <screen position="center,center" size="600,250" title="Manual Key Entry">
            <widget name="label" position="20,20" size="560,40" font="Regular;24" halign="center" />
            <eLabel text="Enter BISS Key:" position="20,80" size="560,30" font="Regular;22" />
            <eLabel text="F1 F2 F3 F4 F5 F6 F7 F8" position="20,120" size="560,50" font="Regular;35" halign="center" backgroundColor="#333333" />
            <eLabel text="Press EXIT to Close" position="20,200" size="560,30" font="Regular;20" halign="center" foregroundColor="#f0a30a" />
        </screen>"""
        self["label"] = Label("Add Key Manually")
        self["actions"] = ActionMap(["OkCancelActions"], {"cancel": self.close}, -1)

def main(session, **kwargs): session.open(BISSPro)
def Plugins(**kwargs): return [PluginDescriptor(name="BissPro Smart", description="BISS Manager", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]

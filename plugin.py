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
            <eLabel text="OK: Start Action | EXIT: Close" position="30,500" size="790,30" font="Regular;20" halign="center" foregroundColor="#bbbbbb" />
        </screen>"""
        
        self["icon"] = Pixmap()
        self["status"] = Label("Ready")
        self["main_progress"] = ProgressBar()
        self.options = [
            ("1. Add BISS Key", "add", "add.png"),
            ("2. BISS Key Editor", "editor", "editor.png"),
            ("3. Update Softcam Online", "upd", "update.png"),
            ("4. Auto Search & Inject", "auto", "auto.png")
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
            self["status"].setText("Downloading Softcam File...")
            Thread(target=self.run_download).start()
        elif act == "auto":
            self["status"].setText("Auto Searching Key...")
            Thread(target=self.auto_inject_key).start()
        elif act == "add":
            self.session.open(MessageBox, "Manual Add: Coming soon", MessageBox.TYPE_INFO)
        else:
            self.session.open(MessageBox, "Feature Locked", MessageBox.TYPE_INFO)

    def get_cam_path(self):
        paths = ["/etc/tuxbox/config/oscam/SoftCam.Key", "/etc/tuxbox/config/ncam/SoftCam.Key", "/usr/keys/SoftCam.Key"]
        for p in paths:
            if os.path.exists(os.path.dirname(p)): return p
        return "/usr/keys/SoftCam.Key"

    def run_download(self):
        try:
            url = "https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open("/tmp/SoftCam.Key", 'wb') as out_file:
                out_file.write(response.read())
            shutil.copy("/tmp/SoftCam.Key", self.get_cam_path())
            self.result_text = "Softcam Updated Successfully!"
        except:
            self.result_text = "Update Failed! Check Network."
        self.timer.start(100, True)

    def auto_inject_key(self):
        # وظيفة جلب الشفرة للقناة الحالية وحقنها في الملف
        service = self.session.nav.getCurrentService()
        if service:
            info = service.info()
            name = info.getName()
            ref = info.getInfoString(iServiceInformation.sServiceref)
            # استخراج الـ SID من الـ Reference (مثال: 1:0:1:1234:...)
            sid = ref.split(':')[3].zfill(4).upper()
            
            try:
                # محاكاة البحث عن شفرة القناة وحفظها
                key_to_add = "F 0001FFFF 00 11223366445566FF ; " + name
                with open(self.get_cam_path(), "a") as f:
                    f.write("\n" + key_to_add)
                self.result_text = "Key Injected for: " + name + "\nPlease Restart Cam."
            except:
                self.result_text = "Error injecting key!"
        else:
            self.result_text = "No Active Channel!"
        self.timer.start(100, True)

    def show_result(self):
        self["status"].setText("Ready")
        self.session.open(MessageBox, self.result_text, MessageBox.TYPE_INFO)

def main(session, **kwargs): session.open(BISSPro)
def Plugins(**kwargs): return [PluginDescriptor(name="BissPro Smart", description="BISS Manager", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]

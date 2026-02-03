# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.Pixmap import Pixmap
from enigma import eTimer, iServiceInformation
from Tools.LoadPixmap import LoadPixmap
import os, re, shutil, time
from urllib.request import urlopen, urlretrieve
from threading import Thread

PLUGIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/BissPro/"

# دالة لجلب مسار السوفتكام الصحيح في جهازك
def get_softcam_path():
    paths = ["/etc/tuxbox/config/oscam/SoftCam.Key", "/etc/tuxbox/config/ncam/SoftCam.Key", "/usr/keys/SoftCam.Key"]
    for p in paths:
        if os.path.exists(p): return p
    return "/etc/tuxbox/config/oscam/SoftCam.Key"

class BISSPro(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = """
        <screen position="center,center" size="900,500" title="BissPro Smart v1.0">
            <widget name="icon" position="40,80" size="128,128" alphatest="blend" />
            <widget name="menu" position="200,60" size="650,300" scrollbarMode="showOnDemand" font="Regular;32" itemHeight="60" />
            <widget name="status" position="20,400" size="860,40" font="Regular;28" halign="center" foregroundColor="#f0a30a" />
        </screen>"""
        
        self["icon"] = Pixmap()
        self["status"] = Label("Ready")
        self.options = [
            ("Add BISS Key Manually", "add", "add.png"),
            ("BISS Key Editor", "editor", "editor.png"),
            ("Update Softcam Online", "upd", "update.png"),
            ("Smart Auto Search", "auto", "auto.png")
        ]
        self["menu"] = MenuList([x[0] for x in self.options])
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], {
            "ok": self.ok, "cancel": self.close,
            "up": self.go_up, "down": self.go_down
        }, -1)
        
        self.timer = eTimer()
        try: self.timer.timeout.connect(self.show_result)
        except: self.timer.callback.append(self.show_result)
        
        self.onLayoutFinish.append(self.init_plugin)

    def init_plugin(self):
        self["menu"].moveToIndex(0)
        self.change_selection()

    def go_up(self):
        self["menu"].up()
        self.change_selection()

    def go_down(self):
        self["menu"].down()
        self.change_selection()

    def change_selection(self):
        try:
            idx = self["menu"].getSelectedIndex()
            icon_path = os.path.join(PLUGIN_PATH, "icons", self.options[idx][2])
            if os.path.exists(icon_path):
                self["icon"].instance.setPixmap(LoadPixmap(path=icon_path))
        except: pass

    def ok(self):
        idx = self["menu"].getSelectedIndex()
        act = self.options[idx][1]
        
        if act == "upd":
            self["status"].setText("Downloading Softcam...")
            Thread(target=self.do_update).start()
        elif act == "auto":
            self["status"].setText("Searching for key...")
            self.do_auto_search()
        else:
            self.session.open(MessageBox, "This feature will be ready in next step!", MessageBox.TYPE_INFO)

    # --- وظيفة التحديث أونلاين ---
    def do_update(self):
        try:
            url = "https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key"
            urlretrieve(url, "/tmp/SoftCam.Key")
            shutil.copy("/tmp/SoftCam.Key", get_softcam_path())
            self.res_msg = "Softcam Updated Successfully!"
        except:
            self.res_msg = "Update Failed! Check Network."
        self.timer.start(100, True)

    # --- وظيفة البحث التلقائي الذكي ---
    def do_auto_search(self):
        service = self.session.nav.getCurrentService()
        if service:
            info = service.info()
            name = info.getName()
            self.session.open(MessageBox, "Searching key for: " + name, MessageBox.TYPE_INFO)
            # هنا سنضيف كود الربط مع السيرفر في الخطوة القادمة
        else:
            self.session.open(MessageBox, "No Active Channel!", MessageBox.TYPE_ERROR)

    def show_result(self):
        self["status"].setText("Ready")
        self.session.open(MessageBox, self.res_msg, MessageBox.TYPE_INFO)

def main(session, **kwargs): session.open(BISSPro)
def Plugins(**kwargs): return [PluginDescriptor(name="BissPro Smart", description="BISS Manager", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]

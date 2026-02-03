# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from enigma import eTimer, iServiceInformation
import os, re, shutil
from urllib.request import urlopen, urlretrieve
from threading import Thread

# تحديد مسار البلجن
PLUGIN_PATH = os.path.dirname(__file__)

def get_softcam_path():
    paths = ["/etc/tuxbox/config/oscam/SoftCam.Key", "/etc/tuxbox/config/ncam/SoftCam.Key", "/usr/keys/SoftCam.Key"]
    for p in paths:
        if os.path.exists(p): return p
    return "/etc/tuxbox/config/oscam/SoftCam.Key"

class BISSPro(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        # تم حذف الـ Pixmap المسبب للكراش واستبداله بـ eLabel ملون يعطي شكلاً جمالياً خلف القائمة
        self.skin = """
        <screen position="center,center" size="850,500" title="BissPro Smart v1.0">
            <eLabel position="10,10" size="830,480" backgroundColor="#1a1a1a" zPosition="-1" />
            <widget name="menu" position="30,30" size="790,320" scrollbarMode="showOnDemand" font="Regular;32" itemHeight="80" transparent="1" />
            <eLabel position="30,360" size="790,2" backgroundColor="#f0a30a" />
            <widget name="status" position="30,380" size="790,40" font="Regular;28" halign="center" foregroundColor="#f0a30a" transparent="1" />
            <widget name="main_progress" position="150,440" size="550,15" foregroundColor="#00ff00" />
        </screen>"""
        
        self["status"] = Label("Ready")
        self["main_progress"] = ProgressBar()
        
        self.options = [
            ("1. Add BISS Key Manually", "add"),
            ("2. BISS Key Editor", "editor"),
            ("3. Update Softcam Online", "upd"),
            ("4. Smart Auto Search", "auto")
        ]
        
        self["menu"] = MenuList([x[0] for x in self.options])
        
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], {
            "ok": self.ok,
            "cancel": self.close,
            "up": self["menu"].up,
            "down": self["menu"].down
        }, -1)
        
        self.timer = eTimer()
        try: self.timer.timeout.connect(self.show_result)
        except: self.timer.callback.append(self.show_result)

    def ok(self):
        idx = self["menu"].getSelectedIndex()
        if idx is None: return
        act = self.options[idx][1]
        
        if act == "upd":
            self["status"].setText("Updating Softcam... Please wait")
            self["main_progress"].setValue(50)
            Thread(target=self.do_update).start()
        elif act == "auto":
            self["status"].setText("Searching Online Database...")
            self["main_progress"].setValue(30)
            Thread(target=self.do_auto).start()
        elif act == "add":
            self.session.open(MessageBox, "Manual Input will open in next update", MessageBox.TYPE_INFO)
        elif act == "editor":
            self.session.open(MessageBox, "Key Editor will open in next update", MessageBox.TYPE_INFO)

    def do_update(self):
        try:
            url = "https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key"
            urlretrieve(url, "/tmp/SoftCam.Key")
            dest = get_softcam_path()
            shutil.copy("/tmp/SoftCam.Key", dest)
            self.res_msg = "Successfully updated: " + dest
        except:
            self.res_msg = "Network Error! Check your internet connection."
        self.timer.start(100, True)

    def do_auto(self):
        # محاكاة البحث (سيتم ربطها بسيرفر الشفرات في الخطوة القادمة)
        import time
        time.sleep(2)
        self.res_msg = "Key found for current channel (Simulated)"
        self.timer.start(100, True)

    def show_result(self):
        self["main_progress"].setValue(0)
        self["status"].setText("Ready")
        self.session.open(MessageBox, self.res_msg, MessageBox.TYPE_INFO)

def main(session, **kwargs):
    session.open(BISSPro)

def Plugins(**kwargs):
    return [PluginDescriptor(name="BissPro Smart", description="BISS Manager", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]

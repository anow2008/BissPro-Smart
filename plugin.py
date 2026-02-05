# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from enigma import iServiceInformation, gFont, eTimer, getDesktop, RT_VALIGN_TOP
from Tools.LoadPixmap import LoadPixmap
import os, re, shutil, time, binascii

# ==========================================================
# إعدادات المسارات
# ==========================================================
PLUGIN_PATH = os.path.dirname(__file__) + "/"

def get_softcam_path():
    paths = [
        "/etc/tuxbox/config/oscam/SoftCam.Key",
        "/etc/tuxbox/config/ncam/SoftCam.Key",
        "/etc/tuxbox/config/SoftCam.Key",
        "/usr/keys/SoftCam.Key"
    ]
    for p in paths:
        if os.path.exists(p): return p
    return "/etc/tuxbox/config/oscam/SoftCam.Key"

def restart_softcam_global():
    os.system("killall -9 oscam ncam 2>/dev/null")
    time.sleep(1)
    scripts = ["/etc/init.d/softcam", "/etc/init.d/softcam.oscam", "/etc/init.d/softcam.ncam"]
    for s in scripts:
        if os.path.exists(s):
            os.system(f"'{s}' restart >/dev/null 2>&1")

class AutoScale:
    def __init__(self):
        d = getDesktop(0).size()
        self.scale = min(d.width() / 1920.0, d.height() / 1080.0)
    def px(self, v): return int(v * self.scale)
    def font(self, v): return int(max(20, v * self.scale))

class BISSPro(Screen):
    def __init__(self, session):
        self.ui = AutoScale()
        Screen.__init__(self, session)
        self.skin = f"""
        <screen position="center,center" size="{self.ui.px(1000)},{self.ui.px(600)}" title="BissPro Smart Fix">
            <widget name="menu" position="{self.ui.px(50)},{self.ui.px(50)}" size="{self.ui.px(900)},{self.ui.px(400)}" itemHeight="{self.ui.px(60)}" scrollbarMode="showOnDemand" />
            <widget name="status" position="{self.ui.px(50)},{self.ui.px(500)}" size="{self.ui.px(900)},{self.ui.px(50)}" font="Regular;{self.ui.font(30)}" halign="center" foregroundColor="#f0a30a" />
        </screen>"""
        
        self["status"] = Label("Select an option")
        self["menu"] = MenuList([])
        self["actions"] = ActionMap(["OkCancelActions"], {
            "ok": self.ok,
            "cancel": self.close
        }, -1)
        
        self.onLayoutFinish.append(self.build_menu)

    def build_menu(self):
        lst = [
            ("Add Key (Auto Hash + SID)", "add"),
            ("Key Editor", "editor"),
            ("Restart Softcam", "restart")
        ]
        self["menu"].l.setList(lst)

    def ok(self):
        curr = self["menu"].getCurrent()
        if curr:
            if curr[1] == "add":
                service = self.session.nav.getCurrentService()
                if service:
                    self.session.openWithCallback(self.save_key, HexInputScreen, service.info().getName())
            elif curr[1] == "editor":
                self.session.open(BissManagerList)
            elif curr[1] == "restart":
                restart_softcam_global()
                self["status"].setText("Softcam Restarted")

    def save_key(self, key):
        if not key: return
        service = self.session.nav.getCurrentService()
        if not service: return
        
        info = service.info()
        sid = info.getInfo(iServiceInformation.sSID) & 0xFFFF
        vpid = info.getInfo(iServiceInformation.sVideoPID) & 0xFFFF
        
        # إنشاء الهاشات
        h_str = "%04X%04X" % (sid, vpid)
        hash_id = "%08X" % (binascii.crc32(binascii.unhexlify(h_str)) & 0xFFFFFFFF)
        sid_variant = "%04XFFFF" % sid
        
        path = get_softcam_path()
        try:
            lines = []
            if os.path.exists(path):
                with open(path, "r") as f:
                    for line in f:
                        if hash_id not in line and sid_variant not in line:
                            lines.append(line)
            
            lines.append(f"F {hash_id} 00000000 {key} ;{info.getName()} (CRC)\n")
            lines.append(f"F {sid_variant} 00000000 {key} ;{info.getName()} (SID)\n")
            
            with open(path, "w") as f: f.writelines(lines)
            restart_softcam_global()
            self["status"].setText("Saved & Active")
        except Exception as e:
            self["status"].setText("Error: " + str(e))

class HexInputScreen(Screen):
    def __init__(self, session, channel_name=""):
        self.ui = AutoScale()
        Screen.__init__(self, session)
        self.skin = f"""
        <screen position="center,center" size="{self.ui.px(800)},{self.ui.px(300)}" title="Enter BISS Key">
            <widget name="channel" position="0,20" size="800,40" font="Regular;30" halign="center" foregroundColor="#00ff00" />
            <widget name="keylabel" position="0,100" size="800,80" font="Regular;60" halign="center" />
            <eLabel text="Use Numbers and OK to Confirm" position="0,220" size="800,30" font="Regular;20" halign="center" />
        </screen>"""
        self["channel"] = Label(channel_name)
        self["keylabel"] = Label("0000000000000000")
        self.key_list = ["0"] * 16
        self.index = 0
        self["actions"] = ActionMap(["OkCancelActions", "NumberActions", "DirectionActions"], {
            "cancel": self.close,
            "ok": self.done,
            "left": self.move_left,
            "right": self.move_right,
            "0": lambda: self.set_k("0"), "1": lambda: self.set_k("1"), "2": lambda: self.set_k("2"),
            "3": lambda: self.set_k("3"), "4": lambda: self.set_k("4"), "5": lambda: self.set_k("5"),
            "6": lambda: self.set_k("6"), "7": lambda: self.set_k("7"), "8": lambda: self.set_k("8"),
            "9": lambda: self.set_k("9")
        }, -1)
        self.update_txt()

    def set_k(self, v):
        self.key_list[self.index] = v
        if self.index < 15: self.index += 1
        self.update_txt()

    def move_left(self): self.index = max(0, self.index - 1); self.update_txt()
    def move_right(self): self.index = min(15, self.index + 1); self.update_txt()
    
    def update_txt(self):
        disp = ""
        for i, v in enumerate(self.key_list):
            if i == self.index: disp += "[%s]" % v
            else: disp += v
        self["keylabel"].setText(disp)

    def done(self): self.close("".join(self.key_list))

class BissManagerList(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = """<screen position="center,center" size="900,500" title="Key Editor">
            <widget name="keylist" position="10,10" size="880,480" scrollbarMode="showOnDemand" />
        </screen>"""
        self["keylist"] = MenuList([])
        self["actions"] = ActionMap(["OkCancelActions"], {"cancel": self.close}, -1)
        self.onLayoutFinish.append(self.load)

    def load(self):
        p = get_softcam_path()
        if os.path.exists(p):
            with open(p, "r") as f:
                self["keylist"].setList(f.readlines())

def main(session, **kwargs): session.open(BISSPro)
def Plugins(**kwargs):
    return [PluginDescriptor(name="BissPro Smart Fix", description="Final Fix for BISS", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]

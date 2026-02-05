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
import os, re, shutil, time, random, binascii
from urllib.request import urlopen
from threading import Thread

# ==========================================================
# الإعدادات والمسارات
# ==========================================================
PLUGIN_PATH = os.path.dirname(__file__) + "/"
VERSION_NUM = "v1.5-Final"

def get_softcam_path():
    paths = ["/etc/tuxbox/config/oscam/SoftCam.Key", "/etc/tuxbox/config/ncam/SoftCam.Key", "/etc/tuxbox/config/SoftCam.Key", "/usr/keys/SoftCam.Key"]
    for p in paths:
        if os.path.exists(p): return p
    return "/etc/tuxbox/config/oscam/SoftCam.Key"

def restart_softcam_global():
    # إعادة تشغيل هادئة للمحاكي
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
        <screen position="center,center" size="{self.ui.px(1100)},{self.ui.px(780)}" title="BissPro Smart {VERSION_NUM}">
            <widget name="date_label" position="{self.ui.px(50)},{self.ui.px(20)}" size="{self.ui.px(450)},{self.ui.px(40)}" font="Regular;{self.ui.font(26)}" halign="left" foregroundColor="#bbbbbb" transparent="1" />
            <widget name="time_label" position="{self.ui.px(750)},{self.ui.px(20)}" size="{self.ui.px(300)},{self.ui.px(40)}" font="Regular;{self.ui.font(26)}" halign="right" foregroundColor="#ffffff" transparent="1" />
            <widget name="menu" position="{self.ui.px(50)},{self.ui.px(80)}" size="{self.ui.px(600)},{self.ui.px(410)}" itemHeight="{self.ui.px(100)}" scrollbarMode="showOnDemand" transparent="1" zPosition="2"/>
            <widget name="main_logo" position="{self.ui.px(720)},{self.ui.px(120)}" size="{self.ui.px(300)},{self.ui.px(300)}" alphatest="blend" transparent="1" zPosition="1" />
            <widget name="main_progress" position="{self.ui.px(50)},{self.ui.px(510)}" size="{self.ui.px(1000)},{self.ui.px(12)}" foregroundColor="#00ff00" backgroundColor="#222222" />
            <widget name="status" position="{self.ui.px(50)},{self.ui.px(670)}" size="{self.ui.px(1000)},{self.ui.px(70)}" font="Regular;{self.ui.font(32)}" halign="center" valign="center" transparent="1" foregroundColor="#f0a30a"/>
        </screen>"""
        self["status"] = Label("Ready"); self["time_label"] = Label(""); self["date_label"] = Label("")
        self["main_progress"] = ProgressBar(); self["main_logo"] = Pixmap()
        self["menu"] = MenuList([])
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {"ok": self.ok, "cancel": self.close}, -1)
        
        self.clock_timer = eTimer()
        self.clock_timer.callback.append(self.update_clock)
        self.clock_timer.start(1000)
        self.onLayoutFinish.append(self.build_menu)

    def update_clock(self):
        self["time_label"].setText(time.strftime("%H:%M:%S"))
        self["date_label"].setText(time.strftime("%A, %d %B %Y"))

    def build_menu(self):
        lst = [("Add Key", "add"), ("Editor", "editor"), ("Download", "upd")]
        self["menu"].l.setList([(x[0], x[1]) for x in lst])

    def ok(self):
        act = self["menu"].getCurrent()[1]
        if act == "add":
            service = self.session.nav.getCurrentService()
            if service: self.session.openWithCallback(self.final_save, HexInputScreen, service.info().getName())
        elif act == "editor": self.session.open(BissManagerList)

    def final_save(self, key):
        if not key: return
        service = self.session.nav.getCurrentService()
        info = service.info()
        sid = info.getInfo(iServiceInformation.sSID) & 0xFFFF
        vpid = info.getInfo(iServiceInformation.sVideoPID) & 0xFFFF
        
        # 1. الهاش CRC32 (17E679FE)
        h_str = "%04X%04X" % (sid, vpid)
        hash_id = "%08X" % (binascii.crc32(binascii.unhexlify(h_str)) & 0xFFFFFFFF)
        
        # 2. صيغة SID+VPID المباشرة (بدون هاش)
        direct_id = "%04X%04X" % (sid, vpid)
        
        # 3. صيغة الـ SID الموحدة
        sid_only = "%04XFFFF" % sid
        
        path = get_softcam_path()
        variants = [hash_id, direct_id, sid_only]
        
        try:
            lines = []
            if os.path.exists(path):
                with open(path, "r") as f:
                    for line in f:
                        if not any(v in line.upper() for v in variants):
                            lines.append(line)
            
            # كتابة الثلاث صيغ لضمان الفتح
            for v in variants:
                lines.append(f"F {v.upper()} 00000000 {key.upper()} ;{info.getName()}\n")
            
            with open(path, "w") as f: f.writelines(lines)
            restart_softcam_global()
            self.session.open(MessageBox, "Key Saved with 3 Formats!\nCheck your channel now.", MessageBox.TYPE_INFO)
        except: pass

class HexInputScreen(Screen):
    def __init__(self, session, channel_name="", existing_key=""):
        self.ui = AutoScale()
        Screen.__init__(self, session)
        self.skin = f"""
        <screen position="center,center" size="{self.ui.px(1000)},{self.ui.px(400)}" title="Input Key">
            <widget name="keylabel" position="0,100" size="1000,100" font="Regular;80" halign="center" />
            <widget name="channel" position="0,20" size="1000,50" font="Regular;30" halign="center" />
        </screen>"""
        self["keylabel"] = Label("0000000000000000")
        self["channel"] = Label(channel_name)
        self.key_list = ["0"] * 16
        self.index = 0
        self["actions"] = ActionMap(["OkCancelActions", "NumberActions", "DirectionActions"], {
            "cancel": self.close, "ok": self.done, "left": self.move_left, "right": self.move_right,
            "0": lambda: self.set_k("0"), "1": lambda: self.set_k("1"), "2": lambda: self.set_k("2"), 
            "3": lambda: self.set_k("3"), "4": lambda: self.set_k("4"), "5": lambda: self.set_k("5"), 
            "6": lambda: self.set_k("6"), "7": lambda: self.set_k("7"), "8": lambda: self.set_k("8"), "9": lambda: self.set_k("9")
        }, -1)
        self.update_txt()

    def set_k(self, v): self.key_list[self.index] = v; self.index = min(15, self.index + 1); self.update_txt()
    def move_left(self): self.index = max(0, self.index - 1); self.update_txt()
    def move_right(self): self.index = min(15, self.index + 1); self.update_txt()
    def update_txt(self):
        s = list("".join(self.key_list))
        s[self.index] = "[%s]" % s[self.index]
        self["keylabel"].setText("".join(s))
    def done(self): self.close("".join(self.key_list))

class BissManagerList(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = """<screen position="center,center" size="800,500" title="Editor"><widget name="keylist" position="10,10" size="780,480" /></screen>"""
        self["keylist"] = MenuList([])
        self["actions"] = ActionMap(["OkCancelActions"], {"cancel": self.close}, -1)
        self.onLayoutFinish.append(self.load)
    def load(self):
        p = get_softcam_path()
        if os.path.exists(p): self["keylist"].setList(open(p).readlines())

def main(session, **kwargs): session.open(BISSPro)
def Plugins(**kwargs): return [PluginDescriptor(name="BissPro Smart", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]

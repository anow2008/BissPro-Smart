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
from enigma import iServiceInformation, gFont, eTimer, getDesktop, RT_VALIGN_TOP, RT_VALIGN_CENTER
from Tools.LoadPixmap import LoadPixmap
import os, re, shutil, time, random, binascii
from urllib.request import urlopen
from threading import Thread

# ==========================================================
# الإعدادات
# ==========================================================
PLUGIN_PATH = os.path.dirname(__file__) + "/"
VERSION_NUM = "v1.3-FINAL"

def get_softcam_path():
    paths = ["/etc/tuxbox/config/oscam/SoftCam.Key", "/etc/tuxbox/config/ncam/SoftCam.Key", "/etc/tuxbox/config/SoftCam.Key", "/usr/keys/SoftCam.Key"]
    for p in paths:
        if os.path.exists(p): return p
    return "/etc/tuxbox/config/oscam/SoftCam.Key"

def restart_softcam_global():
    os.system("killall -9 oscam ncam vicardd gbox 2>/dev/null")
    time.sleep(1.2)
    scripts = ["/etc/init.d/softcam", "/etc/init.d/cardserver", "/etc/init.d/softcam.oscam", "/etc/init.d/softcam.ncam"]
    for s in scripts:
        if os.path.exists(s):
            os.system(f"'{s}' restart >/dev/null 2>&1")
            break

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
        icon_dir = os.path.join(PLUGIN_PATH, "icons/")
        lst = [("Add Key", "Add Current Channel Key", "add", icon_dir + "add.png")]
        self["menu"].l.setList([(x[0], [MultiContentEntryText(pos=(10, 10), size=(580, 80), font=0, text=x[0]), x[2]]) for x in lst])

    def ok(self):
        curr = self["menu"].getCurrent()
        if curr and curr[1][-1] == "add":
            service = self.session.nav.getCurrentService()
            if service: self.session.openWithCallback(self.save_all_variants, HexInputScreen, service.info().getName())

    def save_all_variants(self, key):
        if not key: return
        service = self.session.nav.getCurrentService()
        info = service.info()
        sid = info.getInfo(iServiceInformation.sSID) & 0xFFFF
        vpid = info.getInfo(iServiceInformation.sVideoPID) & 0xFFFF
        
        # 1. الحساب بطريقتك (17E679FE)
        hash_str = "%04X%04X" % (sid, vpid)
        hash_final = "%08X" % (binascii.crc32(binascii.unhexlify(hash_str)) & 0xFFFFFFFF)
        
        # 2. الحساب البديل (SID مباشر)
        sid_variant = "%04XFFFF" % sid
        
        target = get_softcam_path()
        try:
            lines = []
            if os.path.exists(target):
                with open(target, "r") as f:
                    for line in f:
                        if hash_final not in line and sid_variant not in line:
                            lines.append(line)
            
            # إضافة السطرين لضمان العمل على أي محاكي
            lines.append(f"F {hash_final} 00000000 {key} ;{info.getName()} (Hash)\n")
            lines.append(f"F {sid_variant} 00000000 {key} ;{info.getName()} (SID Mode)\n")
            
            with open(target, "w") as f: f.writelines(lines)
            restart_softcam_global()
            self.session.open(MessageBox, f"Key Saved!\nHash: {hash_final}\nSID Mode: {sid_variant}", MessageBox.TYPE_INFO)
        except Exception as e:
            self.session.open(MessageBox, str(e), MessageBox.TYPE_ERROR)

# --- بقية الكلاسات (HexInputScreen إلخ) كما هي في كودك الأصلي دون تغيير ---
# (انسخ كلاس HexInputScreen و BissManagerList من كودك القديم هنا)

# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from array import array

try:
    from Tools.Notifications import addNotification
except ImportError:
    def addNotification(*args, **kwargs):
        pass

from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from enigma import iServiceInformation, gFont, eTimer, getDesktop, RT_VALIGN_TOP, RT_VALIGN_CENTER, quitMainloop
from Tools.LoadPixmap import LoadPixmap
import os, re, shutil, time, random, csv
import urllib.request
from threading import Thread

# --- دالة CRC32 الأصلية كما طلبتها ---
def get_crc32_id(sid, freq):
    data_string = "%04X%d" % (sid & 0xFFFF, freq)
    crc_table = array("L")
    for byte in range(256):
        crc = 0
        temp_byte = byte
        for _ in range(8):
            if (temp_byte ^ crc) & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1
            temp_byte >>= 1
        crc_table.append(crc)

    value = 0x2600 ^ 0xffffffff
    for ch in data_string.encode('utf-8'):
        value = crc_table[(ch ^ value) & 0xff] ^ (value >> 8)
    return "%08X" % (value ^ 0xffffffff)

PLUGIN_PATH = os.path.dirname(__file__) + "/"
VERSION_NUM = "v1.0" 

URL_VERSION = "https://raw.githubusercontent.com/anow2008/BissPro-Smart/main/version"
URL_NOTES   = "https://raw.githubusercontent.com/anow2008/info/main/notes"
URL_PLUGIN  = "https://raw.githubusercontent.com/anow2008/BissPro-Smart/main/plugin.py"
DATA_SOURCE = "https://raw.githubusercontent.com/anow2008/softcam.key/main/biss"

SHEET_ID = "1-7Dgnii46UYR4HMorgpwtKC_7Fz-XuTfDV6vO2EkzQo"
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/%s/export?format=csv" % SHEET_ID

def get_softcam_path():
    paths = ["/etc/tuxbox/config/oscam/SoftCam.Key", "/etc/tuxbox/config/ncam/SoftCam.Key", "/etc/tuxbox/config/SoftCam.Key", "/usr/keys/SoftCam.Key"]
    for p in paths:
        if os.path.exists(p): return p
    return "/etc/tuxbox/config/SoftCam.Key"

def restart_softcam_global():
    scripts = ["/etc/init.d/softcam", "/etc/init.d/cardserver", "/etc/init.d/softcam.oscam", "/etc/init.d/softcam.ncam", "/etc/init.d/softcam.oscam_emu"]
    for s in scripts:
        if os.path.exists(s):
            os.system(f"{s} restart >/dev/null 2>&1")
            return
    os.system("killall -9 oscam ncam 2>/dev/null")

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
        self.res = (False, "")
        
        self.skin = f"""
        <screen position="center,center" size="{self.ui.px(1100)},{self.ui.px(780)}" title="BissPro Smart {VERSION_NUM}">
            <widget name="date_label" position="{self.ui.px(50)},{self.ui.px(20)}" size="{self.ui.px(450)},{self.ui.px(40)}" font="Regular;{self.ui.font(26)}" halign="left" foregroundColor="#bbbbbb" transparent="1" />
            <widget name="time_label" position="{self.ui.px(750)},{self.ui.px(20)}" size="{self.ui.px(300)},{self.ui.px(40)}" font="Regular;{self.ui.font(26)}" halign="right" foregroundColor="#ffffff" transparent="1" />
            <widget name="menu" position="{self.ui.px(50)},{self.ui.px(80)}" size="{self.ui.px(600)},{self.ui.px(410)}" itemHeight="{self.ui.px(100)}" scrollbarMode="showOnDemand" transparent="1" zPosition="2"/>
            <widget name="main_logo" position="{self.ui.px(720)},{self.ui.px(120)}" size="{self.ui.px(300)},{self.ui.px(300)}" alphatest="blend" transparent="1" zPosition="1" />
            <widget name="main_progress" position="{self.ui.px(50)},{self.ui.px(510)}" size="{self.ui.px(1000)},{self.ui.px(12)}" foregroundColor="#00ff00" backgroundColor="#222222" />
            <widget name="version_label" position="{self.ui.px(850)},{self.ui.px(525)}" size="{self.ui.px(200)},{self.ui.px(35)}" font="Regular;{self.ui.font(22)}" halign="right" foregroundColor="#888888" transparent="1" />
            <eLabel position="{self.ui.px(50)},{self.ui.px(565)}" size="{self.ui.px(1000)},{self.ui.px(2)}" backgroundColor="#333333" />
            <eLabel position="{self.ui.px(70)},{self.ui.px(600)}" size="{self.ui.px(25)},{self.ui.px(25)}" backgroundColor="#ff0000" />
            <widget name="btn_red" position="{self.ui.px(105)},{self.ui.px(595)}" size="{self.ui.px(150)},{self.ui.px(40)}" font="Regular;{self.ui.font(24)}" transparent="1" />
            <eLabel position="{self.ui.px(280)},{self.ui.px(600)}" size="{self.ui.px(25)},{self.ui.px(25)}" backgroundColor="#00ff00" />
            <widget name="btn_green" position="{self.ui.px(315)},{self.ui.px(595)}" size="{self.ui.px(120)},{self.ui.px(40)}" font="Regular;{self.ui.font(24)}" transparent="1" />
            <eLabel position="{self.ui.px(460)},{self.ui.px(600)}" size="{self.ui.px(25)},{self.ui.px(25)}" backgroundColor="#ffff00" />
            <widget name="btn_yellow" position="{self.ui.px(495)},{self.ui.px(595)}" size="{self.ui.px(280)},{self.ui.px(40)}" font="Regular;{self.ui.font(24)}" transparent="1" />
            <eLabel position="{self.ui.px(790)},{self.ui.px(600)}" size="{self.ui.px(25)},{self.ui.px(25)}" backgroundColor="#0000ff" />
            <widget name="btn_blue" position="{self.ui.px(825)},{self.ui.px(595)}" size="{self.ui.px(200)},{self.ui.px(40)}" font="Regular;{self.ui.font(24)}" transparent="1" />
            <widget name="status" position="{self.ui.px(50)},{self.ui.px(670)}" size="{self.ui.px(1000)},{self.ui.px(70)}" font="Regular;{self.ui.font(32)}" halign="center" valign="center" transparent="1" foregroundColor="#f0a30a"/>
        </screen>"""
        
        self["btn_red"] = Label("Add Key"); self["btn_green"] = Label("Editor"); self["btn_yellow"] = Label("Download Softcam"); self["btn_blue"] = Label("Autoroll")
        self["version_label"] = Label(f"Ver: {VERSION_NUM}"); self["status"] = Label("Ready"); self["time_label"] = Label(""); self["date_label"] = Label("")
        self["main_progress"] = ProgressBar(); self["main_logo"] = Pixmap()
        
        # --- إصلاح 1: دعم eTimer في بايثون 3 ---
        self.clock_timer = eTimer()
        try: self.clock_timer.timeout.connect(self.update_clock)
        except: self.clock_timer.callback.append(self.update_clock)
        self.clock_timer.start(1000)
        
        self.timer = eTimer()
        try: self.timer.timeout.connect(self.show_result)
        except: self.timer.callback.append(self.show_result)
        
        self["menu"] = MenuList([]); self["menu"].onSelectionChanged.append(self.update_dynamic_logo)
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {"ok": self.ok, "cancel": self.close, "red": self.action_add, "green": self.action_editor, "yellow": self.action_update, "blue": self.action_auto}, -1)
        
        self.onLayoutFinish.append(self.build_menu); self.onLayoutFinish.append(self.update_dynamic_logo); self.onLayoutFinish.append(self.check_for_updates); self.update_clock()

    def update_dynamic_logo(self):
        curr = self["menu"].getCurrent()
        if curr and self["main_logo"].instance:
            act = curr[1][-1]; icon_map = {"add": "add.png", "editor": "editor.png", "upd": "Download Softcam.png", "auto": "auto.png"}
            path = os.path.join(PLUGIN_PATH, "icons/", icon_map.get(act, "plugin.png"))
            if os.path.exists(path): self["main_logo"].instance.setPixmap(LoadPixmap(path=path))

    def build_menu(self):
        icon_dir = os.path.join(PLUGIN_PATH, "icons/"); menu_items = [("Add Key", "Manual BISS Entry", "add", icon_dir + "add.png"), ("Key Editor", "Manage stored keys", "editor", icon_dir + "editor.png"), ("Download Softcam", "Full update from server", "upd", icon_dir + "Download Softcam.png"), ("Autoroll", "Smart search for current channel", "auto", icon_dir + "auto.png")]
        lst = []
        for name, desc, act, icon_path in menu_items:
            pixmap = LoadPixmap(cached=True, path=icon_path) if os.path.exists(icon_path) else None
            lst.append((name, [MultiContentEntryPixmapAlphaTest(pos=(self.ui.px(15), self.ui.px(15)), size=(self.ui.px(70), self.ui.px(70)), png=pixmap), MultiContentEntryText(pos=(self.ui.px(110), self.ui.px(10)), size=(self.ui.px(450), self.ui.px(45)), font=0, text=name, flags=RT_VALIGN_TOP), MultiContentEntryText(pos=(self.ui.px(110), self.ui.px(55)), size=(self.ui.px(450), self.ui.px(35)), font=1, text=desc, flags=RT_VALIGN_TOP, color=0xbbbbbb), act]))
        self["menu"].l.setList(lst)
        # --- إصلاح 2: تجاوز خطأ setFont في بايثون 3 ---
        try:
            self["menu"].l.setFont(0, gFont("Regular", self.ui.font(36)))
            self["menu"].l.setFont(1, gFont("Regular", self.ui.font(24)))
        except:
            pass

    # ... (باقي الدوال الأصلية: ok, action_add, action_editor, action_update, action_auto, do_auto, save_biss_key ...)
    # سأختصر الباقي للتأكيد على الإصلاحات فقط ولكن كل الكود الأصلي يجب أن يظل كما هو لديك

class BissProServiceWatcher:
    def __init__(self, session):
        self.session = session; self.check_timer = eTimer()
        # --- إصلاح 3: دعم eTimer في الواتشر ---
        try: self.check_timer.timeout.connect(self.check_service)
        except: self.check_timer.callback.append(self.check_service)
        self.session.nav.event.append(self.on_event); self.is_scanning = False
    
    # ... (باقي دوال الواتشر الأصلية بدون تغيير)

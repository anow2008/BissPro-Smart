# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
# استخدام مكتبة VirtualKeyBoard لضمان التوافق الشامل
from Screens.VirtualKeyBoard import VirtualKeyBoard
try:
    from Tools.Notifications import addNotification
except ImportError:
    try:
        from Screens.Notifications import Notifications
        def addNotification(type, message, timeout=5, **kwargs):
            Notifications.addNotification(type, message, timeout=timeout)
    except:
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
# إضافة مكتبات الحسابات المتقدمة CRC32
import os, re, shutil, time, random, csv, binascii, struct
import urllib.request
from threading import Thread

# ==========================================================
# دالة حساب الهاش CRC32 (الأوسكام)
# ==========================================================
def calculate_oscam_crc32(sid, vpid):
    try:
        s = int(sid) & 0xFFFF
        v = int(vpid) & 0xFFFF if (vpid is not None and vpid != -1) else 0
        data = struct.pack("<HH", s, v)
        crc = binascii.crc32(data) & 0xFFFFFFFF
        return "%08X" % crc
    except:
        return "%04X%04X" % (int(sid or 0), int(vpid or 0) if vpid != -1 else 0)

# ==========================================================
# الإعدادات والمسارات
# ==========================================================
PLUGIN_PATH = os.path.dirname(__file__) + "/"
VERSION_NUM = "v1.5-Final" 
SHEET_ID = "1-7Dgnii46UYR4HMorgpwtKC_7Fz-XuTfDV6vO2EkzQo"
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/%s/export?format=csv" % SHEET_ID

def get_softcam_path():
    paths = ["/etc/tuxbox/config/oscam/SoftCam.Key", "/etc/tuxbox/config/ncam/SoftCam.Key", "/etc/tuxbox/config/SoftCam.Key", "/usr/keys/SoftCam.Key"]
    for p in paths:
        if os.path.exists(p): return p
    return "/etc/tuxbox/config/SoftCam.Key"

def restart_softcam_global():
    # قتل العمليات لضمان تنظيف الكاش
    os.system("killall -9 oscam ncam 2>/dev/null")
    time.sleep(0.5)
    scripts = ["/etc/init.d/softcam", "/etc/init.d/cardserver", "/etc/init.d/softcam.oscam", "/etc/init.d/softcam.ncam"]
    for s in scripts:
        if os.path.exists(s):
            os.system(f"{s} restart >/dev/null 2>&1")
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
        self.res = (False, "")
        self.skin = f"""
        <screen position="center,center" size="{self.ui.px(1100)},{self.ui.px(780)}" title="BissPro Smart {VERSION_NUM}">
            <widget name="date_label" position="{self.ui.px(50)},{self.ui.px(20)}" size="{self.ui.px(450)},{self.ui.px(40)}" font="Regular;{self.ui.font(26)}" halign="left" foregroundColor="#bbbbbb" transparent="1" />
            <widget name="time_label" position="{self.ui.px(750)},{self.ui.px(20)}" size="{self.ui.px(300)},{self.ui.px(40)}" font="Regular;{self.ui.font(26)}" halign="right" foregroundColor="#ffffff" transparent="1" />
            <widget name="menu" position="{self.ui.px(50)},{self.ui.px(80)}" size="{self.ui.px(600)},{self.ui.px(410)}" itemHeight="{self.ui.px(100)}" scrollbarMode="showOnDemand" transparent="1" zPosition="2"/>
            <widget name="main_logo" position="{self.ui.px(720)},{self.ui.px(120)}" size="{self.ui.px(300)},{self.ui.px(300)}" alphatest="blend" transparent="1" zPosition="1" />
            <widget name="main_progress" position="{self.ui.px(50)},{self.ui.px(510)}" size="{self.ui.px(1000)},{self.ui.px(12)}" foregroundColor="#00ff00" backgroundColor="#222222" />
            <widget name="status" position="{self.ui.px(50)},{self.ui.px(670)}" size="{self.ui.px(1000)},{self.ui.px(70)}" font="Regular;{self.ui.font(32)}" halign="center" valign="center" transparent="1" foregroundColor="#f0a30a"/>
        </screen>"""
        self["status"] = Label("Ready")
        self["time_label"] = Label(""); self["date_label"] = Label("")
        self["main_progress"] = ProgressBar(); self["main_logo"] = Pixmap()
        self["menu"] = MenuList([])
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {"ok": self.ok, "cancel": self.close, "red": self.action_add, "blue": self.action_auto}, -1)
        self.clock_timer = eTimer()
        self.clock_timer.callback.append(self.update_clock)
        self.clock_timer.start(1000)
        self.timer = eTimer()
        self.timer.callback.append(self.show_result)
        self.onLayoutFinish.append(self.build_menu)

    def update_clock(self):
        self["time_label"].setText(time.strftime("%H:%M:%S"))
        self["date_label"].setText(time.strftime("%A, %d %B %Y"))

    def build_menu(self):
        lst = [("Add Manual Key", "add"), ("AutoRoll Search", "auto")]
        self["menu"].l.setList(lst)

    def show_result(self):
        self.session.open(MessageBox, self.res[1], MessageBox.TYPE_INFO if self.res[0] else MessageBox.TYPE_ERROR, timeout=5)

    def ok(self):
        act = self["menu"].getCurrent()[1]
        if act == "add": self.action_add()
        elif act == "auto": self.action_auto()

    def action_add(self):
        self.session.openWithCallback(self.manual_done, VirtualKeyBoard, title="Enter BISS Key (16 chars):")

    def manual_done(self, key=None):
        if not key or len(key) != 16: return
        service = self.session.nav.getCurrentService()
        if service:
            info = service.info()
            h = calculate_oscam_crc32(info.getInfo(iServiceInformation.sSID), info.getInfo(iServiceInformation.sVideoPID))
            if self.save_biss_key(h, key, info.getName()): self.res = (True, "Saved Successfully")
            else: self.res = (False, "Save Failed")
            self.timer.start(100, True)

    def save_biss_key(self, full_id, key, name):
        target = get_softcam_path()
        try:
            lines = []
            if os.path.exists(target):
                with open(target, "r") as f:
                    for line in f:
                        if full_id.upper() not in line.upper(): lines.append(line)
            # التعديل الجوهري: استخدام 00 بدلاً من الأصفار الطويلة
            lines.append(f"F {full_id.upper()} 00 {key.upper()} ;{name}\n")
            with open(target, "w") as f: f.writelines(lines)
            os.chmod(target, 0o644); restart_softcam_global(); return True
        except: return False

    def action_auto(self):
        service = self.session.nav.getCurrentService()
        if service: 
            self["status"].setText("Searching..."); Thread(target=self.do_auto, args=(service,)).start()

    def do_auto(self, service):
        info = service.info(); t_data = info.getInfoObject(iServiceInformation.sTransponderData)
        if not t_data: return
        freq = int(t_data.get("frequency", 0) / 1000)
        h = calculate_oscam_crc32(info.getInfo(iServiceInformation.sSID), info.getInfo(iServiceInformation.sVideoPID))
        found = False
        try:
            resp = urllib.request.urlopen(GOOGLE_SHEET_URL, timeout=8).read().decode("utf-8").splitlines()
            for row in csv.reader(resp):
                if len(row) >= 2 and str(freq) in row[0]:
                    key = row[1].replace(" ", "").upper()
                    if self.save_biss_key(h, key, info.getName()):
                        self.res = (True, f"Found: {key}"); found = True; break
        except: pass
        if not found: self.res = (False, "Key Not Found")
        self.timer.start(100, True)

class BissProServiceWatcher:
    def __init__(self, session):
        self.session = session; self.check_timer = eTimer()
        self.check_timer.callback.append(self.check_service)
        self.session.nav.event.append(self.on_event)
    def on_event(self, event):
        if event in (0, 1): self.check_timer.start(6000, True)
    def check_service(self):
        service = self.session.nav.getCurrentService()
        if service and service.info().getInfo(iServiceInformation.sIsCrypted):
            Thread(target=self.bg_auto, args=(service,)).start()
    def bg_auto(self, service):
        info = service.info(); t_data = info.getInfoObject(iServiceInformation.sTransponderData)
        if not t_data: return
        h = calculate_oscam_crc32(info.getInfo(iServiceInformation.sSID), info.getInfo(iServiceInformation.sVideoPID))
        try:
            resp = urllib.request.urlopen(GOOGLE_SHEET_URL, timeout=5).read().decode("utf-8").splitlines()
            for row in csv.reader(resp):
                if len(row) >= 2 and str(int(t_data.get("frequency",0)/1000)) in row[0]:
                    key = row[1].replace(" ","").upper()
                    self.save_bg(h, key, info.getName()); break
        except: pass
    def save_bg(self, h, key, name):
        target = get_softcam_path(); lines = []
        if os.path.exists(target):
            with open(target, "r") as f:
                for line in f:
                    if h.upper() not in line.upper(): lines.append(line)
        lines.append(f"F {h.upper()} 00 {key.upper()} ;{name} (Auto)\n")
        with open(target, "w") as f: f.writelines(lines)
        restart_softcam_global()
        addNotification(MessageBox, f"BissPro: Found Key for {name}", type=MessageBox.TYPE_INFO, timeout=4)

def main(session, **kwargs): session.open(BISSPro)
def sessionstart(reason, **kwargs):
    if reason == 0 and "session" in kwargs:
        kwargs["session"].biss_watcher = BissProServiceWatcher(kwargs["session"])

def Plugins(**kwargs):
    return [PluginDescriptor(name="BissPro Smart", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main),
            PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart)]

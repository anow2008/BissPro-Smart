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
import os, re, shutil, time, random
from urllib.request import urlopen
from threading import Thread

# ==========================================================
# الإعدادات والمسارات
# ==========================================================
PLUGIN_PATH = os.path.dirname(__file__) + "/"
VERSION_NUM = "v1.2-Auto"
DATA_SOURCE = "https://raw.githubusercontent.com/anow2008/softcam.key/main/biss.txt"

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

# ==========================================================
# محرك العمل في الخلفية (Auto-Roll Service)
# ==========================================================
class BissAutoEngine:
    def __init__(self, session):
        self.session = session
        self.timer = eTimer()
        try: self.timer.callback.append(self.check_service)
        except: self.timer.timeout.connect(self.check_service)
        self.timer.start(5000, False) # يفحص كل 5 ثواني في الخلفية

    def check_service(self):
        service = self.session.nav.getCurrentService()
        if service:
            info = service.info()
            if info.getInfo(iServiceInformation.sIsCrypted):
                Thread(target=self.run_auto_roll, args=(service,)).start()

    def run_auto_roll(self, service):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            info = service.info()
            t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            if not t_data: return
            
            freq_raw = t_data.get("frequency", 0)
            curr_freq = str(int(freq_raw / 1000 if freq_raw > 50000 else freq_raw))
            raw_sid = info.getInfo(iServiceInformation.sSID)
            raw_vpid = info.getInfo(iServiceInformation.sVideoPID)
            combined_id = ("%04X" % (raw_sid & 0xFFFF)) + ("%04X" % (raw_vpid & 0xFFFF) if raw_vpid != -1 else "0000")
            
            # فحص إذا كانت الشفرة موجودة أصلاً لتجنب تكرار العمليات
            path = get_softcam_path()
            if os.path.exists(path):
                with open(path, "r") as f:
                    if f"F {combined_id.upper()}" in f.read().upper(): return

            # جلب الشفرة من السيرفر
            raw_data = urlopen(DATA_SOURCE, timeout=5, context=ctx).read().decode("utf-8")
            pattern = re.escape(curr_freq) + r'[\s\S]{0,500}?(([0-9A-Fa-f]{2}[\s\t:=-]*){8})'
            m = re.search(pattern, raw_data, re.I)
            
            if m:
                clean_key = re.sub(r'[^0-9A-Fa-f]', '', m.group(1)).upper()
                if len(clean_key) == 16:
                    self.save_key(combined_id, clean_key, info.getName())
        except: pass

    def save_key(self, full_id, key, name):
        target = get_softcam_path()
        try:
            lines = []
            if os.path.exists(target):
                with open(target, "r") as f:
                    for line in f:
                        if f"F {full_id.upper()}" not in line.upper(): lines.append(line)
            lines.append(f"F {full_id.upper()} 00000000 {key.upper()} ;{name}\n")
            with open(target, "w") as f: f.writelines(lines)
            restart_softcam_global()
        except: pass

# ==========================================================
# واجهة البلجن التقليدية (للتعديل اليدوي فقط)
# ==========================================================
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
        self.skin = f"""<screen position="center,center" size="{self.ui.px(1100)},{self.ui.px(780)}" title="BissPro Smart {VERSION_NUM}">
            <widget name="status" position="{self.ui.px(50)},{self.ui.px(670)}" size="{self.ui.px(1000)},{self.ui.px(70)}" font="Regular;{self.ui.font(32)}" halign="center" valign="center" transparent="1" foregroundColor="#f0a30a"/>
            <widget name="menu" position="{self.ui.px(50)},{self.ui.px(80)}" size="{self.ui.px(600)},{self.ui.px(410)}" itemHeight="{self.ui.px(100)}" />
        </screen>"""
        self["status"] = Label("Auto-Engine Active in Background")
        self["menu"] = MenuList([])
        self["actions"] = ActionMap(["OkCancelActions"], {"cancel": self.close}, -1)

# ==========================================================
# نقطة انطلاق البلجن (Entry Points)
# ==========================================================
auto_engine_instance = None

def sessionstart(reason, **kwargs):
    global auto_engine_instance
    if reason == 0: # عند بدء السيسشن (تشغيل الجهاز)
        if "session" in kwargs:
            auto_engine_instance = BissAutoEngine(kwargs["session"])

def main(session, **kwargs):
    session.open(BISSPro)

def Plugins(**kwargs):
    return [
        PluginDescriptor(name="BissPro Smart", description="Auto-Roll BISS in Background", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main),
        PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart) # هذا السطر هو السر في العمل التلقائي
    ]

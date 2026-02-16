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
import os, re, shutil, time, random, struct
from urllib.request import urlopen
from threading import Thread

# ==========================================================
# دالة حساب الهاش (CRC32)
# ==========================================================
def generate_crc32_table():
    table = []
    for i in range(256):
        crc = i
        for _ in range(8):
            if crc & 1: crc = (crc >> 1) ^ 0xEDB88320
            else: crc >>= 1
        table.append(crc)
    return table

CRC32_TABLE = generate_crc32_table()

def get_biss_hash(sid, vpid):
    try:
        if vpid == -1: vpid = 0
        data = struct.pack(">HH", sid & 0xFFFF, vpid & 0xFFFF)
        crc = 0x2600 ^ 0xffffffff
        for byte in data:
            if not isinstance(byte, int): byte = ord(byte)
            crc = CRC32_TABLE[(byte ^ crc) & 0xff] ^ (crc >> 8)
        return "%08X" % (crc ^ 0xffffffff & 0xFFFFFFFF)
    except:
        return "%04X%04X" % (sid & 0xFFFF, vpid if vpid != -1 else 0)

# ==========================================================
# الإعدادات والروابط
# ==========================================================
PLUGIN_PATH = os.path.realpath(os.path.dirname(__file__)) + "/"
VERSION_NUM = "v1.2" 
DATA_SOURCE = "https://raw.githubusercontent.com/anow2008/softcam.key/main/biss.txt"
URL_SOFTCAM = "https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key"

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
            <widget name="main_logo" position="{self.ui.px(820)},{self.ui.px(200)}" size="{self.ui.px(120)},{self.ui.px(120)}" alphatest="blend" transparent="1" zPosition="1" />
            <widget name="main_progress" position="{self.ui.px(50)},{self.ui.px(510)}" size="{self.ui.px(1000)},{self.ui.px(12)}" foregroundColor="#00ff00" backgroundColor="#222222" />
            <widget name="version_label" position="{self.ui.px(850)},{self.ui.px(525)}" size="{self.ui.px(200)},{self.ui.px(35)}" font="Regular;{self.ui.font(22)}" halign="right" foregroundColor="#888888" transparent="1" />
            <eLabel position="{self.ui.px(50)},{self.ui.px(565)}" size="{self.ui.px(1000)},{self.ui.px(2)}" backgroundColor="#333333" />
            <eLabel position="{self.ui.px(60)},{self.ui.px(600)}" size="{self.ui.px(25)},{self.ui.px(25)}" backgroundColor="#ff0000" />
            <widget name="btn_red" position="{self.ui.px(90)},{self.ui.px(595)}" size="{self.ui.px(150)},{self.ui.px(40)}" font="Regular;{self.ui.font(24)}" transparent="1" />
            <eLabel position="{self.ui.px(250)},{self.ui.px(600)}" size="{self.ui.px(25)},{self.ui.px(25)}" backgroundColor="#00ff00" />
            <widget name="btn_green" position="{self.ui.px(285)},{self.ui.px(595)}" size="{self.ui.px(120)},{self.ui.px(40)}" font="Regular;{self.ui.font(24)}" transparent="1" />
            <eLabel position="{self.ui.px(420)},{self.ui.px(600)}" size="{self.ui.px(25)},{self.ui.px(25)}" backgroundColor="#ffff00" />
            <widget name="btn_yellow" position="{self.ui.px(455)},{self.ui.px(595)}" size="{self.ui.px(280)},{self.ui.px(40)}" font="Regular;{self.ui.font(24)}" transparent="1" />
            <eLabel position="{self.ui.px(750)},{self.ui.px(600)}" size="{self.ui.px(25)},{self.ui.px(25)}" backgroundColor="#0000ff" />
            <widget name="btn_blue" position="{self.ui.px(785)},{self.ui.px(595)}" size="{self.ui.px(200)},{self.ui.px(40)}" font="Regular;{self.ui.font(24)}" transparent="1" />
            <widget name="status" position="{self.ui.px(50)},{self.ui.px(670)}" size="{self.ui.px(1000)},{self.ui.px(70)}" font="Regular;{self.ui.font(32)}" halign="center" valign="center" transparent="1" foregroundColor="#f0a30a"/>
        </screen>"""
        self["btn_red"] = Label("Add Key"); self["btn_green"] = Label("Editor")
        self["btn_yellow"] = Label("Download Softcam"); self["btn_blue"] = Label("Autoroll")
        self["version_label"] = Label(f"Ver: {VERSION_NUM}"); self["status"] = Label("Ready")
        self["time_label"] = Label(""); self["date_label"] = Label("")
        self["main_progress"] = ProgressBar(); self["main_logo"] = Pixmap()
        self.clock_timer = eTimer()
        try: self.clock_timer.callback.append(self.update_clock)
        except: self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        self.timer = eTimer()
        try: self.timer.callback.append(self.show_result)
        except: self.timer.timeout.connect(self.show_result)
        self["menu"] = MenuList([])
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {"ok": self.ok, "cancel": self.exit_clean, "red": self.action_add, "green": self.action_editor, "yellow": self.action_update, "blue": self.action_auto}, -1)
        self.onLayoutFinish.append(self.build_menu); self.onLayoutFinish.append(self.load_main_logo); self.update_clock()

    def exit_clean(self):
        self.clock_timer.stop()
        self.close()

    def update_clock(self):
        self["time_label"].setText(time.strftime("%H:%M:%S"))
        self["date_label"].setText(time.strftime("%A, %d %B %Y"))

    def build_menu(self):
        menu_items = [("Add Key", "Manual BISS Entry", "add", "add.png"), ("Key Editor", "Manage stored keys", "editor", "editor.png"), ("Download Softcam", "Full update from server", "upd", "update.png"), ("Autoroll", "Smart search for current channel", "auto", "auto.png")]
        lst = []
        for name, desc, act, icon_file in menu_items:
            res = (name, [None, MultiContentEntryText(pos=(self.ui.px(110), self.ui.px(10)), size=(self.ui.px(450), self.ui.px(45)), font=0, text=name, flags=RT_VALIGN_TOP), MultiContentEntryText(pos=(self.ui.px(110), self.ui.px(55)), size=(self.ui.px(450), self.ui.px(35)), font=1, text=desc, flags=RT_VALIGN_TOP, color=0xbbbbbb), act])
            lst.append(res)
        self["menu"].l.setList(lst)
        if hasattr(self["menu"].l, 'setFont'): 
            self["menu"].l.setFont(0, gFont("Regular", self.ui.font(36))); self["menu"].l.setFont(1, gFont("Regular", self.ui.font(24)))

    def load_main_logo(self):
        logo_path = os.path.join(PLUGIN_PATH, "plugin.png")
        if os.path.exists(logo_path): self["main_logo"].instance.setPixmap(LoadPixmap(path=logo_path))

    def ok(self):
        curr = self["menu"].getCurrent()
        if curr:
            act = curr[1][-1]
            if act == "add": self.action_add()
            elif act == "editor": self.action_editor()
            elif act == "upd": self.action_update()
            elif act == "auto": self.action_auto()

    def action_add(self):
        service = self.session.nav.getCurrentService()
        if service: self.session.openWithCallback(self.manual_done, HexInputScreen, service.info().getName())

    def manual_done(self, key=None):
        if key is None: return
        service = self.session.nav.getCurrentService()
        if not service: return
        info = service.info()
        combined_id = get_biss_hash(info.getInfo(iServiceInformation.sSID), info.getInfo(iServiceInformation.sVideoPID))
        if self.save_biss_key(combined_id, key, info.getName()): self.res = (True, f"Saved with Hash: {combined_id}")
        else: self.res = (False, "File Error")
        self.timer.start(100, True)

    def action_editor(self): self.session.open(BissManagerList)

    def action_update(self): 
        self["status"].setText("Downloading Softcam..."); Thread(target=self.do_update).start()

    def do_update(self):
        try:
            import ssl; ctx = ssl._create_unverified_context()
            data = urlopen(URL_SOFTCAM, context=ctx).read()
            tp = get_softcam_path()
            with open(tp, "wb") as f: f.write(data)
            os.chmod(tp, 0o644); restart_softcam_global(); self.res = (True, "Softcam Updated")
        except: self.res = (False, "Update Failed")
        self.timer.start(100, True)

    # ==========================================================
    # الـ Autoroll المطور (بحث بالتردد + السمبل + القطبية)
    # ==========================================================
    def action_auto(self):
        service = self.session.nav.getCurrentService()
        if service: 
            self["status"].setText("Searching (Freq+SR+Pol)..."); self["main_progress"].setValue(30)
            Thread(target=self.do_auto, args=(service,)).start()

    def do_auto(self, service):
        try:
            import ssl; ctx = ssl._create_unverified_context()
            info = service.info()
            t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            
            # جلب البيانات الأساسية
            freq = str(int(t_data.get("frequency", 0)/1000 if t_data.get("frequency", 0)>50000 else t_data.get("frequency", 0)))
            sr = str(int(t_data.get("symbol_rate", 0)/1000 if t_data.get("symbol_rate", 0)>1000 else t_data.get("symbol_rate", 0)))
            
            # جلب القطبية: 0=H, 1=V
            pol_num = t_data.get("polarization", 0)
            pol = "H" if pol_num == 0 else "V"
            
            # البحث في السورس أونلاين بالثلاثي
            raw_data = urlopen(DATA_SOURCE, timeout=12, context=ctx).read().decode("utf-8")
            
            # ريجيكس متطور يبحث عن التردد والقطبية والسمبل ريت في مسافة قريبة من بعض
            pattern = r"(?i)" + re.escape(freq) + r".*?" + re.escape(pol) + r".*?" + re.escape(sr) + r"[\s\S]{0,100}?(([0-9A-Fa-f]{2}[\s\t:=-]*){8})"
            m = re.search(pattern, raw_data)
            
            if m:
                ckey = re.sub(r'[^0-9A-Fa-f]', '', m.group(1)).upper()
                raw_id = get_biss_hash(info.getInfo(iServiceInformation.sSID), info.getInfo(iServiceInformation.sVideoPID))
                if self.save_biss_key(raw_id, ckey, info.getName()):
                    self.res = (True, f"Found! {freq}{pol} {sr} Saved to {raw_id}")
                else: self.res = (False, "Write Error")
            else: self.res = (False, "Key not found for this TP")
        except Exception as e: self.res = (False, f"Error: {str(e)}")
        self.timer.start(100, True)

    def save_biss_key(self, full_id, key, name):
        target = get_softcam_path()
        try:
            lines = []
            if os.path.exists(target):
                with open(target, "r") as f:
                    for line in f:
                        if f"F {full_id.upper()}" not in line.upper(): lines.append(line)
            lines.append(f"F {full_id.upper()} 00000000 {key.upper()} ;{name}\n")
            with open(target, "w") as f: f.writelines(lines)
            os.chmod(target, 0o644); restart_softcam_global(); return True
        except: return False

    def show_result(self): 
        self["main_progress"].setValue(0); self["status"].setText("Ready")
        self.session.open(MessageBox, self.res[1], MessageBox.TYPE_INFO if self.res[0] else MessageBox.TYPE_ERROR, timeout=5)

# ==========================================================
# الخلفية (Service Watcher) مع دعم القطبية
# ==========================================================
class BissProServiceWatcher:
    def __init__(self, session):
        self.session = session; self.check_timer = eTimer()
        try: self.check_timer.callback.append(self.check_service)
        except: self.check_timer.timeout.connect(self.check_service)
        self.session.nav.event.append(self.on_event); self.is_scanning = False
    
    def on_event(self, event):
        if event in (0, 1): self.check_timer.start(5000, True)

    def check_service(self):
        if self.is_scanning: return
        service = self.session.nav.getCurrentService()
        if not service or not service.info().getInfo(iServiceInformation.sIsCrypted): return
        caids = service.info().getInfoObject(iServiceInformation.sCAIDs)
        if caids and 0x2600 in caids:
            self.is_scanning = True; Thread(target=self.bg_thread, args=(service,)).start()

    def bg_thread(self, service):
        try:
            import ssl; ctx = ssl._create_unverified_context()
            info = service.info(); t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            freq = str(int(t_data.get("frequency",0)/1000 if t_data.get("frequency",0)>50000 else t_data.get("frequency",0)))
            sr = str(int(t_data.get("symbol_rate",0)/1000 if t_data.get("symbol_rate",0)>1000 else t_data.get("symbol_rate",0)))
            pol = "H" if t_data.get("polarization", 0) == 0 else "V"
            
            raw_data = urlopen(DATA_SOURCE, timeout=10, context=ctx).read().decode("utf-8")
            pattern = r"(?i)" + re.escape(freq) + r".*?" + re.escape(pol) + r".*?" + re.escape(sr) + r"[\s\S]{0,100}?(([0-9A-Fa-f]{2}[\s\t:=-]*){8})"
            m = re.search(pattern, raw_data)
            
            if m:
                ckey = re.sub(r'[^0-9A-Fa-f]', '', m.group(1)).upper()
                raw_id = get_biss_hash(info.getInfo(iServiceInformation.sSID), info.getInfo(iServiceInformation.sVideoPID))
                target = get_softcam_path(); lines = []
                if os.path.exists(target):
                    with open(target, "r") as f:
                        for l in f:
                            if f"F {raw_id.upper()}" not in l.upper(): lines.append(l)
                lines.append(f"F {raw_id.upper()} 00000000 {ckey} ;{info.getName()} (Auto-Watcher)\n")
                with open(target, "w") as f: f.writelines(lines)
                os.chmod(target, 0o644); restart_softcam_global()
        except: pass
        self.is_scanning = False

# [ملاحظة: محرر المفاتيح وشاشة الإدخال يبقون كما هم في الكود السابق]

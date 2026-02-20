# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
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
import os, re, shutil, time, random, csv, binascii, struct
import urllib.request
from threading import Thread

# ==========================================================
# الإعدادات والمسارات (نفس كودك الأصلي)
# ==========================================================
PLUGIN_PATH = os.path.dirname(__file__) + "/"
VERSION_NUM = "v1.2-Fixed" 

URL_VERSION = "https://raw.githubusercontent.com/anow2008/BissPro-Smart/main/version"
URL_NOTES   = "https://raw.githubusercontent.com/anow2008/info/main/notes"
URL_PLUGIN  = "https://raw.githubusercontent.com/anow2008/BissPro-Smart/main/plugin.py"
DATA_SOURCE = "https://raw.githubusercontent.com/anow2008/softcam.key/main/biss"
SHEET_ID = "1-7Dgnii46UYR4HMorgpwtKC_7Fz-XuTfDV6vO2EkzQo"
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/%s/export?format=csv" % SHEET_ID

# --- الدالة الجديدة للحساب (التعديل الوحيد المطلوب) ---
def calculate_oscam_hash(sid, vpid):
    try:
        if vpid == -1 or vpid is None: vpid = 0
        data = struct.pack(">HH", int(sid) & 0xFFFF, int(vpid) & 0xFFFF)
        crc = binascii.crc32(data) & 0xFFFFFFFF
        return "%08X" % crc
    except:
        return "%04X%04X" % (int(sid) & 0xFFFF, int(vpid) & 0xFFFF if vpid != -1 else 0)

def get_softcam_path():
    paths = ["/etc/tuxbox/config/oscam/SoftCam.Key", "/etc/tuxbox/config/ncam/SoftCam.Key", "/etc/tuxbox/config/SoftCam.Key", "/usr/keys/SoftCam.Key"]
    for p in paths:
        if os.path.exists(p): return p
    return "/etc/tuxbox/config/SoftCam.Key"

# --- دالة الريستارت كما هي في كودك الأصلي بالظبط ---
def restart_softcam_global():
    scripts = ["/etc/init.d/softcam", "/etc/init.d/cardserver", "/etc/init.d/softcam.oscam", "/etc/init.d/softcam.ncam", "/etc/init.d/softcam.oscam_emu"]
    restarted = False
    for s in scripts:
        if os.path.exists(s):
            os.system(f"{s} restart >/dev/null 2>&1")
            restarted = True
            break
    if not restarted:
        os.system("killall -9 oscam ncam vicardd gbox 2>/dev/null")
        time.sleep(1.0)
        for s in scripts:
            if os.path.exists(s):
                os.system(f"{s} start >/dev/null 2>&1")
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
        # سكين الواجهة الأصلي
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
        self["menu"].onSelectionChanged.append(self.update_dynamic_logo)
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {"ok": self.ok, "cancel": self.close, "red": self.action_add, "green": self.action_editor, "yellow": self.action_update, "blue": self.action_auto}, -1)
        
        self.onLayoutFinish.append(self.build_menu)
        self.onLayoutFinish.append(self.update_dynamic_logo)
        self.onLayoutFinish.append(self.check_for_updates)

    def update_clock(self):
        self["time_label"].setText(time.strftime("%H:%M:%S"))
        self["date_label"].setText(time.strftime("%A, %d %B %Y"))

    def update_dynamic_logo(self):
        curr = self["menu"].getCurrent()
        if curr:
            icon_map = {"add": "add.png", "editor": "editor.png", "upd": "Download Softcam.png", "auto": "auto.png"}
            icon_file = icon_map.get(curr[1][-1], "plugin.png")
            path = os.path.join(PLUGIN_PATH, "icons/", icon_file)
            if os.path.exists(path): self["main_logo"].instance.setPixmap(LoadPixmap(path=path))

    def check_for_updates(self): Thread(target=self.thread_check_version).start()
    
    def thread_check_version(self):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            v_url = URL_VERSION + "?nocache=" + str(random.randint(1000, 9999))
            remote_data = urllib.request.urlopen(v_url, timeout=10, context=ctx).read().decode("utf-8")
            remote_v = float(re.search(r"(\d+\.\d+)", remote_data).group(1))
            local_v = float(re.search(r"(\d+\.\d+)", VERSION_NUM).group(1))
            if remote_v > local_v:
                msg = "Update Found: v%s\nInstall Update?" % str(remote_v)
                self.session.openWithCallback(self.install_update, MessageBox, msg, MessageBox.TYPE_YESNO)
        except: pass

    def install_update(self, answer):
        if answer:
            self["status"].setText("Downloading...")
            Thread(target=self.do_plugin_download).start()

    def do_plugin_download(self):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            new_code = urllib.request.urlopen(URL_PLUGIN, timeout=30, context=ctx).read()
            if len(new_code) > 2000:
                with open(os.path.join(PLUGIN_PATH, "plugin.py"), "wb") as f: f.write(new_code)
                self.res = (True, "Plugin Updated!\nRestart Enigma2?", "plugin_upd")
        except: self.res = (False, "Update Failed")
        self.timer.start(100, True)

    def show_result(self):
        if self.res[0]:
            if len(self.res) > 2 and self.res[2] == "plugin_upd":
                self.session.openWithCallback(lambda a: quitMainloop(3) if a else None, MessageBox, self.res[1], MessageBox.TYPE_YESNO)
            else: self.session.open(MessageBox, self.res[1], MessageBox.TYPE_INFO, timeout=5)
        else: self.session.open(MessageBox, self.res[1], MessageBox.TYPE_ERROR, timeout=5)

    def build_menu(self):
        icon_dir = os.path.join(PLUGIN_PATH, "icons/")
        menu_items = [("Add Key", "Manual BISS Entry", "add", icon_dir + "add.png"), ("Key Editor", "Manage stored keys", "editor", icon_dir + "editor.png"), ("Download Softcam", "Full server update", "upd", icon_dir + "Download Softcam.png"), ("Autoroll", "Smart current channel search", "auto", icon_dir + "auto.png")]
        lst = []
        for name, desc, act, icon_path in menu_items:
            pixmap = LoadPixmap(cached=True, path=icon_path) if os.path.exists(icon_path) else None
            lst.append((name, [MultiContentEntryPixmapAlphaTest(pos=(self.ui.px(15), self.ui.px(15)), size=(self.ui.px(70), self.ui.px(70)), png=pixmap), MultiContentEntryText(pos=(self.ui.px(110), self.ui.px(10)), size=(self.ui.px(450), self.ui.px(45)), font=0, text=name), MultiContentEntryText(pos=(self.ui.px(110), self.ui.px(55)), size=(self.ui.px(450), self.ui.px(35)), font=1, text=desc, color=0xbbbbbb), act]))
        self["menu"].l.setList(lst)

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
        if service:
            info = service.info()
            h = calculate_oscam_hash(info.getInfo(iServiceInformation.sSID), info.getInfo(iServiceInformation.sVideoPID))
            if self.save_biss_key(h, key, info.getName()): self.res = (True, f"Saved: {info.getName()}")
            else: self.res = (False, "File Error")
        self.timer.start(100, True)

    def save_biss_key(self, h, key, name):
        target = get_softcam_path()
        try:
            lines = []
            if os.path.exists(target):
                with open(target, "r") as f:
                    for line in f:
                        if f"F {h.upper()}" not in line.upper(): lines.append(line)
            lines.append(f"F {h.upper()} 00000000 {key.upper()} ;{name}\n")
            with open(target, "w") as f: f.writelines(lines)
            os.chmod(target, 0o644)
            restart_softcam_global(); return True
        except: return False

    def action_update(self): Thread(target=self.do_update).start()
    def do_update(self):
        try:
            data = urllib.request.urlopen("https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key").read()
            with open(get_softcam_path(), "wb") as f: f.write(data)
            restart_softcam_global(); self.res = (True, "Updated")
        except: self.res = (False, "Failed")
        self.timer.start(100, True)

    def action_auto(self):
        service = self.session.nav.getCurrentService()
        if service: Thread(target=self.do_auto, args=(service,)).start()

    def do_auto(self, service):
        try:
            info = service.info(); t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            f = int(t_data.get("frequency", 0) / 1000 if t_data.get("frequency", 0) > 50000 else t_data.get("frequency", 0))
            h = calculate_oscam_hash(info.getInfo(iServiceInformation.sSID), info.getInfo(iServiceInformation.sVideoPID))
            resp = urllib.request.urlopen(GOOGLE_SHEET_URL, timeout=8).read().decode("utf-8").splitlines()
            found = False
            for row in csv.reader(resp):
                if len(row) >= 2 and str(f) in row[0]:
                    k = row[1].replace(" ", "").strip().upper()
                    if len(k) == 16: self.save_biss_key(h, k, info.getName()); self.res = (True, f"Found: {k}"); found = True; break
            if not found: self.res = (False, "Not found")
        except: self.res = (False, "Error")
        self.timer.start(100, True)

    def action_editor(self): self.session.open(BissManagerList)

class BissProServiceWatcher:
    def __init__(self, session):
        self.session = session; self.check_timer = eTimer()
        try: self.check_timer.callback.append(self.check_service)
        except: self.check_timer.timeout.connect(self.check_service)
        self.session.nav.event.append(self.on_event)
        self.is_scanning = False
    def on_event(self, event):
        if event in (0, 1): self.check_timer.start(6000, True)
    def check_service(self):
        if self.is_scanning: return
        service = self.session.nav.getCurrentService()
        if service and service.info().getInfo(iServiceInformation.sIsCrypted):
            self.is_scanning = True; Thread(target=self.bg_do_auto, args=(service,)).start()
    def bg_do_auto(self, service):
        try:
            info = service.info(); t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            f = int(t_data.get("frequency", 0) / 1000 if t_data.get("frequency", 0) > 50000 else t_data.get("frequency", 0))
            h = calculate_oscam_hash(info.getInfo(iServiceInformation.sSID), info.getInfo(iServiceInformation.sVideoPID))
            resp = urllib.request.urlopen(GOOGLE_SHEET_URL, timeout=8).read().decode("utf-8").splitlines()
            for row in csv.reader(resp):
                if len(row) >= 2 and str(f) in row[0]:
                    k = row[1].replace(" ", "").strip().upper()
                    if len(k) == 16: self.save_biss_key_background(h, k, info.getName()); break
        except: pass
        self.is_scanning = False
    def save_biss_key_background(self, h, key, name):
        target = get_softcam_path()
        try:
            lines = []
            if os.path.exists(target):
                with open(target, "r") as f:
                    for line in f:
                        if f"F {h.upper()}" not in line.upper(): lines.append(line)
            lines.append(f"F {h.upper()} 00000000 {key.upper()} ;{name} (AutoRoll)\n")
            with open(target, "w") as f: f.writelines(lines)
            os.chmod(target, 0o644); restart_softcam_global()
            addNotification(MessageBox, f"Found: {key}", type=MessageBox.TYPE_INFO, timeout=3)
        except: pass

class BissManagerList(Screen):
    def __init__(self, session):
        self.ui = AutoScale()
        Screen.__init__(self, session)
        self.skin = f"""<screen position="center,center" size="{self.ui.px(1000)},{self.ui.px(700)}" title="Editor"><widget name="keylist" position="20,20" size="960,650" itemHeight="50" /></screen>"""
        self["keylist"] = MenuList([]); self["actions"] = ActionMap(["OkCancelActions"], {"cancel": self.close}, -1)
        self.onLayoutFinish.append(self.load)
    def load(self):
        p = get_softcam_path(); keys = []
        if os.path.exists(p):
            with open(p, "r") as f:
                for l in f:
                    if l.strip().upper().startswith("F "): keys.append(l.strip())
        self["keylist"].setList(keys)

class HexInputScreen(Screen):
    def __init__(self, session, channel_name=""):
        self.ui = AutoScale()
        Screen.__init__(self, session)
        self.skin = f"""<screen position="center,center" size="1150,400" title="Input"><widget name="keylabel" position="25,100" size="1100,110" font="Regular;80" halign="center" /></screen>"""
        self["keylabel"] = Label(""); self["actions"] = ActionMap(["OkCancelActions", "NumberActions"], {"cancel": lambda: self.close(None), "0": lambda: self.k("0"), "1": lambda: self.k("1"), "2": lambda: self.k("2"), "3": lambda: self.k("3"), "4": lambda: self.k("4"), "5": lambda: self.k("5"), "6": lambda: self.k("6"), "7": lambda: self.k("7"), "8": lambda: self.k("8"), "9": lambda: self.k("9")}, -1)
        self.key = ["0"] * 16; self.idx = 0; self.update()
    def k(self, n):
        if self.idx < 16: self.key[self.idx] = n; self.idx += 1; self.update()
        if self.idx == 16: self.close("".join(self.key))
    def update(self): self["keylabel"].setText("".join(self.key))

watcher_instance = None
def main(session, **kwargs): session.open(BISSPro)
def Plugins(**kwargs):
    return [PluginDescriptor(name="BissPro Smart", description="v1.2 Fixed", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main),
            PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart)]
def sessionstart(reason, session=None, **kwargs):
    global watcher_instance
    if reason == 0 and session is not None and watcher_instance is None: watcher_instance = BissProServiceWatcher(session)

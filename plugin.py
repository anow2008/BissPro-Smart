# -*- coding: utf-8 -*-
# BissPro Smart v1.0 - Full Fixed Version for Python 3
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

# ==========================================================
# دالة CRC32 الأصلية
# ==========================================================
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

# ==========================================================
# الإعدادات والمسارات
# ==========================================================
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
        
        self["btn_red"] = Label("Add Key")
        self["btn_green"] = Label("Editor")
        self["btn_yellow"] = Label("Download Softcam")
        self["btn_blue"] = Label("Autoroll")
        self["version_label"] = Label(f"Ver: {VERSION_NUM}")
        self["status"] = Label("Ready")
        self["time_label"] = Label("")
        self["date_label"] = Label("")
        self["main_progress"] = ProgressBar()
        self["main_logo"] = Pixmap()
        
        # --- إصلاح 1: دعم eTimer في بايثون 3 ---
        self.clock_timer = eTimer()
        try:
            self.clock_timer.timeout.connect(self.update_clock)
        except AttributeError:
            self.clock_timer.callback.append(self.update_clock)
        self.clock_timer.start(1000, False)
        
        self.timer = eTimer()
        try:
            self.timer.timeout.connect(self.show_result)
        except AttributeError:
            self.timer.callback.append(self.show_result)
        
        self["menu"] = MenuList([])
        self["menu"].onSelectionChanged.append(self.update_dynamic_logo)
        
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.ok,
            "cancel": self.close,
            "red": self.action_add,
            "green": self.action_editor,
            "yellow": self.action_update,
            "blue": self.action_auto
        }, -1)
        
        self.onLayoutFinish.append(self.build_menu)
        self.onLayoutFinish.append(self.update_dynamic_logo)
        self.onLayoutFinish.append(self.check_for_updates)
        self.update_clock()

    def update_dynamic_logo(self):
        curr = self["menu"].getCurrent()
        if curr and self["main_logo"].instance:
            act = curr[1][-1]
            icon_map = {"add": "add.png", "editor": "editor.png", "upd": "Download Softcam.png", "auto": "auto.png"}
            path = os.path.join(PLUGIN_PATH, "icons/", icon_map.get(act, "plugin.png"))
            if os.path.exists(path):
                self["main_logo"].instance.setPixmap(LoadPixmap(path=path))

    def build_menu(self):
        icon_dir = os.path.join(PLUGIN_PATH, "icons/")
        menu_items = [
            ("Add Key", "Manual BISS Entry", "add", icon_dir + "add.png"),
            ("Key Editor", "Manage stored keys", "editor", icon_dir + "editor.png"),
            ("Download Softcam", "Full update from server", "upd", icon_dir + "Download Softcam.png"),
            ("Autoroll", "Smart search for current channel", "auto", icon_dir + "auto.png")
        ]
        lst = []
        for name, desc, act, icon_path in menu_items:
            pixmap = LoadPixmap(cached=True, path=icon_path) if os.path.exists(icon_path) else None
            lst.append((name, [
                MultiContentEntryPixmapAlphaTest(pos=(self.ui.px(15), self.ui.px(15)), size=(self.ui.px(70), self.ui.px(70)), png=pixmap),
                MultiContentEntryText(pos=(self.ui.px(110), self.ui.px(10)), size=(self.ui.px(450), self.ui.px(45)), font=0, text=name, flags=RT_VALIGN_TOP),
                MultiContentEntryText(pos=(self.ui.px(110), self.ui.px(55)), size=(self.ui.px(450), self.ui.px(35)), font=1, text=desc, flags=RT_VALIGN_TOP, color=0xbbbbbb),
                act
            ]))
        
        self["menu"].l.setList(lst)
        # --- إصلاح 2: تجاوز خطأ setFont المسبب للكراش ---
        try:
            self["menu"].l.setFont(0, gFont("Regular", self.ui.font(36)))
            self["menu"].l.setFont(1, gFont("Regular", self.ui.font(24)))
        except (AttributeError, TypeError):
            pass

    def check_for_updates(self):
        Thread(target=self.thread_check_version).start()

    def thread_check_version(self):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            headers = {'User-Agent': 'Mozilla/5.0'}
            v_url = URL_VERSION + "?nocache=" + str(random.randint(1000, 9999))
            req = urllib.request.Request(v_url, headers=headers)
            remote_data = urllib.request.urlopen(req, timeout=10, context=ctx).read().decode("utf-8")
            remote_v = float(re.search(r"(\d+\.\d+)", remote_data).group(1))
            if remote_v > 1.0:
                self.session.openWithCallback(self.install_update, MessageBox, "Update Found: v%s\nInstall now?" % remote_v, MessageBox.TYPE_YESNO)
        except:
            pass

    def install_update(self, answer):
        if answer:
            self["status"].setText("Downloading...")
            Thread(target=self.do_plugin_download).start()

    def do_plugin_download(self):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            headers = {'User-Agent': 'Mozilla/5.0'}
            new_code = urllib.request.urlopen(urllib.request.Request(URL_PLUGIN, headers=headers), timeout=30, context=ctx).read()
            if len(new_code) > 2000:
                with open(os.path.join(PLUGIN_PATH, "plugin.py"), "wb") as f:
                    f.write(new_code)
                self.res = (True, "Updated Successfully! Restart Enigma2?", "plugin_upd")
        except Exception as e:
            self.res = (False, str(e))
        self.timer.start(100, True)

    def show_result(self): 
        if self.res[0]:
            if len(self.res) > 2 and self.res[2] == "plugin_upd":
                self.session.openWithCallback(lambda a: quitMainloop(3) if a else None, MessageBox, self.res[1], MessageBox.TYPE_YESNO)
            else:
                self.session.open(MessageBox, self.res[1], MessageBox.TYPE_INFO, timeout=5)
        else:
            self.session.open(MessageBox, self.res[1], MessageBox.TYPE_ERROR, timeout=5)

    def update_clock(self):
        self["time_label"].setText(time.strftime("%H:%M:%S"))
        self["date_label"].setText(time.strftime("%A, %d %B %Y"))

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
        if service:
            self.session.openWithCallback(self.manual_done, HexInputScreen, service.info().getName())

    def manual_done(self, key=None):
        if key is None: return
        service = self.session.nav.getCurrentService()
        if not service: return
        info = service.info()
        t_data = info.getInfoObject(iServiceInformation.sTransponderData)
        freq = int(t_data.get("frequency", 0) / 1000 if t_data.get("frequency", 0) > 50000 else t_data.get("frequency", 0))
        crc_id = get_crc32_id(info.getInfo(iServiceInformation.sSID), freq)
        if self.save_biss_key(crc_id, key, info.getName()):
            self.res = (True, f"Saved: {info.getName()}")
        else:
            self.res = (False, "File Error")
        self.timer.start(100, True)

    def save_biss_key(self, full_id, key, name):
        target = get_softcam_path()
        try:
            current_date = time.strftime("%d-%m-%Y")
            lines = []
            if os.path.exists(target):
                with open(target, "r") as f:
                    for line in f:
                        if f"F {full_id.upper()}" not in line.upper():
                            lines.append(line)
            lines.append(f"F {full_id.upper()} 00000000 {key.upper()} ;{name} | {current_date}\n")
            with open(target, "w") as f:
                f.writelines(lines)
            os.chmod(target, 0o644)
            restart_softcam_global()
            return True
        except:
            return False

    def action_editor(self):
        self.session.open(BissManagerList)

    def action_update(self):
        self["status"].setText("Downloading...")
        Thread(target=self.do_update).start()

    def do_update(self):
        try:
            data = urllib.request.urlopen("https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key").read()
            with open(get_softcam_path(), "wb") as f:
                f.write(data)
            restart_softcam_global()
            self.res = (True, "Updated Successfully")
        except:
            self.res = (False, "Failed")
        self.timer.start(100, True)

    def action_auto(self):
        service = self.session.nav.getCurrentService()
        if service:
            self["status"].setText("Searching...")
            Thread(target=self.do_auto, args=(service,)).start()

    def do_auto(self, service):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            info = service.info()
            ch_name = info.getName()
            t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            freq = int(t_data.get("frequency", 0) / 1000 if t_data.get("frequency", 0) > 50000 else t_data.get("frequency", 0))
            pol = "V" if t_data.get("polarization", 0) else "H"
            crc_id = get_crc32_id(info.getInfo(iServiceInformation.sSID), freq)
            found = False
            resp = urllib.request.urlopen(urllib.request.Request(GOOGLE_SHEET_URL), timeout=8, context=ctx).read().decode("utf-8").splitlines()
            for row in csv.reader(resp):
                if len(row) >= 2:
                    if str(freq) in row[0] and pol in row[0].upper():
                        key = row[1].replace(" ", "").strip().upper()
                        if len(key) == 16:
                            self.save_biss_key(crc_id, key, ch_name)
                            found = True
                            break
            if found: self.res = (True, f"Found: {ch_name}")
            else: self.res = (False, "Not found")
        except:
            self.res = (False, "Auto Error")
        self.timer.start(100, True)

class BissProServiceWatcher:
    def __init__(self, session):
        self.session = session
        self.check_timer = eTimer()
        try:
            self.check_timer.timeout.connect(self.check_service)
        except AttributeError:
            self.check_timer.callback.append(self.check_service)
        self.session.nav.event.append(self.on_event)
        self.is_scanning = False

    def on_event(self, event):
        if event in (0, 1):
            self.check_timer.start(6000, True)

    def check_service(self):
        if self.is_scanning: return
        service = self.session.nav.getCurrentService()
        if service and service.info().getInfo(iServiceInformation.sIsCrypted):
            caids = service.info().getInfoObject(iServiceInformation.sCAIDs)
            if caids and 0x2600 in caids:
                self.is_scanning = True
                Thread(target=self.bg_do_auto, args=(service,)).start()

    def bg_do_auto(self, service):
        try:
            info = service.info()
            t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            freq = int(t_data.get("frequency", 0) / 1000 if t_data.get("frequency", 0) > 50000 else t_data.get("frequency", 0))
            crc_id = get_crc32_id(info.getInfo(iServiceInformation.sSID), freq)
            resp = urllib.request.urlopen(GOOGLE_SHEET_URL, timeout=8).read().decode("utf-8").splitlines()
            for row in csv.reader(resp):
                if len(row) >= 2 and str(freq) in row[0]:
                    key = row[1].replace(" ", "").strip().upper()
                    if len(key) == 16:
                        self.save_biss_key_background(crc_id, key, info.getName())
                        break
        except:
            pass
        self.is_scanning = False

    def save_biss_key_background(self, full_id, key, name):
        target = get_softcam_path()
        date_str = time.strftime("%d-%m-%Y")
        try:
            lines = [l for l in open(target).readlines() if f"F {full_id.upper()}" not in l.upper()]
            lines.append(f"F {full_id.upper()} 00000000 {key.upper()} ;{name} (Auto) | {date_str}\n")
            with open(target, "w") as f:
                f.writelines(lines)
            restart_softcam_global()
            addNotification(MessageBox, f"Found: {name}", type=MessageBox.TYPE_INFO, timeout=3)
        except:
            pass

class BissManagerList(Screen):
    def __init__(self, session):
        self.ui = AutoScale()
        Screen.__init__(self, session)
        self.skin = f"""<screen position="center,center" size="{self.ui.px(1000)},{self.ui.px(700)}" title="BissPro - Key Editor">
            <widget name="keylist" position="{self.ui.px(20)},{self.ui.px(20)}" size="{self.ui.px(960)},{self.ui.px(520)}" itemHeight="{self.ui.px(50)}" />
            <eLabel text="GREEN: Edit | RED: Delete" position="50,600" size="800,50" font="Regular;26" />
        </screen>"""
        self["keylist"] = MenuList([])
        self["actions"] = ActionMap(["ColorActions", "OkCancelActions"], {
            "green": self.edit_key,
            "red": self.delete_confirm,
            "cancel": self.close
        })
        self.onLayoutFinish.append(self.load_keys)

    def load_keys(self):
        p = get_softcam_path()
        keys = []
        if os.path.exists(p):
            keys = [l.strip() for l in open(p).readlines() if l.startswith("F ")]
        self["keylist"].setList(keys)

    def edit_key(self):
        curr = self["keylist"].getCurrent()
        if curr:
            self.old = curr
            self.session.openWithCallback(self.finish_edit, HexInputScreen, curr.split(";")[-1], curr.split()[3])

    def finish_edit(self, key):
        if key:
            p = get_softcam_path()
            lines = open(p).readlines()
            with open(p, "w") as f:
                for l in lines:
                    f.write(l.replace(self.old, self.old.replace(self.old.split()[3], key)))
            self.load_keys()
            restart_softcam_global()

    def delete_confirm(self):
        if self["keylist"].getCurrent():
            self.session.openWithCallback(self.delete_key, MessageBox, "Delete selected key?", MessageBox.TYPE_YESNO)

    def delete_key(self, ans):
        if ans:
            curr = self["keylist"].getCurrent()
            p = get_softcam_path()
            lines = [l for l in open(p).readlines() if l.strip() != curr]
            with open(p, "w") as f:
                f.writelines(lines)
            self.load_keys()
            restart_softcam_global()

class HexInputScreen(Screen):
    def __init__(self, session, channel_name="", existing_key=""):
        self.ui = AutoScale()
        Screen.__init__(self, session)
        self.skin = f"""<screen position="center,center" size="1150,650" title="BISS Input">
            <widget name="channel" position="10,20" size="1130,60" font="Regular;45" halign="center" />
            <widget name="keylabel" position="25,120" size="1100,110" font="Regular;80" halign="center" foregroundColor="#f0a30a" />
            <eLabel text="Use 0-9 for numbers | OK to confirm letter | GREEN to Save" position="50,550" size="1050,40" font="Regular;24" halign="center" />
        </screen>"""
        self["channel"] = Label(channel_name)
        self["keylabel"] = Label("")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "NumberActions", "DirectionActions"], {
            "cancel": lambda: self.close(None),
            "green": self.save,
            "ok": self.confirm,
            "left": self.move_l,
            "right": self.move_r,
            "up": self.up,
            "down": self.down,
            "0": lambda: self.keyN("0"), "1": lambda: self.keyN("1"), "2": lambda: self.keyN("2"),
            "3": lambda: self.keyN("3"), "4": lambda: self.keyN("4"), "5": lambda: self.keyN("5"),
            "6": lambda: self.keyN("6"), "7": lambda: self.keyN("7"), "8": lambda: self.keyN("8"),
            "9": lambda: self.keyN("9")
        }, -1)
        self.key = list(existing_key.upper()) if len(existing_key)==16 else ["0"]*16
        self.idx = 0
        self.chars = ["A","B","C","D","E","F"]
        self.c_idx = 0
        self.update()

    def update(self):
        res = ""
        for i, c in enumerate(self.key):
            if i == self.idx: res += f"[{c}]"
            else: res += c
        self["keylabel"].setText(res)

    def confirm(self):
        self.key[self.idx] = self.chars[self.c_idx]
        self.idx = min(15, self.idx + 1)
        self.update()

    def up(self):
        self.c_idx = (self.c_idx - 1) % 6
        self.key[self.idx] = self.chars[self.c_idx]
        self.update()

    def down(self):
        self.c_idx = (self.c_idx + 1) % 6
        self.key[self.idx] = self.chars[self.c_idx]
        self.update()

    def move_l(self):
        self.idx = max(0, self.idx - 1)
        self.update()

    def move_r(self):
        self.idx = min(15, self.idx + 1)
        self.update()

    def keyN(self, n):
        self.key[self.idx] = n
        self.idx = min(15, self.idx + 1)
        self.update()

    def save(self):
        self.close("".join(self.key))

watcher_instance = None

def main(session, **kwargs):
    session.open(BISSPro)

def Plugins(**kwargs):
    return [
        PluginDescriptor(name="BissPro Smart", description="Smart BISS Manager v1.0", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main),
        PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart)
    ]

def sessionstart(reason, session=None, **kwargs):
    global watcher_instance
    if reason == 0 and session is not None:
        watcher_instance = BissProServiceWatcher(session)

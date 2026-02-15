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
# حساب جدول الـ CRC32 ديناميكياً لتوفير مساحة الكود
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
    """دالة حساب الهاش المتوافق مع Oscam/Ncam/Emu باستخدام الجدول الديناميكي"""
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
# الإعدادات والمسارات
# ==========================================================
PLUGIN_PATH = os.path.realpath(os.path.dirname(__file__)) + "/"
VERSION_NUM = "v1.2" 

URL_VERSION = "https://raw.githubusercontent.com/anow2008/BissPro-Smart/main/version.txt"
URL_PLUGIN  = "https://raw.githubusercontent.com/anow2008/BissPro-Smart/main/plugin.py"
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
        self["menu"].onSelectionChanged.append(self.update_menu_logo)
        
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {"ok": self.ok, "cancel": self.close, "red": self.action_add, "green": self.action_editor, "yellow": self.action_update, "blue": self.action_auto}, -1)
        self.onLayoutFinish.append(self.build_menu)
        self.onLayoutFinish.append(self.load_main_logo)
        self.onLayoutFinish.append(self.check_for_updates)
        self.update_clock()

    def update_menu_logo(self):
        curr = self["menu"].getCurrent()
        if curr:
            act = curr[1][-1]
            icon_path = os.path.join(PLUGIN_PATH, "icons", f"{act}.png")
            if os.path.exists(icon_path): self["main_logo"].instance.setPixmap(LoadPixmap(path=icon_path))
            else: self.load_main_logo()

    def load_main_logo(self):
        logo_path = os.path.join(PLUGIN_PATH, "plugin.png")
        if os.path.exists(logo_path): self["main_logo"].instance.setPixmap(LoadPixmap(path=logo_path))

    def check_for_updates(self): Thread(target=self.thread_check_version).start()

    def thread_check_version(self):
        try:
            import ssl; ctx = ssl._create_unverified_context()
            v_url = URL_VERSION + "?nocache=" + str(random.randint(1000, 9999))
            remote_data = urlopen(v_url, timeout=10, context=ctx).read().decode("utf-8")
            remote_search = re.search(r"(\d+\.\d+)", remote_data)
            if remote_search:
                remote_v = float(remote_search.group(1)); local_v = float(re.search(r"(\d+\.\d+)", VERSION_NUM).group(1))
                if remote_v > local_v:
                    self.session.openWithCallback(self.install_update, MessageBox, "New Version v%s available!\nUpdate?" % str(remote_v), MessageBox.TYPE_YESNO)
        except: pass

    def install_update(self, answer):
        if answer: self["status"].setText("Updating..."); Thread(target=self.do_plugin_download).start()

    def do_plugin_download(self):
        try:
            import ssl; ctx = ssl._create_unverified_context()
            new_code = urlopen(URL_PLUGIN, timeout=15, context=ctx).read()
            with open(os.path.join(PLUGIN_PATH, "plugin.py"), "wb") as f: f.write(new_code)
            self.res = (True, "Updated Successfully! Restart Enigma2.")
        except Exception as e: self.res = (False, "Failed: " + str(e))
        self.timer.start(100, True)

    def update_clock(self):
        self["time_label"].setText(time.strftime("%H:%M:%S"))
        self["date_label"].setText(time.strftime("%A, %d %B %Y"))

    def build_menu(self):
        icon_dir = os.path.join(PLUGIN_PATH, "icons")
        menu_items = [("Add Key", "Manual BISS Entry", "add", "add.png"), ("Key Editor", "Manage stored keys", "editor", "editor.png"), ("Download Softcam", "Full update from server", "upd", "update.png"), ("Autoroll", "Smart search for current channel", "auto", "auto.png")]
        lst = []
        for name, desc, act, icon_file in menu_items:
            path = os.path.join(icon_dir, icon_file)
            pixmap = LoadPixmap(path=path) if os.path.exists(path) else None
            res = (name, [MultiContentEntryPixmapAlphaTest(pos=(self.ui.px(15), self.ui.px(15)), size=(self.ui.px(70), self.ui.px(70)), png=pixmap), MultiContentEntryText(pos=(self.ui.px(110), self.ui.px(10)), size=(self.ui.px(450), self.ui.px(45)), font=0, text=name, flags=RT_VALIGN_TOP), MultiContentEntryText(pos=(self.ui.px(110), self.ui.px(55)), size=(self.ui.px(450), self.ui.px(35)), font=1, text=desc, flags=RT_VALIGN_TOP, color=0xbbbbbb), act])
            lst.append(res)
        self["menu"].l.setList(lst)
        if hasattr(self["menu"].l, 'setFont'): 
            self["menu"].l.setFont(0, gFont("Regular", self.ui.font(36))); self["menu"].l.setFont(1, gFont("Regular", self.ui.font(24)))
        self.update_menu_logo()

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

    def action_editor(self): self.session.open(BissManagerList)

    def manual_done(self, key=None):
        if key is None: return
        service = self.session.nav.getCurrentService()
        if not service: return
        info = service.info(); combined_id = get_biss_hash(info.getInfo(iServiceInformation.sSID), info.getInfo(iServiceInformation.sVideoPID))
        if self.save_biss_key(combined_id, key, info.getName()): self.res = (True, f"Saved with Hash: {combined_id}")
        else: self.res = (False, "File Error")
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

    def action_update(self): 
        self["status"].setText("Downloading Softcam..."); self["main_progress"].setValue(50); Thread(target=self.do_update).start()

    def do_update(self):
        try:
            import ssl; ctx = ssl._create_unverified_context()
            data = urlopen("https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key", context=ctx).read()
            tp = get_softcam_path()
            with open(tp, "wb") as f: f.write(data)
            os.chmod(tp, 0o644); restart_softcam_global(); self.res = (True, "Softcam Updated Successfully")
        except: self.res = (False, "Softcam Update Failed")
        self.timer.start(100, True)

    def action_auto(self):
        service = self.session.nav.getCurrentService()
        if service: self["status"].setText("Autorolling..."); self["main_progress"].setValue(40); Thread(target=self.do_auto, args=(service,)).start()

    def do_auto(self, service):
        try:
            import ssl; ctx = ssl._create_unverified_context()
            info = service.info(); t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            freq = str(int(t_data.get("frequency", 0)/1000 if t_data.get("frequency", 0)>50000 else t_data.get("frequency", 0)))
            sr = str(int(t_data.get("symbol_rate", 0)/1000 if t_data.get("symbol_rate", 0)>1000 else t_data.get("symbol_rate", 0)))
            raw_id = get_biss_hash(info.getInfo(iServiceInformation.sSID), info.getInfo(iServiceInformation.sVideoPID))
            raw_data = urlopen(DATA_SOURCE, timeout=12, context=ctx).read().decode("utf-8")
            m = re.search(r"(?i)"+re.escape(freq)+r".*?"+re.escape(sr)+r"[\s\S]{0,150}?(([0-9A-Fa-f]{2}[\s\t:=-]*){8})", raw_data)
            if m:
                ckey = re.sub(r'[^0-9A-Fa-f]', '', m.group(1)).upper()
                if self.save_biss_key(raw_id, ckey, info.getName()): self.res = (True, f"Key Found! Hash: {raw_id}")
                else: self.res = (False, "Write Error")
            else: self.res = (False, "Not found")
        except: self.res = (False, "Auto Error")
        self.timer.start(100, True)

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
            raw_data = urlopen(DATA_SOURCE, timeout=10, context=ctx).read().decode("utf-8")
            m = re.search(r"(?i)"+re.escape(freq)+r".*?"+re.escape(sr)+r"[\s\S]{0,150}?(([0-9A-Fa-f]{2}[\s\t:=-]*){8})", raw_data)
            if m:
                ckey = re.sub(r'[^0-9A-Fa-f]', '', m.group(1)).upper()
                raw_id = get_biss_hash(info.getInfo(iServiceInformation.sSID), info.getInfo(iServiceInformation.sVideoPID))
                target = get_softcam_path(); lines = []
                if os.path.exists(target):
                    with open(target, "r") as f:
                        for l in f:
                            if f"F {raw_id.upper()}" not in l.upper(): lines.append(l)
                lines.append(f"F {raw_id.upper()} 00000000 {ckey} ;{info.getName()} (Auto)\n")
                with open(target, "w") as f: f.writelines(lines)
                os.chmod(target, 0o644); restart_softcam_global()
        except: pass
        self.is_scanning = False

class BissManagerList(Screen):
    def __init__(self, session):
        self.ui = AutoScale(); Screen.__init__(self, session)
        self.skin = f"""<screen position="center,center" size="{self.ui.px(1000)},{self.ui.px(700)}" title="BissPro - Key Editor"><widget name="keylist" position="{self.ui.px(20)},{self.ui.px(20)}" size="{self.ui.px(960)},{self.ui.px(520)}" itemHeight="{self.ui.px(50)}" scrollbarMode="showOnDemand" /><eLabel position="0,{self.ui.px(560)}" size="{self.ui.px(1000)},{self.ui.px(140)}" backgroundColor="#252525" zPosition="-1" /><eLabel position="{self.ui.px(30)},{self.ui.px(590)}" size="{self.ui.px(30)},{self.ui.px(30)}" backgroundColor="#00ff00" /><eLabel text="GREEN: Edit" position="{self.ui.px(75)},{self.ui.px(585)}" size="{self.ui.px(300)},{self.ui.px(40)}" font="Regular;26" transparent="1" /><eLabel position="{self.ui.px(30)},{self.ui.px(635)}" size="{self.ui.px(30)},{self.ui.px(30)}" backgroundColor="#ff0000" /><eLabel text="RED: Delete" position="{self.ui.px(75)},{self.ui.px(630)}" size="{self.ui.px(300)},{self.ui.px(40)}" font="Regular;26" transparent="1" /></screen>"""
        self["keylist"] = MenuList([]); self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {"green": self.edit_key, "cancel": self.close, "red": self.delete_confirm}, -1)
        self.onLayoutFinish.append(self.load_keys)
    def load_keys(self):
        path = get_softcam_path(); keys = []
        if os.path.exists(path):
            with open(path, "r") as f:
                for line in f:
                    if line.strip().upper().startswith("F "): keys.append(line.strip())
        self["keylist"].setList(keys)
    def edit_key(self):
        curr = self["keylist"].getCurrent()
        if curr: self.old_line = curr; parts = curr.split(); self.session.openWithCallback(self.finish_edit, HexInputScreen, curr.split(";")[-1] if ";" in curr else "Unknown", parts[3] if len(parts)>3 else "")
    def finish_edit(self, new_key=None):
        if new_key is None: return
        path = get_softcam_path(); parts = self.old_line.split(); parts[3] = str(new_key).upper(); new_line = " ".join(parts)
        with open(path, "r") as f: lines = f.readlines()
        with open(path, "w") as f:
            for l in lines: f.write((new_line+"\n") if l.strip()==self.old_line.strip() else l)
        self.load_keys(); restart_softcam_global()
    def delete_confirm(self):
        if self["keylist"].getCurrent(): self.session.openWithCallback(self.delete_key, MessageBox, "Delete this key?", MessageBox.TYPE_YESNO)
    def delete_key(self, answer):
        if answer:
            curr = self["keylist"].getCurrent(); path = get_softcam_path()
            with open(path, "r") as f: lines = f.readlines()
            with open(path, "w") as f:
                for l in lines:
                    if l.strip() != curr.strip(): f.write(l)
            self.load_keys(); restart_softcam_global()

class HexInputScreen(Screen):
    def __init__(self, session, ch_name="", exist_key=""):
        self.ui = AutoScale(); Screen.__init__(self, session)
        self.skin = f"""<screen position="center,center" size="{self.ui.px(1150)},{self.ui.px(650)}" title="BissPro - Key Input" backgroundColor="#1a1a1a"><widget name="channel" position="{self.ui.px(10)},{self.ui.px(20)}" size="{self.ui.px(1130)},{self.ui.px(60)}" font="Regular;{self.ui.font(45)}" halign="center" foregroundColor="#00ff00" transparent="1" /><widget name="progress" position="{self.ui.px(175)},{self.ui.px(90)}" size="{self.ui.px(800)},{self.ui.px(10)}" foregroundColor="#00ff00" /><widget name="keylabel" position="{self.ui.px(25)},{self.ui.px(120)}" size="{self.ui.px(1100)},{self.ui.px(110)}" font="Regular;{self.ui.font(80)}" halign="center" foregroundColor="#f0a30a" transparent="1" /><widget name="channel_data" position="{self.ui.px(10)},{self.ui.px(240)}" size="{self.ui.px(1130)},{self.ui.px(50)}" font="Regular;{self.ui.font(32)}" halign="center" foregroundColor="#ffffff" transparent="1" /><widget name="char_list" position="{self.ui.px(1020)},{self.ui.px(120)}" size="{self.ui.px(100)},{self.ui.px(300)}" font="Regular;{self.ui.font(45)}" halign="center" foregroundColor="#ffffff" transparent="1" /><eLabel position="0,{self.ui.px(460)}" size="{self.ui.px(1150)},{self.ui.px(190)}" backgroundColor="#252525" zPosition="-1" /><widget name="l_red" position="{self.ui.px(115)},{self.ui.px(495)}" size="{self.ui.px(150)},{self.ui.px(40)}" font="Regular;{self.ui.font(26)}" transparent="1" /><widget name="l_green" position="{self.ui.px(365)},{self.ui.px(495)}" size="{self.ui.px(150)},{self.ui.px(40)}" font="Regular;{self.ui.font(26)}" transparent="1" /></screen>"""
        self["channel"] = Label(ch_name); self["channel_data"] = Label(""); self["keylabel"] = Label(""); self["char_list"] = Label(""); self["progress"] = ProgressBar()
        self["l_red"] = Label("Exit"); self["l_green"] = Label("Save")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "NumberActions", "DirectionActions"], {"cancel": self.exit_clean, "red": self.exit_clean, "green": self.save, "ok": self.confirm_char, "left": self.move_left, "right": self.move_right, "up": self.move_char_up, "down": self.move_char_down, "0": lambda: self.keyNum("0"), "1": lambda: self.keyNum("1"), "2": lambda: self.keyNum("2"), "3": lambda: self.keyNum("3"), "4": lambda: self.keyNum("4"), "5": lambda: self.keyNum("5"), "6": lambda: self.keyNum("6"), "7": lambda: self.keyNum("7"), "8": lambda: self.keyNum("8"), "9": lambda: self.keyNum("9")}, -1)
        self.key_list = list(exist_key.upper()) if (exist_key and len(exist_key)==16) else ["0"]*16
        self.index = 0; self.chars = ["A","B","C","D","E","F"]; self.char_index = 0; self.onLayoutFinish.append(self.get_active_channel_data); self.update_display()
    def get_active_channel_data(self):
        service = self.session.nav.getCurrentService()
        if service:
            i = service.info(); t = i.getInfoObject(iServiceInformation.sTransponderData); f = t.get("frequency", 0); f = f/1000 if f>50000 else f
            self["channel_data"].setText(f"FREQ: {int(f)} | SID: %04X | VPID: %04X" % (i.getInfo(iServiceInformation.sSID)&0xFFFF, i.getInfo(iServiceInformation.sVideoPID)&0xFFFF if i.getInfo(iServiceInformation.sVideoPID)!=-1 else 0))
    def update_display(self):
        res = []
        for i in range(16):
            res.append("[%s]" % self.key_list[i] if i==self.index else self.key_list[i])
            if (i+1)%4==0 and i<15: res.append("-")
        self["keylabel"].setText("".join(res)); self["progress"].setValue(int(((self.index+1)/16.0)*100))
        c_col = ""
        for i, c in enumerate(self.chars): c_col += ("\c00f0a30a[%s]\n" if i==self.char_index else "\c00ffffff %s \n") % c
        self["char_list"].setText(c_col)
    def confirm_char(self): self.key_list[self.index] = self.chars[self.char_index]; self.index = min(15, self.index + 1); self.update_display()
    def move_char_up(self): self.char_index = (self.char_index-1)%len(self.chars); self.update_display()
    def move_char_down(self): self.char_index = (self.char_index+1)%len(self.chars); self.update_display()
    def keyNum(self, n): self.key_list[self.index] = n; self.index = min(15, self.index + 1); self.update_display()
    def move_left(self): self.index = max(0, self.index - 1); self.update_display()
    def move_right(self): self.index = min(15, self.index + 1); self.update_display()
    def save(self): self.close("".join(self.key_list))
    def exit_clean(self): self.close(None)

def main(session, **kwargs): session.open(BISSPro)
def Plugins(**kwargs): return [PluginDescriptor(name="BissPro Smart", description="Advanced BISS Key Tool", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=main)]

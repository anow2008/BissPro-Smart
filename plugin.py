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
import os, re, shutil, time, random
from urllib.request import urlopen
from threading import Thread

# ==========================================================
# الإعدادات والمسارات - (تم الحفاظ عليها بالكامل)
# ==========================================================
PLUGIN_PATH = os.path.dirname(__file__) + "/"
VERSION_NUM = "v1.2" 

URL_VERSION = "https://raw.githubusercontent.com/anow2008/BissPro-Smart/main/version.txt"
URL_NOTES   = "https://raw.githubusercontent.com/anow2008/BissPro-Smart/main/notes.txt"
URL_PLUGIN  = "https://raw.githubusercontent.com/anow2008/BissPro-Smart/main/plugin.py"
DATA_SOURCE = "https://raw.githubusercontent.com/anow2008/softcam.key/main/biss.txt"

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
    # تعديلك المطلوب: ريستارت رسمي بدل القتل فقط
    scripts = ["/etc/init.d/softcam", "/etc/init.d/cardserver", "/etc/init.d/softcam.oscam", "/etc/init.d/softcam.ncam"]
    restarted = False
    for s in scripts:
        if os.path.exists(s):
            os.system(f"{s} restart >/dev/null 2>&1")
            restarted = True
            break
    if not restarted:
        os.system("killall -9 oscam ncam 2>/dev/null")
        time.sleep(1.0)
        for s in scripts:
            if os.path.exists(s): os.system(f"{s} start >/dev/null 2>&1")

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
            <widget name="version_label" position="{self.ui.px(850)},{self.ui.px(525)}" size="{self.ui.px(200)},{self.ui.px(35)}" font="Regular;{self.ui.font(22)}" halign="right" foregroundColor="#888888" transparent="1" />
            <eLabel position="{self.ui.px(50)},{self.ui.px(565)}" size="{self.ui.px(1000)},{self.ui.px(2)}" backgroundColor="#333333" />
            <widget name="status" position="{self.ui.px(50)},{self.ui.px(670)}" size="{self.ui.px(1000)},{self.ui.px(70)}" font="Regular;{self.ui.font(32)}" halign="center" valign="center" transparent="1" foregroundColor="#f0a30a"/>
        </screen>"""
        
        self["version_label"] = Label(f"Ver: {VERSION_NUM}")
        self["status"] = Label("Ready")
        self["time_label"] = Label(""); self["date_label"] = Label("")
        self["main_progress"] = ProgressBar()
        self["main_logo"] = Pixmap()
        
        self.clock_timer = eTimer()
        try: self.clock_timer.callback.append(self.update_clock)
        except: self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        
        self.timer = eTimer()
        try: self.timer.callback.append(self.show_result)
        except: self.timer.timeout.connect(self.show_result)
        
        self["menu"] = MenuList([])
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {"ok": self.ok, "cancel": self.close, "red": self.action_add, "green": self.action_editor, "yellow": self.action_update, "blue": self.action_auto}, -1)
        
        # ربط الحركة باللوجو
        self["menu"].onSelectionChanged.append(self.update_dynamic_logo)
        
        self.onLayoutFinish.append(self.build_menu)
        self.onLayoutFinish.append(self.check_for_updates)
        self.update_clock()

    def update_clock(self):
        self["time_label"].setText(time.strftime("%H:%M:%S"))
        self["date_label"].setText(time.strftime("%A, %d %B %Y"))

    def check_for_updates(self):
        Thread(target=self.thread_check_version).start()

    def thread_check_version(self):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            v_url = URL_VERSION + "?nocache=" + str(random.randint(1000, 9999))
            remote_data = urlopen(v_url, timeout=10, context=ctx).read().decode("utf-8")
            remote_search = re.search(r"(\d+\.\d+)", remote_data)
            if remote_search:
                remote_v = float(remote_search.group(1))
                local_v = float(re.search(r"(\d+\.\d+)", VERSION_NUM).group(1))
                if remote_v > local_v:
                    msg = "New Version v%s available!\n\nUpdate now?" % str(remote_v)
                    self.session.openWithCallback(self.install_update, MessageBox, msg, MessageBox.TYPE_YESNO)
        except: pass

    def install_update(self, answer):
        if answer:
            self["status"].setText("Updating...")
            Thread(target=self.do_plugin_download).start()

    def do_plugin_download(self):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            new_code = urlopen(URL_PLUGIN, timeout=15, context=ctx).read()
            with open(os.path.join(PLUGIN_PATH, "plugin.py"), "wb") as f: f.write(new_code)
            self.res = (True, "Updated! Restart Enigma2.")
        except Exception as e: self.res = (False, "Error: " + str(e))
        self.timer.start(100, True)

    def build_menu(self):
        icon_dir = os.path.join(PLUGIN_PATH, "icons/")
        menu_items = [
            ("Add Key", "Manual BISS Entry", "add", icon_dir + "add.png"), 
            ("Key Editor", "Manage stored keys", "editor", icon_dir + "editor.png"), 
            ("Download Softcam", "Full update from server", "upd", icon_dir + "update.png"), 
            ("Autoroll", "Smart search for current channel", "auto", icon_dir + "auto.png")
        ]
        lst = []
        for name, desc, act, icon_path in menu_items:
            pixmap = LoadPixmap(cached=True, path=icon_path) if os.path.exists(icon_path) else None
            res = (name, [
                MultiContentEntryPixmapAlphaTest(pos=(self.ui.px(15), self.ui.px(15)), size=(self.ui.px(70), self.ui.px(70)), png=pixmap), 
                MultiContentEntryText(pos=(self.ui.px(110), self.ui.px(10)), size=(self.ui.px(450), self.ui.px(45)), font=0, text=name, flags=RT_VALIGN_TOP), 
                MultiContentEntryText(pos=(self.ui.px(110), self.ui.px(55)), size=(self.ui.px(450), self.ui.px(35)), font=1, text=desc, flags=RT_VALIGN_TOP, color=0xbbbbbb), 
                act, icon_path
            ])
            lst.append(res)
        self["menu"].l.setList(lst)
        self["menu"].l.setFont(0, gFont("Regular", self.ui.font(36)))
        self["menu"].l.setFont(1, gFont("Regular", self.ui.font(24)))
        self.update_dynamic_logo()

    def update_dynamic_logo(self):
        curr = self["menu"].getCurrent()
        if curr:
            icon_path = curr[1][-1]
            if os.path.exists(icon_path):
                self["main_logo"].instance.setPixmap(LoadPixmap(path=icon_path))
            else:
                p_logo = os.path.join(PLUGIN_PATH, "plugin.png")
                if os.path.exists(p_logo): self["main_logo"].instance.setPixmap(LoadPixmap(path=p_logo))

    def ok(self):
        curr = self["menu"].getCurrent()
        if curr:
            act = curr[1][-2]
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
        info = service.info()
        combined_id = ("%04X" % (info.getInfo(iServiceInformation.sSID) & 0xFFFF)) + ("%04X" % (info.getInfo(iServiceInformation.sVideoPID) & 0xFFFF) if info.getInfo(iServiceInformation.sVideoPID) != -1 else "0000")
        if self.save_biss_key(combined_id, key, info.getName()): self.res = (True, f"Saved: {info.getName()}")
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
            os.chmod(target, 0o644)
            restart_softcam_global(); return True
        except: return False

    def show_result(self): 
        self["main_progress"].setValue(0); self["status"].setText("Ready")
        self.session.open(MessageBox, self.res[1], MessageBox.TYPE_INFO if self.res[0] else MessageBox.TYPE_ERROR, timeout=5)

    def action_update(self): 
        self["status"].setText("Downloading Softcam..."); 
        Thread(target=self.do_update).start()

    def do_update(self):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            data = urlopen("https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key", context=ctx).read()
            target_path = get_softcam_path()
            with open(target_path, "wb") as f: f.write(data)
            os.chmod(target_path, 0o644)
            restart_softcam_global()
            self.res = (True, "Softcam Updated Successfully")
        except: self.res = (False, "Softcam Update Failed")
        self.timer.start(100, True)

    def action_auto(self):
        service = self.session.nav.getCurrentService()
        if service: 
            self["status"].setText("Autorolling..."); 
            Thread(target=self.do_auto, args=(service,)).start()

    def do_auto(self, service):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            info = service.info(); ch_name = info.getName()
            t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            freq_raw = t_data.get("frequency", 0)
            curr_freq = str(int(freq_raw / 1000 if freq_raw > 50000 else freq_raw))
            raw_sid = info.getInfo(iServiceInformation.sSID); raw_vpid = info.getInfo(iServiceInformation.sVideoPID)
            combined_id = ("%04X" % (raw_sid & 0xFFFF)) + ("%04X" % (raw_vpid & 0xFFFF) if raw_vpid != -1 else "0000")
            raw_data = urlopen(DATA_SOURCE, timeout=12, context=ctx).read().decode("utf-8")
            pattern = re.escape(curr_freq) + r'[\s\S]{0,500}?(([0-9A-Fa-f]{2}[\s\t:=-]*){8})'
            m = re.search(pattern, raw_data, re.I)
            if m:
                clean_key = re.sub(r'[^0-9A-Fa-f]', '', m.group(1)).upper()
                if len(clean_key) == 16:
                    if self.save_biss_key(combined_id, clean_key, ch_name): self.res = (True, f"Key Found: {clean_key}")
                    else: self.res = (False, "Write Error")
                else: self.res = (False, "Invalid key")
            else: self.res = (False, "Not found")
        except: self.res = (False, "Auto Error")
        self.timer.start(100, True)

# ==========================================================
# (Watcher) تم الحفاظ عليه مع ربطه بنفس وظائف الحفظ الرسمية
# ==========================================================
class BissProServiceWatcher:
    def __init__(self, session):
        self.session = session
        self.check_timer = eTimer()
        try: self.check_timer.callback.append(self.check_service)
        except: self.check_timer.timeout.connect(self.check_service)
        self.session.nav.event.append(self.on_event)
        self.is_scanning = False

    def on_event(self, event):
        if event in (0, 1): self.check_timer.start(6000, True) 

    def check_service(self):
        if self.is_scanning: return
        service = self.session.nav.getCurrentService()
        if not service: return
        info = service.info()
        if info.getInfo(iServiceInformation.sIsCrypted):
            self.is_scanning = True
            Thread(target=self.bg_do_auto, args=(service,)).start()

    def bg_do_auto(self, service):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            info = service.info(); ch_name = info.getName()
            t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            if t_data:
                freq_raw = t_data.get("frequency", 0)
                curr_freq = str(int(freq_raw / 1000 if freq_raw > 50000 else freq_raw))
                raw_sid = info.getInfo(iServiceInformation.sSID); raw_vpid = info.getInfo(iServiceInformation.sVideoPID)
                combined_id = ("%04X" % (raw_sid & 0xFFFF)) + ("%04X" % (raw_vpid & 0xFFFF) if raw_vpid != -1 else "0000")
                raw_data = urlopen(DATA_SOURCE, timeout=12, context=ctx).read().decode("utf-8")
                pattern = re.escape(curr_freq) + r'[\s\S]{0,500}?(([0-9A-Fa-f]{2}[\s\t:=-]*){8})'
                m = re.search(pattern, raw_data, re.I)
                if m:
                    clean_key = re.sub(r'[^0-9A-Fa-f]', '', m.group(1)).upper()
                    if len(clean_key) == 16:
                        # استخدام الحفظ الرسمي لضمان الريستارت
                        self.save_biss_bg(combined_id, clean_key, ch_name)
        except: pass
        self.is_scanning = False

    def save_biss_bg(self, full_id, key, name):
        target = get_softcam_path()
        try:
            lines = []
            if os.path.exists(target):
                with open(target, "r") as f:
                    for line in f:
                        if f"F {full_id.upper()}" not in line.upper(): lines.append(line)
            lines.append(f"F {full_id.upper()} 00000000 {key.upper()} ;{name} (AutoRoll)\n")
            with open(target, "w") as f: f.writelines(lines)
            os.chmod(target, 0o644)
            restart_softcam_global()
        except: pass

class BissManagerList(Screen):
    def __init__(self, session):
        self.ui = AutoScale()
        Screen.__init__(self, session)
        self.skin = f"""
        <screen position="center,center" size="{self.ui.px(1000)},{self.ui.px(700)}" title="BissPro - Key Editor">
            <widget name="keylist" position="{self.ui.px(20)},{self.ui.px(20)}" size="{self.ui.px(960)},{self.ui.px(520)}" itemHeight="{self.ui.px(50)}" scrollbarMode="showOnDemand" />
            <eLabel position="0,{self.ui.px(560)}" size="{self.ui.px(1000)},{self.ui.px(140)}" backgroundColor="#252525" zPosition="-1" />
            <eLabel text="GREEN: Edit | RED: Delete" position="{self.ui.px(50)},{self.ui.px(600)}" size="{self.ui.px(500)},{self.ui.px(40)}" font="Regular;26" transparent="1" />
        </screen>"""
        self["keylist"] = MenuList([])
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {"green": self.edit_key, "cancel": self.close, "red": self.delete_confirm}, -1)
        self.onLayoutFinish.append(self.load_keys)
    def load_keys(self):
        path = get_softcam_path(); keys = []
        if os.path.exists(path):
            with open(path, "r") as f:
                for line in f:
                    if line.strip().upper().startswith("F "): keys.append(line.strip())
        self["keylist"].setList(keys)
    def edit_key(self):
        current = self["keylist"].getCurrent()
        if current:
            parts = current.split(); ch_name = current.split(";")[-1] if ";" in current else "Unknown"; self.old_line = current
            self.session.openWithCallback(self.finish_edit, HexInputScreen, ch_name, parts[3] if len(parts) > 3 else "")
    def finish_edit(self, new_key=None):
        if new_key is None: return
        path = get_softcam_path(); parts = self.old_line.split(); parts[3] = str(new_key).upper(); new_line = " ".join(parts)
        try:
            with open(path, "r") as f: lines = f.readlines()
            with open(path, "w") as f:
                for line in lines:
                    if line.strip() == self.old_line.strip(): f.write(new_line + "\n")
                    else: f.write(line)
            self.load_keys(); restart_softcam_global()
        except: pass
    def delete_confirm(self):
        current = self["keylist"].getCurrent()
        if current: self.session.openWithCallback(self.delete_key, MessageBox, "Delete this key?", MessageBox.TYPE_YESNO)
    def delete_key(self, answer):
        if answer:
            current = self["keylist"].getCurrent(); path = get_softcam_path()
            try:
                with open(path, "r") as f: lines = f.readlines()
                with open(path, "w") as f:
                    for line in lines:
                        if line.strip() != current.strip(): f.write(line)
                self.load_keys(); restart_softcam_global()
            except: pass

class HexInputScreen(Screen):
    def __init__(self, session, channel_name="", existing_key=""):
        self.ui = AutoScale()
        Screen.__init__(self, session)
        self.skin = f"""
        <screen position="center,center" size="{self.ui.px(1150)},{self.ui.px(650)}" title="BissPro - Key Input">
            <widget name="channel" position="{self.ui.px(10)},{self.ui.px(20)}" size="{self.ui.px(1130)},{self.ui.px(60)}" font="Regular;{self.ui.font(45)}" halign="center" foregroundColor="#00ff00" />
            <widget name="keylabel" position="{self.ui.px(25)},{self.ui.px(120)}" size="{self.ui.px(1100)},{self.ui.px(110)}" font="Regular;{self.ui.font(80)}" halign="center" foregroundColor="#f0a30a" />
            <widget name="char_list" position="{self.ui.px(1020)},{self.ui.px(120)}" size="{self.ui.px(100)},{self.ui.px(300)}" font="Regular;{self.ui.font(45)}" />
        </screen>"""
        self["channel"] = Label(f"{channel_name}"); self["keylabel"] = Label(""); self["char_list"] = Label("")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "NumberActions", "DirectionActions"], {
            "cancel": self.close, "ok": self.confirm_char, "left": self.move_left, "right": self.move_right, "up": self.move_char_up, "down": self.move_char_down,
            "0": lambda: self.keyNum("0"), "1": lambda: self.keyNum("1"), "2": lambda: self.keyNum("2"), "3": lambda: self.keyNum("3"), "4": lambda: self.keyNum("4"), 
            "5": lambda: self.keyNum("5"), "6": lambda: self.keyNum("6"), "7": lambda: self.keyNum("7"), "8": lambda: self.keyNum("8"), "9": lambda: self.keyNum("9")
        }, -1)
        self.key_list = list(existing_key.upper()) if (existing_key and len(existing_key) == 16) else ["0"] * 16
        self.index = 0; self.chars = ["A","B","C","D","E","F"]; self.char_index = 0
        self.update_display()
    def update_display(self):
        dp = []
        for i in range(16):
            c = self.key_list[i]; dp.append("[%s]" % c if i == self.index else c)
            if (i+1)%4==0 and i<15: dp.append("-")
        self["keylabel"].setText("".join(dp))
        cl = ""
        for i, c in enumerate(self.chars): cl += ("\c00f0a30a[%s]\n" if i == self.char_index else "\c00ffffff %s \n") % c
        self["char_list"].setText(cl)
    def confirm_char(self): self.key_list[self.index] = self.chars[self.char_index]; self.index = min(15, self.index + 1); self.update_display()
    def keyNum(self, n): self.key_list[self.index] = n; self.index = min(15, self.index + 1); self.update_display()
    def move_left(self): self.index = max(0, self.index - 1); self.update_display()
    def move_right(self): self.index = min(15, self.index + 1); self.update_display()
    def move_char_up(self): self.char_index = (self.char_index - 1) % len(self.chars); self.update_display()
    def move_char_down(self): self.char_index = (self.char_index + 1) % len(self.chars); self.update_display()
    def save(self): self.close("".join(self.key_list))

watcher_instance = None
def main(session, **kwargs): session.open(BISSPro)
def Plugins(**kwargs):
    return [PluginDescriptor(name="BissPro Smart", description="Smart BISS Manager v1.2", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main),
            PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart)]
def sessionstart(reason, session=None, **kwargs):
    global watcher_instance
    if reason == 0 and session is not None: 
        if watcher_instance is None: watcher_instance = BissProServiceWatcher(session)

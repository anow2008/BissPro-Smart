# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from enigma import iServiceInformation, gFont, eTimer, getDesktop, RT_VALIGN_TOP, RT_VALIGN_CENTER
from Tools.LoadPixmap import LoadPixmap
import os, re, shutil, time, random
from urllib.request import urlopen, urlretrieve
from threading import Thread

# ==========================================================
# الإعدادات والمسارات
# ==========================================================
PLUGIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/BissPro/"
VERSION_NUM = "v1.1"

URL_VERSION = "https://raw.githubusercontent.com/anow2008/BissPro-Smart/main/version.txt"
URL_NOTES   = "https://raw.githubusercontent.com/anow2008/BissPro-Smart/main/notes.txt"
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
            <widget name="menu" position="{self.ui.px(50)},{self.ui.px(80)}" size="{self.ui.px(1000)},{self.ui.px(410)}" itemHeight="{self.ui.px(100)}" scrollbarMode="showOnDemand" transparent="1"/>
            <widget name="main_progress" position="{self.ui.px(50)},{self.ui.px(510)}" size="{self.ui.px(1000)},{self.ui.px(12)}" foregroundColor="#00ff00" backgroundColor="#222222" />
            <widget name="version_label" position="{self.ui.px(850)},{self.ui.px(525)}" size="{self.ui.px(200)},{self.ui.px(35)}" font="Regular;{self.ui.font(22)}" halign="right" foregroundColor="#888888" transparent="1" />
            <eLabel position="{self.ui.px(50)},{self.ui.px(555)}" size="{self.ui.px(1000)},{self.ui.px(2)}" backgroundColor="#333333" />
            <eLabel position="{self.ui.px(70)},{self.ui.px(585)}" size="{self.ui.px(25)},{self.ui.px(25)}" backgroundColor="#ff0000" />
            <widget name="btn_red" position="{self.ui.px(105)},{self.ui.px(580)}" size="{self.ui.px(180)},{self.ui.px(40)}" font="Regular;{self.ui.font(24)}" transparent="1" />
            <eLabel position="{self.ui.px(300)},{self.ui.px(585)}" size="{self.ui.px(25)},{self.ui.px(25)}" backgroundColor="#00ff00" />
            <widget name="btn_green" position="{self.ui.px(335)},{self.ui.px(580)}" size="{self.ui.px(180)},{self.ui.px(40)}" font="Regular;{self.ui.font(24)}" transparent="1" />
            <eLabel position="{self.ui.px(530)},{self.ui.px(585)}" size="{self.ui.px(25)},{self.ui.px(25)}" backgroundColor="#ffff00" />
            <widget name="btn_yellow" position="{self.ui.px(565)},{self.ui.px(580)}" size="{self.ui.px(220)},{self.ui.px(40)}" font="Regular;{self.ui.font(24)}" transparent="1" />
            <eLabel position="{self.ui.px(790)},{self.ui.px(585)}" size="{self.ui.px(25)},{self.ui.px(25)}" backgroundColor="#0000ff" />
            <widget name="btn_blue" position="{self.ui.px(825)},{self.ui.px(580)}" size="{self.ui.px(180)},{self.ui.px(40)}" font="Regular;{self.ui.font(24)}" transparent="1" />
            <widget name="status" position="{self.ui.px(50)},{self.ui.px(660)}" size="{self.ui.px(1000)},{self.ui.px(70)}" font="Regular;{self.ui.font(32)}" halign="center" valign="center" transparent="1" foregroundColor="#f0a30a"/>
        </screen>"""
        
        self["btn_red"] = Label("Add Key")
        self["btn_green"] = Label("Editor")
        self["btn_yellow"] = Label("Download Softcam")
        self["btn_blue"] = Label("Autoroll")
        self["version_label"] = Label(f"Version: {VERSION_NUM}")
        self["status"] = Label("Ready")
        self["time_label"] = Label(""); self["date_label"] = Label("")
        self["main_progress"] = ProgressBar()
        
        self.clock_timer = eTimer()
        try: self.clock_timer.callback.append(self.update_clock)
        except: self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        
        self.timer = eTimer()
        try: self.timer.callback.append(self.show_result)
        except: self.timer.timeout.connect(self.show_result)
        
        self["menu"] = MenuList([])
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {"ok": self.ok, "cancel": self.close, "red": self.action_add, "green": self.action_editor, "yellow": self.action_update, "blue": self.action_auto}, -1)
        self.onLayoutFinish.append(self.build_menu)
        self.onLayoutFinish.append(self.check_for_updates)
        self.update_clock()

    def check_for_updates(self):
        Thread(target=self.thread_check_version).start()

    def thread_check_version(self):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            v_url = URL_VERSION + "?nocache=" + str(random.randint(1000, 9999))
            remote_data = urlopen(v_url, timeout=10, context=ctx).read().decode("utf-8")
            
            remote_search = re.search(r"(\d+\.\d+)", remote_data)
            local_search = re.search(r"(\d+\.\d+)", VERSION_NUM)
            
            if remote_search and local_search:
                remote_v = float(remote_search.group(1))
                local_v = float(local_search.group(1))
                
                if remote_v > local_v:
                    try:
                        n_url = URL_NOTES + "?nocache=" + str(random.randint(1000, 9999))
                        update_notes = urlopen(n_url, timeout=7, context=ctx).read().decode("utf-8").strip()
                    except: update_notes = "Improvements and bug fixes."

                    msg = "New Version v%s is available!\n\n" % str(remote_v)
                    msg += "What's New:\n%s\n\n" % update_notes
                    msg += "Do you want to update now?"
                    self.session.openWithCallback(self.install_update, MessageBox, msg, MessageBox.TYPE_YESNO)
        except: pass

    def install_update(self, answer):
        if answer:
            self["status"].setText("Updating Plugin...")
            Thread(target=self.do_plugin_download).start()

    def do_plugin_download(self):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            # تحميل الكود الجديد في الذاكرة أولاً
            new_code = urlopen(URL_PLUGIN, timeout=15, context=ctx).read()
            
            # تغيير صلاحيات المجلد والملف قبل الكتابة (للتأكد)
            os.system("chmod 755 " + PLUGIN_PATH)
            os.system("chmod 755 " + PLUGIN_PATH + "plugin.py")
            
            # الكتابة بطريقة Binary لضمان عدم تلف الملف
            with open(PLUGIN_PATH + "plugin.py", "wb") as f:
                f.write(new_code)
            
            self.res = (True, "Plugin Updated Successfully!\nPlease RESTART Enigma2 to apply changes.")
        except Exception as e:
            self.res = (False, "Update Failed: " + str(e))
        self.timer.start(100, True)

    def update_clock(self):
        self["time_label"].setText(time.strftime("%H:%M:%S"))
        self["date_label"].setText(time.strftime("%A, %d %B %Y"))

    def build_menu(self):
        icon_dir = PLUGIN_PATH + "icons/"
        menu_items = [
            ("Add Key", "Manual BISS Entry", "add", icon_dir + "add.png"), 
            ("Key Editor", "Manage stored SoftCam keys", "editor", icon_dir + "editor.png"), 
            ("Download Softcam", "Update SoftCam.Key from server", "upd", icon_dir + "update.png"), 
            ("Autoroll", "Search current channel key online", "auto", icon_dir + "auto.png")
        ]
        lst = []
        for name, desc, act, icon_path in menu_items:
            pixmap = None
            if os.path.exists(icon_path):
                pixmap = LoadPixmap(cached=True, path=icon_path)
            
            res = (name, [
                MultiContentEntryPixmapAlphaTest(pos=(self.ui.px(15), self.ui.px(15)), size=(self.ui.px(70), self.ui.px(70)), png=pixmap), 
                MultiContentEntryText(pos=(self.ui.px(110), self.ui.px(10)), size=(self.ui.px(850), self.ui.px(45)), font=0, text=name, flags=RT_VALIGN_TOP), 
                MultiContentEntryText(pos=(self.ui.px(110), self.ui.px(55)), size=(self.ui.px(850), self.ui.px(35)), font=1, text=desc, flags=RT_VALIGN_TOP, color=0xbbbbbb), 
                act
            ])
            lst.append(res)
        self["menu"].l.setList(lst)
        if hasattr(self["menu"].l, 'setFont'): 
            self["menu"].l.setFont(0, gFont("Regular", self.ui.font(36)))
            self["menu"].l.setFont(1, gFont("Regular", self.ui.font(24)))

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
            restart_softcam_global(); return True
        except: return False

    def show_result(self): 
        self["main_progress"].setValue(0)
        self["status"].setText("Ready")
        self.session.open(MessageBox, self.res[1], MessageBox.TYPE_INFO if self.res[0] else MessageBox.TYPE_ERROR, timeout=5)

    def action_update(self): 
        self["status"].setText("Downloading Softcam File..."); 
        self["main_progress"].setValue(50); 
        Thread(target=self.do_update).start()

    def do_update(self):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            data = urlopen("https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key", context=ctx).read()
            with open("/tmp/SoftCam.Key", "wb") as f: f.write(data)
            shutil.copy("/tmp/SoftCam.Key", get_softcam_path())
            restart_softcam_global()
            self.res = (True, "Softcam File Updated Successfully")
        except: self.res = (False, "Softcam Update Failed")
        self.timer.start(100, True)

    def action_auto(self):
        service = self.session.nav.getCurrentService()
        if service: 
            self["status"].setText("Autorolling..."); 
            self["main_progress"].setValue(40); 
            Thread(target=self.do_auto, args=(service,)).start()

    def do_auto(self, service):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            info = service.info()
            ch_name = info.getName()
            t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            freq_raw = t_data.get("frequency", 0)
            curr_freq = str(int(freq_raw / 1000 if freq_raw > 50000 else freq_raw))
            raw_sid = info.getInfo(iServiceInformation.sSID)
            raw_vpid = info.getInfo(iServiceInformation.sVideoPID)
            combined_id = ("%04X" % (raw_sid & 0xFFFF)) + ("%04X" % (raw_vpid & 0xFFFF) if raw_vpid != -1 else "0000")
            raw_data = urlopen(DATA_SOURCE, timeout=12, context=ctx).read().decode("utf-8")
            self["main_progress"].setValue(70)
            pattern = re.escape(curr_freq) + r'[\s\S]{0,500}?(([0-9A-Fa-f]{2}[\s\t:=-]*){8})'
            m = re.search(pattern, raw_data, re.I)
            if m:
                clean_key = re.sub(r'[^0-9A-Fa-f]', '', m.group(1)).upper()
                if len(clean_key) == 16:
                    if self.save_biss_key(combined_id, clean_key, ch_name):
                        self.res = (True, f"Key Found & Saved: {clean_key}")
                    else: self.res = (False, "Error Writing to SoftCam.Key")
                else: self.res = (False, "Found invalid key length")
            else: self.res = (False, f"Key not found for freq {curr_freq}")
        except Exception as e:
            self.res = (False, f"Error: {str(e)}")
        self.timer.start(100, True)

# محرر المفاتيح وشاشة الإدخال تظل كما هي في الكود السابق...
# [بقية الكود الخاص بـ BissManagerList و HexInputScreen و main و Plugins]

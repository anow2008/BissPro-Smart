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
        def addNotification(*args, **kwargs): pass

from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from enigma import iServiceInformation, gFont, eTimer, getDesktop, RT_VALIGN_TOP, RT_VALIGN_CENTER, quitMainloop
from Tools.LoadPixmap import LoadPixmap
import os, re, shutil, time, random, csv, struct
import urllib.request
from threading import Thread

# ==========================================================
# دالة الهاش الاحترافية - تم ضبطها لتظهر الهاش المطلوب 
# ==========================================================
def get_biss_crc32(sid, freq):
    # تحويل التردد لـ MHz والـ SID لـ Hex ودمجهم بطريقة الـ MPEG
    # مثال: تردد 11000 و SID 1 -> الهاش 9DE5E789
    data = struct.pack(">IH", int(freq), int(sid))
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= (byte << 24)
        for _ in range(8):
            if crc & 0x80000000:
                crc = (crc << 1) ^ 0x04C11DB7
            else:
                crc <<= 1
        crc &= 0xFFFFFFFF
    return "%08X" % crc

# ==========================================================
# الإعدادات والمسارات الأصلية (نسخة الـ 500 سطر)
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
    paths = [
        "/etc/tuxbox/config/oscam/SoftCam.Key", 
        "/etc/tuxbox/config/ncam/SoftCam.Key", 
        "/etc/tuxbox/config/SoftCam.Key", 
        "/usr/keys/SoftCam.Key"
    ]
    for p in paths:
        if os.path.exists(p): return p
    return "/etc/tuxbox/config/SoftCam.Key"

def restart_softcam_global():
    os.system("killall -9 oscam ncam vicardd gbox 2>/dev/null")
    time.sleep(1.2)
    scripts = ["/etc/init.d/softcam", "/etc/init.d/cardserver", "/etc/init.d/softcam.oscam", "/etc/init.d/softcam.ncam"]
    for s in scripts:
        if os.path.exists(s):
            os.system(f"{s} start >/dev/null 2>&1")

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
        
        # السكين الأصلي كامل بدون حذف
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
        self.clock_timer.callback.append(self.update_clock)
        self.clock_timer.start(1000)
        
        self.timer = eTimer()
        self.timer.callback.append(self.show_result)
        
        self["menu"] = MenuList([])
        self["menu"].onSelectionChanged.append(self.update_dynamic_logo)
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.ok, "cancel": self.close, "red": self.action_add, 
            "green": self.action_editor, "yellow": self.action_update, "blue": self.action_auto
        }, -1)
        
        self.onLayoutFinish.append(self.build_menu)
        self.update_clock()

    def update_clock(self):
        self["time_label"].setText(time.strftime("%H:%M:%S"))
        self["date_label"].setText(time.strftime("%A, %d %B %Y"))

    def update_dynamic_logo(self):
        curr = self["menu"].getCurrent()
        if curr:
            icon_file = {"add": "add.png", "editor": "editor.png", "upd": "Download Softcam.png", "auto": "auto.png"}.get(curr[1][-1], "plugin.png")
            path = os.path.join(PLUGIN_PATH, "icons/", icon_file)
            if os.path.exists(path): self["main_logo"].instance.setPixmap(LoadPixmap(path=path))

    def build_menu(self):
        icon_dir = os.path.join(PLUGIN_PATH, "icons/")
        items = [
            ("Add Key", "Manual BISS Entry", "add", icon_dir + "add.png"), 
            ("Key Editor", "Manage stored keys", "editor", icon_dir + "editor.png"), 
            ("Download Softcam", "Full update from server", "upd", icon_dir + "Download Softcam.png"), 
            ("Autoroll", "Smart search for current channel", "auto", icon_dir + "auto.png")
        ]
        lst = []
        for name, desc, act, icon in items:
            pix = LoadPixmap(path=icon) if os.path.exists(icon) else None
            lst.append((name, [
                MultiContentEntryPixmapAlphaTest(pos=(15, 15), size=(70, 70), png=pix), 
                MultiContentEntryText(pos=(110, 10), size=(450, 45), font=0, text=name), 
                MultiContentEntryText(pos=(110, 55), size=(450, 35), font=1, text=desc, color=0xbbbbbb), 
                act
            ]))
        self["menu"].l.setList(lst)
        self["menu"].l.setFont(0, gFont("Regular", 36)); self["menu"].l.setFont(1, gFont("Regular", 24))

    def ok(self):
        curr = self["menu"].getCurrent()
        if curr:
            act = curr[1][-1]
            if act == "add": self.action_add()
            elif act == "editor": self.action_editor()
            elif act == "upd": self.action_update()
            elif act == "auto": self.action_auto()

    def action_add(self):
        s = self.session.nav.getCurrentService()
        if s: self.session.openWithCallback(self.manual_done, HexInputScreen, s.info().getName())

    def manual_done(self, key=None):
        if key:
            info = self.session.nav.getCurrentService().info()
            t = info.getInfoObject(iServiceInformation.sTransponderData)
            f = int(t.get("frequency", 0) / 1000 if t.get("frequency", 0) > 50000 else t.get("frequency", 0))
            crc_id = get_biss_crc32(info.getInfo(iServiceInformation.sSID), f)
            if self.save_biss_key(crc_id, key, info.getName()): self.res = (True, f"Saved [{crc_id}]")
            self.timer.start(100, True)

    def save_biss_key(self, full_id, key, name):
        target = get_softcam_path()
        try:
            lines = [l for l in open(target).readlines() if f"F {full_id.upper()}" not in l.upper()] if os.path.exists(target) else []
            lines.append(f"F {full_id.upper()} 00000000 {key.upper()} ;{name} | {time.strftime('%d-%m-%Y')}\n")
            with open(target, "w") as f: f.writelines(lines)
            restart_softcam_global(); return True
        except: return False

    def action_editor(self): self.session.open(BissManagerList)
    def action_update(self): self["status"].setText("Updating..."); Thread(target=self.do_upd).start()
    def do_upd(self):
        try:
            d = urllib.request.urlopen("https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key").read()
            open(get_softcam_path(), "wb").write(d); restart_softcam_global(); self.res = (True, "Updated")
        except: self.res = (False, "Failed")
        self.timer.start(100, True)

    def action_auto(self):
        s = self.session.nav.getCurrentService()
        if s: self["status"].setText("Searching..."); Thread(target=self.do_auto, args=(s,)).start()

    def do_auto(self, s):
        try:
            info = s.info(); t = info.getInfoObject(iServiceInformation.sTransponderData)
            f = int(t.get("frequency", 0) / 1000 if t.get("frequency", 0) > 50000 else t.get("frequency", 0))
            crc_id = get_biss_crc32(info.getInfo(iServiceInformation.sSID), f)
            resp = urllib.request.urlopen(GOOGLE_SHEET_URL).read().decode("utf-8").splitlines()
            found = False
            for row in csv.reader(resp):
                if len(row) >= 2 and str(f) in row[0]:
                    k = row[1].replace(" ", "").upper()
                    if len(k) == 16: self.save_biss_key(crc_id, k, info.getName()); found = True; break
            self.res = (True, "Found") if found else (False, "Not found")
        except: self.res = (False, "Error")
        self.timer.start(100, True)

    def show_result(self): 
        self["status"].setText("Ready")
        self.session.open(MessageBox, self.res[1], MessageBox.TYPE_INFO if self.res[0] else MessageBox.TYPE_ERROR)

# ==========================================================
# شاشة تعديل الشفرات - كاملة بكل أزرارها وتصميمها
# ==========================================================
class BissManagerList(Screen):
    def __init__(self, session):
        self.ui = AutoScale()
        Screen.__init__(self, session)
        self.skin = f"""
        <screen position="center,center" size="{self.ui.px(1000)},{self.ui.px(700)}" title="BissPro - Key Editor">
            <widget name="keylist" position="{self.ui.px(20)},{self.ui.px(20)}" size="{self.ui.px(960)},{self.ui.px(520)}" itemHeight="{self.ui.px(50)}" scrollbarMode="showOnDemand" />
            <eLabel position="0,{self.ui.px(560)}" size="{self.ui.px(1000)},{self.ui.px(140)}" backgroundColor="#252525" zPosition="-1" />
            <eLabel position="{self.ui.px(30)},{self.ui.px(590)}" size="{self.ui.px(30)},{self.ui.px(30)}" backgroundColor="#00ff00" />
            <eLabel text="GREEN: Edit" position="{self.ui.px(75)},{self.ui.px(585)}" size="{self.ui.px(300)},{self.ui.px(40)}" font="Regular;26" transparent="1" />
            <eLabel position="{self.ui.px(30)},{self.ui.px(635)}" size="{self.ui.px(30)},{self.ui.px(30)}" backgroundColor="#ff0000" />
            <eLabel text="RED: Delete" position="{self.ui.px(75)},{self.ui.px(630)}" size="{self.ui.px(300)},{self.ui.px(40)}" font="Regular;26" transparent="1" />
        </screen>"""
        self["keylist"] = MenuList([])
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "green": self.edit_key, "cancel": self.close, "red": self.delete_confirm
        }, -1)
        self.onLayoutFinish.append(self.load_keys)

    def load_keys(self):
        p = get_softcam_path(); keys = []
        if os.path.exists(p): keys = [l.strip() for l in open(p).readlines() if l.strip().upper().startswith("F ")]
        self["keylist"].setList(keys)

    def edit_key(self):
        curr = self["keylist"].getCurrent()
        if curr:
            parts = curr.split(); name = curr.split(";")[-1] if ";" in curr else "Key"
            self.old_line = curr
            self.session.openWithCallback(self.finish_edit, HexInputScreen, name, parts[3] if len(parts) > 3 else "")

    def finish_edit(self, new_key=None):
        if not new_key: return
        p = get_softcam_path(); parts = self.old_line.split(); parts[3] = new_key.upper(); new_line = " ".join(parts)
        ls = open(p).readlines()
        with open(p, "w") as f:
            for l in ls: f.write((new_line + "\n") if l.strip() == self.old_line.strip() else l)
        self.load_keys(); restart_softcam_global()

    def delete_confirm(self): 
        self.session.openWithCallback(self.delete_key, MessageBox, "Are you sure you want to delete this key?", MessageBox.TYPE_YESNO)

    def delete_key(self, ans):
        if ans:
            curr = self["keylist"].getCurrent(); p = get_softcam_path()
            ls = open(p).readlines()
            with open(p, "w") as f:
                for l in ls: 
                    if l.strip() != curr.strip(): f.write(l)
            self.load_keys(); restart_softcam_global()

# ==========================================================
# شاشة إدخال الشفرة (Keyboard) - كاملة مع التنقل والـ ProgressBar
# ==========================================================
class HexInputScreen(Screen):
    def __init__(self, session, channel_name="", existing_key=""):
        self.ui = AutoScale()
        Screen.__init__(self, session)
        self.skin = f"""
        <screen position="center,center" size="{self.ui.px(1150)},{self.ui.px(650)}" title="BissPro - Key Input" backgroundColor="#1a1a1a">
            <widget name="channel" position="{self.ui.px(10)},{self.ui.px(20)}" size="{self.ui.px(1130)},{self.ui.px(60)}" font="Regular;{self.ui.font(45)}" halign="center" foregroundColor="#00ff00" transparent="1" />
            <widget name="progress" position="{self.ui.px(175)},{self.ui.px(90)}" size="{self.ui.px(800)},{self.ui.px(10)}" foregroundColor="#00ff00" />
            <widget name="keylabel" position="{self.ui.px(25)},{self.ui.px(120)}" size="{self.ui.px(1100)},{self.ui.px(110)}" font="Regular;{self.ui.font(80)}" halign="center" foregroundColor="#f0a30a" transparent="1" />
            <widget name="channel_data" position="{self.ui.px(10)},{self.ui.px(280)}" size="{self.ui.px(1130)},{self.ui.px(50)}" font="Regular;{self.ui.font(32)}" halign="center" foregroundColor="#ffffff" transparent="1" />
            <widget name="char_list" position="{self.ui.px(1020)},{self.ui.px(120)}" size="{self.ui.px(100)},{self.ui.px(300)}" font="Regular;{self.ui.font(45)}" halign="center" foregroundColor="#ffffff" transparent="1" />
            <eLabel position="0,{self.ui.px(460)}" size="{self.ui.px(1150)},{self.ui.px(190)}" backgroundColor="#252525" zPosition="-1" />
            <eLabel position="{self.ui.px(80)},{self.ui.px(500)}" size="{self.ui.px(25)},{self.ui.px(25)}" backgroundColor="#ff0000" />
            <widget name="l_red" position="{self.ui.px(115)},{self.ui.px(495)}" size="{self.ui.px(150)},{self.ui.px(40)}" font="Regular;{self.ui.font(26)}" transparent="1" />
            <eLabel position="{self.ui.px(330)},{self.ui.px(500)}" size="{self.ui.px(25)},{self.ui.px(25)}" backgroundColor="#00ff00" />
            <widget name="l_green" position="{self.ui.px(365)},{self.ui.px(495)}" size="{self.ui.px(150)},{self.ui.px(40)}" font="Regular;{self.ui.font(26)}" transparent="1" />
            <eLabel position="{self.ui.px(580)},{self.ui.px(500)}" size="{self.ui.px(25)},{self.ui.px(25)}" backgroundColor="#ffff00" />
            <widget name="l_yellow" position="{self.ui.px(615)},{self.ui.px(495)}" size="{self.ui.px(150)},{self.ui.px(40)}" font="Regular;{self.ui.font(26)}" transparent="1" />
            <eLabel position="{self.ui.px(830)},{self.ui.px(500)}" size="{self.ui.px(25)},{self.ui.px(25)}" backgroundColor="#0000ff" />
            <widget name="l_blue" position="{self.ui.px(865)},{self.ui.px(495)}" size="{self.ui.px(200)},{self.ui.px(40)}" font="Regular;{self.ui.font(26)}" transparent="1" />
        </screen>"""
        
        self["channel"] = Label(channel_name); self["channel_data"] = Label("")
        self["keylabel"] = Label(""); self["char_list"] = Label(""); self["progress"] = ProgressBar()
        self["l_red"] = Label("Exit"); self["l_green"] = Label("Save")
        self["l_yellow"] = Label("Clear"); self["l_blue"] = Label("Reset")
        
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "NumberActions", "DirectionActions"], {
            "cancel": self.close, "red": self.close, "green": self.save, "yellow": self.clear, "blue": self.reset,
            "ok": self.confirm, "left": self.left, "right": self.right, "up": self.up, "down": self.down,
            "0": lambda: self.keyN("0"), "1": lambda: self.keyN("1"), "2": lambda: self.keyN("2"), "3": lambda: self.keyN("3"),
            "4": lambda: self.keyN("4"), "5": lambda: self.keyN("5"), "6": lambda: self.keyN("6"), "7": lambda: self.keyN("7"),
            "8": lambda: self.keyN("8"), "9": lambda: self.keyN("9")
        }, -1)
        
        self.k = list(existing_key.upper()) if len(existing_key) == 16 else ["0"]*16
        self.idx = 0; self.chars = ["A","B","C","D","E","F"]; self.c_idx = 0
        self.onLayoutFinish.append(self.get_data); self.upd()

    def get_data(self):
        s = self.session.nav.getCurrentService()
        if s:
            info = s.info(); t = info.getInfoObject(iServiceInformation.sTransponderData)
            f = t.get("frequency", 0); f = f/1000 if f>50000 else f
            sid = info.getInfo(iServiceInformation.sSID)
            self["channel_data"].setText(f"Freq: {int(f)} | SID: {hex(sid).upper().replace('0X','')}")

    def upd(self):
        res = ""
        for i in range(16):
            char = self.k[i]
            res += ("[%s]" if i==self.idx else " %s ") % char
            if (i+1)%4 == 0 and i<15: res += "-"
        self["keylabel"].setText(res)
        self["progress"].setValue(int(((self.idx+1)/16.0)*100))
        c_res = ""
        for i, c in enumerate(self.chars):
            c_res += ("\c00f0a30a[%s]\n" if i==self.c_idx else " %s \n") % c
        self["char_list"].setText(c_res)

    def confirm(self): self.k[self.idx] = self.chars[self.c_idx]; self.idx = min(15, self.idx+1); self.upd()
    def up(self): self.c_idx = (self.c_idx-1)%6; self.upd()
    def down(self): self.c_idx = (self.c_idx+1)%6; self.upd()
    def left(self): self.idx = max(0, self.idx-1); self.upd()
    def right(self): self.idx = min(15, self.idx+1); self.upd()
    def keyN(self, n): self.k[self.idx] = n; self.idx = min(15, self.idx+1); self.upd()
    def clear(self): self.k[self.idx] = "0"; self.upd()
    def reset(self): self.k = ["0"]*16; self.idx = 0; self.upd()
    def save(self): self.close("".join(self.k))

# ==========================================================
# نظام المراقبة التلقائي (AutoRoll)
# ==========================================================
class BissProServiceWatcher:
    def __init__(self, session):
        self.session = session
        self.timer = eTimer()
        self.timer.callback.append(self.check)
        self.session.nav.event.append(self.on_ev)

    def on_ev(self, ev):
        if ev in (0, 1): self.timer.start(8000, True)

    def check(self):
        s = self.session.nav.getCurrentService()
        if s and s.info().getInfo(iServiceInformation.sIsCrypted):
            Thread(target=self.bg_auto, args=(s,)).start()

    def bg_auto(self, s):
        try:
            info = s.info(); t = info.getInfoObject(iServiceInformation.sTransponderData)
            f = int(t.get("frequency", 0) / 1000 if t.get("frequency", 0) > 50000 else t.get("frequency", 0))
            crc_id = get_biss_crc32(info.getInfo(iServiceInformation.sSID), f)
            resp = urllib.request.urlopen(GOOGLE_SHEET_URL, timeout=10).read().decode("utf-8").splitlines()
            for row in csv.reader(resp):
                if len(row) >= 2 and str(f) in row[0]:
                    k = row[1].replace(" ", "").upper()
                    if len(k) == 16:
                        p = get_softcam_path()
                        ls = [l for l in open(p).readlines() if f"F {crc_id}" not in l.upper()] if os.path.exists(p) else []
                        ls.append(f"F {crc_id} 00000000 {k} ;{info.getName()} (AutoRoll)\n")
                        with open(p, "w") as f_out: f_out.writelines(ls)
                        restart_softcam_global()
                        addNotification(MessageBox, f"AutoRoll: {info.getName()}\nKey: {k}", type=MessageBox.TYPE_INFO, timeout=4)
                        break
        except: pass

watcher = None
def main(session, **kwargs): session.open(BISSPro)
def Plugins(**kwargs):
    return [
        PluginDescriptor(name="BissPro Smart", description="Smart BISS Manager v1.0", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main),
        PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart)
    ]
def sessionstart(reason, session=None, **kwargs):
    global watcher
    if reason == 0 and session and watcher is None: watcher = BissProServiceWatcher(session)

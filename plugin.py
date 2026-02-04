# -*- coding: utf-8 -*-
# BissPro Smart v1.1 - Background Skin Edition
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from Components.Pixmap import Pixmap
from Components.MultiContent import MultiContentEntryText
from enigma import iServiceInformation, gFont, eTimer, getDesktop, RT_VALIGN_TOP
import os, re, shutil, time
from urllib.request import urlopen, urlretrieve
from threading import Thread

# المسارات
PLUGIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/BissPro/"
DATA_SOURCE = "https://raw.githubusercontent.com/anow2008/softcam.key/refs/heads/main/biss.txt"

def get_softcam_path():
    paths = ["/etc/tuxbox/config/oscam/SoftCam.Key", "/etc/tuxbox/config/ncam/SoftCam.Key", "/usr/keys/SoftCam.Key"]
    for p in paths:
        if os.path.exists(p): return p
    return "/etc/tuxbox/config/oscam/SoftCam.Key"

def restart_softcam():
    os.system("killall -9 oscam ncam 2>/dev/null")
    time.sleep(1.2)
    scripts = ["/etc/init.d/softcam", "/etc/init.d/softcam.oscam", "/etc/init.d/softcam.ncam"]
    for s in scripts:
        if os.path.exists(s):
            os.system(f"'{s}' restart >/dev/null 2>&1")
            break

class BISSPro(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        
        # تصميم الواجهة المعتمد على صورة الخلفية الكاملة
        self.skin = f"""
        <screen position="center,center" size="1100,780" title="BissPro Smart" flags="wfNoBorder" backgroundColor="transparent">
            <widget name="bg_image" position="0,0" size="1100,780" zPosition="-1" alphatest="blend" />
            
            <widget name="date_label" position="50,40" size="400,40" font="Regular;26" halign="left" foregroundColor="#ffffff" transparent="1" />
            <widget name="time_label" position="750,40" size="300,40" font="Regular;26" halign="right" foregroundColor="#ffffff" transparent="1" />
            
            <widget name="menu" position="115,185" size="870,400" itemHeight="98" selectionPixmap="{PLUGIN_PATH}icons/selection.png" scrollbarMode="hide" transparent="1"/>
            
            <widget name="main_progress" position="200,605" size="700,10" foregroundColor="#00ff00" backgroundColor="#222222" />
            
            <widget name="status" position="50,640" size="1000,60" font="Regular;32" halign="center" foregroundColor="#f0a30a" transparent="1" />
            
            <widget name="version_label" position="850,730" size="200,30" font="Regular;20" halign="right" foregroundColor="#888888" transparent="1" />
        </screen>"""

        self["bg_image"] = Pixmap()
        self["date_label"] = Label("")
        self["time_label"] = Label("")
        self["status"] = Label("Ready")
        self["version_label"] = Label("v1.1")
        self["main_progress"] = ProgressBar()
        self["menu"] = MenuList([])

        self.clock_timer = eTimer()
        self.clock_timer.callback.append(self.update_clock)
        self.clock_timer.start(1000)

        self.timer = eTimer()
        self.timer.callback.append(self.show_result)

        self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.ok, "cancel": self.close}, -1)
        self.onLayoutFinish.append(self.init_layout)

    def init_layout(self):
        # تحميل صورة الخلفية من المجلد
        bg_path = PLUGIN_PATH + "background.png"
        if os.path.exists(bg_path):
            self["bg_image"].instance.setPixmapFromFile(bg_path)
        self.build_menu()
        self.update_clock()

    def update_clock(self):
        self["time_label"].setText(time.strftime("%H:%M:%S"))
        self["date_label"].setText(time.strftime("%A, %B %d"))

    def build_menu(self):
        # تنسيق النصوص لتكون مطابقة لأماكن الفراغات في صورتك
        menu_items = [
            ("Add Key", "Manual BISS Entry", "add"), 
            ("Key Editor", "Manage Saved Keys", "editor"), 
            ("Download Softcam", "Update From Server", "upd"), 
            ("Smart Auto Search", "Search Online Now", "auto")
        ]
        lst = []
        for name, desc, act in menu_items:
            res = (name, [
                # النص الأساسي (يسار المستطيل)
                MultiContentEntryText(pos=(100, 20), size=(300, 50), font=0, text=name, flags=RT_VALIGN_TOP), 
                # الوصف (منتصف المستطيل)
                MultiContentEntryText(pos=(400, 28), size=(400, 40), font=1, text=desc, flags=RT_VALIGN_TOP, color=0xbbbbbb), 
                act
            ])
            lst.append(res)
        self["menu"].l.setList(lst)
        self["menu"].l.setFont(0, gFont("Regular", 36))
        self["menu"].l.setFont(1, gFont("Regular", 22))

    def ok(self):
        curr = self["menu"].getCurrent()
        if not curr: return
        act = curr[1][-1]
        if act == "add": self.action_add()
        elif act == "editor": self.session.open(BissManagerList)
        elif act == "upd": self.action_update()
        elif act == "auto": self.action_auto()

    def action_add(self):
        service = self.session.nav.getCurrentService()
        if service: self.session.openWithCallback(self.manual_done, HexInputScreen, service.info().getName())

    def manual_done(self, key=None):
        if not key: return
        service = self.session.nav.getCurrentService()
        info = service.info()
        combined_id = ("%04X" % (info.getInfo(iServiceInformation.sSID) & 0xFFFF)) + ("%04X" % (info.getInfo(iServiceInformation.sVideoPID) & 0xFFFF) if info.getInfo(iServiceInformation.sVideoPID) != -1 else "0000")
        if self.save_biss_key(combined_id, key, info.getName()): self.res = (True, "Key Saved Successfully")
        else: self.res = (False, "Error Saving Key")
        self.timer.start(100, True)

    def action_update(self):
        self["status"].setText("Updating Softcam..."); self["main_progress"].setValue(50)
        Thread(target=self.do_update).start()

    def do_update(self):
        try:
            urlretrieve("https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key", "/tmp/SoftCam.Key")
            shutil.copy("/tmp/SoftCam.Key", get_softcam_path())
            restart_softcam(); self.res = (True, "Softcam Updated!")
        except: self.res = (False, "Update Failed")
        self.timer.start(100, True)

    def action_auto(self):
        service = self.session.nav.getCurrentService()
        if service:
            self["status"].setText("Searching Online..."); self["main_progress"].setValue(30)
            Thread(target=self.do_auto, args=(service,)).start()

    def do_auto(self, service):
        try:
            info = service.info(); ch_name = info.getName()
            t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            freq_raw = t_data.get("frequency", 0)
            curr_freq = str(int(freq_raw / 1000 if freq_raw > 50000 else freq_raw))
            raw_sid = info.getInfo(iServiceInformation.sSID)
            raw_vpid = info.getInfo(iServiceInformation.sVideoPID)
            combined_id = ("%04X" % (raw_sid & 0xFFFF)) + ("%04X" % (raw_vpid & 0xFFFF) if raw_vpid != -1 else "0000")
            
            raw_data = urlopen(DATA_SOURCE, timeout=12).read().decode("utf-8")
            self["main_progress"].setValue(70)
            
            # --- تعديل البحث ليتخطى 1000 حرف (ليدعم ملف biss.txt الخاص بك) ---
            search_range = 1000
            pattern = re.escape(curr_freq) + r'[\s\S]{0,' + str(search_range) + r'}?(([0-9A-Fa-f]{2}[\s\t:=-]*){8})'
            m = re.search(pattern, raw_data, re.I)
            
            if m:
                clean_key = re.sub(r'[^0-9A-Fa-f]', '', m.group(1)).upper()
                if len(clean_key) == 16:
                    if self.save_biss_key(combined_id, clean_key, ch_name): self.res = (True, f"Found: {clean_key}")
                    else: self.res = (False, "Save Error")
                else: self.res = (False, "Invalid Key Format")
            else: self.res = (False, f"No Key Found for {curr_freq}")
        except Exception as e: self.res = (False, str(e))
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
            restart_softcam(); return True
        except: return False

    def show_result(self):
        self["main_progress"].setValue(0); self["status"].setText("Ready")
        self.session.open(MessageBox, self.res[1], MessageBox.TYPE_INFO if self.res[0] else MessageBox.TYPE_ERROR, timeout=5)

# --- شاشات الإدخال (تستخدم ألوان متناسقة مع الخلفية الغامقة) ---
class BissManagerList(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = """<screen position="center,center" size="1000,600" title="Key Editor" backgroundColor="#151515">
            <widget name="keylist" position="20,20" size="960,480" itemHeight="40" scrollbarMode="showOnDemand" transparent="1" />
            <eLabel text="Green: Edit | Red: Delete" position="center,530" size="600,40" font="Regular;26" halign="center" />
        </screen>"""
        self["keylist"] = MenuList([]); self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {"green": self.edit, "red": self.delete, "cancel": self.close}, -1)
        self.onLayoutFinish.append(self.load_keys)
    def load_keys(self):
        p = get_softcam_path(); keys = [l.strip() for l in open(p).readlines() if l.strip().upper().startswith("F ")] if os.path.exists(p) else []
        self["keylist"].setList(keys)
    def edit(self):
        curr = self["keylist"].getCurrent()
        if curr:
            self.old = curr; p = curr.split(); n = curr.split(";")[-1] if ";" in curr else "Key"
            self.session.openWithCallback(self.done, HexInputScreen, n, p[3])
    def done(self, key=None):
        if key:
            p = get_softcam_path(); lines = open(p).readlines()
            with open(p, "w") as f:
                for l in lines:
                    if l.strip() == self.old.strip():
                        parts = l.split(); parts[3] = key.upper(); f.write(" ".join(parts) + "\n")
                    else: f.write(l)
            self.load_keys(); restart_softcam()
    def delete(self):
        curr = self["keylist"].getCurrent()
        if curr:
            p = get_softcam_path(); lines = open(p).readlines()
            with open(p, "w") as f:
                for l in lines:
                    if l.strip() != curr.strip(): f.write(l)
            self.load_keys(); restart_softcam()

class HexInputScreen(Screen):
    def __init__(self, session, name="", key=""):
        Screen.__init__(self, session)
        self.skin = """<screen position="center,center" size="800,400" title="Input Key" backgroundColor="#101010">
            <widget name="ch" position="center,30" size="700,50" font="Regular;32" halign="center" foregroundColor="#00ff00" transparent="1" />
            <widget name="key" position="center,120" size="700,80" font="Regular;60" halign="center" foregroundColor="#f0a30a" transparent="1" />
            <eLabel text="Use Numbers / Up-Down for Letters" position="center,250" size="700,30" font="Regular;22" halign="center" />
            <eLabel text="Green: Save | Red: Exit" position="center,330" size="700,40" font="Regular;26" halign="center" />
        </screen>"""
        self["ch"] = Label(name); self["key"] = Label("")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "NumberActions", "DirectionActions"], {
            "green": self.save, "red": self.close, "left": self.L, "right": self.R, "up": self.U, "down": self.D,
            "0": lambda: self.N("0"), "1": lambda: self.N("1"), "2": lambda: self.N("2"), "3": lambda: self.N("3"), "4": lambda: self.N("4"), "5": lambda: self.N("5"), "6": lambda: self.N("6"), "7": lambda: self.N("7"), "8": lambda: self.N("8"), "9": lambda: self.N("9")
        }, -1)
        self.k = list(key) if len(key)==16 else ["0"]*16; self.i = 0; self.chars = ["A","B","C","D","E","F"]; self.ci = 0; self.upd()
    def upd(self):
        d = "".join(["[%s]" % self.k[j] if j==self.i else self.k[j] for j in range(16)])
        self["key"].setText(d)
    def N(self, n): self.k[self.i]=n; self.i=min(15, self.i+1); self.upd()
    def L(self): self.i=max(0, self.i-1); self.upd()
    def R(self): self.i=min(15, self.i+1); self.upd()
    def U(self): self.ci=(self.ci-1)%6; self.k[self.i]=self.chars[self.ci]; self.upd()
    def D(self): self.ci=(self.ci+1)%6; self.k[self.i]=self.chars[self.ci]; self.upd()
    def save(self): self.close("".join(self.k))

def main(session, **kwargs): session.open(BISSPro)
def Plugins(**kwargs): return [PluginDescriptor(name="BissPro Smart", description="Smart BISS Manager v1.1", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]

# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
# تم إزالة الاستدعاء المسبب للكراش وإبقاء الأساسيات فقط
from enigma import iServiceInformation, gFont, eTimer, getDesktop, RT_VALIGN_TOP
from Tools.LoadPixmap import LoadPixmap
import os, re, shutil, time
from urllib.request import urlopen, urlretrieve
from threading import Thread

PLUGIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/BissPro/"

def get_softcam_path():
    paths = ["/etc/tuxbox/config/oscam/SoftCam.Key", "/etc/tuxbox/config/ncam/SoftCam.Key", "/etc/tuxbox/config/SoftCam.Key", "/usr/keys/SoftCam.Key"]
    for p in paths:
        if os.path.exists(p): return p
    return "/etc/tuxbox/config/oscam/SoftCam.Key"

def restart_softcam_global():
    os.system("killall -9 oscam ncam 2>/dev/null")
    time.sleep(1)
    if os.path.exists("/etc/init.d/softcam"): os.system("/etc/init.d/softcam restart >/dev/null 2>&1")
    elif os.path.exists("/etc/init.d/softcam.oscam"): os.system("/etc/init.d/softcam.oscam restart >/dev/null 2>&1")

class BISSPro(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        # استخدام سكين بسيط ومباشر لتجنب أي تعارض في القياسات
        self.skin = """
        <screen position="center,center" size="900,600" title="BissPro Smart">
            <widget name="menu" position="20,20" size="860,400" itemHeight="100" scrollbarMode="showOnDemand" transparent="1"/>
            <widget name="status" position="20,440" size="860,50" font="Regular;30" halign="center" foregroundColor="#f0a30a" transparent="1"/>
            <widget name="main_progress" position="150,510" size="600,10" foregroundColor="#00ff00" />
            <eLabel text="OK: Select | EXIT: Close" position="20,540" size="860,30" font="Regular;22" halign="center" foregroundColor="#bbbbbb" />
        </screen>"""
        
        self["menu"] = MenuList([])
        self["status"] = Label("Ready")
        self["main_progress"] = ProgressBar()
        self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.ok, "cancel": self.close}, -1)
        
        self.timer = eTimer()
        try: self.timer_conn = self.timer.timeout.connect(self.show_result)
        except: self.timer.callback.append(self.show_result)
        
        self.onLayoutFinish.append(self.build_menu)

    def build_menu(self):
        icon_dir = PLUGIN_PATH + "icons/"
        menu_items = [
            ("Add Key", "Add BISS Key Manually", "add", "add.png"), 
            ("Key Editor", "Edit or Delete Stored Keys", "editor", "editor.png"), 
            ("Update Softcam", "Download latest SoftCam.Key", "upd", "update.png"), 
            ("Smart Auto Search", "Auto find key for current channel", "auto", "auto.png")
        ]
        
        lst = []
        for name, desc, act, icon_name in menu_items:
            # تحميل الأيقونة مع التأكد من وجودها
            p_icon = icon_dir + icon_name
            pix = None
            if os.path.exists(p_icon):
                pix = LoadPixmap(p_icon)
            
            lst.append((name, [
                MultiContentEntryPixmapAlphaTest(pos=(10, 15), size=(70, 70), png=pix),
                MultiContentEntryText(pos=(100, 15), size=(700, 40), font=0, text=name),
                MultiContentEntryText(pos=(100, 55), size=(700, 30), font=1, text=desc, color=0xbbbbbb),
                act
            ]))
            
        self["menu"].l.setList(lst)
        self["menu"].l.setItemHeight(100)
        self["menu"].l.setFont(0, gFont("Regular", 32))
        self["menu"].l.setFont(1, gFont("Regular", 22))

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
        if not key: return
        service = self.session.nav.getCurrentService()
        if not service: return
        info = service.info()
        combined_id = ("%04X%04X" % (info.getInfo(iServiceInformation.sSID) & 0xFFFF, info.getInfo(iServiceInformation.sVideoPID) & 0xFFFF))
        if self.save_biss_key(combined_id, key, info.getName()):
            self.res = (True, "Saved: " + info.getName())
        else: self.res = (False, "Error Saving Key")
        self.timer.start(100, True)

    def save_biss_key(self, full_id, key, name):
        target = get_softcam_path()
        try:
            lines = []
            if os.path.exists(target):
                with open(target, "r") as f:
                    for line in f:
                        if "F " + full_id.upper() not in line.upper(): lines.append(line)
            lines.append("F " + full_id.upper() + " 00000000 " + key.upper() + " ;" + name + "\n")
            with open(target, "w") as f: f.writelines(lines)
            restart_softcam_global(); return True
        except: return False

    def show_result(self): 
        self["status"].setText("Ready")
        self.session.open(MessageBox, self.res[1], MessageBox.TYPE_INFO if self.res[0] else MessageBox.TYPE_ERROR)

    def action_update(self): 
        self["status"].setText("Downloading...")
        Thread(target=self.do_update).start()

    def do_update(self):
        try:
            urlretrieve("https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key", "/tmp/SoftCam.Key")
            shutil.copy("/tmp/SoftCam.Key", get_softcam_path())
            restart_softcam_global()
            self.res = (True, "Softcam Updated")
        except: self.res = (False, "Update Failed")
        self.timer.start(100, True)

    def action_auto(self):
        service = self.session.nav.getCurrentService()
        if service: 
            self["status"].setText("Searching Online...")
            Thread(target=self.do_auto, args=(service,)).start()

    def do_auto(self, service):
        try:
            info = service.info()
            t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            freq = str(int(t_data.get("frequency", 0) / 1000))
            raw_data = urlopen("https://raw.githubusercontent.com/anow2008/softcam.key/refs/heads/main/biss.txt").read().decode("utf-8")
            m = re.search(re.escape(freq) + r'.*?(([0-9A-F]{2}\s*){8})', raw_data, re.I)
            if m:
                key = m.group(1).replace(" ", "").upper()
                combined_id = ("%04X%04X" % (info.getInfo(iServiceInformation.sSID) & 0xFFFF, info.getInfo(iServiceInformation.sVideoPID) & 0xFFFF))
                if self.save_biss_key(combined_id, key, info.getName()):
                    self.res = (True, "Key Found: " + key)
                else: self.res = (False, "Found but save error")
            else: self.res = (False, "No Key Found Online")
        except: self.res = (False, "Network Error")
        self.timer.start(100, True)

class BissManagerList(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = """
        <screen position="center,center" size="800,500" title="Key Editor">
            <widget name="keylist" position="10,10" size="780,420" scrollbarMode="showOnDemand" />
            <eLabel text="RED: Delete | EXIT: Back" position="10,440" size="780,40" font="Regular;24" halign="center" />
        </screen>"""
        self["keylist"] = MenuList([])
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {"cancel": self.close, "red": self.delete_confirm}, -1)
        self.onLayoutFinish.append(self.load_keys)

    def load_keys(self):
        path = get_softcam_path()
        keys = []
        if os.path.exists(path):
            with open(path, "r") as f:
                for line in f:
                    if line.strip().upper().startswith("F "): keys.append(line.strip())
        self["keylist"].setList(keys)

    def delete_confirm(self):
        if self["keylist"].getCurrent():
            self.session.openWithCallback(self.delete_key, MessageBox, "Delete this key?", MessageBox.TYPE_YESNO)

    def delete_key(self, answer):
        if answer:
            curr = self["keylist"].getCurrent()
            path = get_softcam_path()
            lines = [l for l in open(path).readlines() if l.strip() != curr]
            with open(path, "w") as f: f.writelines(lines)
            self.load_keys()

class HexInputScreen(Screen):
    def __init__(self, session, channel_name=""):
        Screen.__init__(self, session)
        self.skin = """
        <screen position="center,center" size="600,250" title="Manual Input">
            <widget name="channel" position="10,20" size="580,40" font="Regular;28" halign="center" />
            <widget name="keylabel" position="10,80" size="580,60" font="Regular;45" halign="center" foregroundColor="#f0a30a" />
            <eLabel text="Enter 16 digits then press OK" position="10,160" size="580,30" font="Regular;20" halign="center" />
        </screen>"""
        self["channel"] = Label(channel_name)
        self["keylabel"] = Label("")
        self["actions"] = ActionMap(["OkCancelActions", "NumberActions"], {
            "ok": self.save, "cancel": self.close,
            "0": lambda: self.keyNum("0"), "1": lambda: self.keyNum("1"), "2": lambda: self.keyNum("2"), 
            "3": lambda: self.keyNum("3"), "4": lambda: self.keyNum("4"), "5": lambda: self.keyNum("5"), 
            "6": lambda: self.keyNum("6"), "7": lambda: self.keyNum("7"), "8": lambda: self.keyNum("8"), "9": lambda: self.keyNum("9")
        }, -1)
        self.key = ""
        
    def keyNum(self, n):
        if len(self.key) < 16:
            self.key += n
            self["keylabel"].setText(self.key)
            
    def save(self):
        if len(self.key) == 16: self.close(self.key)
        else: self.session.open(MessageBox, "Key must be 16 digits", MessageBox.TYPE_ERROR)

def main(session, **kwargs): session.open(BISSPro)
def Plugins(**kwargs): return [PluginDescriptor(name="BissPro Smart", description="BISS Manager", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]

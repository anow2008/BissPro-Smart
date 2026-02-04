# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from enigma import iServiceInformation, gFont, eTimer, getDesktop
from Tools.LoadPixmap import LoadPixmap
import os, re, shutil, time
from urllib.request import urlopen, urlretrieve
from threading import Thread

# تحديد المسارات بشكل آمن
PLUGIN_PATH = os.path.dirname(__file__)
ICONS = os.path.join(PLUGIN_PATH, "icons")
VERSION_NUM = "v1.0"

def get_softcam_path():
    paths = ["/etc/tuxbox/config/oscam/SoftCam.Key", "/etc/tuxbox/config/ncam/SoftCam.Key", "/usr/keys/SoftCam.Key"]
    for p in paths:
        if os.path.exists(p): return p
    return "/etc/tuxbox/config/oscam/SoftCam.Key"

def restart_softcam_global():
    os.system("killall -9 oscam ncam 2>/dev/null")
    time.sleep(1)
    scripts = ["/etc/init.d/softcam", "/etc/init.d/softcam.oscam", "/etc/init.d/softcam.ncam"]
    for s in scripts:
        if os.path.exists(s):
            os.system(f"'{s}' restart >/dev/null 2>&1")
            break

class BISSPro(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        # سكين مبسط لتجنب كراش القياسات (Scaling)
        self.skin = """
        <screen position="center,center" size="850,600" title="BissPro Smart">
            <widget name="menu" position="25,20" size="800,400" itemHeight="50" scrollbarMode="showOnDemand" font="Regular;30" transparent="1" />
            <widget name="status" position="25,440" size="800,50" font="Regular;28" halign="center" foregroundColor="#f0a30a" />
            <widget name="main_progress" position="150,510" size="550,15" foregroundColor="#00ff00" />
            <eLabel text="RED: Add | GREEN: Edit | YELLOW: Update | BLUE: Auto" position="25,550" size="800,30" font="Regular;20" halign="center" />
        </screen>"""
        
        self["status"] = Label("Ready")
        self["main_progress"] = ProgressBar()
        self.res = (True, "")

        self.options = [
            ("1. Add BISS Key", "add"),
            ("2. BISS Key Editor", "editor"),
            ("3. Update Softcam Online", "upd"),
            ("4. Smart Auto Search", "auto")
        ]
        
        self["menu"] = MenuList([x[0] for x in self.options])
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.ok, 
            "cancel": self.close,
            "red": self.action_add,
            "green": self.action_editor,
            "yellow": self.action_update,
            "blue": self.action_auto
        }, -1)

        self.timer = eTimer()
        try: self.timer.timeout.connect(self.show_result)
        except: self.timer.callback.append(self.show_result)

    def ok(self):
        idx = self["menu"].getSelectedIndex()
        act = self.options[idx][1]
        if act == "add": self.action_add()
        elif act == "editor": self.action_editor()
        elif act == "upd": self.action_update()
        elif act == "auto": self.action_auto()

    def action_add(self):
        service = self.session.nav.getCurrentService()
        if service: self.session.openWithCallback(self.manual_done, HexInputScreen, service.info().getName())

    def action_editor(self): self.session.open(BissManagerList)

    def manual_done(self, key=None):
        if key:
            service = self.session.nav.getCurrentService()
            info = service.info()
            sid = "%04X" % (info.getInfo(iServiceInformation.sSID) & 0xFFFF)
            vpid = "%04X" % (info.getInfo(iServiceInformation.sVideoPID) & 0xFFFF)
            if self.save_biss_key(sid + vpid, key, info.getName()):
                self.res = (True, "Saved Successfully")
            self.timer.start(100, True)

    def save_biss_key(self, full_id, key, name):
        target = get_softcam_path()
        try:
            lines = []
            if os.path.exists(target):
                with open(target, "r") as f:
                    for line in f:
                        if f"F {full_id.upper()}" not in line.upper(): lines.append(line)
            lines.append(f"F {full_id.upper()} 00 {key.upper()} ; {name}\n")
            with open(target, "w") as f: f.writelines(lines)
            restart_softcam_global()
            return True
        except: return False

    def action_update(self):
        self["status"].setText("Updating Softcam...")
        Thread(target=self.do_update).start()

    def do_update(self):
        try:
            urlretrieve("https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key", "/tmp/SoftCam.Key")
            shutil.copy("/tmp/SoftCam.Key", get_softcam_path())
            restart_softcam_global()
            self.res = (True, "Update Done")
        except: self.res = (False, "Update Failed")
        self.timer.start(100, True)

    def action_auto(self):
        service = self.session.nav.getCurrentService()
        if service:
            self["status"].setText("Searching Online...")
            Thread(target=self.do_auto, args=(service,)).start()

    def do_auto(self, service):
        try:
            info = service.info(); name = info.getName()
            t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            freq = str(int(t_data.get("frequency", 0) / 1000))
            sid = "%04X" % (info.getInfo(iServiceInformation.sSID) & 0xFFFF)
            vpid = "%04X" % (info.getInfo(iServiceInformation.sVideoPID) & 0xFFFF)
            
            data = urlopen("https://raw.githubusercontent.com/anow2008/softcam.key/refs/heads/main/biss.txt").read().decode("utf-8")
            m = re.search(re.escape(freq) + r'.*?(([0-9A-Fa-f]{2}[\s\t]*){8})', data, re.I)
            if m:
                key = m.group(1).replace(" ", "").upper()
                self.save_biss_key(sid + vpid, key, name)
                self.res = (True, f"Found & Injected: {key}")
            else: self.res = (False, "No Key Found")
        except: self.res = (False, "Network Error")
        self.timer.start(100, True)

    def show_result(self):
        self["status"].setText("Ready")
        self.session.open(MessageBox, self.res[1], MessageBox.TYPE_INFO)

# --- شاشات مساعدة (Editor & Input) مبسطة ---
class BissManagerList(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = """<screen position="center,center" size="700,500" title="Editor"><widget name="keylist" position="20,20" size="660,450" itemHeight="40" font="Regular;24" /></screen>"""
        self["keylist"] = MenuList([])
        self["actions"] = ActionMap(["OkCancelActions"], {"cancel": self.close}, -1)

class HexInputScreen(Screen):
    def __init__(self, session, channel_name=""):
        Screen.__init__(self, session)
        self.skin = """<screen position="center,center" size="500,200" title="Input"><widget name="label" position="20,20" size="460,150" font="Regular;30" halign="center" /></screen>"""
        self["label"] = Label(f"Input for: {channel_name}\n(Use Remote Numbers)")
        self["actions"] = ActionMap(["OkCancelActions"], {"cancel": self.close}, -1)

def main(session, **kwargs): session.open(BISSPro)
def Plugins(**kwargs): return [PluginDescriptor(name="BissPro Smart", description="BISS Manager", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]

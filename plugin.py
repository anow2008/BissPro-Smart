# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from enigma import iServiceInformation, eTimer
import os, re, shutil, time
import urllib.request
from threading import Thread

PLUGIN_PATH = os.path.dirname(__file__)
VERSION_NUM = "v1.1"

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
        self.skin = """
        <screen position="center,center" size="850,600" title="BissPro Smart v1.1">
            <widget name="menu" position="25,20" size="800,400" itemHeight="50" scrollbarMode="showOnDemand" font="Regular;30" transparent="1" />
            <widget name="status" position="25,440" size="800,50" font="Regular;28" halign="center" foregroundColor="#f0a30a" />
            <widget name="main_progress" position="150,510" size="550,15" foregroundColor="#00ff00" />
            <eLabel text="BLUE: Auto Search | YELLOW: Update Softcam" position="25,550" size="800,30" font="Regular;20" halign="center" />
        </screen>"""
        
        self["status"] = Label("Ready")
        self["main_progress"] = ProgressBar()
        self.res = (True, "")

        self.options = [
            ("1. Smart Auto Search (Current Channel)", "auto"),
            ("2. Update Full Softcam Online", "upd"),
            ("3. Manual Add Key", "add")
        ]
        
        self["menu"] = MenuList([x[0] for x in self.options])
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.ok, 
            "cancel": self.close,
            "yellow": self.action_update,
            "blue": self.action_auto
        }, -1)

        self.timer = eTimer()
        try: self.timer.timeout.connect(self.show_result)
        except: self.timer.callback.append(self.show_result)

    def ok(self):
        idx = self["menu"].getSelectedIndex()
        act = self.options[idx][1]
        if act == "auto": self.action_auto()
        elif act == "upd": self.action_update()
        else: self.session.open(MessageBox, "Feature coming soon", MessageBox.TYPE_INFO)

    def action_update(self):
        self["status"].setText("Downloading Softcam...")
        Thread(target=self.do_update).start()

    def do_update(self):
        try:
            url = "https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open("/tmp/SoftCam.Key", 'wb') as out_file:
                out_file.write(response.read())
            shutil.copy("/tmp/SoftCam.Key", get_softcam_path())
            restart_softcam_global()
            self.res = (True, "Softcam Updated & Cam Restarted")
        except:
            self.res = (False, "Update Failed")
        self.timer.start(100, True)

    def action_auto(self):
        service = self.session.nav.getCurrentService()
        if service:
            self["status"].setText("Searching Online Database...")
            Thread(target=self.do_auto, args=(service,)).start()
        else:
            self.session.open(MessageBox, "No Channel Active", MessageBox.TYPE_ERROR)

    def do_auto(self, service):
        try:
            info = service.info()
            name = info.getName()
            t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            
            # معالجة التردد بشكل أكثر دقة
            freq_raw = t_data.get("frequency", 0)
            freq = str(int(freq_raw / 1000)) if freq_raw > 50000 else str(freq_raw)
            
            sid = "%04X" % (info.getInfo(iServiceInformation.sSID) & 0xFFFF)
            
            # رابط قاعدة البيانات المحدثة
            url = "https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            data = urllib.request.urlopen(req).read().decode("utf-8")
            
            # البحث عن الشفرة باستخدام التردد أو الـ SID
            pattern = re.escape(freq) + r'.*?(([0-9A-Fa-f]{2}[\s\t]*){8})'
            m = re.search(pattern, data, re.I)
            
            if m:
                key = m.group(1).replace(" ", "").upper()
                full_id = sid + "FFFF" # صيغة افتراضية متوافقة مع أوسكام
                
                target = get_softcam_path()
                with open(target, "a") as f:
                    f.write(f"\nF {full_id} 00 {key} ; {name}\n")
                
                restart_softcam_global()
                self.res = (True, f"Key Found: {key}\nInjected to {target}")
            else:
                self.res = (False, f"No Key found for Freq: {freq}")
        except Exception as e:
            self.res = (False, f"Error: {str(e)}")
        self.timer.start(100, True)

    def show_result(self):
        self["status"].setText("Ready")
        self.session.open(MessageBox, self.res[1], MessageBox.TYPE_INFO if self.res[0] else MessageBox.TYPE_ERROR)

def main(session, **kwargs): session.open(BISSPro)
def Plugins(**kwargs): return [PluginDescriptor(name="BissPro Smart", description="BISS Manager", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]

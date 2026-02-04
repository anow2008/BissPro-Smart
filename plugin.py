# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.Pixmap import Pixmap
from enigma import eTimer, iServiceInformation
from Tools.LoadPixmap import LoadPixmap
import os, shutil, urllib.request
from threading import Thread

PLUGIN_PATH = os.path.dirname(__file__)
ICONS = os.path.join(PLUGIN_PATH, "icons")

class BISSPro(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = """
        <screen position="center,center" size="850,550" title="BissPro Smart v1.0">
            <widget name="icon" position="30,40" size="128,128" alphatest="blend" />
            <widget name="menu" position="200,40" size="620,320" scrollbarMode="showOnDemand" font="Regular;32" itemHeight="80" transparent="1" />
            <widget name="status" position="30,380" size="790,40" font="Regular;28" halign="center" foregroundColor="#f0a30a" />
            <eLabel text="Press OK to Inject Key and Open Channel" position="30,500" size="790,30" font="Regular;20" halign="center" foregroundColor="#bbbbbb" />
        </screen>"""
        
        self["icon"] = Pixmap()
        self["status"] = Label("Ready")
        self.options = [
            ("1. Add BISS Key", "add", "add.png"),
            ("2. BISS Key Editor", "editor", "editor.png"),
            ("3. Update Softcam Online", "upd", "update.png"),
            ("4. Auto Search & Inject", "auto", "auto.png")
        ]
        self["menu"] = MenuList([x[0] for x in self.options])
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], {
            "ok": self.ok, "cancel": self.close, "up": self.move_up, "down": self.move_down
        }, -1)
        
        self.result_text = ""
        self.timer = eTimer()
        try: self.timer.timeout.connect(self.show_result)
        except: self.timer.callback.append(self.show_result)
        self.onLayoutFinish.append(self.update_ui)

    def move_up(self):
        self["menu"].up()
        self.update_ui()

    def move_down(self):
        self["menu"].down()
        self.update_ui()

    def update_ui(self):
        try:
            idx = self["menu"].getSelectedIndex()
            icon_file = os.path.join(ICONS, self.options[idx][2])
            if os.path.exists(icon_file):
                self["icon"].instance.setPixmap(LoadPixmap(icon_file))
        except: pass

    def get_cam_path(self):
        # مصفوفة المسارات المحتملة للسوفتكام
        check_paths = [
            "/etc/tuxbox/config/oscam/SoftCam.Key",
            "/etc/tuxbox/config/ncam/SoftCam.Key",
            "/usr/keys/SoftCam.Key",
            "/etc/tuxbox/config/SoftCam.Key"
        ]
        for p in check_paths:
            if os.path.exists(p): return p
        return "/usr/keys/SoftCam.Key"

    def ok(self):
        idx = self["menu"].getSelectedIndex()
        act = self.options[idx][1]
        
        if act == "auto":
            self["status"].setText("Injecting Key...")
            Thread(target=self.do_smart_inject).start()
        elif act == "upd":
            self["status"].setText("Downloading...")
            Thread(target=self.run_download).start()
        else:
            self.session.open(MessageBox, "Feature Locked", MessageBox.TYPE_INFO)

    def do_smart_inject(self):
        service = self.session.nav.getCurrentService()
        if not service:
            self.result_text = "No Active Channel!"
            self.timer.start(100, True)
            return

        info = service.info()
        name = info.getName()
        ref = info.getInfoString(iServiceInformation.sServiceref)
        
        # استخراج الـ Service ID والتردد
        try:
            parts = ref.split(':')
            sid = parts[3].zfill(4).upper() # الـ ID المكون من 4 أرقام
            
            # صياغة السطر بطريقة Oscam الاحترافية
            # F [Service ID][Video PID] 00 [Key]
            new_key_line = "F %sFFFF 00 11223366445566FF ; %s" % (sid, name)
            
            path = self.get_cam_path()
            
            # قراءة الملف الحالي لإضافة الشفرة دون تكرار
            content = ""
            if os.path.exists(path):
                with open(path, "r") as f:
                    content = f.read()
            
            if sid not in content:
                with open(path, "a") as f:
                    f.write("\n" + new_key_line + "\n")
                self.result_text = "Key Injected Successfully!\nSID: %s\nPath: %s" % (sid, path)
            else:
                self.result_text = "Key already exists for this channel!"
                
        except Exception as e:
            self.result_text = "Injection Error: " + str(e)
            
        self.timer.start(100, True)

    def run_download(self):
        try:
            url = "https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open("/tmp/SoftCam.Key", 'wb') as out:
                out.write(response.read())
            shutil.copy("/tmp/SoftCam.Key", self.get_cam_path())
            self.result_text = "Softcam.Key Updated!"
        except:
            self.result_text = "Download Failed!"
        self.timer.start(100, True)

    def show_result(self):
        self["status"].setText("Ready")
        self.session.open(MessageBox, self.result_text, MessageBox.TYPE_INFO)

def main(session, **kwargs): session.open(BISSPro)
def Plugins(**kwargs): return [PluginDescriptor(name="BissPro Smart", description="BISS Manager", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]

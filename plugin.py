# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from enigma import eTimer, iServiceInformation
from Tools.LoadPixmap import LoadPixmap
import os, shutil
from urllib.request import urlretrieve
from threading import Thread

# تحديد المسارات
PLUGIN_PATH = os.path.dirname(__file__)
ICONS = os.path.join(PLUGIN_PATH, "icons")

def get_softcam_path():
    # البحث عن مسار السوفتكام المتاح في جهازك
    paths = ["/etc/tuxbox/config/oscam/SoftCam.Key", "/etc/tuxbox/config/ncam/SoftCam.Key", "/usr/keys/SoftCam.Key"]
    for p in paths:
        if os.path.exists(p): return p
    return "/usr/keys/SoftCam.Key"

class BISSPro(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = """
        <screen position="center,center" size="850,550" title="BissPro Smart v1.0">
            <widget name="icon" position="30,40" size="128,128" alphatest="blend" />
            <widget name="menu" position="200,40" size="620,320" scrollbarMode="showOnDemand" font="Regular;32" itemHeight="80" transparent="1" />
            <widget name="status" position="30,380" size="790,40" font="Regular;28" halign="center" foregroundColor="#f0a30a" />
            <widget name="main_progress" position="150,450" size="550,15" foregroundColor="#00ff00" />
        </screen>"""
        
        self["icon"] = Pixmap()
        self["status"] = Label("Ready")
        self["main_progress"] = ProgressBar()
        
        # ربط الوظائف بالأسماء والأيقونات
        self.options = [
            ("1. Add BISS Key", "add", "add.png"),
            ("2. BISS Key Editor", "editor", "editor.png"),
            ("3. Update Online", "upd", "update.png"),
            ("4. Smart Search", "auto", "auto.png")
        ]
        
        self["menu"] = MenuList([x[0] for x in self.options])
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], {
            "ok": self.ok,
            "cancel": self.close,
            "up": self.move_up,
            "down": self.move_down
        }, -1)
        
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
        # تحديث الأيقونة عند التنقل
        idx = self["menu"].getSelectedIndex()
        icon_file = os.path.join(ICONS, self.options[idx][2])
        if os.path.exists(icon_file):
            self["icon"].instance.setPixmap(LoadPixmap(icon_file))

    def ok(self):
        idx = self["menu"].getSelectedIndex()
        act = self.options[idx][1]
        
        if act == "upd":
            self["status"].setText("Updating Softcam...")
            self["main_progress"].setValue(50)
            Thread(target=self.run_update).start()
        elif act == "auto":
            self["status"].setText("Searching for current channel key...")
            self.run_search()
        else:
            self.session.open(MessageBox, "قيد التطوير في النسخة النهائية", MessageBox.TYPE_INFO)

    def run_update(self):
        # وظيفة التحديث الحقيقية
        try:
            url = "https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key"
            urlretrieve(url, "/tmp/SoftCam.Key")
            shutil.copy("/tmp/SoftCam.Key", get_softcam_path())
            self.msg = "تم تحديث السوفتكام بنجاح!"
        except:
            self.msg = "فشل التحديث! تأكد من الإنترنت"
        self.timer.start(100, True)

    def run_search(self):
        # جلب اسم القناة الحالية
        service = self.session.nav.getCurrentService()
        if service:
            name = service.info().getName()
            self.session.open(MessageBox, "جاري البحث عن شفرة قناة: " + name, MessageBox.TYPE_INFO)
        else:
            self.session.open(MessageBox, "لا توجد قناة تعمل حالياً", MessageBox.TYPE_ERROR)

    def show_result(self):
        self["main_progress"].setValue(0)
        self["status"].setText("Ready")
        self.session.open(MessageBox, self.msg, MessageBox.TYPE_INFO)

def main(session, **kwargs): session.open(BISSPro)
def Plugins(**kwargs): return [PluginDescriptor(name="BissPro Smart", description="BISS Manager", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]

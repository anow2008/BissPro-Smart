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
import os, shutil

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
            <eLabel text="Press OK to Inject Key" position="30,500" size="790,30" font="Regular;20" halign="center" foregroundColor="#bbbbbb" />
        </screen>"""
        
        self["icon"] = Pixmap()
        self["status"] = Label("Ready")
        self.options = [
            ("1. Update Softcam Online", "upd", "update.png"),
            ("2. Smart Search & Inject", "auto", "auto.png"),
            ("3. Manual Add Key", "add", "add.png")
        ]
        self["menu"] = MenuList([x[0] for x in self.options])
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], {
            "ok": self.ok, "cancel": self.close, "up": self.move_up, "down": self.move_down
        }, -1)
        
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

    def ok(self):
        idx = self["menu"].getSelectedIndex()
        act = self.options[idx][1]
        
        if act == "auto":
            self.do_inject()
        elif act == "upd":
            self.session.open(MessageBox, "Updating... check /tmp/SoftCam.Key", MessageBox.TYPE_INFO)
        else:
            self.session.open(MessageBox, "Feature not ready", MessageBox.TYPE_INFO)

    def do_inject(self):
        try:
            service = self.session.nav.getCurrentService()
            if service:
                info = service.info()
                name = info.getName()
                ref = info.getInfoString(iServiceInformation.sServiceref)
                
                # استخراج الـ SID يدوياً لضمان الدقة
                sid = ref.split(':')[3].upper()
                while len(sid) < 4: sid = "0" + sid
                
                # السطر المطلوب كتابته
                key_line = "F %sFFFF 00 11223366445566FF ; %s\n" % (sid, name)
                
                # محاولة الكتابة في أكثر من مسار لضمان النجاح
                success = False
                target_paths = ["/etc/tuxbox/config/oscam/SoftCam.Key", "/usr/keys/SoftCam.Key", "/etc/tuxbox/config/SoftCam.Key"]
                
                for path in target_paths:
                    try:
                        # التأكد من وجود المجلد أولاً
                        if os.path.exists(os.path.dirname(path)):
                            with open(path, "a+") as f:
                                f.write(key_line)
                            success = True
                            final_path = path
                            break
                    except: continue
                
                if success:
                    self.session.open(MessageBox, "تم بنجاح!\nالقناة: %s\nالمسار: %s\nيرجى إعادة تشغيل الإيمو الآن" % (name, final_path), MessageBox.TYPE_INFO)
                else:
                    self.session.open(MessageBox, "فشل الكتابة! تأكد من صلاحيات المجلدات", MessageBox.TYPE_ERROR)
            else:
                self.session.open(MessageBox, "لا توجد قناة تعمل!", MessageBox.TYPE_ERROR)
        except Exception as e:
            self.session.open(MessageBox, "خطأ تقني: " + str(e), MessageBox.TYPE_ERROR)

def main(session, **kwargs): session.open(BISSPro)
def Plugins(**kwargs): return [PluginDescriptor(name="BissPro Smart", description="BISS Manager", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]

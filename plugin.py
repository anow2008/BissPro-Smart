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
from enigma import iServiceInformation, gFont, eTimer, getDesktop, RT_VALIGN_TOP
from Tools.LoadPixmap import LoadPixmap
import os, re, shutil, time, random
from urllib.request import urlopen
from threading import Thread

# ==========================================================
# الإعدادات والروابط
# ==========================================================
VERSION_NUM = "v1.2"
PLUGIN_PATH = os.path.dirname(__file__) + "/"
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

# ==========================================================
# كلاس المراقب التلقائي (الذي يحقق فكرتك)
# ==========================================================
class BissAutoRollService:
    def __init__(self, session):
        self.session = session
        self.last_service = None
        self.timer = eTimer()
        try: self.timer.callback.append(self.check_service)
        except: self.timer.timeout.connect(self.check_service)
        self.timer.start(5000, False) # يفحص كل 5 ثواني بهدوء

    def check_service(self):
        service = self.session.nav.getCurrentService()
        if not service: return
        
        # التأكد من أننا غيرنا القناة لتجنب تكرار البحث على نفس القناة
        current_ref = service.info().getInfoString(iServiceInformation.sServiceref)
        if current_ref != self.last_service:
            self.last_service = current_ref
            info = service.info()
            # إذا كانت القناة مشفرة، ابدأ الـ Auto Roll تلقائياً في الخلفية
            if info.getInfo(iServiceInformation.sIsCrypted) == 1:
                Thread(target=self.silent_auto_roll, args=(service,)).start()

    def silent_auto_roll(self, service):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            info = service.info()
            t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            freq_raw = t_data.get("frequency", 0)
            curr_freq = str(int(freq_raw / 1000 if freq_raw > 50000 else freq_raw))
            
            # جلب البيانات من السيرفر
            raw_data = urlopen(DATA_SOURCE, timeout=7, context=ctx).read().decode("utf-8")
            pattern = re.escape(curr_freq) + r'[\s\S]{0,500}?(([0-9A-Fa-f]{2}[\s\t:=-]*){8})'
            m = re.search(pattern, raw_data, re.I)
            
            if m:
                clean_key = re.sub(r'[^0-9A-Fa-f]', '', m.group(1)).upper()
                sid = info.getInfo(iServiceInformation.sSID)
                vpid = info.getInfo(iServiceInformation.sVideoPID)
                combined_id = ("%04X%04X" % (sid & 0xFFFF, vpid & 0xFFFF if vpid != -1 else 0))
                
                # حفظ الشفرة فوراً
                target = get_softcam_path()
                lines = []
                if os.path.exists(target):
                    with open(target, "r") as f:
                        for line in f:
                            if f"F {combined_id.upper()}" not in line.upper(): lines.append(line)
                lines.append(f"F {combined_id.upper()} 00000000 {clean_key} ;{info.getName()}\n")
                with open(target, "w") as f: f.writelines(lines)
                
                restart_softcam_global()
                # يمكن إضافة Notification صغير هنا ليخبر المستخدم أنه تم جلب الشفرة تلقائياً
        except: pass

# ==========================================================
# واجهة البلجن (BISSPro)
# ==========================================================
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
        
        self["btn_red"] = Label("Add Key")
        self["btn_green"] = Label("Editor")
        self["btn_yellow"] = Label("Download Softcam")
        self["btn_blue"] = Label("Autoroll")
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
        self.onLayoutFinish.append(self.build_menu); self.onLayoutFinish.append(self.load_main_logo); self.onLayoutFinish.append(self.check_for_updates)

    # (بقية الدوال المساعدة: update_clock, check_for_updates, action_auto، إلخ)
    def update_clock(self):
        self["time_label"].setText(time.strftime("%H:%M:%S"))
        self["date_label"].setText(time.strftime("%A, %d %B %Y"))

    def action_auto(self):
        service = self.session.nav.getCurrentService()
        if service: 
            self["status"].setText("Manual AutoRoll Started...")
            Thread(target=self.do_manual_auto, args=(service,)).start()

    def do_manual_auto(self, service):
        # الكود الذي ينفذ عند الضغط اليدوي على الزر الأزرق
        pass 

    # (بقية الكود الخاص بالمنيو والتحميل...)
    def build_menu(self):
        icon_dir = os.path.join(PLUGIN_PATH, "icons/")
        menu_items = [("Add Key", "Manual BISS Entry", "add", icon_dir + "add.png"), ("Key Editor", "Manage stored SoftCam keys", "editor", icon_dir + "editor.png"), ("Download Softcam", "Update SoftCam.Key from server", "upd", icon_dir + "update.png"), ("Autoroll", "Smart Search for current channel", "auto", icon_dir + "auto.png")]
        lst = []
        for name, desc, act, icon_path in menu_items:
            pixmap = LoadPixmap(cached=True, path=icon_path) if os.path.exists(icon_path) else None
            res = (name, [MultiContentEntryPixmapAlphaTest(pos=(self.ui.px(15), self.ui.px(15)), size=(self.ui.px(70), self.ui.px(70)), png=pixmap), MultiContentEntryText(pos=(self.ui.px(110), self.ui.px(10)), size=(self.ui.px(450), self.ui.px(45)), font=0, text=name, flags=RT_VALIGN_TOP), MultiContentEntryText(pos=(self.ui.px(110), self.ui.px(55)), size=(self.ui.px(450), self.ui.px(35)), font=1, text=desc, flags=RT_VALIGN_TOP, color=0xbbbbbb), act])
            lst.append(res)
        self["menu"].l.setList(lst)

    def ok(self):
        curr = self["menu"].getCurrent()
        if curr:
            act = curr[1][-1]
            if act == "add": self.action_add()
            elif act == "editor": self.action_editor()
            elif act == "upd": self.action_update()
            elif act == "auto": self.action_auto()
    
    def action_update(self): self["status"].setText("Downloading Softcam..."); Thread(target=self.do_update).start()
    def action_add(self):
        service = self.session.nav.getCurrentService()
        if service: self.session.openWithCallback(self.manual_done, HexInputScreen, service.info().getName())
    def action_editor(self): self.session.open(BissManagerList)
    def load_main_logo(self):
        logo_path = os.path.join(PLUGIN_PATH, "plugin.png")
        if os.path.exists(logo_path): self["main_logo"].instance.setPixmap(LoadPixmap(path=logo_path))
    def show_result(self): 
        self["main_progress"].setValue(0); self["status"].setText("Ready")
        self.session.open(MessageBox, self.res[1], MessageBox.TYPE_INFO if self.res[0] else MessageBox.TYPE_ERROR, timeout=5)

# ==========================================================
# تفعيل الخدمة التلقائية عند إقلاع الجهاز
# ==========================================================
def sessionstart(reason, **kwargs):
    if "session" in kwargs and reason == 0:
        global global_autoroll_monitor
        global_autoroll_monitor = BissAutoRollService(kwargs["session"])

def main(session, **kwargs): session.open(BISSPro)

def Plugins(**kwargs):
    return [
        PluginDescriptor(name="BissPro Smart", description="Smart BISS Manager v1.2", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main),
        PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart)
    ]

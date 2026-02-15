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
from enigma import iServiceInformation, gFont, eTimer, getDesktop, RT_VALIGN_TOP, RT_VALIGN_CENTER
from Tools.LoadPixmap import LoadPixmap
import os, re, shutil, time, random, struct
from urllib.request import urlopen
from threading import Thread

# ==========================================================
# مصفوفة الـ CRC32 الكاملة (أضيفت لضمان حساب الهاش الاحترافي)
# ==========================================================
crc_table = [
    0x00000000, 0x77073096, 0xee0e612c, 0x990951ba, 0x076dc419, 0x706af48f, 0xe963a535, 0x9e6495a3,
    0x0edb8832, 0x79dcb8a4, 0xe0d5e91e, 0x97d2d988, 0x09b64c2b, 0x7eb17cbd, 0xe7b82d07, 0x90bf1d91,
    0x1db71064, 0x6ab020f2, 0xf3b97148, 0x84be41de, 0x1adad47d, 0x6ddde4eb, 0xf4d4b551, 0x83d385c7,
    0x136c9856, 0x646ba8c0, 0xfd62f97a, 0x8a65c9ec, 0x14015c4f, 0x63066cd9, 0xfa0f3d63, 0x8d080df5,
    0x3b6e20c8, 0x4c69105e, 0xd56041e4, 0xa2677172, 0x3c03e4d1, 0x4b04d447, 0xd20d85fd, 0xa50ab56b,
    0x35b5a8fa, 0x42b2986c, 0xdbbbc9d6, 0xacbcf940, 0x32d86ce3, 0x45df5c75, 0xdcd60dcf, 0xabd13d59,
    0x26d930ac, 0x51de003a, 0xc8d75180, 0xbfd06116, 0x21b4f4b5, 0x56b3c423, 0xcfba9599, 0xb8bda50f,
    0x2802b89e, 0x5f058808, 0xc60cd9b2, 0xb10be924, 0x2f6f7c87, 0x58684c11, 0xc1611dab, 0xb6662d3d,
    0x76dc4190, 0x01db7106, 0x98d220bc, 0xefd5102a, 0x71b18589, 0x06b6b51f, 0x9fbfe4a5, 0xe8b8d433,
    0x7807c11e, 0x0f00f188, 0x9609a032, 0xaf0eb0a4, 0x7f6a0db7, 0x086d3d21, 0x91646c9b, 0xe6635c0d,
    0x6b6b51f4, 0x1c6c6162, 0x856530d8, 0xf262004e, 0x6c0695ed, 0x1b01a57b, 0x8208f4c1, 0xf50fc457,
    0x65b0d9c6, 0x12b7e950, 0x8bbeb8ea, 0xfcb9887c, 0x62dd1ddf, 0x15da2d49, 0x8cd37cf3, 0xfbd44c65,
    0x4db26158, 0x3ab551ce, 0xa3bc0074, 0xd4bb30e2, 0x4adfa541, 0x3dd895d7, 0xa4d1c46d, 0xd3d6f4fb,
    0x4369e96a, 0x346ed9fc, 0xad678846, 0xda60b8d0, 0x44042d73, 0x33031de5, 0xaa0a4c5f, 0xdd0d7cc9,
    0x5005713c, 0x270241aa, 0xbe0b1010, 0xc90c2086, 0x5768b525, 0x206f85b3, 0xb966d409, 0xce61e49f,
    0x5edef90e, 0x29d9c998, 0xb0d09822, 0xc7d7a8b4, 0x59b33d17, 0x2eb40d81, 0xb7bd5c3b, 0xc0ba6cad,
    0xedb88320, 0x9abfb3b6, 0x03b6e20c, 0x74b1d29a, 0xead54739, 0x9dd277af, 0x04db2615, 0x73dc1683,
    0xe3630b12, 0x94643b84, 0x0d6d6a3e, 0x7a6a5aa8, 0xe40ecf0b, 0x9309ff9d, 0x0a00ae27, 0x7d079eb1,
    0xf00f9344, 0x8708a3d2, 0x1e01f268, 0x6906c2fe, 0xf762575d, 0x806567cb, 0x196c3671, 0x6e6b06e7,
    0xfed41b76, 0x89d32be0, 0x10da7a5a, 0x67dd4acc, 0xf9b9df6f, 0x8ebeeff9, 0x17b7be43, 0x60b08ed5,
    0xd6d6a3e8, 0xa1d1937e, 0x38d8c2c4, 0x4fdff252, 0xd1bb67f1, 0xa6bc5767, 0x3fb506dd, 0x48b2364b,
    0xd80d2bda, 0xaf0a1b4c, 0x36034af6, 0x41047a60, 0xdf60efc3, 0xa867df55, 0x316e8eef, 0x4669be79,
    0xcb61b38c, 0xbc66831a, 0x256fd2a0, 0x5268e236, 0xcc0c7795, 0xbb0b4703, 0x220216b9, 0x5505262f,
    0xc5ba3bbe, 0xb2bd0b28, 0x2bb45a92, 0x5cb36a04, 0xc2d7ffa7, 0xb5d0cf31, 0x2cd99e8b, 0x5bdeae1d,
    0x9b64c2b0, 0xec63f226, 0x756aa39c, 0x026d930a, 0x9c0906a9, 0xeb0e363f, 0x72076785, 0x05005713,
    0x95bf4a82, 0xe2b87a14, 0x7bb12bae, 0x0cb61b38, 0x92d28e9b, 0xe5d5be0d, 0x7cdcefb7, 0x0bdbdf21,
    0x86d3d2d4, 0xf1d4e242, 0x68ddb3f8, 0x1fda836e, 0x81be16cd, 0xf6b9265b, 0x6fb077e1, 0x18b74777,
    0x88085ae6, 0xff0f6a70, 0x66063bca, 0x11010b5c, 0x8f659eff, 0xf862ae69, 0x616bffd3, 0x166ccf45,
    0xa00ae278, 0xd70dd2ee, 0x4e048354, 0x3903b3c2, 0xa7672661, 0xd06016f7, 0x4969474d, 0x3e6e77db,
    0xaed16a4a, 0xd9d65adc, 0x40df0b66, 0x37d83bf0, 0xa9bcae53, 0xdebb9ec5, 0x47b2cf7f, 0x30b5ffe9,
    0xbdbdf21c, 0xcabac28a, 0x53b39330, 0x24b4a3a6, 0xbad03605, 0xcdd70693, 0x54de5729, 0x23d967bf,
    0xb3667a2e, 0xc4614ab8, 0x5d681b02, 0x2a6f2b94, 0xb40bbe37, 0xc30c8ea1, 0x5a05df1b, 0x2d02ef8d
]

def get_biss_hash(sid, vpid):
    """دالة حساب الهاش المتوافق مع Oscam/Ncam/Emu"""
    try:
        if vpid == -1: vpid = 0
        data = struct.pack(">HH", sid & 0xFFFF, vpid & 0xFFFF)
        crc = 0x2600 ^ 0xffffffff
        for byte in data:
            if not isinstance(byte, int): byte = ord(byte)
            crc = crc_table[(byte ^ crc) & 0xff] ^ (crc >> 8)
        value = crc ^ 0xffffffff
        return "%08X" % (value & 0xFFFFFFFF)
    except:
        return "%04X%04X" % (sid & 0xFFFF, vpid if vpid != -1 else 0)

# ==========================================================
# الإعدادات والمسارات
# ==========================================================
PLUGIN_PATH = os.path.realpath(os.path.dirname(__file__)) + "/"
VERSION_NUM = "v1.2" 

URL_VERSION = "https://raw.githubusercontent.com/anow2008/BissPro-Smart/main/version.txt"
URL_NOTES   = "https://raw.githubusercontent.com/anow2008/BissPro-Smart/main/notes.txt"
URL_PLUGIN  = "https://raw.githubusercontent.com/anow2008/BissPro-Smart/main/plugin.py"
DATA_SOURCE = "https://raw.githubusercontent.com/anow2008/softcam.key/main/biss.txt"

def get_softcam_path():
    paths = [
        "/etc/tuxbox/config/oscam/SoftCam.Key", 
        "/etc/tuxbox/config/ncam/SoftCam.Key", 
        "/etc/tuxbox/config/SoftCam.Key", 
        "/usr/keys/SoftCam.Key"
    ]
    for p in paths:
        if os.path.exists(p): return p
    for p in paths:
        if os.path.exists(os.path.dirname(p)): return p
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
            <widget name="menu" position="{self.ui.px(50)},{self.ui.px(80)}" size="{self.ui.px(600)},{self.ui.px(410)}" itemHeight="{self.ui.px(100)}" scrollbarMode="showOnDemand" transparent="1" zPosition="2"/>
            
            <widget name="main_logo" position="{self.ui.px(820)},{self.ui.px(200)}" size="{self.ui.px(120)},{self.ui.px(120)}" alphatest="blend" transparent="1" zPosition="1" />
            
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
        
        # ربط تغير الاختيار بتحديث الأيقونة
        self["menu"].onSelectionChanged.append(self.update_menu_logo)
        
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {"ok": self.ok, "cancel": self.close, "red": self.action_add, "green": self.action_editor, "yellow": self.action_update, "blue": self.action_auto}, -1)
        
        self.onLayoutFinish.append(self.build_menu)
        self.onLayoutFinish.append(self.load_main_logo)
        self.onLayoutFinish.append(self.check_for_updates)
        self.update_clock()

    def update_menu_logo(self):
        """دالة تحديث الأيقونة بناءً على العنصر المختار"""
        curr = self["menu"].getCurrent()
        if curr:
            act = curr[1][-1]
            icon_path = os.path.join(PLUGIN_PATH, "icons", f"{act}.png")
            if os.path.exists(icon_path):
                self["main_logo"].instance.setPixmap(LoadPixmap(path=icon_path))
            else:
                self.load_main_logo()

    def load_main_logo(self):
        logo_path = os.path.join(PLUGIN_PATH, "plugin.png")
        if os.path.exists(logo_path):
            self["main_logo"].instance.setPixmap(LoadPixmap(path=logo_path))

    def check_for_updates(self):
        Thread(target=self.thread_check_version).start()

    def thread_check_version(self):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            v_url = URL_VERSION + "?nocache=" + str(random.randint(1000, 9999))
            remote_data = urlopen(v_url, timeout=10, context=ctx).read().decode("utf-8")
            remote_search = re.search(r"(\d+\.\d+)", remote_data)
            if remote_search:
                remote_v = float(remote_search.group(1))
                local_v = float(re.search(r"(\d+\.\d+)", VERSION_NUM).group(1))
                if remote_v > local_v:
                    msg = "New Version v%s available!\n\nUpdate?" % str(remote_v)
                    self.session.openWithCallback(self.install_update, MessageBox, msg, MessageBox.TYPE_YESNO)
        except: pass

    def install_update(self, answer):
        if answer:
            self["status"].setText("Updating...")
            Thread(target=self.do_plugin_download).start()

    def do_plugin_download(self):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            new_code = urlopen(URL_PLUGIN, timeout=15, context=ctx).read()
            with open(os.path.join(PLUGIN_PATH, "plugin.py"), "wb") as f: f.write(new_code)
            self.res = (True, "Updated Successfully! Restart Enigma2.")
        except Exception as e: self.res = (False, "Failed: " + str(e))
        self.timer.start(100, True)

    def update_clock(self):
        self["time_label"].setText(time.strftime("%H:%M:%S"))
        self["date_label"].setText(time.strftime("%A, %d %B %Y"))

    def build_menu(self):
        icon_dir = os.path.join(PLUGIN_PATH, "icons")
        menu_items = [
            ("Add Key", "Manual BISS Entry", "add", os.path.join(icon_dir, "add.png")), 
            ("Key Editor", "Manage stored keys", "editor", os.path.join(icon_dir, "editor.png")), 
            ("Download Softcam", "Full update from server", "upd", os.path.join(icon_dir, "update.png")), 
            ("Autoroll", "Smart search for current channel", "auto", os.path.join(icon_dir, "auto.png"))
        ]
        lst = []
        for name, desc, act, icon_path in menu_items:
            pixmap = LoadPixmap(path=icon_path) if os.path.exists(icon_path) else None
            res = (name, [
                MultiContentEntryPixmapAlphaTest(pos=(self.ui.px(15), self.ui.px(15)), size=(self.ui.px(70), self.ui.px(70)), png=pixmap), 
                MultiContentEntryText(pos=(self.ui.px(110), self.ui.px(10)), size=(self.ui.px(450), self.ui.px(45)), font=0, text=name, flags=RT_VALIGN_TOP), 
                MultiContentEntryText(pos=(self.ui.px(110), self.ui.px(55)), size=(self.ui.px(450), self.ui.px(35)), font=1, text=desc, flags=RT_VALIGN_TOP, color=0xbbbbbb), 
                act
            ])
            lst.append(res)
        self["menu"].l.setList(lst)
        if hasattr(self["menu"].l, 'setFont'): 
            self["menu"].l.setFont(0, gFont("Regular", self.ui.font(36)))
            self["menu"].l.setFont(1, gFont("Regular", self.ui.font(24)))
        # تفعيل أيقونة أول عنصر عند الفتح
        self.update_menu_logo()

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
        sid = info.getInfo(iServiceInformation.sSID)
        vpid = info.getInfo(iServiceInformation.sVideoPID)
        combined_id = get_biss_hash(sid, vpid)
        if self.save_biss_key(combined_id, key, info.getName()): self.res = (True, f"Saved with Hash: {combined_id}")
        else: self.res = (False, "File Error")
        self.timer.start(100, True)

    def save_biss_key(self, full_id, key, name):
        target = get_softcam_path()
        try:
            target_dir = os.path.dirname(target)
            if not os.path.exists(target_dir): os.makedirs(target_dir)
            lines = []
            if os.path.exists(target):
                with open(target, "r") as f:
                    for line in f:
                        if f"F {full_id.upper()}" not in line.upper(): lines.append(line)
            lines.append(f"F {full_id.upper()} 00000000 {key.upper()} ;{name}\n")
            with open(target, "w") as f: f.writelines(lines)
            os.chmod(target, 0o644)
            restart_softcam_global(); return True
        except: return False

    def show_result(self): 
        self["main_progress"].setValue(0)
        self["status"].setText("Ready")
        self.session.open(MessageBox, self.res[1], MessageBox.TYPE_INFO if self.res[0] else MessageBox.TYPE_ERROR, timeout=5)

    def action_update(self): 
        self["status"].setText("Downloading Softcam..."); 
        self["main_progress"].setValue(50); 
        Thread(target=self.do_update).start()

    def do_update(self):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            data = urlopen("https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key", context=ctx).read()
            target_path = get_softcam_path()
            target_dir = os.path.dirname(target_path)
            if not os.path.exists(target_dir): os.makedirs(target_dir)
            with open(target_path, "wb") as f: f.write(data)
            os.chmod(target_path, 0o644)
            restart_softcam_global()
            self.res = (True, "Softcam Updated Successfully")
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
            info = service.info(); ch_name = info.getName()
            t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            freq_raw = t_data.get("frequency", 0)
            curr_freq = str(int(freq_raw / 1000 if freq_raw > 50000 else freq_raw))
            sr_raw = t_data.get("symbol_rate", 0)
            curr_sr = str(int(sr_raw / 1000 if sr_raw > 1000 else sr_raw))
            raw_sid = info.getInfo(iServiceInformation.sSID)
            raw_vpid = info.getInfo(iServiceInformation.sVideoPID)
            combined_id = get_biss_hash(raw_sid, raw_vpid)
            raw_data = urlopen(DATA_SOURCE, timeout=12, context=ctx).read().decode("utf-8")
            self["main_progress"].setValue(70)
            pattern = r"(?i)" + re.escape(curr_freq) + r".*?" + re.escape(curr_sr) + r"[\s\S]{0,150}?(([0-9A-Fa-f]{2}[\s\t:=-]*){8})"
            m = re.search(pattern, raw_data)
            if m:
                clean_key = re.sub(r'[^0-9A-Fa-f]', '', m.group(1)).upper()
                if len(clean_key) == 16:
                    if self.save_biss_key(combined_id, clean_key, ch_name):
                        self.res = (True, f"Key Found! Hash: {combined_id}")
                    else: self.res = (False, "Write Error")
                else: self.res = (False, "Invalid key length")
            else:
                self.res = (False, "Not found for %s / %s" % (curr_freq, curr_sr))
        except: self.res = (False, "Auto Error")
        self.timer.start(100, True)

class BissProServiceWatcher:
    def __init__(self, session):
        self.session = session
        self.check_timer = eTimer()
        try: self.check_timer.callback.append(self.check_service)
        except: self.check_timer.timeout.connect(self.check_service)
        self.session.nav.event.append(self.on_event)
        self.is_scanning = False

    def on_event(self, event):
        if event in (0, 1): 
            self.check_timer.start(5000, True)

    def check_service(self):
        if self.is_scanning: return
        service = self.session.nav.getCurrentService()
        if not service: return
        info = service.info()
        if not info.getInfo(iServiceInformation.sIsCrypted): return
        caids = info.getInfoObject(iServiceInformation.sCAIDs)
        is_biss = False
        if caids:
            for caid in caids:
                if caid == 0x2600:
                    is_biss = True; break
        if not is_biss: return 
        self.is_scanning = True
        Thread(target=self.bg_thread, args=(service,)).start()

    def bg_thread(self, service):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            info = service.info(); ch_name = info.getName()
            t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            freq_raw = t_data.get("frequency", 0)
            curr_freq = str(int(freq_raw / 1000 if freq_raw > 50000 else freq_raw))
            sr_raw = t_data.get("symbol_rate", 0)
            curr_sr = str(int(sr_raw / 1000 if sr_raw > 1000 else sr_raw))
            raw_data = urlopen(DATA_SOURCE, timeout=10, context=ctx).read().decode("utf-8")
            pattern = r"(?i)" + re.escape(curr_freq) + r".*?" + re.escape(curr_sr) + r"[\s\S]{0,150}?(([0-9A-Fa-f]{2}[\s\t:=-]*){8})"
            m = re.search(pattern, raw_data)
            if m:
                clean_key = re.sub(r'[^0-9A-Fa-f]', '', m.group(1)).upper()
                if len(clean_key) == 16:
                    raw_sid = info.getInfo(iServiceInformation.sSID)
                    raw_vpid = info.getInfo(iServiceInformation.sVideoPID)
                    combined_id = get_biss_hash(raw_sid, raw_vpid)
                    target = get_softcam_path()
                    lines_cam = []
                    if os.path.exists(target):
                        with open(target, "r") as f:
                            for l in f:
                                if f"F {combined_id.upper()}" not in l.upper(): lines_cam.append(l)
                    lines_cam.append(f"F {combined_id.upper()} 00000000 {clean_key} ;{ch_name} (Auto)\n")
                    with open(target, "w") as f: f.writelines(lines_cam)
                    os.chmod(target, 0o644)
                    restart_softcam_global()
        except: pass
        self.is_scanning = False

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
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {"green": self.edit_key, "cancel": self.close, "red": self.delete_confirm}, -1)
        self.onLayoutFinish.append(self.load_keys)
    def load_keys(self):
        path = get_softcam_path(); keys = []
        if os.path.exists(path):
            with open(path, "r") as f:
                for line in f:
                    if line.strip().upper().startswith("F "): keys.append(line.strip())
        self["keylist"].setList(keys)
    def edit_key(self):
        current = self["keylist"].getCurrent()
        if current:
            parts = current.split(); ch_name = current.split(";")[-1] if ";" in current else "Unknown"; self.old_line = current
            self.session.openWithCallback(self.finish_edit, HexInputScreen, ch_name, parts[3] if len(parts) > 3 else "")
    def finish_edit(self, new_key=None):
        if new_key is None: return
        path = get_softcam_path(); parts = self.old_line.split(); parts[3] = str(new_key).upper(); new_line = " ".join(parts)
        try:
            with open(path, "r") as f: lines = f.readlines()
            with open(path, "w") as f:
                for line in lines:
                    if line.strip() == self.old_line.strip(): f.write(new_line + "\n")
                    else: f.write(line)
            self.load_keys(); restart_softcam_global()
        except: pass
    def delete_confirm(self):
        current = self["keylist"].getCurrent()
        if current: self.session.openWithCallback(self.delete_key, MessageBox, "Delete this key?", MessageBox.TYPE_YESNO)
    def delete_key(self, answer):
        if answer:
            current = self["keylist"].getCurrent(); path = get_softcam_path()
            try:
                with open(path, "r") as f: lines = f.readlines()
                with open(path, "w") as f:
                    for line in lines:
                        if line.strip() != current.strip(): f.write(line)
                self.load_keys(); restart_softcam_global()
            except: pass

class HexInputScreen(Screen):
    def __init__(self, session, channel_name="", existing_key=""):
        self.ui = AutoScale()
        Screen.__init__(self, session)
        self.skin = f"""
        <screen position="center,center" size="{self.ui.px(1150)},{self.ui.px(650)}" title="BissPro - Key Input" backgroundColor="#1a1a1a">
            <widget name="channel" position="{self.ui.px(10)},{self.ui.px(20)}" size="{self.ui.px(1130)},{self.ui.px(60)}" font="Regular;{self.ui.font(45)}" halign="center" foregroundColor="#00ff00" transparent="1" />
            <widget name="progress" position="{self.ui.px(175)},{self.ui.px(90)}" size="{self.ui.px(800)},{self.ui.px(10)}" foregroundColor="#00ff00" />
            <widget name="keylabel" position="{self.ui.px(25)},{self.ui.px(120)}" size="{self.ui.px(1100)},{self.ui.px(110)}" font="Regular;{self.ui.font(80)}" halign="center" foregroundColor="#f0a30a" transparent="1" />
            <widget name="channel_data" position="{self.ui.px(10)},{self.ui.px(240)}" size="{self.ui.px(1130)},{self.ui.px(50)}" font="Regular;{self.ui.font(32)}" halign="center" foregroundColor="#ffffff" transparent="1" />
            <widget name="char_list" position="{self.ui.px(1020)},{self.ui.px(120)}" size="{self.ui.px(100)},{self.ui.px(300)}" font="Regular;{self.ui.font(45)}" halign="center" foregroundColor="#ffffff" transparent="1" />
            <eLabel text="OK: Confirm | Arrows: Move | Numbers: Input" position="{self.ui.px(10)},{self.ui.px(410)}" size="{self.ui.px(1130)},{self.ui.px(35)}" font="Regular;{self.ui.font(24)}" halign="center" foregroundColor="#888888" transparent="1" />
            <eLabel position="0,{self.ui.px(460)}" size="{self.ui.px(1150)},{self.ui.px(190)}" backgroundColor="#252525" zPosition="-1" />
            <eLabel position="{self.ui.px(80)},{self.ui.px(500)}" size="{self.ui.px(25)},{self.ui.px(25)}" backgroundColor="#ff0000" />
            <widget name="l_red" position="{self.ui.px(115)},{self.ui.px(495)}" size="{self.ui.px(150)},{self.ui.px(40)}" font="Regular;{self.ui.font(26)}" transparent="1" />
            <eLabel position="{self.ui.px(330)},{self.ui.px(500)}" size="{self.ui.px(25)},{self.ui.px(25)}" backgroundColor="#00ff00" />
            <widget name="l_green" position="{self.ui.px(365)},{self.ui.px(495)}" size="{self.ui.px(150)},{self.ui.px(40)}" font="Regular;{self.ui.font(26)}" transparent="1" />
            <eLabel position="{self.ui.px(580)},{self.ui.px(500)}" size="{self.ui.px(25)},{self.ui.px(25)}" backgroundColor="#ffff00" />
            <widget name="l_yellow" position="{self.ui.px(615)},{self.ui.px(495)}" size="{self.ui.px(150)},{self.ui.px(40)}" font="Regular;{self.ui.font(26)}" transparent="1" />
            <eLabel position="{self.ui.px(830)},{self.ui.px(500)}" size="{self.ui.px(25)},{self.ui.px(25)}" backgroundColor="#0000ff" />
            <widget name="l_blue" position="{self.ui.px(865)},{self.ui.px(495)}" size="{self.ui.px(150)},{self.ui.px(40)}" font="Regular;{self.ui.font(26)}" transparent="1" />
        </screen>"""
        self["channel"] = Label(f"{channel_name}"); self["channel_data"] = Label(""); self["keylabel"] = Label(""); self["char_list"] = Label(""); self["progress"] = ProgressBar()
        self["l_red"] = Label("Exit"); self["l_green"] = Label("Save"); self["l_yellow"] = Label("Clear"); self["l_blue"] = Label("Reset All")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "NumberActions", "DirectionActions"], {
            "cancel": self.exit_clean, "red": self.exit_clean, "green": self.save, "yellow": self.clear_current, "blue": self.reset_all,
            "ok": self.confirm_char, "left": self.move_left, "right": self.move_right, "up": self.move_char_up, "down": self.move_char_down,
            "0": lambda: self.keyNum("0"), "1": lambda: self.keyNum("1"), "2": lambda: self.keyNum("2"), 
            "3": lambda: self.keyNum("3"), "4": lambda: self.keyNum("4"), "5": lambda: self.keyNum("5"), 
            "6": lambda: self.keyNum("6"), "7": lambda: self.keyNum("7"), "8": lambda: self.keyNum("8"), "9": lambda: self.keyNum("9")
        }, -1)
        self.key_list = list(existing_key.upper()) if (existing_key and len(existing_key) == 16) else ["0"] * 16
        self.index = 0; self.chars = ["A","B","C","D","E","F"]; self.char_index = 0
        self.onLayoutFinish.append(self.get_active_channel_data)
        self.update_display()
    def get_active_channel_data(self):
        service = self.session.nav.getCurrentService()
        if service:
            info = service.info(); t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            freq = t_data.get("frequency", 0)
            if freq > 50000: freq = freq / 1000
            pol = "H" if t_data.get("polarization", 0) == 0 else "V"
            sid = info.getInfo(iServiceInformation.sSID); vpid = info.getInfo(iServiceInformation.sVideoPID)
            self["channel_data"].setText(f"FREQ: {int(freq)} {pol} | SID: %04X | VPID: %04X" % (sid&0xFFFF, vpid&0xFFFF if vpid!=-1 else 0))
    def update_display(self):
        display_parts = []
        for i in range(16):
            char = self.key_list[i]; display_parts.append("[%s]" % char if i == self.index else char)
            if (i + 1) % 4 == 0 and i < 15: display_parts.append("-")
        self["keylabel"].setText("".join(display_parts))
        self["progress"].setValue(int(((self.index + 1) / 16.0) * 100))
        char_col = ""
        for i, c in enumerate(self.chars): char_col += ("\c00f0a30a[%s]\n" if i == self.char_index else "\c00ffffff %s \n") % c
        self["char_list"].setText(char_col)
    def confirm_char(self): self.key_list[self.index] = self.chars[self.char_index]; self.index = min(15, self.index + 1); self.update_display()
    def clear_current(self): self.key_list[self.index] = "0"; self.update_display()
    def reset_all(self): self.key_list = ["0"] * 16; self.index = 0; self.update_display()
    def move_char_up(self): self.char_index = (self.char_index - 1) % len(self.chars); self.update_display()
    def move_char_down(self): self.char_index = (self.char_index + 1) % len(self.chars); self.update_display()
    def keyNum(self, n): self.key_list[self.index] = n; self.index = min(15, self.index + 1); self.update_display()
    def move_left(self): self.index = max(0, self.index - 1); self.update_display()
    def move_right(self): self.index = min(15, self.index + 1); self.update_display()
    def save(self): self.close("".join(self.key_list))
    def exit_clean(self): self.close(None)

def main(session, **kwargs):
    session.open(BISSPro)

def Plugins(**kwargs):
    return [PluginDescriptor(name="BissPro Smart", description="Advanced BISS Key Tool", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=main)]

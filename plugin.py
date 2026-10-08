# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen

# --- تم تبسيط التنبيهات لإلغاء المزعج منها والحفاظ على استقرار البلجن ---
def addNotification(*args, **kwargs):
    pass
# --------------------------------------------------

from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from enigma import iServiceInformation, gFont, eTimer, getDesktop, eListboxPythonMultiContent, RT_HALIGN_LEFT, RT_VALIGN_TOP, RT_VALIGN_CENTER, quitMainloop
from Tools.LoadPixmap import LoadPixmap
import os, re, shutil, time, random, csv, json
import urllib.request
from threading import Thread
from array import array
import binascii

# ==========================================================
# إعدادات الهاش CRC32
# ==========================================================
crc32_table = array("L")
for byte in range(256):
    crc = 0
    for bit in range(8):
        if (byte ^ crc) & 1:
            crc = (crc >> 1) ^ 0xEDB88320
        else:
            crc >>= 1
        byte >>= 1
    crc32_table.append(crc)

def crc32_calc(string_data):
    value = 0x2600 ^ 0xffffffff
    for ch in string_data:
        try:
            value = crc32_table[(ord(ch) ^ value) & 0xff] ^ (value >> 8)
        except:
            value = crc32_table[(ch ^ value) & 0xff] ^ (value >> 8)
    return value ^ 0xffffffff

def getHash(session):
    try:
        ref = session.nav.getCurrentlyPlayingServiceReference()
        if not ref: return None
        sid = ref.getUnsignedData(1)
        tsid = ref.getUnsignedData(2)
        onid = ref.getUnsignedData(3)
        namespace = ref.getUnsignedData(4) | 0xA0000000
        if namespace & 0xFFFF == 0:
            data = "%04X%04X%04X%08X" % (sid, tsid, onid, namespace)
        else:
            data = "%04X%08X" % (sid, namespace)
        return "%08X" % (crc32_calc(binascii.unhexlify(data)) & 0xFFFFFFFF)
    except:
        return None

# ==========================================================
# الإعدادات والمسارات ودالة الحفظ الآمنة
# ==========================================================
PLUGIN_PATH = os.path.dirname(__file__) + "/"
VERSION_NUM = "v1.0" 
MODE_FILE = PLUGIN_PATH + "mode.txt"
BG_FILE = PLUGIN_PATH + "bg_search.txt"

def bg_search_enabled():
    try:
        with open(BG_FILE, "r") as f:
            return f.read().strip().lower() != "off"
    except:
        return True

def set_bg_search(on):
    try:
        with open(BG_FILE, "w") as f:
            f.write("on" if on else "off")
    except: pass

URL_VERSION = "https://raw.githubusercontent.com/anow2008/BissPro-Smart/main/version"
URL_NOTES   = "https://raw.githubusercontent.com/anow2008/info/main/notes"
URL_PLUGIN  = "https://raw.githubusercontent.com/anow2008/BissPro-Smart/main/plugin.py"

FIREBASE_URL = "https://bisspro-dcfa5-default-rtdb.europe-west1.firebasedatabase.app/.json"
SHEET_ID = "1-7Dgnii46UYR4HMorgpwtKC_7Fz-XuTfDV6vO2EkzQo"
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/%s/export?format=csv" % SHEET_ID

# --- الرابط الجديد المضاف (JSON) ---
NEW_JSON_URL = "https://script.google.com/macros/s/AKfycbwRfgMD6ReOMoNlXlNc0jSSjs2jB6Grg9l4Ucry-x7yJTMh74wFgiuBuE2-kFd4xirdYg/exec"

# --- الروابط الإضافية المطلوبة من الجيت هاب ---
GITHUB_SOURCES = [
    "https://raw.githubusercontent.com/anow2008/biss/refs/heads/main/bisskeys.json",
    "https://raw.githubusercontent.com/anow2008/biss/refs/heads/main/feeds.json",
    "https://raw.githubusercontent.com/anow2008/biss/refs/heads/main/for%20me.json"
]

def get_softcam_path():
    paths = [
        "/etc/tuxbox/config/SoftCam.Key", 
        "/etc/tuxbox/config/ncam/SoftCam.Key", 
        "/etc/tuxbox/config/oscam/SoftCam.Key", 
        "/usr/keys/SoftCam.Key"
    ]
    for p in paths:
        if os.path.exists(p): return p
    for p in paths:
        if os.path.exists(os.path.dirname(p)): return p
    return "/etc/tuxbox/config/SoftCam.Key"

def restart_softcam_global():
    scripts = ["/etc/init.d/softcam", "/etc/init.d/cardserver", "/etc/init.d/softcam.oscam", "/etc/init.d/softcam.ncam", "/etc/init.d/softcam.oscam_emu"]
    restarted = False
    for s in scripts:
        if os.path.exists(s):
            os.system(f"{s} restart >/dev/null 2>&1")
            restarted = True
            break
    if not restarted:
        os.system("killall -9 oscam ncam vicardd gbox 2>/dev/null")
        time.sleep(1.0)
        for s in scripts:
            if os.path.exists(s):
                os.system(f"{s} start >/dev/null 2>&1")
                break

class AutoScale:
    def __init__(self):
        d = getDesktop(0).size()
        self.scale = min(d.width() / 1920.0, d.height() / 1080.0)
    def px(self, v): return int(v * self.scale)
    def font(self, v): return int(max(20, v * self.scale))

# ==========================================================
# السكين المدمج - مستقل تماماً عن سكين الصورة
# كل الألوان والخلفيات والقوائم والرسائل معرّفة هنا
# ==========================================================
FONT = "Regular"          # الخط الوحيد المضمون في كل الصور
C_BG = "#0d1117"
C_BAR = "#161b26"
C_PANEL = "#141a25"
C_ROW = "#1a2233"
C_SEL = "#2b3f63"
C_ACCENT = "#f0a30a"
C_TEXT = "#ffffff"
C_MUTED = "#8b95a7"
C_OK = "#2ecc71"
C_ERR = "#e74c3c"
C_TRACK = "#222a38"

def _ci(c):
    return int(c[1:], 16)

def sk_rect(ui, x, y, w, h, color, z=-1):
    return '<eLabel position="%d,%d" size="%d,%d" backgroundColor="%s" zPosition="%d" />' % (
        ui.px(x), ui.px(y), ui.px(w), ui.px(h), color, z)

def sk_text(ui, text, x, y, w, h, size=24, fg=C_TEXT, align="left"):
    return ('<eLabel text="%s" position="%d,%d" size="%d,%d" font="%s;%d" foregroundColor="%s" '
            'halign="%s" valign="center" transparent="1" />') % (
        text, ui.px(x), ui.px(y), ui.px(w), ui.px(h), FONT, ui.font(size), fg, align)

def sk_widget(ui, name, x, y, w, h, size=24, fg=C_TEXT, align="left", bg=None, z=0):
    back = 'backgroundColor="%s"' % bg if bg else 'transparent="1"'
    return ('<widget name="%s" position="%d,%d" size="%d,%d" font="%s;%d" foregroundColor="%s" %s '
            'halign="%s" valign="center" zPosition="%d" />') % (
        name, ui.px(x), ui.px(y), ui.px(w), ui.px(h), FONT, ui.font(size), fg, back, align, z)

def sk_list(ui, name, x, y, w, h, item_h, bg=C_PANEL):
    return ('<widget name="%s" position="%d,%d" size="%d,%d" itemHeight="%d" scrollbarMode="showNever" '
            'backgroundColor="%s" backgroundColorSelected="%s" foregroundColor="%s" '
            'foregroundColorSelected="%s" zPosition="2" />') % (
        name, ui.px(x), ui.px(y), ui.px(w), ui.px(h), ui.px(item_h), bg, C_SEL, C_TEXT, C_ACCENT)

def sk_progress(ui, name, x, y, w, h, fg=C_OK):
    return ('<widget name="%s" position="%d,%d" size="%d,%d" foregroundColor="%s" '
            'backgroundColor="%s" borderWidth="0" />') % (
        name, ui.px(x), ui.px(y), ui.px(w), ui.px(h), fg, C_TRACK)

def sk_button(ui, color, x, y, w, name=None, text="", size=24):
    out = sk_rect(ui, x, y + 12, 26, 26, color, 0) + "\n"
    if name:
        out += sk_widget(ui, name, x + 38, y, w, 50, size, C_TEXT)
    else:
        out += sk_text(ui, text, x + 38, y, w, 50, size, C_TEXT)
    return out

def sk_screen(ui, w, h):
    return '<screen position="center,center" size="%d,%d" backgroundColor="%s" flags="wfNoBorder">' % (
        ui.px(w), ui.px(h), C_BG)

# ---------------- الشاشة الرئيسية ----------------
def build_main_skin(ui):
    p = [sk_screen(ui, 1100, 780),
         sk_rect(ui, 0, 0, 1100, 80, C_BAR),
         sk_rect(ui, 0, 80, 1100, 3, C_ACCENT),
         sk_text(ui, "BISSPRO SMART", 35, 14, 520, 52, 40, C_ACCENT),
         sk_widget(ui, "time_label", 760, 6, 300, 40, 30, C_TEXT, "right"),
         sk_widget(ui, "date_label", 560, 46, 500, 30, 20, C_MUTED, "right"),
         sk_rect(ui, 30, 105, 640, 440, C_PANEL),
         sk_rect(ui, 695, 105, 375, 440, C_PANEL),
         sk_list(ui, "menu", 40, 115, 620, 420, 100),
         '<widget name="main_logo" position="%d,%d" size="%d,%d" alphatest="blend" zPosition="1" />' % (
             ui.px(745), ui.px(170), ui.px(280), ui.px(280)),
         sk_progress(ui, "main_progress", 30, 566, 1040, 8),
         sk_widget(ui, "status", 30, 582, 1040, 56, 30, C_ACCENT, "center"),
         sk_text(ui, "MENU: Settings", 30, 646, 400, 30, 20, C_MUTED),
         sk_widget(ui, "version_label", 870, 646, 200, 30, 20, C_MUTED, "right"),
         sk_rect(ui, 0, 685, 1100, 95, C_BAR),
         sk_button(ui, "#e74c3c", 40, 710, 215, "btn_red", size=22),
         sk_button(ui, "#2ecc71", 305, 710, 215, "btn_green", size=22),
         sk_button(ui, "#f1c40f", 570, 710, 215, "btn_yellow", size=22),
         sk_button(ui, "#3498db", 835, 710, 215, "btn_blue", size=22),
         "</screen>"]
    return "\n".join(p)

# ---------------- محرر المفاتيح ----------------
def build_editor_skin(ui):
    p = [sk_screen(ui, 1000, 700),
         sk_rect(ui, 0, 0, 1000, 70, C_BAR),
         sk_rect(ui, 0, 70, 1000, 3, C_ACCENT),
         sk_text(ui, "KEY EDITOR", 30, 10, 500, 50, 36, C_ACCENT),
         sk_widget(ui, "count", 700, 16, 270, 40, 26, C_MUTED, "right"),
         sk_rect(ui, 20, 95, 960, 480, C_PANEL),
         sk_list(ui, "keylist", 20, 95, 960, 480, 60),
         sk_rect(ui, 0, 595, 1000, 105, C_BAR),
         sk_button(ui, "#2ecc71", 40, 625, 200, text="Edit"),
         sk_button(ui, "#e74c3c", 300, 625, 200, text="Delete"),
         sk_text(ui, "EXIT: Back", 640, 625, 330, 50, 22, C_MUTED, "right"),
         "</screen>"]
    return "\n".join(p)

# ---------------- شاشة إدخال المفتاح ----------------
def build_hex_skin(ui):
    p = [sk_screen(ui, 1150, 650),
         sk_rect(ui, 0, 0, 1150, 80, C_BAR),
         sk_rect(ui, 0, 80, 1150, 3, C_ACCENT),
         sk_widget(ui, "channel", 20, 12, 1110, 56, 40, C_ACCENT, "center"),
         sk_progress(ui, "progress", 175, 105, 800, 10),
         sk_rect(ui, 20, 130, 990, 120, C_PANEL),
         sk_widget(ui, "keylabel", 20, 130, 990, 120, 64, C_ACCENT, "center"),
         sk_rect(ui, 1030, 105, 100, 345, C_PANEL),
         sk_widget(ui, "char_list", 1030, 108, 100, 340, 45, C_TEXT, "center"),
         sk_widget(ui, "channel_data", 10, 265, 1130, 44, 30, C_TEXT, "center"),
         sk_text(ui, "OK: confirm  |  LEFT / RIGHT: move  |  UP / DOWN: letters", 10, 320, 1130, 40, 26, C_MUTED, "center"),
         sk_rect(ui, 0, 480, 1150, 170, C_BAR),
         sk_button(ui, "#e74c3c", 60, 535, 170, "l_red", size=26),
         sk_button(ui, "#2ecc71", 340, 535, 170, "l_green", size=26),
         sk_button(ui, "#f1c40f", 620, 535, 170, "l_yellow", size=26),
         sk_button(ui, "#3498db", 900, 535, 210, "l_blue", size=26),
         "</screen>"]
    return "\n".join(p)

# ---------------- القوائم (لا تعتمد على ستايل الصورة) ----------------
def new_list():
    return MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)

def setup_list(menu, ui, f0, f1, item_h):
    try:
        menu.l.setFont(0, gFont(FONT, ui.font(f0)))
        menu.l.setFont(1, gFont(FONT, ui.font(f1)))
        menu.l.setItemHeight(ui.px(item_h))
    except Exception as e:
        print("[BissPro] list setup error:", e)

def row_bg(ui, w, h):
    # خلفية الصف + لون التحديد معرّفين هنا بدل ستايل الصورة
    return MultiContentEntryText(pos=(0, ui.px(3)), size=(w, h - ui.px(6)), font=0, text="",
                                 backcolor=_ci(C_ROW), backcolor_sel=_ci(C_SEL))

def menu_row(ui, name, desc, act, icon_path):
    w, h = ui.px(620), ui.px(100)
    res = [act, row_bg(ui, w, h)]
    x_text = ui.px(25)
    if icon_path and os.path.exists(icon_path):
        pm = LoadPixmap(cached=True, path=icon_path)
        if pm:
            res.append(MultiContentEntryPixmapAlphaTest(pos=(ui.px(15), ui.px(15)), size=(ui.px(70), ui.px(70)), png=pm))
            x_text = ui.px(105)
    tw = w - x_text - ui.px(10)
    res.append(MultiContentEntryText(pos=(x_text, ui.px(10)), size=(tw, ui.px(45)), font=0,
                                     flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=name,
                                     color=_ci(C_TEXT), color_sel=_ci(C_ACCENT)))
    res.append(MultiContentEntryText(pos=(x_text, ui.px(55)), size=(tw, ui.px(35)), font=1,
                                     flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=desc,
                                     color=_ci(C_MUTED), color_sel=_ci(C_TEXT)))
    return res

def key_row(ui, line):
    w, h = ui.px(960), ui.px(60)
    parts = line.split()
    hash_id = parts[1] if len(parts) > 1 else ""
    key = parts[3] if len(parts) > 3 else ""
    name = line.split(";", 1)[1].strip() if ";" in line else ""
    fl = RT_HALIGN_LEFT | RT_VALIGN_CENTER
    return [line,
            row_bg(ui, w, h),
            MultiContentEntryText(pos=(ui.px(20), 0), size=(ui.px(190), h), font=1, flags=fl, text=hash_id,
                                  color=_ci(C_MUTED), color_sel=_ci(C_TEXT)),
            MultiContentEntryText(pos=(ui.px(215), 0), size=(ui.px(340), h), font=0, flags=fl, text=key,
                                  color=_ci(C_ACCENT), color_sel=_ci(C_ACCENT)),
            MultiContentEntryText(pos=(ui.px(565), 0), size=(ui.px(380), h), font=1, flags=fl, text=name,
                                  color=_ci(C_TEXT), color_sel=_ci(C_TEXT))]

def choice_row(ui, item):
    w, h = ui.px(760), ui.px(70)
    return [item, row_bg(ui, w, h),
            MultiContentEntryText(pos=(ui.px(25), 0), size=(w - ui.px(50), h), font=0,
                                  flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(item[0]),
                                  color=_ci(C_TEXT), color_sel=_ci(C_ACCENT))]

# ---------------- رسالة التأكيد الخاصة بالبلجن (بديل MessageBox) ----------------
class BPMessageBox(Screen):
    TYPE_YESNO = 0
    TYPE_INFO = 1
    TYPE_ERROR = 2

    def __init__(self, session, text="", type=1, timeout=0, **kwargs):
        self.ui = AutoScale()
        Screen.__init__(self, session)
        ui = self.ui
        self.mtype = type
        self.yesno = (type == self.TYPE_YESNO)
        self.sel = 0
        accent = {0: C_ACCENT, 1: C_OK, 2: C_ERR}.get(type, C_ACCENT)
        title = {0: "CONFIRM", 1: "INFO", 2: "ERROR"}.get(type, "INFO")
        p = [sk_screen(ui, 900, 400),
             sk_rect(ui, 0, 0, 900, 70, C_BAR),
             sk_rect(ui, 0, 70, 900, 4, accent),
             sk_text(ui, title, 35, 10, 600, 50, 34, accent),
             sk_widget(ui, "text", 40, 95, 820, 200, 26, C_TEXT, "center")]
        if self.yesno:
            p += [sk_widget(ui, "yes", 120, 315, 300, 60, 28, C_TEXT, "center", "#1f3d2c"),
                  sk_widget(ui, "yes_on", 120, 315, 300, 60, 28, "#000000", "center", C_OK, 1),
                  sk_widget(ui, "no", 480, 315, 300, 60, 28, C_TEXT, "center", "#4a2323"),
                  sk_widget(ui, "no_on", 480, 315, 300, 60, 28, "#ffffff", "center", C_ERR, 1)]
        else:
            p.append(sk_widget(ui, "ok_on", 300, 315, 300, 60, 28, "#000000", "center", accent, 1))
        p.append("</screen>")
        self.skin = "\n".join(p)

        self["text"] = Label(text)
        if self.yesno:
            self["yes"] = Label("YES"); self["yes_on"] = Label("YES")
            self["no"] = Label("NO"); self["no_on"] = Label("NO")
        else:
            self["ok_on"] = Label("OK")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"], {
            "ok": self.on_ok, "cancel": self.on_cancel,
            "green": self.on_yes, "red": self.on_no,
            "left": self.toggle, "right": self.toggle}, -1)

        self.timeout = int(timeout or 0)
        self.timer = eTimer()
        try: self.timer.callback.append(self.on_timeout)
        except: self.timer.timeout.connect(self.on_timeout)
        self.onLayoutFinish.append(self.start)
        self.onClose.append(self.timer.stop)

    def start(self):
        self.refresh()
        if self.timeout > 0:
            self.timer.start(self.timeout * 1000, True)

    def refresh(self):
        if self.yesno:
            if self.sel == 0:
                self["yes_on"].show(); self["no_on"].hide()
            else:
                self["yes_on"].hide(); self["no_on"].show()

    def toggle(self):
        if self.yesno:
            self.sel = 1 - self.sel
            self.refresh()

    def on_ok(self):
        self.close((self.sel == 0) if self.yesno else True)

    def on_yes(self):
        if self.yesno: self.close(True)

    def on_no(self):
        if self.yesno: self.close(False)

    def on_cancel(self):
        self.close(False)

    def on_timeout(self):
        self.close(False if self.yesno else True)

# ---------------- قائمة الاختيار الخاصة بالبلجن (بديل ChoiceBox) ----------------
class BPChoiceBox(Screen):
    def __init__(self, session, title="", list=None, **kwargs):
        self.ui = AutoScale()
        Screen.__init__(self, session)
        ui = self.ui
        self.items = [] if list is None else [i for i in list]
        rows = max(1, min(len(self.items), 8))
        list_h = rows * 70
        p = [sk_screen(ui, 800, 90 + list_h + 70),
             sk_rect(ui, 0, 0, 800, 70, C_BAR),
             sk_rect(ui, 0, 70, 800, 4, C_ACCENT),
             sk_widget(ui, "title", 35, 10, 730, 50, 30, C_ACCENT),
             sk_rect(ui, 20, 90, 760, list_h, C_PANEL),
             sk_list(ui, "list", 20, 90, 760, list_h, 70),
             sk_text(ui, "OK: Select     EXIT: Cancel", 20, 90 + list_h + 15, 760, 40, 22, C_MUTED, "center"),
             "</screen>"]
        self.skin = "\n".join(p)
        self["title"] = Label(title)
        self["list"] = new_list()
        self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.on_ok, "cancel": self.on_cancel}, -1)
        self.onLayoutFinish.append(self.fill)

    def fill(self):
        setup_list(self["list"], self.ui, 30, 22, 70)
        self["list"].setList([choice_row(self.ui, i) for i in self.items])

    def on_ok(self):
        cur = self["list"].getCurrent()
        self.close(cur[0] if cur else None)

    def on_cancel(self):
        self.close(None)


class BISSPro(Screen):
    def __init__(self, session):
        self.ui = AutoScale()
        Screen.__init__(self, session)
        self.res = (False, "")
        
        self.save_mode = "dual"
        if os.path.exists(MODE_FILE):
            try:
                with open(MODE_FILE, "r") as f:
                    self.save_mode = f.read().strip().lower()
            except: pass
        
        self.skin = build_main_skin(self.ui)
        
        self["btn_red"] = Label("Add Key")
        self["btn_green"] = Label("Editor")
        self["btn_yellow"] = Label("Download Softcam")
        self["btn_blue"] = Label("Autoroll")
        self["version_label"] = Label(f"Ver: {VERSION_NUM}")
        self["status"] = Label(self.status_text())
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
        
        self["menu"] = new_list()
        self["menu"].onSelectionChanged.append(self.update_dynamic_logo)
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "MenuActions"], {
            "ok": self.ok, 
            "cancel": self.close, 
            "menu": self.open_settings,
            "red": self.action_add, 
            "green": self.action_editor, 
            "yellow": self.action_update, 
            "blue": self.action_auto
        }, -1)
        
        self.onLayoutFinish.append(self.build_menu)
        self.onLayoutFinish.append(self.update_dynamic_logo)
        self.onLayoutFinish.append(self.check_for_updates)
        self.update_clock()

    def status_text(self):
        return "Mode: %s  |  Background: %s" % (self.save_mode.upper(), "ON" if bg_search_enabled() else "OFF")

    def open_settings(self):
        options = [
            ("Background Search: " + ("ON" if bg_search_enabled() else "OFF"), "bg"),
            ("Save Mode: " + self.save_mode.upper(), "mode")
        ]
        self.session.openWithCallback(self.settings_done, BPChoiceBox, title="Settings (OK to change)", list=options)

    def settings_done(self, choice):
        if not choice: return
        if choice[1] == "bg": self.toggle_bg()
        elif choice[1] == "mode": self.open_save_mode()

    def toggle_bg(self):
        new_state = not bg_search_enabled()
        set_bg_search(new_state)
        self["status"].setText("Background Search: " + ("ON" if new_state else "OFF"))
        if new_state and watcher_instance is not None:
            watcher_instance.check_timer.start(1500, True)

    def open_save_mode(self):
        options = [
            ("Dual Mode (Smart + Classic)", "dual"),
            ("Smart Hash Only", "smart"),
            ("Classic (SID/VPID) Only", "classic")
        ]
        self.session.openWithCallback(self.set_save_mode, BPChoiceBox, title="Permanent Saving Method:", list=options)

    def set_save_mode(self, mode):
        if mode:
            selected_mode = mode[1]
            self.save_mode = selected_mode
            try:
                with open(MODE_FILE, "w") as f:
                    f.write(selected_mode)
            except: pass
            self["status"].setText("Mode Saved: " + selected_mode.upper())

    def update_dynamic_logo(self):
        if not self.instance or "main_logo" not in self or not self["main_logo"].instance:
            return
            
        curr = self["menu"].getCurrent()
        if curr:
            act = curr[0]
            icon_map = {"add": "add.png", "editor": "editor.png", "upd": "Download Softcam.png", "auto": "auto.png"}
            icon_file = icon_map.get(act, "plugin.png")
            path = os.path.join(PLUGIN_PATH, "icons/", icon_file)
            if not os.path.exists(path): path = os.path.join(PLUGIN_PATH, "plugin.png")
            if os.path.exists(path):
                self["main_logo"].instance.setPixmap(LoadPixmap(path=path))

    def check_for_updates(self):
        Thread(target=self.thread_check_version).start()

    def thread_check_version(self):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            headers = {'User-Agent': 'Mozilla/5.0'}
            v_url = URL_VERSION + "?nocache=" + str(random.randint(1000, 9999))
            req = urllib.request.Request(v_url, headers=headers)
            remote_data = urllib.request.urlopen(req, timeout=10, context=ctx).read().decode("utf-8")
            
            remote_search = re.search(r"(\d+\.\d+)", remote_data)
            if remote_search:
                remote_v = float(remote_search.group(1))
                local_v = float(re.search(r"(\d+\.\d+)", VERSION_NUM.split('-')[0]).group(1))
                if remote_v > local_v:
                    try:
                        req_n = urllib.request.Request(URL_NOTES + "?nocache=" + str(random.randint(1000, 9999)), headers=headers)
                        notes = urllib.request.urlopen(req_n, timeout=5, context=ctx).read().decode("utf-8")
                    except:
                        notes = "New update available."
                    
                    msg = "Update Found: v%s\n\nWhat's New:\n%s\n\nInstall Update?" % (str(remote_v), notes)
                    self.session.openWithCallback(self.install_update, BPMessageBox, msg, BPMessageBox.TYPE_YESNO)
        except: pass

    def install_update(self, answer):
        if answer:
            self["status"].setText("Downloading...")
            Thread(target=self.do_plugin_download).start()

    def do_plugin_download(self):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(URL_PLUGIN + "?nocache=" + str(random.randint(1000, 9999)), headers=headers)
            new_code = urllib.request.urlopen(req, timeout=30, context=ctx).read()
            
            if len(new_code) > 2000:
                target_file = os.path.join(PLUGIN_PATH, "plugin.py")
                os.system("chmod 755 %s" % PLUGIN_PATH)
                with open(target_file, "wb") as f:
                    f.write(new_code)
                for ext in [".pyo", ".pyc"]:
                    cp = target_file.replace(".py", ext)
                    if os.path.exists(cp):
                        try: os.remove(cp)
                        except: pass
                self.res = (True, "Plugin Updated Successfully!\nRestart Enigma2?", "plugin_upd")
            else:
                self.res = (False, "Download incomplete.")
        except Exception as e: 
            self.res = (False, "Error: " + str(e))
        self.timer.start(100, True)

    def show_result(self): 
        self["main_progress"].setValue(0)
        self["status"].setText(self.status_text())
        if self.res[0]:
            if len(self.res) > 2 and self.res[2] == "plugin_upd":
                self.session.openWithCallback(self.answer_restart, BPMessageBox, self.res[1], BPMessageBox.TYPE_YESNO)
            else:
                self.session.open(BPMessageBox, self.res[1], BPMessageBox.TYPE_INFO, timeout=5)
        else:
            self.session.open(BPMessageBox, self.res[1], BPMessageBox.TYPE_ERROR, timeout=5)

    def answer_restart(self, answer):
        if answer: quitMainloop(3)

    def update_clock(self):
        self["time_label"].setText(time.strftime("%H:%M:%S"))
        self["date_label"].setText(time.strftime("%A, %d %B %Y"))

    def build_menu(self):
        icon_dir = os.path.join(PLUGIN_PATH, "icons/")
        menu_items = [
            ("Add Key", "Manual BISS Entry", "add", icon_dir + "add.png"),
            ("Key Editor", "Manage stored keys", "editor", icon_dir + "editor.png"),
            ("Download Softcam", "Full update from server", "upd", icon_dir + "Download Softcam.png"),
            ("Autoroll", "Smart search for current channel", "auto", icon_dir + "auto.png")
        ]
        setup_list(self["menu"], self.ui, 34, 24, 100)
        self["menu"].setList([menu_row(self.ui, n, d, a, p) for n, d, a, p in menu_items])

    def ok(self):
        curr = self["menu"].getCurrent()
        if curr:
            act = curr[0]
            if act == "add": self.action_add()
            elif act == "editor": self.action_editor()
            elif act == "upd": self.action_update()
            elif act == "auto": self.action_auto()

    def get_existing_key(self, ch_hash):
        target = get_softcam_path()
        if not os.path.exists(target): return ""
        
        alt_hash_video = ""
        alt_hash_audio = ""
        service = self.session.nav.getCurrentService()
        if service:
            info = service.info()
            sid = info.getInfo(iServiceInformation.sSID) & 0xFFFF
            vpid = info.getInfo(iServiceInformation.sVideoPID) & 0xFFFF
            apid = info.getInfo(iServiceInformation.sAudioPID) & 0xFFFF
            if vpid == 65535 or vpid == -1: vpid = 0
            if apid == 65535 or apid == -1: apid = 0
            alt_hash_video = "%04X%04X" % (sid, vpid)
            alt_hash_audio = "%04X%04X" % (sid, apid)

        try:
            with open(target, "r") as f:
                content = f.readlines()
                for line in content:
                    if f"F {ch_hash.upper()}" in line.upper():
                        parts = line.split()
                        if len(parts) > 3: return parts[3][:16]
                
                if alt_hash_video:
                    for line in content:
                        if f"F {alt_hash_video.upper()}" in line.upper():
                            parts = line.split()
                            if len(parts) > 3: return parts[3][:16]

                if alt_hash_audio:
                    for line in content:
                        if f"F {alt_hash_audio.upper()}" in line.upper():
                            parts = line.split()
                            if len(parts) > 3: return parts[3][:16]
        except: pass
        return ""

    def action_add(self):
        service = self.session.nav.getCurrentService()
        if service: 
            ch_hash = getHash(self.session)
            info = service.info()
            if not ch_hash:
                ch_hash = ("%04X" % (info.getInfo(iServiceInformation.sSID) & 0xFFFF)) + ("%04X" % (info.getInfo(iServiceInformation.sVideoPID) & 0xFFFF) if info.getInfo(iServiceInformation.sVideoPID) != -1 else "0000")
            
            existing_key = self.get_existing_key(ch_hash)
            display_name = info.getName()
            if ch_hash: display_name += " (Hash: %s)" % ch_hash
            self.session.openWithCallback(self.manual_done, HexInputScreen, display_name, existing_key)

    def action_editor(self): self.session.open(BissManagerList)

    def manual_done(self, key=None):
        if key is None: return
        service = self.session.nav.getCurrentService()
        if not service: return
        info = service.info()
        ch_hash = getHash(self.session)
        if not ch_hash:
            ch_hash = ("%04X" % (info.getInfo(iServiceInformation.sSID) & 0xFFFF)) + ("%04X" % (info.getInfo(iServiceInformation.sVideoPID) & 0xFFFF) if info.getInfo(iServiceInformation.sVideoPID) != -1 else "0000")
            
        if self.save_biss_key(ch_hash, key, info.getName()): 
            self.res = (True, f"Key Saved in {self.save_mode} Mode\nChannel: {info.getName()}")
        else: 
            self.res = (False, "File Error")
        self.timer.start(100, True)

    def save_biss_key(self, full_id, key, name):
        target = get_softcam_path()
        try:
            target_dir = os.path.dirname(target)
            if not os.path.exists(target_dir): os.makedirs(target_dir)

            current_date = time.strftime("%d/%m/%Y")
            alt_hash_video = "00000000"
            alt_hash_audio = "00000000"
            service = self.session.nav.getCurrentService()
            if service:
                info = service.info()
                sid = info.getInfo(iServiceInformation.sSID) & 0xFFFF
                vpid = info.getInfo(iServiceInformation.sVideoPID) & 0xFFFF
                apid = info.getInfo(iServiceInformation.sAudioPID) & 0xFFFF
                if vpid == 65535 or vpid == -1: vpid = 0
                if apid == 65535 or apid == -1: apid = 0
                alt_hash_video = "%04X%04X" % (sid, vpid)
                alt_hash_audio = "%04X%04X" % (sid, apid)

            lines = []
            if os.path.exists(target):
                with open(target, "r") as f:
                    for line in f:
                        if f"F {full_id.upper()}" not in line.upper() and f"F {alt_hash_video.upper()}" not in line.upper() and f"F {alt_hash_audio.upper()}" not in line.upper():
                            lines.append(line)
            
            if self.save_mode in ["smart", "dual"]:
                lines.append(f"F {full_id.upper()} 00000000 {key.upper()} ;{name} (Smart) | {current_date}\n")
            if self.save_mode in ["classic", "dual"]:
                lines.append(f"F {alt_hash_video.upper()} 00000000 {key.upper()} ;{name} (Classic Video) | {current_date}\n")
                lines.append(f"F {alt_hash_audio.upper()} 00000000 {key.upper()} ;{name} (Classic Audio) | {current_date}\n")
            
            with open(target, "w") as f:
                f.writelines(lines)
                f.flush()
            os.chmod(target, 0o644)
            restart_softcam_global()
            return True
        except Exception as e:
            print("[BissPro] Save Error:", str(e))
            return False

    def action_update(self): 
        self["status"].setText("Downloading Softcam..."); 
        self["main_progress"].setValue(50); 
        Thread(target=self.do_update).start()

    def do_update(self):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request("https://raw.githubusercontent.com/anow2008/softcam.key/main/softcam.key", headers=headers)
            data = urllib.request.urlopen(req, context=ctx).read()
            target_path = get_softcam_path()
            
            with open(target_path, "wb") as f:
                f.write(data)
            restart_softcam_global()
            self.res = (True, "Softcam Updated Successfully")
        except Exception as e: 
            self.res = (False, "Update Error: " + str(e))
        self.timer.start(100, True)

    def action_auto(self):
        service = self.session.nav.getCurrentService()
        if service: 
            self["status"].setText("Searching..."); self["main_progress"].setValue(40)
            Thread(target=self.do_auto, args=(service,)).start()

    def do_auto(self, service):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            info = service.info(); ch_name = info.getName().upper().strip()
            t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            freq_raw = t_data.get("frequency", 0)
            curr_freq = int(freq_raw / 1000 if freq_raw > 50000 else freq_raw)
            curr_pol = "V" if t_data.get("polarization", 0) else "H"
            curr_sr = int(t_data.get("symbol_rate", 0) // 1000)
            
            freq_search = "%s %s %s" % (curr_freq, curr_pol, curr_sr)
            
            ch_hash = getHash(self.session)
            if not ch_hash:
                raw_sid = info.getInfo(iServiceInformation.sSID)
                raw_vpid = info.getInfo(iServiceInformation.sVideoPID)
                ch_hash = ("%04X" % (raw_sid & 0xFFFF)) + ("%04X" % (raw_vpid & 0xFFFF) if raw_vpid != -1 else "0000")
            
            found = False
            
            try:
                # --- تطوير الربط الأساسي ليكون ذكياً (الأولوية للاسم والتردد معاً) ---
                resp = urllib.request.urlopen(FIREBASE_URL, timeout=8, context=ctx).read()
                db = json.loads(resp)
                if db:
                    # الخطوة 1: البحث الدقيق (تردد + اسم) - شرط "و" الذكي
                    for db_key, db_val in db.items():
                        db_key_up = db_key.upper()
                        # يشترط وجود التردد واسم القناة معاً في المفتاح
                        if str(curr_freq) in db_key_up and ch_name in db_key_up:
                            clean_key = db_val.replace(" ", "").replace(":", "").strip().upper()
                            if len(clean_key) == 16:
                                if self.save_biss_key(ch_hash, clean_key, info.getName()):
                                    self.res = (True, f"Found Exact: {clean_key}\nSaved for {info.getName()}")
                                    found = True; break
                    
                    # الخطوة 2: البحث الاحتياطي (بالتردد فقط) كخيار ثانٍ إذا لم ينجح الأول
                    if not found:
                        for db_key, db_val in db.items():
                            db_key_up = db_key.upper()
                            if (freq_search in db_key_up) or (str(curr_freq) in db_key_up):
                                clean_key = db_val.replace(" ", "").replace(":", "").strip().upper()
                                if len(clean_key) == 16:
                                    if self.save_biss_key(ch_hash, clean_key, info.getName()):
                                        self.res = (True, f"Found by Freq: {clean_key}\nSaved for {info.getName()}")
                                        found = True; break
            except: pass

            # --- البحث في روابط GITHUB_SOURCES المضافة مع فلترة الـ id للقنوات المتكررة ---
            if not found:
                for g_url in GITHUB_SOURCES:
                    try:
                        headers = {'User-Agent': 'Mozilla/5.0'}
                        req_g = urllib.request.Request(g_url, headers=headers)
                        resp_g = urllib.request.urlopen(req_g, timeout=8, context=ctx).read().decode("utf-8")
                        json_g = json.loads(resp_g)
                        if isinstance(json_g, list):
                            for item in json_g:
                                raw_f = str(item.get("frequency", "")).upper()
                                if str(curr_freq) in raw_f and curr_pol in raw_f:
                                    # فلترة إضافية باسم القناة id لمنع التداخل عند تكرار التردد
                                    json_id = str(item.get("id", "")).upper().strip()
                                    if json_id and (json_id not in ch_name and ch_name not in json_id):
                                        continue
                                    clean_key = item.get("key", "").replace(" ", "").strip().upper()
                                    if len(clean_key) == 16:
                                        if self.save_biss_key(ch_hash, clean_key, info.getName()):
                                            self.res = (True, f"Found in GitHub Link: {clean_key}\nSaved for {info.getName()}")
                                            found = True; break
                        if found: break
                    except: pass

            # --- البحث في الرابط الجديد (NEW_JSON_URL) المضاف مع فلترة الـ id للقنوات المتكررة ---
            if not found:
                try:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    req_j = urllib.request.Request(NEW_JSON_URL, headers=headers)
                    resp_j = urllib.request.urlopen(req_j, timeout=8, context=ctx).read().decode("utf-8")
                    json_db = json.loads(resp_j)
                    for item in json_db:
                        raw_f = str(item.get("frequency", "")).upper()
                        if str(curr_freq) in raw_f and curr_pol in raw_f:
                            # فلترة إضافية باسم القناة id لمنع التداخل عند تكرار التردد
                            json_id = str(item.get("id", "")).upper().strip()
                            if json_id and (json_id not in ch_name and ch_name not in json_id):
                                continue
                            clean_key = item.get("key", "").replace(" ", "").strip().upper()
                            if len(clean_key) == 16:
                                if self.save_biss_key(ch_hash, clean_key, info.getName()):
                                    self.res = (True, f"Found in New Link: {clean_key}\nSaved for {info.getName()}")
                                    found = True; break
                except: pass

            if not found:
                headers = {'User-Agent': 'Mozilla/5.0'}
                try:
                    req_s = urllib.request.Request(GOOGLE_SHEET_URL, headers=headers)
                    response = urllib.request.urlopen(req_s, timeout=8, context=ctx).read().decode("utf-8").splitlines()
                    for row in csv.reader(response):
                        if len(row) >= 2:
                            sheet_info = row[0].upper()
                            nums = re.findall(r'\d+', sheet_info)
                            if len(nums) >= 2:
                                sheet_freq = int(nums[0])
                                sheet_sr = int(nums[1])
                                if abs(curr_freq - sheet_freq) <= 3 and curr_pol in sheet_info and abs(curr_sr - sheet_sr) <= 10:
                                    if len(row) >= 3 and row[2].strip():
                                        sheet_name_filter = row[2].strip().upper()
                                        curr_ch_name = info.getName().upper()
                                        if sheet_name_filter not in curr_ch_name and curr_ch_name not in sheet_name_filter:
                                            continue
                                    clean_key = row[1].replace(" ", "").strip().upper()
                                    if len(clean_key) == 16:
                                        if self.save_biss_key(ch_hash, clean_key, info.getName()):
                                            self.res = (True, f"Found: {clean_key}\nSaved in {self.save_mode} Mode"); found = True; break
                except: pass
            
            if not found: self.res = (False, "Not found for %d %s %d" % (curr_freq, curr_pol, curr_sr))
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
        if event in (0, 1): self.check_timer.start(6000, True)
    def check_service(self):
        if self.is_scanning: return
        if not bg_search_enabled(): return
        service = self.session.nav.getCurrentService()
        if not service: return
        info = service.info()
        if info.getInfo(iServiceInformation.sIsCrypted):
            is_biss = False
            caids = info.getInfoObject(iServiceInformation.sCAIDs)
            if caids:
                for caid in caids:
                    if caid == 0x2600: is_biss = True; break
            if is_biss:
                self.is_scanning = True
                Thread(target=self.bg_do_auto, args=(service,)).start()
    def bg_do_auto(self, service):
        try:
            import ssl
            ctx = ssl._create_unverified_context()
            info = service.info(); ch_name = info.getName().upper().strip()
            t_data = info.getInfoObject(iServiceInformation.sTransponderData)
            if not t_data: self.is_scanning = False; return
            freq_raw = t_data.get("frequency", 0)
            curr_freq = int(freq_raw / 1000 if freq_raw > 50000 else freq_raw)
            curr_pol = "V" if t_data.get("polarization", 0) else "H"
            curr_sr = int(t_data.get("symbol_rate", 0) // 1000)
            
            freq_search = "%s %s %s" % (curr_freq, curr_pol, curr_sr)
            
            ch_hash = getHash(self.session)
            if not ch_hash:
                raw_sid = info.getInfo(iServiceInformation.sSID)
                raw_vpid = info.getInfo(iServiceInformation.sVideoPID)
                ch_hash = ("%04X" % (raw_sid & 0xFFFF)) + ("%04X" % (raw_vpid & 0xFFFF) if raw_vpid != -1 else "0000")
            
            found = False
            
            try:
                # --- تطوير الربط في الخلفية (شرط التردد واسم القناة معاً) ---
                resp = urllib.request.urlopen(FIREBASE_URL, timeout=8, context=ctx).read()
                db = json.loads(resp)
                if db:
                    # الخطوة 1: تطابق تام (الاسم والتردد)
                    for db_key, db_val in db.items():
                        db_key_up = db_key.upper()
                        if str(curr_freq) in db_key_up and ch_name in db_key_up:
                            clean = db_val.replace(" ", "").replace(":", "").strip().upper()
                            if len(clean) == 16: 
                                self.save_biss_key_background(ch_hash, clean, info.getName())
                                found = True; break
                    
                    # الخطوة 2: البحث بالتردد إذا لم ينجح الأول
                    if not found:
                        for db_key, db_val in db.items():
                            db_key_up = db_key.upper()
                            if (freq_search in db_key_up) or (str(curr_freq) in db_key_up):
                                clean = db_val.replace(" ", "").replace(":", "").strip().upper()
                                if len(clean) == 16: 
                                    self.save_biss_key_background(ch_hash, clean, info.getName())
                                    found = True; break
            except: pass

            # --- البحث في الخلفية داخل روابط GITHUB_SOURCES المضافة مع فلترة الـ id للقنوات المتكررة ---
            if not found:
                for g_url in GITHUB_SOURCES:
                    try:
                        headers = {'User-Agent': 'Mozilla/5.0'}
                        req_g = urllib.request.Request(g_url, headers=headers)
                        resp_g = urllib.request.urlopen(req_g, timeout=8, context=ctx).read().decode("utf-8")
                        json_g = json.loads(resp_g)
                        if isinstance(json_g, list):
                            for item in json_g:
                                raw_f = str(item.get("frequency", "")).upper()
                                if str(curr_freq) in raw_f and curr_pol in raw_f:
                                    # فلترة إضافية باسم القناة id لمنع التداخل عند تكرار التردد
                                    json_id = str(item.get("id", "")).upper().strip()
                                    if json_id and (json_id not in ch_name and ch_name not in json_id):
                                        continue
                                    clean = item.get("key", "").replace(" ", "").strip().upper()
                                    if len(clean) == 16:
                                        self.save_biss_key_background(ch_hash, clean, info.getName())
                                        found = True; break
                        if found: break
                    except: pass

            # --- البحث في الخلفية داخل الرابط الجديد المضاف (JSON) مع فلترة الـ id للقنوات المتكررة ---
            if not found:
                try:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    req_j = urllib.request.Request(NEW_JSON_URL, headers=headers)
                    resp_j = urllib.request.urlopen(req_j, timeout=8, context=ctx).read().decode("utf-8")
                    json_db = json.loads(resp_j)
                    for item in json_db:
                        raw_f = str(item.get("frequency", "")).upper()
                        if str(curr_freq) in raw_f and curr_pol in raw_f:
                            # فلترة إضافية باسم القناة id لمنع التداخل عند تكرار التردد
                            json_id = str(item.get("id", "")).upper().strip()
                            if json_id and (json_id not in ch_name and ch_name not in json_id):
                                continue
                            clean = item.get("key", "").replace(" ", "").strip().upper()
                            if len(clean) == 16:
                                self.save_biss_key_background(ch_hash, clean, info.getName())
                                found = True; break
                except: pass

            if not found:
                headers = {'User-Agent': 'Mozilla/5.0'}
                try:
                    req_s = urllib.request.Request(GOOGLE_SHEET_URL, headers=headers)
                    resp = urllib.request.urlopen(req_s, timeout=8, context=ctx).read().decode("utf-8").splitlines()
                    for row in csv.reader(resp):
                        if len(row) >= 2:
                            sheet_info = row[0].upper()
                            nums = re.findall(r'\d+', sheet_info)
                            if len(nums) >= 2:
                                sheet_freq = int(nums[0]); sheet_sr = int(nums[1])
                                if abs(curr_freq - sheet_freq) <= 3 and curr_pol in sheet_info and abs(curr_sr - sheet_sr) <= 10:
                                    if len(row) >= 3 and row[2].strip():
                                        sheet_name_filter = row[2].strip().upper()
                                        curr_ch_name = ch_name.upper()
                                        if sheet_name_filter not in curr_ch_name and curr_ch_name not in sheet_name_filter:
                                            continue
                                    clean = row[1].replace(" ", "").strip().upper()
                                    if len(clean) == 16: self.save_biss_key_background(ch_hash, clean, info.getName()); break
                except: pass
        except: pass
        self.is_scanning = False

    def save_biss_key_background(self, full_id, key, name):
        if not bg_search_enabled(): return False
        target = get_softcam_path()
        try:
            current_mode = "dual"
            if os.path.exists(MODE_FILE):
                try:
                    with open(MODE_FILE, "r") as f:
                        current_mode = f.read().strip().lower()
                except: pass

            current_date = time.strftime("%d/%m/%Y")
            alt_hash_video = "00000000"
            alt_hash_audio = "00000000"
            service = self.session.nav.getCurrentService()
            if service:
                info = service.info()
                sid = info.getInfo(iServiceInformation.sSID) & 0xFFFF
                vpid = info.getInfo(iServiceInformation.sVideoPID) & 0xFFFF
                apid = info.getInfo(iServiceInformation.sAudioPID) & 0xFFFF
                if vpid == 65535 or vpid == -1: vpid = 0
                if apid == 65535 or apid == -1: apid = 0
                alt_hash_video = "%04X%04X" % (sid, vpid)
                alt_hash_audio = "%04X%04X" % (sid, apid)

            if os.path.exists(target):
                with open(target, "r") as f:
                    content = f.read().upper()
                    check_smart = f"F {full_id.upper()} 00000000 {key.upper()}" in content
                    check_video = f"F {alt_hash_video.upper()} 00000000 {key.upper()}" in content
                    check_audio = f"F {alt_hash_audio.upper()} 00000000 {key.upper()}" in content
                    
                    if current_mode == "smart" and check_smart: return False
                    if current_mode == "classic" and check_video and check_audio: return False
                    if current_mode == "dual" and check_smart and check_video and check_audio: return False

            lines = []
            if os.path.exists(target):
                with open(target, "r") as f:
                    for line in f:
                        if f"F {full_id.upper()}" not in line.upper() and f"F {alt_hash_video.upper()}" not in line.upper() and f"F {alt_hash_audio.upper()}" not in line.upper():
                            lines.append(line)
            
            if current_mode in ["smart", "dual"]:
                lines.append(f"F {full_id.upper()} 00000000 {key.upper()} ;{name} (Smart) | {current_date}\n")
            if current_mode in ["classic", "dual"]:
                lines.append(f"F {alt_hash_video.upper()} 00000000 {key.upper()} ;{name} (Classic Video) | {current_date}\n")
                lines.append(f"F {alt_hash_audio.upper()} 00000000 {key.upper()} ;{name} (Classic Audio) | {current_date}\n")
            
            with open(target, "w") as f:
                f.writelines(lines)
                f.flush()
            os.chmod(target, 0o644)
            restart_softcam_global()
            self.session.open(BPMessageBox, f"Key Found & Saved ({current_mode.upper()}): {key}\nChannel: {name}", BPMessageBox.TYPE_INFO, timeout=4)
            return True
        except: return False
        
class BissManagerList(Screen):
    def __init__(self, session):
        self.ui = AutoScale()
        Screen.__init__(self, session)
        self.skin = build_editor_skin(self.ui)
        self.entries = []
        self["keylist"] = new_list()
        self["count"] = Label("")
        self["keylist"].onSelectionChanged.append(self.update_count)
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {"green": self.edit_key, "cancel": self.close, "red": self.delete_confirm}, -1)
        self.onLayoutFinish.append(self.load_keys)
    def load_keys(self):
        path = get_softcam_path(); keys = []
        if os.path.exists(path):
            with open(path, "r") as f:
                for line in f:
                    if line.strip().upper().startswith("F "): keys.append(line.strip())
        self.entries = keys
        setup_list(self["keylist"], self.ui, 28, 24, 60)
        self["keylist"].setList([key_row(self.ui, k) for k in keys])
        self.update_count()
    def current_line(self):
        cur = self["keylist"].getCurrent()
        return cur[0] if cur else None
    def update_count(self):
        n = len(self.entries)
        idx = (self["keylist"].getSelectionIndex() + 1) if n else 0
        self["count"].setText("%d / %d" % (idx, n))
    def edit_key(self):
        current = self.current_line()
        if current:
            parts = current.split(); ch_name = current.split(";")[-1] if ";" in current else "Unknown"; self.old_line = current
            self.session.openWithCallback(self.finish_edit, HexInputScreen, ch_name, parts[3] if len(parts) > 3 else "")
    def finish_edit(self, new_key=None):
        if new_key is None: return
        path = get_softcam_path(); parts = self.old_line.split(); parts[3] = str(new_key).upper(); new_line = " ".join(parts)
        try:
            with open(path, "r") as f: lines = f.readlines()
            new_list = []
            for line in lines:
                if line.strip() == self.old_line.strip(): new_list.append(new_line + "\n")
                else: new_list.append(line)
            
            with open(path, "w") as f:
                f.writelines(new_list)
                f.flush()
            os.chmod(path, 0o644)
            restart_softcam_global()
            self.load_keys()
        except: pass
    def delete_confirm(self):
        current = self.current_line()
        if current: self.session.openWithCallback(self.delete_key, BPMessageBox, "Delete this key?", BPMessageBox.TYPE_YESNO)
    def delete_key(self, answer):
        if answer:
            current = self.current_line(); path = get_softcam_path()
            try:
                with open(path, "r") as f: lines = f.readlines()
                new_list = []
                for line in lines:
                    if line.strip() != current.strip(): new_list.append(line)
                
                with open(path, "w") as f:
                    f.writelines(new_list)
                    f.flush()
                os.chmod(path, 0o644)
                restart_softcam_global()
                self.load_keys()
            except: pass

class HexInputScreen(Screen):
    def __init__(self, session, channel_name="", existing_key=""):
        self.ui = AutoScale()
        Screen.__init__(self, session)
        self.skin = build_hex_skin(self.ui)
        self["channel"] = Label(f"{channel_name}"); self["channel_data"] = Label(""); self["keylabel"] = Label(""); self["char_list"] = Label(""); self["progress"] = ProgressBar()
        self["l_red"] = Label("Exit"); self["l_green"] = Label("Save"); self["l_yellow"] = Label("Clear"); self["l_blue"] = Label("Reset All")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "NumberActions", "DirectionActions"], {
            "cancel": self.exit_clean, "red": self.exit_clean, "green": self.save, "yellow": self.clear_current, "blue": self.reset_all,
            "ok": self.confirm_char, "left": self.move_left, "right": self.move_right, "up": self.move_char_up, "down": self.move_char_down,
            "0": lambda: self.keyNum("0"), "1": lambda: self.keyNum("1"), "2": lambda: self.keyNum("2"), "3": lambda: self.keyNum("3"),
            "4": lambda: self.keyNum("4"), "5": lambda: self.keyNum("5"), "6": lambda: self.keyNum("6"), "7": lambda: self.keyNum("7"),
            "8": lambda: self.keyNum("8"), "9": lambda: self.keyNum("9")
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
            sr = t_data.get("symbol_rate", 0) // 1000
            sid = info.getInfo(iServiceInformation.sSID); vpid = info.getInfo(iServiceInformation.sVideoPID)
            self["channel_data"].setText(f"{int(freq)} {pol} {sr} | SID: %04X | VPID: %04X" % (sid&0xFFFF, vpid&0xFFFF if vpid!=-1 else 0))
    def update_display(self):
        display_parts = []
        for i in range(16):
            char = self.key_list[i]; display_parts.append("[%s]" % char if i == self.index else char)
            if (i + 1) % 4 == 0 and i < 15: display_parts.append("-")
        self["keylabel"].setText("".join(display_parts))
        self["progress"].setValue(int(((self.index + 1) / 16.0) * 100))
        char_col = ""
        for i, c in enumerate(self.chars): char_col += ("\\c00f0a30a[%s]\n" if i == self.char_index else "\\c00ffffff %s \n") % c
        self["char_list"].setText(char_col)
    def confirm_char(self): self.key_list[self.index] = self.chars[self.char_index]; self.index = min(15, self.index + 1); self.update_display()
    def clear_current(self): self.key_list[self.index] = "0"; self.update_display()
    def reset_all(self): self.key_list = ["0"] * 16; self.index = 0; self.update_display()
    def move_char_up(self): self.char_index = (self.char_index - 1) % len(self.chars); self.update_display()
    def move_char_down(self): self.char_index = (self.char_index + 1) % len(self.chars); self.update_display()
    def keyNum(self, n): self.key_list[self.index] = n; self.index = min(15, self.index + 1); self.update_display()
    def move_left(self): self.index = max(0, self.index - 1); self.update_display()
    def move_right(self): self.index = min(15, self.index + 1); self.update_display()
    def exit_clean(self): self.close(None)
    def save(self): self.close("".join(self.key_list))

watcher_instance = None
def main(session, **kwargs): session.open(BISSPro)
def Plugins(**kwargs):
    return [PluginDescriptor(name="BissPro Smart", description="Smart BISS Manager", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main),
            PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart)]
def sessionstart(reason, session=None, **kwargs):
    global watcher_instance
    if reason == 0 and session is not None and watcher_instance is None: watcher_instance = BissProServiceWatcher(session)

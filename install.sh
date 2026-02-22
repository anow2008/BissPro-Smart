#!/bin/sh
# ==========================================
#  BissPro-Smart Online Installer (Direct TGZ)
#  Author : anow2008
# ==========================================

PLUGIN="BissPro-Smart"
BASE_DIR="/usr/lib/enigma2/python/Plugins/Extensions"
TARGET="$BASE_DIR/$PLUGIN"

# الرابط الجديد: بيستهدف الملف اللي انت رفعته بالظبط
# ملاحظة: استبدل 'main' باسم الفرع لو كان مختلف عندك
ZIP_URL="https://github.com/anow2008/BissPro-Smart/raw/main/BissPro-Smart.tar.gz"

LOG="/tmp/bisspro_smart_install.log"

echo "🔧 BissPro-Smart Installer Started" | tee $LOG

# --- Detect Python ---
PYTHON=$(command -v python3 || command -v python)

stop_enigma2() {
    echo "⏹ Stopping Enigma2..." | tee -a $LOG
    [ -x /usr/bin/systemctl ] && systemctl stop enigma2 || init 4
    sleep 2
}

start_enigma2() {
    echo "▶ Starting Enigma2..." | tee -a $LOG
    [ -x /usr/bin/systemctl ] && systemctl start enigma2 || init 3
}

install_plugin() {
    stop_enigma2

    mkdir -p "$BASE_DIR"
    cd /tmp || exit 1
    
    # تنظيف التحميلات القديمة
    rm -rf BissPro-Smart* echo "⬇ Downloading $PLUGIN..." | tee -a $LOG
    # استخدمنا -L عشان لو GitHub عمل Redirect للرابط
    if ! wget -L -O "BissPro-Smart.tar.gz" "$ZIP_URL" >> $LOG 2>&1; then
        echo "❌ Download failed" | tee -a $LOG
        start_enigma2
        exit 1
    fi

    echo "📦 Extracting..." | tee -a $LOG
    tar -xzf "BissPro-Smart.tar.gz" || {
        echo "❌ Extract failed" | tee -a $LOG
        start_enigma2
        exit 1
    }

    # مسح النسخة القديمة من البلجن
    rm -rf "$TARGET"

    # النقل: بيفترض إن الملف المضغوط جواه فولدر اسمه BissPro-Smart
    # لو الملف المضغوط جواه الملفات مباشرة بدون فولدر، هنحتاج تعديل بسيط
    if [ -d "BissPro-Smart" ]; then
        mv "BissPro-Smart" "$TARGET"
    else
        # إذا كانت الملفات مضغوطة مباشرة بدون مجلد رئيسي
        mkdir -p "$TARGET"
        # نقل كل الملفات المفكوكة (ما عدا ملف الـ tar نفسه)
        find . -maxdepth 1 ! -name "." ! -name "BissPro-Smart.tar.gz" -exec mv {} "$TARGET" \;
    fi

    echo "⚙ Finalizing permissions..." | tee -a $LOG
    chmod -R 755 "$TARGET"
    find "$TARGET" -name "*.pyc" -delete

    sync
    start_enigma2

    echo "================================="
    echo " ✅ BissPro-Smart Installed Successfully"
    echo " 📄 Log: $LOG"
    echo "================================="
}

install_plugin
exit 0

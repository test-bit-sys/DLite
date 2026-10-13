"""
DLite Internationalization (i18n) Engine
Supports dynamic switching between English and Arabic (RTL).
"""
from engine.config import config

TRANSLATIONS = {
    "en": {
        "app_title": "DLite — Download Manager",
        "menu_file": "File",
        "menu_downloads": "Downloads",
        "menu_options": "Options",
        "menu_help": "Help",
        "action_add_url": "Add URL",
        "action_import_urls": "Import URLs from File...",
        "action_settings": "Settings",
        "action_quit": "Quit",
        "action_pause_all": "Pause All",
        "action_resume_all": "Resume All",
        "action_clear_completed": "Clear Completed",
        "action_about": "About DLite",
        "menu_on_complete": "When All Downloads Finish",
        "opt_do_nothing": "Do Nothing",
        "opt_exit_app": "Exit DLite",
        "opt_sleep_pc": "Sleep Computer",
        "opt_shutdown_pc": "Shut Down Computer",
        "col_filename": "File Name",
        "col_size": "Size",
        "col_progress": "Progress",
        "col_speed": "Speed",
        "col_eta": "Time Left",
        "col_status": "Status",
        "col_added": "Added",
        "cat_all": "All Downloads",
        "cat_archives": "Archives",
        "cat_audio": "Audio",
        "cat_documents": "Documents",
        "cat_general": "General",
        "cat_images": "Images",
        "cat_programs": "Programs",
        "cat_videos": "Videos",
        "tab_speed_graph": "Speed Graph",
        "tab_connections": "Segment Connections",
        "tab_logs": "System Logs",
        "ctx_pause": "Pause",
        "ctx_resume": "Resume",
        "ctx_cancel": "Cancel",
        "ctx_open_folder": "Open containing folder",
        "ctx_open_file": "Open file",
        "ctx_checksum": "Checksum & File Integrity",
        "ctx_remove": "Remove from list",
        "ctx_delete_file": "Remove and delete file",
        "btn_browse": "Browse...",
        "btn_start_now": "Start Download",
        "btn_cancel": "Cancel",
        "btn_close": "Close",
    },
    "ar": {
        "app_title": "دي لايت (DLite) — مدير التنزيلات السريع",
        "menu_file": "ملف",
        "menu_downloads": "تنزيلات",
        "menu_options": "خيارات",
        "menu_help": "مساعدة",
        "action_add_url": "إضافة رابط",
        "action_import_urls": "استيراد روابط من ملف...",
        "action_settings": "الإعدادات",
        "action_quit": "خروج",
        "action_pause_all": "إيقاف مؤقت للكل",
        "action_resume_all": "استئناف الكل",
        "action_clear_completed": "مسح المكتملة",
        "action_about": "حول DLite",
        "menu_on_complete": "عند اكتمال كافة التنزيلات",
        "opt_do_nothing": "عدم فعل شيء",
        "opt_exit_app": "إغلاق البرنامج",
        "opt_sleep_pc": "وضع السكون للكمبيوتر (Sleep)",
        "opt_shutdown_pc": "إيقاف تشغيل الكمبيوتر (Shut Down)",
        "col_filename": "اسم الملف",
        "col_size": "الحجم",
        "col_progress": "التقدم",
        "col_speed": "السرعة",
        "col_eta": "الوقت المتبقي",
        "col_status": "الحالة",
        "col_added": "تاريخ الإضافة",
        "cat_all": "كافة التنزيلات",
        "cat_archives": "المضغوطات والأرشيف",
        "cat_audio": "الصوتيات",
        "cat_documents": "المستندات",
        "cat_general": "عام",
        "cat_images": "الصور",
        "cat_programs": "البرامج والتطبيقات",
        "cat_videos": "الفيديوهات",
        "tab_speed_graph": "مخطط السرعة اللحظي",
        "tab_connections": "اتصالات الأجزاء المتزامنة",
        "tab_logs": "سجل النظام والعمليات",
        "ctx_pause": "إيقاف مؤقت",
        "ctx_resume": "استئناف التنزيل",
        "ctx_cancel": "إلغاء التنزيل",
        "ctx_open_folder": "فتح المجلد الحاوي للملف",
        "ctx_open_file": "فتح الملف",
        "ctx_checksum": "فحص البصمة الرقمية وسلامة الملف (Checksum)",
        "ctx_remove": "حذف من القائمة",
        "ctx_delete_file": "حذف من القائمة ومسح الملف من القرص",
        "btn_browse": "تصفح...",
        "btn_start_now": "بدء التنزيل",
        "btn_cancel": "إلغاء",
        "btn_close": "إغلاق",
    },
}


def get_current_language() -> str:
    return config.get("language", "en")


def set_current_language(lang: str):
    if lang in TRANSLATIONS:
        config.set("language", lang)


def t(key: str, default: str = "") -> str:
    lang = get_current_language()
    return TRANSLATIONS.get(lang, {}).get(key, default or key)

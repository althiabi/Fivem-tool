import base64
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import time
import requests
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote, urlparse
from datetime import datetime, timedelta
from collections import defaultdict
import math
import psutil
from Cryptodome.Cipher import AES, ChaCha20
from Cryptodome.Util.Padding import unpad
import ctypes
import ctypes.wintypes as wintypes
import warnings
import urllib3
from typing import Optional, Dict, List, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn, TimeElapsedColumn
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.syntax import Syntax
from rich import box
from rich.rule import Rule
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from rich.columns import Columns
from rich.align import Align
from rich.style import Style
from rich import print as rprint
import msvcrt

console = Console()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_READWRITE = 0x04
PAGE_READONLY = 0x02
PAGE_GUARD = 0x100

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

if hasattr(ctypes, 'c_size_t'):
    SIZE_T = ctypes.c_size_t
else:
    if ctypes.sizeof(ctypes.c_void_p) == 4:
        SIZE_T = ctypes.c_uint32
    else:
        SIZE_T = ctypes.c_uint64

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", ctypes.c_ulong),
        ("RegionSize", SIZE_T),
        ("State", ctypes.c_ulong),
        ("Protect", ctypes.c_ulong),
        ("Type", ctypes.c_ulong),
    ]

VirtualQueryEx = kernel32.VirtualQueryEx
VirtualQueryEx.restype = SIZE_T
VirtualQueryEx.argtypes = [
    wintypes.HANDLE,
    wintypes.LPCVOID,
    ctypes.POINTER(MEMORY_BASIC_INFORMATION),
    SIZE_T
]

ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.restype = wintypes.BOOL
ReadProcessMemory.argtypes = [
    wintypes.HANDLE,
    wintypes.LPCVOID,
    wintypes.LPVOID,
    SIZE_T,
    ctypes.POINTER(SIZE_T)
]

current_resource_index = 0
total_resources = 0
total_downloaded_size = 0
failed_files = []
successful_files = []
dump_log = []
log_counter = 1
connection_pool = {}

TRANSLATIONS = {
    "en": {
        "main_menu_title": "ADVANCED SNEAKS DUMPER & DECRYPTOR",
        "main_menu_subtitle": "v3.0.0",
        "status_grants_file": "Grants file:",
        "status_output_size": "Output size:",
        "status_multi_threading": "Multi-threading:",
        "enabled": "Enabled",
        "disabled": "Disabled",
        "ready": "Ready",
        "not_found": "Not found",
        "menu_dump_cfx": "Dump from cfx.re link",
        "menu_dump_cfx_desc": "Auto IP + Auto token",
        "menu_dump_ip": "Dump from Server IP",
        "menu_dump_ip_desc": "Manual IP + Auto token",
        "menu_manual_token": "Manual Token Mode",
        "menu_manual_token_desc": "Manual IP + Manual token",
        "menu_dump_domain": "Dump from Domain",
        "menu_dump_domain_desc": "Domain + Auto token",
        "menu_decrypt": "Decrypt Resources",
        "menu_decrypt_desc": "Use saved grants",
        "menu_manage_cache": "Manage Cache",
        "menu_manage_cache_desc": "Clear cache and history",
        "menu_view_logs": "View Logs",
        "menu_view_logs_desc": "Browse dump logs",
        "menu_settings": "Settings",
        "menu_settings_desc": "Configure settings",
        "menu_exit": "Exit",
        "menu_exit_desc": "Close program",
        "press_enter_continue": "Press Enter to continue...",
        "thank_you": "Thank you for using FiveM Advanced Sneaks Dumper!",
        "program_interrupted": "Program interrupted by user",
        "unexpected_error": "Unexpected error",
        "settings_title": "SETTINGS CONFIGURATION",
        "settings_subtitle": "Use arrows to navigate • Enter to select • Space to toggle • ESC to cancel",
        "settings_configuration": "CONFIGURATION",
        "setting_multithreading": "Multi-threading",
        "setting_multithreading_desc": "Enable parallel downloads",
        "setting_max_workers": "Max Workers",
        "setting_max_workers_desc": "Parallel download threads (1-500)",
        "setting_retry_count": "Retry Count",
        "setting_retry_count_desc": "Retries for failed downloads",
        "setting_auto_cleanup": "Auto Cleanup",
        "setting_auto_cleanup_desc": "Clean temp files after dump",
        "setting_auto_decrypt": "Auto Decrypt",
        "setting_auto_decrypt_desc": "Auto decrypt after dump",
        "setting_logging": "Enable Logging",
        "setting_logging_desc": "Save detailed logs",
        "setting_download_timeout": "Download Timeout",
        "setting_download_timeout_desc": "Timeout in seconds (10-300)",
        "setting_connection_timeout": "Connection Timeout",
        "setting_connection_timeout_desc": "Connection timeout (5-120)",
        "setting_progress_bars": "Show Progress Bars",
        "setting_progress_bars_desc": "Show download progress bars",
        "setting_adaptive_speed": "Adaptive Speed",
        "setting_adaptive_speed_desc": "Auto-adjust speed based on server",
        "setting_batch_size": "Batch Size",
        "setting_batch_size_desc": "Files per batch (1-500)",
        "setting_connection_pooling": "Connection Pooling",
        "setting_connection_pooling_desc": "Reuse connections for speed",
        "setting_theme": "Theme Settings",
        "setting_theme_desc": "Customize menu colors and appearance",
        "setting_language": "Language",
        "setting_language_desc": "Change tool language",
        "setting_reset": "Reset to Defaults",
        "setting_reset_desc": "Reset all settings to default values",
        "setting_back": "Save & Return",
        "setting_back_desc": "Save changes and return to main menu",
        "value_on": "ON",
        "value_off": "OFF",
        "action": "Action",
        "save_settings_success": "✓ Settings saved successfully!",
        "reset_defaults_confirm": "Reset all settings to defaults?",
        "reset_defaults_success": "✓ Settings reset to defaults!",
        "changes_cancelled": "✗ Changes cancelled",
        "lang_title": "LANGUAGE SETTINGS",
        "lang_subtitle": "Select your preferred language",
        "lang_en": "English",
        "lang_tr": "Turkish (Türkçe)",
        "lang_es": "Spanish (Español)",
        "lang_zh": "Chinese (中文)",
        "lang_back": "Back to Settings",
        "lang_changed": "✓ Language changed to",
        "enter_value": "Enter value",
        "must_be_between": "Value must be between",
        "and": "and",
        "theme_title": "THEME SETTINGS",
        "theme_subtitle": "Customize menu colors and appearance",
        "theme_color_settings": "COLOR SETTINGS",
        "color_primary": "Primary Color",
        "color_primary_desc": "Main text and headings color",
        "color_secondary": "Secondary Color",
        "color_secondary_desc": "Descriptions and less important text",
        "color_accent": "Accent Color",
        "color_accent_desc": "Accent color for highlights",
        "color_success": "Success Color",
        "color_success_desc": "Success messages color",
        "color_warning": "Warning Color",
        "color_warning_desc": "Warning messages color",
        "color_error": "Error Color",
        "color_error_desc": "Error messages color",
        "color_highlight": "Highlight Color",
        "color_highlight_desc": "Selected item highlight",
        "color_border": "Border Color",
        "color_border_desc": "Panel and table borders",
        "color_category": "Category Color",
        "color_category_desc": "Resource category headers",
        "color_resource_index": "Resource Index Color",
        "color_resource_index_desc": "Resource index numbers",
        "color_resource_name": "Resource Name Color",
        "color_resource_name_desc": "Resource names in lists",
        "color_file_count": "File Count Color",
        "color_file_count_desc": "File count numbers",
        "color_size_estimate": "Size Estimate Color",
        "color_size_estimate_desc": "File size estimates",
        "live_preview": "LIVE PREVIEW",
        "common_colors": "Common colors:",
        "special_formats": "Special formats: reverse <color>, bold <color>, dim <color>",
        "examples": "Examples: reverse grey70, bold cyan, dim yellow",
        "enter_color_value": "Enter color value",
        "color_updated": "✓ {name} updated",
        "reset_color_confirm": "Reset {name} to default ({default})?",
        "color_reset_success": "✓ {name} reset to default"
    },
    "tr": {
        "main_menu_title": "GELİŞMİŞ SNEAKS DUMPER & DECRYPTOR",
        "main_menu_subtitle": "v3.0.0",
        "status_grants_file": "Grants dosyası:",
        "status_output_size": "Çıktı boyutu:",
        "status_multi_threading": "Çoklu iş parçacığı:",
        "enabled": "Etkin",
        "disabled": "Devre dışı",
        "ready": "Hazır",
        "not_found": "Bulunamadı",
        "menu_dump_cfx": "cfx.re linkinden dump al",
        "menu_dump_cfx_desc": "Otomatik IP + Otomatik token",
        "menu_dump_ip": "Sunucu IP'sinden dump al",
        "menu_dump_ip_desc": "Manuel IP + Otomatik token",
        "menu_manual_token": "Manuel Token Modu",
        "menu_manual_token_desc": "Manuel IP + Manuel token",
        "menu_dump_domain": "Domain'den dump al",
        "menu_dump_domain_desc": "Domain + Otomatik token",
        "menu_decrypt": "Kaynakları Şifre Çöz",
        "menu_decrypt_desc": "Kaydedilen grantları kullan",
        "menu_manage_cache": "Önbellek Yönetimi",
        "menu_manage_cache_desc": "Önbellek ve geçmişi temizle",
        "menu_view_logs": "Günlükleri Görüntüle",
        "menu_view_logs_desc": "Dump günlüklerine göz at",
        "menu_settings": "Ayarlar",
        "menu_settings_desc": "Ayarları yapılandır",
        "menu_exit": "Çıkış",
        "menu_exit_desc": "Programı kapat",
        "press_enter_continue": "Devam etmek için Enter'a basın...",
        "thank_you": "FiveM Advanced Sneaks Dumper'ı kullandığınız için teşekkürler!",
        "program_interrupted": "Program kullanıcı tarafından durduruldu",
        "unexpected_error": "Beklenmeyen hata",
        "settings_title": "AYARLAR YAPILANDIRMASI",
        "settings_subtitle": "Gezinmek için okları • Seçmek için Enter • Değiştirmek için Space • İptal için ESC",
        "settings_configuration": "YAPILANDIRMA",
        "setting_multithreading": "Çoklu iş parçacığı",
        "setting_multithreading_desc": "Paralel indirmeleri etkinleştir",
        "setting_max_workers": "Maks. İşçiler",
        "setting_max_workers_desc": "Paralel indirme iş parçacıkları (1-500)",
        "setting_retry_count": "Yeniden Deneme Sayısı",
        "setting_retry_count_desc": "Başarısız indirmeler için deneme",
        "setting_auto_cleanup": "Otomatik Temizleme",
        "setting_auto_cleanup_desc": "Dumptan sonra geçici dosyaları temizle",
        "setting_auto_decrypt": "Otomatik Şifre Çözme",
        "setting_auto_decrypt_desc": "Dumptan sonra otomatik şifre çöz",
        "setting_logging": "Günlüklemeyi Etkinleştir",
        "setting_logging_desc": "Ayrıntılı günlükleri kaydet",
        "setting_download_timeout": "İndirme Zaman Aşımı",
        "setting_download_timeout_desc": "Saniye cinsinden zaman aşımı (10-300)",
        "setting_connection_timeout": "Bağlantı Zaman Aşımı",
        "setting_connection_timeout_desc": "Bağlantı zaman aşımı (5-120)",
        "setting_progress_bars": "İlerleme Çubuklarını Göster",
        "setting_progress_bars_desc": "İndirme ilerleme çubuklarını göster",
        "setting_adaptive_speed": "Uyarlanabilir Hız",
        "setting_adaptive_speed_desc": "Sunucuya göre hızı otomatik ayarla",
        "setting_batch_size": "Yığın Boyutu",
        "setting_batch_size_desc": "Yığın başına dosya (1-500)",
        "setting_connection_pooling": "Bağlantı Havuzu",
        "setting_connection_pooling_desc": "Hız için bağlantıları yeniden kullan",
        "setting_theme": "Tema Ayarları",
        "setting_theme_desc": "Menü renklerini ve görünümünü özelleştir",
        "setting_language": "Dil",
        "setting_language_desc": "Araç dilini değiştir",
        "setting_reset": "Varsayılanlara Sıfırla",
        "setting_reset_desc": "Tüm ayarları varsayılan değerlere sıfırla",
        "setting_back": "Kaydet & Geri Dön",
        "setting_back_desc": "Değişiklikleri kaydet ve ana menüye dön",
        "value_on": "AÇIK",
        "value_off": "KAPALI",
        "action": "Eylem",
        "save_settings_success": "✓ Ayarlar başarıyla kaydedildi!",
        "reset_defaults_confirm": "Tüm ayarlar varsayılanlara sıfırlansın mı?",
        "reset_defaults_success": "✓ Ayarlar varsayılanlara sıfırlandı!",
        "changes_cancelled": "✗ Değişiklikler iptal edildi",
        "lang_title": "DİL AYARLARI",
        "lang_subtitle": "Tercih ettiğiniz dili seçin",
        "lang_en": "İngilizce (English)",
        "lang_tr": "Türkçe",
        "lang_es": "İspanyolca (Español)",
        "lang_zh": "Çince (中文)",
        "lang_back": "Aylara Geri Dön",
        "lang_changed": "✓ Dil değiştirildi:",
        "enter_value": "Değer girin",
        "must_be_between": "Değer şunun arasında olmalıdır",
        "and": "ve",
        "theme_title": "TEMA AYARLARI",
        "theme_subtitle": "Menü renklerini ve görünümünü özelleştir",
        "theme_color_settings": "RENK AYARLARI",
        "color_primary": "Ana Renk",
        "color_primary_desc": "Ana metin ve başlıklar rengi",
        "color_secondary": "İkincil Renk",
        "color_secondary_desc": "Açıklamalar ve daha az önemli metin",
        "color_accent": "Vurgu Rengi",
        "color_accent_desc": "Vurgular için vurgu rengi",
        "color_success": "Başarı Rengi",
        "color_success_desc": "Başarı mesajları rengi",
        "color_warning": "Uyarı Rengi",
        "color_warning_desc": "Uyarı mesajları rengi",
        "color_error": "Hata Rengi",
        "color_error_desc": "Hata mesajları rengi",
        "color_highlight": "Vurgulama Rengi",
        "color_highlight_desc": "Seçili öğe vurgulaması",
        "color_border": "Kenarlık Rengi",
        "color_border_desc": "Panel ve tablo kenarlıkları",
        "color_category": "Kategori Rengi",
        "color_category_desc": "Kaynak kategori başlıkları",
        "color_resource_index": "Kaynak İndeksi Rengi",
        "color_resource_index_desc": "Kaynak indeks numaraları",
        "color_resource_name": "Kaynak Adı Rengi",
        "color_resource_name_desc": "Listelerdeki kaynak adları",
        "color_file_count": "Dosya Sayısı Rengi",
        "color_file_count_desc": "Dosya sayısı numaraları",
        "color_size_estimate": "Boyut Tahmini Rengi",
        "color_size_estimate_desc": "Dosya boyutu tahminleri",
        "live_preview": "CANLI ÖNİZLEME",
        "common_colors": "Yaygın renkler:",
        "special_formats": "Özel formatlar: reverse <renk>, bold <renk>, dim <renk>",
        "examples": "Örnekler: reverse grey70, bold cyan, dim yellow",
        "enter_color_value": "Renk değeri girin",
        "color_updated": "✓ {name} güncellendi",
        "reset_color_confirm": "{name} varsayılana ({default}) sıfırlansın mı?",
        "color_reset_success": "✓ {name} varsayılana sıfırlandı"
    },
    "es": {
        "main_menu_title": "ADVANCED SNEAKS DUMPER & DECRYPTOR",
        "main_menu_subtitle": "v3.0.0",
        "status_grants_file": "Archivo de concesiones:",
        "status_output_size": "Tamaño de salida:",
        "status_multi_threading": "Multi-threading:",
        "enabled": "Habilitado",
        "disabled": "Deshabilitado",
        "ready": "Listo",
        "not_found": "No encontrado",
        "menu_dump_cfx": "Volcar desde enlace cfx.re",
        "menu_dump_cfx_desc": "IP Auto + Token Auto",
        "menu_dump_ip": "Volcar desde IP del Servidor",
        "menu_dump_ip_desc": "IP Manual + Token Auto",
        "menu_manual_token": "Modo Token Manual",
        "menu_manual_token_desc": "IP Manual + Token Manual",
        "menu_dump_domain": "Volcar desde Dominio",
        "menu_dump_domain_desc": "Dominio + Token Auto",
        "menu_decrypt": "Desencriptar Recursos",
        "menu_decrypt_desc": "Usar concesiones guardadas",
        "menu_manage_cache": "Gestionar Caché",
        "menu_manage_cache_desc": "Limpiar caché e historial",
        "menu_view_logs": "Ver Registros",
        "menu_view_logs_desc": "Explorar registros de volcado",
        "menu_settings": "Ajustes",
        "menu_settings_desc": "Configurar ajustes",
        "menu_exit": "Salir",
        "menu_exit_desc": "Cerrar programa",
        "press_enter_continue": "Presione Enter para continuar...",
        "thank_you": "¡Gracias por usar FiveM Advanced Sneaks Dumper!",
        "program_interrupted": "Programa interrumpido por el usuario",
        "unexpected_error": "Error inesperado",
        "settings_title": "CONFIGURACIÓN DE AJUSTES",
        "settings_subtitle": "Use flechas para navegar • Enter para seleccionar • Espacio para alternar • ESC para cancelar",
        "settings_configuration": "CONFIGURACIÓN",
        "setting_multithreading": "Multi-threading",
        "setting_multithreading_desc": "Habilitar descargas paralelas",
        "setting_max_workers": "Trabajadores Máx.",
        "setting_max_workers_desc": "Hilos de descarga paralela (1-500)",
        "setting_retry_count": "Conteo de Reintentos",
        "setting_retry_count_desc": "Reintentos para descargas fallidas",
        "setting_auto_cleanup": "Limpieza Automática",
        "setting_auto_cleanup_desc": "Limpiar archivos temporales después de volcar",
        "setting_auto_decrypt": "Desencriptado Automático",
        "setting_auto_decrypt_desc": "Desencriptar automáticamente después de volcar",
        "setting_logging": "Habilitar Registro",
        "setting_logging_desc": "Guardar registros detallados",
        "setting_download_timeout": "Tiempo de Espera de Descarga",
        "setting_download_timeout_desc": "Tiempo de espera en segundos (10-300)",
        "setting_connection_timeout": "Tiempo de Espera de Conexión",
        "setting_connection_timeout_desc": "Tiempo de espera de conexión (5-120)",
        "setting_progress_bars": "Mostrar Barras de Progreso",
        "setting_progress_bars_desc": "Mostrar barras de progreso de descarga",
        "setting_adaptive_speed": "Velocidad Adaptativa",
        "setting_adaptive_speed_desc": "Auto-ajustar velocidad basado en el servidor",
        "setting_batch_size": "Tamaño de Lote",
        "setting_batch_size_desc": "Archivos por lote (1-500)",
        "setting_connection_pooling": "Agrupación de Conexiones",
        "setting_connection_pooling_desc": "Reutilizar conexiones para velocidad",
        "setting_theme": "Ajustes de Tema",
        "setting_theme_desc": "Personalizar colores y apariencia del menú",
        "setting_language": "Idioma",
        "setting_language_desc": "Cambiar idioma de la herramienta",
        "setting_reset": "Restablecer Valores",
        "setting_reset_desc": "Restablecer todos los ajustes a valores por defecto",
        "setting_back": "Guardar y Volver",
        "setting_back_desc": "Guardar cambios y volver al menú principal",
        "value_on": "ENCENDIDO",
        "value_off": "APAGADO",
        "action": "Acción",
        "save_settings_success": "✓ ¡Ajustes guardados exitosamente!",
        "reset_defaults_confirm": "¿Restablecer todos los ajustes a valores por defecto?",
        "reset_defaults_success": "✓ ¡Ajustes restablecidos a valores por defecto!",
        "changes_cancelled": "✗ Cambios cancelados",
        "lang_title": "AJUSTES DE IDIOMA",
        "lang_subtitle": "Seleccione su idioma preferido",
        "lang_en": "Inglés (English)",
        "lang_tr": "Turco (Türkçe)",
        "lang_es": "Español",
        "lang_zh": "Chino (中文)",
        "lang_back": "Volver a Ajustes",
        "lang_changed": "✓ Idioma cambiado a",
        "enter_value": "Ingresar valor",
        "must_be_between": "El valor debe estar entre",
        "and": "y",
        "theme_title": "AJUSTES DE TEMA",
        "theme_subtitle": "Personalizar colores y apariencia del menú",
        "theme_color_settings": "AJUSTES DE COLOR",
        "color_primary": "Color Primario",
        "color_primary_desc": "Color de texto principal y encabezados",
        "color_secondary": "Color Secundario",
        "color_secondary_desc": "Descripciones y texto menos importante",
        "color_accent": "Color de Acento",
        "color_accent_desc": "Color de acento para resaltados",
        "color_success": "Color de Éxito",
        "color_success_desc": "Color de mensajes de éxito",
        "color_warning": "Color de Advertencia",
        "color_warning_desc": "Color de mensajes de advertencia",
        "color_error": "Color de Error",
        "color_error_desc": "Color de mensajes de error",
        "color_highlight": "Color de Resaltado",
        "color_highlight_desc": "Resaltado de elemento seleccionado",
        "color_border": "Color de Borde",
        "color_border_desc": "Bordes de panel y tabla",
        "color_category": "Color de Categoría",
        "color_category_desc": "Encabezados de categoría de recursos",
        "color_resource_index": "Color de Índice de Recursos",
        "color_resource_index_desc": "Números de índice de recursos",
        "color_resource_name": "Color de Nombre de Recurso",
        "color_resource_name_desc": "Nombres de recursos en listas",
        "color_file_count": "Color de Conteo de Archivos",
        "color_file_count_desc": "Números de conteo de archivos",
        "color_size_estimate": "Color de Estimación de Tamaño",
        "color_size_estimate_desc": "Estimaciones de tamaño de archivo",
        "live_preview": "VISTA PREVIA EN VIVO",
        "common_colors": "Colores comunes:",
        "special_formats": "Formatos especiales: reverse <color>, bold <color>, dim <color>",
        "examples": "Ejemplos: reverse grey70, bold cyan, dim yellow",
        "enter_color_value": "Ingresar valor de color",
        "color_updated": "✓ {name} actualizado",
        "reset_color_confirm": "¿Restablecer {name} al valor por defecto ({default})?",
        "color_reset_success": "✓ {name} restablecido al valor por defecto"
    },
    "zh": {
        "main_menu_title": "高级潜伏转储器和解密器",
        "main_menu_subtitle": "v3.0.0",
        "status_grants_file": "授权文件：",
        "status_output_size": "输出大小：",
        "status_multi_threading": "多线程：",
        "enabled": "已启用",
        "disabled": "已禁用",
        "ready": "就绪",
        "not_found": "未找到",
        "menu_dump_cfx": "从 cfx.re 链接转储",
        "menu_dump_cfx_desc": "自动 IP + 自动令牌",
        "menu_dump_ip": "从服务器 IP 转储",
        "menu_dump_ip_desc": "手动 IP + 自动令牌",
        "menu_manual_token": "手动令牌模式",
        "menu_manual_token_desc": "手动 IP + 手动令牌",
        "menu_dump_domain": "从域名转储",
        "menu_dump_domain_desc": "域名 + 自动令牌",
        "menu_decrypt": "解密资源",
        "menu_decrypt_desc": "使用保存的授权",
        "menu_manage_cache": "管理缓存",
        "menu_manage_cache_desc": "清除缓存和历史记录",
        "menu_view_logs": "查看日志",
        "menu_view_logs_desc": "浏览转储日志",
        "menu_settings": "设置",
        "menu_settings_desc": "配置设置",
        "menu_exit": "退出",
        "menu_exit_desc": "关闭程序",
        "press_enter_continue": "按 Enter 继续...",
        "thank_you": "感谢您使用 FiveM 高级潜伏转储器！",
        "program_interrupted": "程序被用户中断",
        "unexpected_error": "意外错误",
        "settings_title": "设置配置",
        "settings_subtitle": "使用箭头导航 • Enter 选择 • Space 切换 • ESC 取消",
        "settings_configuration": "配置",
        "setting_multithreading": "多线程",
        "setting_multithreading_desc": "启用并行下载",
        "setting_max_workers": "最大工作线程",
        "setting_max_workers_desc": "并行下载线程 (1-500)",
        "setting_retry_count": "重试次数",
        "setting_retry_count_desc": "失败下载的重试次数",
        "setting_auto_cleanup": "自动清理",
        "setting_auto_cleanup_desc": "转储后清理临时文件",
        "setting_auto_decrypt": "自动解密",
        "setting_auto_decrypt_desc": "转储后自动解密",
        "setting_logging": "启用日志",
        "setting_logging_desc": "保存详细日志",
        "setting_download_timeout": "下载超时",
        "setting_download_timeout_desc": "超时时间（秒）(10-300)",
        "setting_connection_timeout": "连接超时",
        "setting_connection_timeout_desc": "连接超时 (5-120)",
        "setting_progress_bars": "显示进度条",
        "setting_progress_bars_desc": "显示下载进度条",
        "setting_adaptive_speed": "自适应速度",
        "setting_adaptive_speed_desc": "根据服务器自动调整速度",
        "setting_batch_size": "批量大小",
        "setting_batch_size_desc": "每批文件数 (1-500)",
        "setting_connection_pooling": "连接池",
        "setting_connection_pooling_desc": "重用连接以提高速度",
        "setting_theme": "主题设置",
        "setting_theme_desc": "自定义菜单颜色和外观",
        "setting_language": "语言",
        "setting_language_desc": "更改工具语言",
        "setting_reset": "重置为默认值",
        "setting_reset_desc": "将所有设置重置为默认值",
        "setting_back": "保存并返回",
        "setting_back_desc": "保存更改并返回主菜单",
        "value_on": "开",
        "value_off": "关",
        "action": "动作",
        "save_settings_success": "✓ 设置保存成功！",
        "reset_defaults_confirm": "将所有设置重置为默认值？",
        "reset_defaults_success": "✓ 设置已重置为默认值！",
        "changes_cancelled": "✗ 更改已取消",
        "lang_title": "语言设置",
        "lang_subtitle": "选择您的首选语言",
        "lang_en": "英语",
        "lang_tr": "土耳其语 (Türkçe)",
        "lang_es": "西班牙语 (Español)",
        "lang_zh": "中文",
        "lang_back": "返回设置",
        "lang_changed": "✓ 语言已更改为",
        "enter_value": "输入值",
        "must_be_between": "值必须介于",
        "and": "和",
        "theme_title": "主题设置",
        "theme_subtitle": "自定义菜单颜色和外观",
        "theme_color_settings": "颜色设置",
        "color_primary": "主要颜色",
        "color_primary_desc": "主要文本和标题颜色",
        "color_secondary": "次要颜色",
        "color_secondary_desc": "描述和次要文本",
        "color_accent": "强调颜色",
        "color_accent_desc": "用于高亮的强调颜色",
        "color_success": "成功颜色",
        "color_success_desc": "成功消息颜色",
        "color_warning": "警告颜色",
        "color_warning_desc": "警告消息颜色",
        "color_error": "错误颜色",
        "color_error_desc": "错误消息颜色",
        "color_highlight": "高亮颜色",
        "color_highlight_desc": "选定项目高亮",
        "color_border": "边框颜色",
        "color_border_desc": "面板和表格边框",
        "color_category": "类别颜色",
        "color_category_desc": "资源类别标题",
        "color_resource_index": "资源索引颜色",
        "color_resource_index_desc": "资源索引编号",
        "color_resource_name": "资源名称颜色",
        "color_resource_name_desc": "列表中的资源名称",
        "color_file_count": "文件计数颜色",
        "color_file_count_desc": "文件计数编号",
        "color_size_estimate": "大小估算颜色",
        "color_size_estimate_desc": "文件大小估算",
        "live_preview": "实时预览",
        "common_colors": "常用颜色：",
        "special_formats": "特殊格式：reverse <颜色>, bold <颜色>, dim <颜色>",
        "examples": "示例：reverse grey70, bold cyan, dim yellow",
        "enter_color_value": "输入颜色值",
        "color_updated": "✓ {name} 已更新",
        "reset_color_confirm": "将 {name} 重置为默认值 ({default})？",
        "color_reset_success": "✓ {name} 已重置为默认值"
    }
}

def t(key):
    lang = settings.get("language", "en")
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    return lang_dict.get(key, TRANSLATIONS["en"].get(key, key))

DEFAULT_SETTINGS = {
    "language": "en",
    "multi_threading": True,
    "max_workers": 500,
    "retry_count": 15,
    "auto_cleanup": False,
    "auto_decrypt": False,
    "enable_logging": True,
    "download_timeout": 120,
    "connection_timeout": 15,
    "show_progress_bars": True,
    "adaptive_speed": True,
    "batch_size": 100,
    "connection_pooling": True,
    "theme": {
        "primary": "grey70",
        "secondary": "grey50",
        "accent": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "red",
        "highlight": "reverse grey70",
        "border": "grey50",
        "background": "default",
        "category": "bold cyan",
        "resource_index": "bold white",
        "resource_name": "white",
        "file_count": "yellow",
        "size_estimate": "magenta"
    }
}

class Settings:
    def __init__(self):
        self.settings_file = None
        self.settings = DEFAULT_SETTINGS.copy()

    def load_settings(self):
        return DEFAULT_SETTINGS.copy()

    def save_settings(self):
        # Disabled: No settings.json should be created
        return True

    def get(self, key, default=None):
        return self.settings.get(key, DEFAULT_SETTINGS.get(key, default))

    def get_theme(self, key):
        theme = self.settings.get("theme", DEFAULT_SETTINGS["theme"])
        return theme.get(key, DEFAULT_SETTINGS["theme"][key])

    def set(self, key, value):
        self.settings[key] = value
        return self.save_settings()

    def set_theme(self, key, value):
        if "theme" not in self.settings:
            self.settings["theme"] = DEFAULT_SETTINGS["theme"].copy()
        self.settings["theme"][key] = value
        return self.save_settings()

    def reset_to_defaults(self):
        self.settings = DEFAULT_SETTINGS.copy()
        return self.save_settings()

    def get_all_settings(self):
        return self.settings.copy()

settings = Settings()

class Logger:
    @staticmethod
    def info(msg: str):
        global log_counter
        timestamp = datetime.now().strftime("%H:%M:%S")
        console.print(f"[{settings.get_theme('primary')}][{timestamp}][/{settings.get_theme('primary')}] [{settings.get_theme('primary')}]INFO[/{settings.get_theme('primary')}] {msg}")
        dump_log.append(f"{log_counter:>4} [{timestamp}] [INFO] {msg}")
        log_counter += 1

    @staticmethod
    def warning(msg: str):
        global log_counter
        timestamp = datetime.now().strftime("%H:%M:%S")
        console.print(f"[{settings.get_theme('primary')}][{timestamp}][/{settings.get_theme('primary')}] [{settings.get_theme('warning')}]WARN[/{settings.get_theme('warning')}] {msg}")
        dump_log.append(f"{log_counter:>4} [{timestamp}] [WARN] {msg}")
        log_counter += 1

    @staticmethod
    def error(msg: str):
        global log_counter
        timestamp = datetime.now().strftime("%H:%M:%S")
        console.print(f"[{settings.get_theme('primary')}][{timestamp}][/{settings.get_theme('primary')}] [{settings.get_theme('error')}]ERROR[/{settings.get_theme('error')}] {msg}")
        dump_log.append(f"{log_counter:>4} [{timestamp}] [ERROR] {msg}")
        log_counter += 1

    @staticmethod
    def success(msg: str):
        global log_counter
        timestamp = datetime.now().strftime("%H:%M:%S")
        console.print(f"[{settings.get_theme('primary')}][{timestamp}][/{settings.get_theme('primary')}] [{settings.get_theme('success')}]SUCCESS[/{settings.get_theme('success')}] {msg}")
        dump_log.append(f"{log_counter:>4} [{timestamp}] [SUCCESS] {msg}")
        log_counter += 1

    @staticmethod
    def dump(msg: str):
        global log_counter
        timestamp = datetime.now().strftime("%H:%M:%S")
        console.print(f"[{settings.get_theme('primary')}][{timestamp}][/{settings.get_theme('primary')}] [{settings.get_theme('accent')}]DUMP[/{settings.get_theme('accent')}] {msg}")
        dump_log.append(f"{log_counter:>4} [{timestamp}] [DUMP] {msg}")
        log_counter += 1

    @staticmethod
    def display(msg: str):
        console.print(msg)

def format_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def get_cache_locations():
    return [
        {"path": os.path.expandvars(r"%LOCALAPPDATA%\FiveM\FiveM.app\cache"), "name": "Main Cache", "description": "Game files and resources cache"},
        {"path": os.path.expandvars(r"%LOCALAPPDATA%\FiveM\FiveM.app\data\cache"), "name": "Data Cache", "description": "Game data and settings cache"},
        {"path": os.path.expandvars(r"%LOCALAPPDATA%\FiveM\FiveM.app\data\server-cache"), "name": "Server Cache", "description": "Server-specific cache files"},
        {"path": os.path.expandvars(r"%LOCALAPPDATA%\FiveM\FiveM.app\data\browser"), "name": "Browser History", "description": "In-game browser history and cookies"},
        {"path": os.path.expandvars(r"%LOCALAPPDATA%\FiveM\FiveM.app\data\nui-storage"), "name": "NUI Storage", "description": "NUI interface storage and cache"},
        {"path": os.path.expandvars(r"%LOCALAPPDATA%\FiveM\FiveM.app\data\shared"), "name": "Shared Data", "description": "Shared game data and preferences"},
        {"path": os.path.expandvars(r"%LOCALAPPDATA%\FiveM\FiveM.app\logs"), "name": "Game Logs", "description": "Game and server connection logs"},
        {"path": os.path.expandvars(r"%LOCALAPPDATA%\FiveM\FiveM.app\crashes"), "name": "Crash Reports", "description": "Crash reports and diagnostics"},
        {"path": os.path.expandvars(r"%LOCALAPPDATA%\FiveM\FiveM.app\temp"), "name": "Temp Files", "description": "Temporary game files"}
    ]

def clear_specific_cache(cache_info):
    path = cache_info["path"]
    name = cache_info["name"]

    if not os.path.exists(path):
        return False, f"{name}: Not found"

    try:
        if os.path.isfile(path):
            os.remove(path)
            size = os.path.getsize(path) if os.path.exists(path) else 0
        else:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)
            shutil.rmtree(path)
            size = total_size
        return True, f"{name}: Cleared {format_size(size)}"
    except Exception as e:
        return False, f"{name}: Failed - {str(e)}"

def clear_all_fivem_cache():
    cache_locations = get_cache_locations()
    console.clear()
    primary = settings.get_theme("primary")
    secondary = settings.get_theme("secondary")
    border = settings.get_theme("border")

    console.print(Panel.fit(f"[bold {primary}]CLEAR ALL FIVEM CACHE[/bold {primary}]\n[{secondary}]This will delete ALL cache and reset your history[/{secondary}]", border_style=border, padding=(1, 2)))

    warning_panel = Panel.fit(f"[bold {primary}]WARNING:[/bold {primary}] This action will:\n• Delete ALL cached game files\n• Remove server connection history\n• Clear recently played servers\n• Reset game preferences\n• Delete crash reports and logs\n\n[{secondary}]This cannot be undone![/{secondary}]", border_style=border, padding=(1, 2))
    console.print(warning_panel)
    console.print()

    if not Confirm.ask(f"[bold {primary}]Are you absolutely sure you want to continue?[/bold {primary}]"):
        console.print(f"\n[{secondary}]Cache cleanup cancelled[/{secondary}]")
        time.sleep(1)
        return

    console.print(f"\n[bold {primary}]Cache locations to be cleared:[/bold {primary}]")
    cache_table = Table(box=box.SIMPLE, show_header=True, header_style=f"bold {primary}")
    cache_table.add_column("#", style=primary, width=3)
    cache_table.add_column("Cache Name", style=primary, width=20)
    cache_table.add_column("Description", style=secondary, width=40)
    cache_table.add_column("Status", style=primary, width=15)

    for i, cache_info in enumerate(cache_locations, 1):
        exists = os.path.exists(cache_info["path"])
        status = f"[{primary}]Found[/{primary}]" if exists else f"[{secondary}]Not found[/{secondary}]"
        cache_table.add_row(str(i), cache_info["name"], cache_info["description"], status)

    console.print(cache_table)
    console.print()

    if not Confirm.ask(f"[bold {primary}]Proceed with clearing all cache?[/bold {primary}]"):
        console.print(f"\n[{secondary}]Cache cleanup cancelled[/{secondary}]")
        time.sleep(1)
        return

    console.print(f"\n[bold {primary}]Clearing FiveM Cache...[/bold {primary}]")

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(bar_width=40), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"), TimeRemainingColumn(), console=console, transient=True) as progress:
        task = progress.add_task(f"[{primary}]Cleaning cache...[/{primary}]", total=len(cache_locations))
        results = []
        for cache_info in cache_locations:
            success, message = clear_specific_cache(cache_info)
            results.append((cache_info["name"], success, message))
            progress.update(task, advance=1)

    console.print(f"\n[bold {primary}]Cleanup Results:[/bold {primary}]")
    results_table = Table(box=box.SIMPLE, show_header=True, header_style=f"bold {primary}")
    results_table.add_column("Cache", style=primary, width=20)
    results_table.add_column("Result", style=primary, width=15)
    results_table.add_column("Details", style=secondary, width=40)

    successful = 0
    total = 0

    for name, success, message in results:
        total += 1
        if success:
            successful += 1
            result_text = f"[{primary}]Cleared[/{primary}]"
        else:
            result_text = f"[{secondary}]Failed[/{secondary}]"
        results_table.add_row(name, result_text, message)

    console.print(results_table)

    if successful > 0:
        console.print(f"\n[{primary}]✓ Successfully cleared {successful}/{total} cache locations[/{primary}]")
        console.print(f"[{secondary}]Note: You may need to restart FiveM for changes to take full effect[/{secondary}]")
    else:
        console.print(f"\n[{secondary}]No cache was cleared[/{secondary}]")

    console.print()
    Prompt.ask(f"[bold {primary}]{t('press_enter_continue')}[/bold {primary}]")

def display_cache_menu():
    primary = settings.get_theme("primary")
    secondary = settings.get_theme("secondary")
    border = settings.get_theme("border")
    highlight = settings.get_theme("highlight")

    cache_menu = [
        {"id": "clear_all", "name": "Clear All Cache", "type": "action", "desc": "Delete ALL cache and reset history"},
        {"id": "clear_game", "name": "Clear Game Cache Only", "type": "action", "desc": "Delete only game files cache"},
        {"id": "clear_history", "name": "Clear History Only", "type": "action", "desc": "Delete only history and recently played"},
        {"id": "view_details", "name": "View Cache Details", "type": "action", "desc": "See what will be deleted"},
        {"id": "back", "name": "Back to Main Menu", "type": "action", "desc": "Return to main menu"}
    ]

    selected_index = 0
    needs_refresh = True

    while True:
        if needs_refresh:
            console.clear()
            console.print(Panel.fit(f"[bold {primary}]FIVEM CACHE MANAGER[/bold {primary}]\n[{secondary}]Manage your FiveM cache and game history[/{secondary}]", border_style=border, padding=(1, 2)))

            cache_locations = get_cache_locations()
            total_size = 0
            found_locations = 0

            for cache_info in cache_locations:
                path = cache_info["path"]
                if os.path.exists(path):
                    found_locations += 1
                    if os.path.isfile(path):
                        total_size += os.path.getsize(path)
                    else:
                        for dirpath, dirnames, filenames in os.walk(path):
                            for f in filenames:
                                fp = os.path.join(dirpath, f)
                                if os.path.exists(fp):
                                    total_size += os.path.getsize(fp)

            status_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
            status_table.add_column("Metric", style=primary, width=20)
            status_table.add_column("Value", style=primary, width=30)
            status_table.add_row("Cache Locations Found", f"[{primary}]{found_locations}/{len(cache_locations)}[/{primary}]")
            status_table.add_row("Total Cache Size", f"[{primary}]{format_size(total_size)}[/{primary}]")
            status_table.add_row("Game History", f"[{primary}]Present[/{primary}]" if found_locations > 0 else f"[{secondary}]Not found[/{secondary}]")
            console.print(Panel(status_table, title=f"[bold {primary}]Current Cache Status[/bold {primary}]", border_style=border))
            console.print()

            cache_options_table = Table(box=box.SIMPLE, show_header=True, header_style=f"bold {primary}", border_style=border, padding=(0, 1), title=f"[bold {primary}]Cache Options[/bold {primary}]", title_style=f"bold {primary}")
            cache_options_table.add_column("", style=primary, width=3)
            cache_options_table.add_column("Option", style=primary, width=25)
            cache_options_table.add_column("Description", style=secondary, width=45)

            for i, item in enumerate(cache_menu):
                if i == selected_index:
                    option_name = f"[{highlight}] {item['name']} [/{highlight}]"
                    description = f"[{highlight}] {item['desc']} [/{highlight}]"
                else:
                    option_name = f" {item['name']}"
                    description = f" {item['desc']}"
                cache_options_table.add_row("▶" if i == selected_index else " ", option_name, description)

            console.print(cache_options_table)
            console.print()

            footer_text = Text()
            footer_text.append(" • ", style=secondary)
            footer_text.append("↑↓", style=f"bold {primary}")
            footer_text.append(" Navigate  • ", style=secondary)
            footer_text.append("Enter", style=f"bold {primary}")
            footer_text.append(" Select  • ", style=secondary)
            footer_text.append("ESC", style=f"bold {primary}")
            footer_text.append(" Back", style=secondary)
            console.print(Panel(footer_text, border_style=border, padding=(0, 1)))
            needs_refresh = False

        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'\xe0':
                arrow_key = msvcrt.getch()
                if arrow_key == b'H':
                    selected_index = (selected_index - 1) % len(cache_menu)
                    needs_refresh = True
                elif arrow_key == b'P':
                    selected_index = (selected_index + 1) % len(cache_menu)
                    needs_refresh = True
            elif key == b'\r':
                selected_item = cache_menu[selected_index]
                if selected_item["id"] == "back":
                    break
                elif selected_item["id"] == "clear_all":
                    clear_all_fivem_cache()
                    needs_refresh = True
                elif selected_item["id"] == "clear_game":
                    clear_game_cache_only()
                    needs_refresh = True
                elif selected_item["id"] == "clear_history":
                    clear_history_only()
                    needs_refresh = True
                elif selected_item["id"] == "view_details":
                    view_cache_details()
                    needs_refresh = True
            elif key == b'\x1b':
                break
        time.sleep(0.01)

def clear_game_cache_only():
    primary = settings.get_theme("primary")
    secondary = settings.get_theme("secondary")
    border = settings.get_theme("border")

    console.clear()
    console.print(Panel.fit(f"[bold {primary}]CLEAR GAME CACHE[/bold {primary}]\n[{secondary}]Delete only game files cache (preserves history)[/{secondary}]", border_style=border, padding=(1, 2)))

    game_cache_locations = [
        os.path.expandvars(r"%LOCALAPPDATA%\FiveM\FiveM.app\cache"),
        os.path.expandvars(r"%LOCALAPPDATA%\FiveM\FiveM.app\data\cache"),
        os.path.expandvars(r"%LOCALAPPDATA%\FiveM\FiveM.app\data\server-cache"),
        os.path.expandvars(r"%LOCALAPPDATA%\FiveM\FiveM.app\temp"),
    ]

    console.print(f"\n[bold {primary}]Game cache locations:[/bold {primary}]")
    for i, path in enumerate(game_cache_locations, 1):
        exists = os.path.exists(path)
        status = f"[{primary}]Found[/{primary}]" if exists else f"[{secondary}]Not found[/{secondary}]"
        console.print(f"  {i}. {os.path.basename(path)} {status}")

    console.print()
    console.print(f"[{primary}]This will delete cached game files but preserve your history[/{primary}]")

    if not Confirm.ask(f"\n[bold {primary}]Clear game cache?[/bold {primary}]"):
        console.print(f"\n[{secondary}]Operation cancelled[/{secondary}]")
        time.sleep(1)
        return

    cleared = 0
    total = len(game_cache_locations)

    for path in game_cache_locations:
        if os.path.exists(path):
            try:
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)
                cleared += 1
                console.print(f"[{primary}]✓ Cleared: {os.path.basename(path)}[/{primary}]")
            except Exception as e:
                console.print(f"[{secondary}]✗ Failed: {os.path.basename(path)} - {str(e)}[/{secondary}]")

    console.print(f"\n[{primary}]Cleared {cleared}/{total} game cache locations[/{primary}]")
    console.print()
    Prompt.ask(f"[bold {primary}]{t('press_enter_continue')}[/bold {primary}]")

def clear_history_only():
    primary = settings.get_theme("primary")
    secondary = settings.get_theme("secondary")
    border = settings.get_theme("border")

    console.clear()
    console.print(Panel.fit(f"[bold {primary}]CLEAR HISTORY[/bold {primary}]\n[{secondary}]Delete history and recently played servers[/{secondary}]", border_style=border, padding=(1, 2)))

    history_locations = [
        os.path.expandvars(r"%LOCALAPPDATA%\FiveM\FiveM.app\data\browser"),
        os.path.expandvars(r"%LOCALAPPDATA%\FiveM\FiveM.app\data\nui-storage"),
        os.path.expandvars(r"%LOCALAPPDATA%\FiveM\FiveM.app\logs"),
        os.path.expandvars(r"%LOCALAPPDATA%\FiveM\FiveM.app\crashes"),
    ]

    warning_panel = Panel.fit(f"[bold {primary}]WARNING:[/bold {primary}] This will:\n• Delete your server connection history\n• Clear recently played servers list\n• Remove browser history and cookies\n• Delete game logs and crash reports\n\n[{secondary}]Your game cache will be preserved[/{secondary}]", border_style=border, padding=(1, 2))
    console.print(warning_panel)
    console.print()

    if not Confirm.ask(f"\n[bold {primary}]Are you sure you want to clear your history?[/bold {primary}]"):
        console.print(f"\n[{secondary}]Operation cancelled[/{secondary}]")
        time.sleep(1)
        return

    cleared = 0
    total = len(history_locations)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(bar_width=40), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"), console=console, transient=True) as progress:
        task = progress.add_task(f"[{primary}]Clearing history...[/{primary}]", total=total)
        for path in history_locations:
            if os.path.exists(path):
                try:
                    if os.path.isfile(path):
                        os.remove(path)
                    else:
                        shutil.rmtree(path)
                    cleared += 1
                except Exception:
                    pass
            progress.update(task, advance=1)

    console.print(f"\n[{primary}]Cleared {cleared}/{total} history locations[/{primary}]")
    console.print(f"[{primary}]Your server history and recently played list has been reset[/{primary}]")
    console.print()
    Prompt.ask(f"[bold {primary}]{t('press_enter_continue')}[/bold {primary}]")

def view_cache_details():
    primary = settings.get_theme("primary")
    secondary = settings.get_theme("secondary")
    border = settings.get_theme("border")

    console.clear()
    console.print(Panel.fit(f"[bold {primary}]CACHE DETAILS[/bold {primary}]\n[{secondary}]View what cache will be deleted[/{secondary}]", border_style=border, padding=(1, 2)))

    cache_locations = get_cache_locations()
    details_table = Table(box=box.ROUNDED, show_header=True, header_style=f"bold {primary}", border_style=border, title=f"[bold {primary}]FiveM Cache Locations[/bold {primary}]")
    details_table.add_column("Cache Name", style=primary, width=20)
    details_table.add_column("Path", style=secondary, width=50)
    details_table.add_column("Size", style=primary, width=15)
    details_table.add_column("Type", style=primary, width=15)

    total_size = 0
    found_count = 0

    for cache_info in cache_locations:
        path = cache_info["path"]
        if os.path.exists(path):
            found_count += 1
            if os.path.isfile(path):
                size = os.path.getsize(path)
                cache_type = "File"
            else:
                size = 0
                try:
                    for dirpath, dirnames, filenames in os.walk(path):
                        for f in filenames:
                            fp = os.path.join(dirpath, f)
                            if os.path.exists(fp):
                                size += os.path.getsize(fp)
                except:
                    size = 0
                cache_type = "Folder"

            total_size += size
            size_str = format_size(size)
            display_path = path
            if len(path) > 45:
                display_path = "..." + path[-42:]
            details_table.add_row(cache_info["name"], display_path, size_str, cache_type)
        else:
            details_table.add_row(cache_info["name"], path, f"[{secondary}]Not found[/{secondary}]", f"[{secondary}]N/A[/{secondary}]")

    console.print(details_table)
    console.print()

    summary_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    summary_table.add_column("", style=primary, width=20)
    summary_table.add_column("", style=primary, width=20)
    summary_table.add_row("Total Cache Locations", f"[{primary}]{len(cache_locations)}[/{primary}]")
    summary_table.add_row("Locations Found", f"[{primary}]{found_count}[/{primary}]")
    summary_table.add_row("Total Cache Size", f"[{primary}]{format_size(total_size)}[/{primary}]")
    console.print(Panel(summary_table, title=f"[bold {primary}]Cache Summary[/bold {primary}]", border_style=border))
    console.print(f"\n[{secondary}]Note: Clearing cache will delete all files in these locations[/{secondary}]")
    console.print()
    Prompt.ask(f"[bold {primary}]{t('press_enter_continue')}[/bold {primary}]")

def find_fivem_process():
    pattern = re.compile(r"FiveM(_b\d+)?_GTAProcess", re.IGNORECASE)
    for proc in psutil.process_iter(attrs=["pid", "name"]):
        try:
            if pattern.match(proc.info["name"]):
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None

def get_token():
    proc = find_fivem_process()
    if not proc:
        raise RuntimeError("FiveM process not found")

    handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, proc.pid)
    if not handle:
        raise RuntimeError("Failed to open FiveM process")

    token_marker = b"X-CitizenFX-Token: "
    address = 0
    mbi = MEMORY_BASIC_INFORMATION()

    while VirtualQueryEx(handle, ctypes.c_void_p(address), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        if (mbi.State == MEM_COMMIT and (mbi.Protect & (PAGE_READWRITE | PAGE_READONLY)) and not (mbi.Protect & PAGE_GUARD)):
            if mbi.RegionSize > 64 * 1024 * 1024:
                address += mbi.RegionSize
                continue

            buffer = (ctypes.c_char * mbi.RegionSize)()
            bytesRead = SIZE_T()
            if ReadProcessMemory(handle, mbi.BaseAddress, buffer, mbi.RegionSize, ctypes.byref(bytesRead)):
                data = bytes(buffer)[: bytesRead.value]
                idx = data.find(token_marker)
                if idx != -1:
                    end = data.find(b"\x00", idx)
                    if end == -1:
                        end = idx + 100
                    token = data[idx:end].decode("ascii", errors="ignore")
                    return token.replace("X-CitizenFX-Token:", "").strip()
        address += mbi.RegionSize
    return None

def normalize_cfx_link(user_input: str) -> str:
    user_input = user_input.strip().lower()
    user_input = user_input.rstrip('/')

    if '/' not in user_input:
        return f"https://cfx.re/join/{user_input}"
    if user_input.startswith('cfx.re/join/'):
        return f"https://{user_input}"
    if user_input.startswith('https://cfx.re/join/'):
        return user_input
    if user_input.startswith('http://cfx.re/join/'):
        return user_input.replace('http://', 'https://', 1)
    if 'cfx.re/join/' in user_input:
        parts = user_input.split('cfx.re/join/')
        if len(parts) > 1:
            code = parts[1].split('/')[0].split('?')[0]
            return f"https://cfx.re/join/{code}"
    return user_input

def test_server_connection(base_url, timeout=10):
    urls_to_try = []
    if base_url.startswith('http://'):
        urls_to_try.append(base_url)
        urls_to_try.append(base_url.replace('http://', 'https://'))
    elif base_url.startswith('https://'):
        urls_to_try.append(base_url)
        urls_to_try.append(base_url.replace('https://', 'http://'))
    else:
        urls_to_try.append(f"https://{base_url}")
        urls_to_try.append(f"http://{base_url}")

    endpoints = ['/client', '/info.json', '/players.json', '/dynamic.json']
    session = requests.Session()
    session.verify = False
    session.headers.update({"User-Agent": "CitizenFX/1", "Accept": "*/*", "Accept-Encoding": "gzip, deflate", "Connection": "close", "Cache-Control": "no-cache"})
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')

    for url_base in urls_to_try:
        for endpoint in endpoints:
            try:
                test_url = f"{url_base}{endpoint}"
                Logger.info(f"Testing: {test_url}")
                resp = session.get(test_url, timeout=timeout, allow_redirects=False, stream=False)
                if resp.status_code in [200, 401, 403, 404]:
                    Logger.success(f"Server responded at {test_url} (Status: {resp.status_code})")
                    if 'X-CitizenFX-Token' in resp.headers or 'citizenfx' in resp.text.lower():
                        Logger.success(f"Confirmed FiveM server at {url_base}")
                        return url_base, True
                    else:
                        Logger.warning(f"Server at {url_base} may not be a FiveM server")
                        return url_base, True
            except requests.exceptions.SSLError:
                continue
            except requests.exceptions.ConnectionError as e:
                continue
            except requests.exceptions.Timeout:
                continue
            except Exception as e:
                continue
    return None, False

def get_ip_from_cfx(link: str) -> str:
    import ctypes as _ctypes
    import ctypes.wintypes as _wintypes
    import psutil as _psutil
    import re as _re
    import requests as _requests
    import threading as _threading

    link = normalize_cfx_link(link)
    join_code = link.lower().split("cfx.re/join/")[-1].strip("/")
    target_url = f"https://cfx.re/join/{join_code}"

    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010
    MEM_COMMIT = 0x1000
    PAGE_READWRITE = 0x04
    PAGE_READONLY = 0x02
    PAGE_GUARD = 0x100
    kernel32 = _ctypes.WinDLL("kernel32", use_last_error=True)

    if hasattr(_ctypes, 'c_size_t'):
        SIZE_T = _ctypes.c_size_t
    else:
        if _ctypes.sizeof(_ctypes.c_void_p) == 4:
            SIZE_T = _ctypes.c_uint32
        else:
            SIZE_T = _ctypes.c_uint64

    class MEMORY_BASIC_INFORMATION_LOCAL(_ctypes.Structure):
        _fields_ = [
            ("BaseAddress", _wintypes.LPVOID),
            ("AllocationBase", _wintypes.LPVOID),
            ("AllocationProtect", _ctypes.c_ulong),
            ("RegionSize", SIZE_T),
            ("State", _ctypes.c_ulong),
            ("Protect", _ctypes.c_ulong),
            ("Type", _ctypes.c_ulong),
        ]

    VirtualQueryEx = kernel32.VirtualQueryEx
    VirtualQueryEx.restype = SIZE_T
    VirtualQueryEx.argtypes = [_wintypes.HANDLE, _wintypes.LPCVOID, _ctypes.POINTER(MEMORY_BASIC_INFORMATION_LOCAL), SIZE_T]

    ReadProcessMemory = kernel32.ReadProcessMemory
    ReadProcessMemory.restype = _wintypes.BOOL
    ReadProcessMemory.argtypes = [_wintypes.HANDLE, _wintypes.LPCVOID, _wintypes.LPVOID, SIZE_T, _ctypes.POINTER(SIZE_T)]

    OpenProcess = kernel32.OpenProcess
    OpenProcess.restype = _wintypes.HANDLE
    OpenProcess.argtypes = [_wintypes.DWORD, _wintypes.BOOL, _wintypes.DWORD]

    CloseHandle = kernel32.CloseHandle
    CloseHandle.restype = _wintypes.BOOL

    IP_PORT_PATTERN = _re.compile(rb"(?:http://)?((?:\d{1,3}\.){3}\d{1,3}):(\d{1,5})")
    stop_event = _threading.Event()
    match_ip = {"val": None}

    def find_proc():
        for proc in _psutil.process_iter(["pid", "name"]):
            try:
                if _re.match(r"FiveM(_b\d+)?_GTAProcess", proc.info["name"] or "", _re.I):
                    return proc
            except (_psutil.NoSuchProcess, _psutil.AccessDenied):
                pass
        return None

    def test_ip(ip: str):
        if stop_event.is_set():
            return
        try:
            for protocol in ['http', 'https']:
                try:
                    r = _requests.get(f"{protocol}://{ip}/", allow_redirects=False, timeout=2.0, verify=False)
                    loc = r.headers.get("Location") or r.headers.get("location") or ""
                    if loc and join_code in loc.lower():
                        match_ip["val"] = ip
                        stop_event.set()
                        return
                except:
                    continue
        except Exception:
            pass

    proc = find_proc()
    if not proc:
        raise RuntimeError("No FiveM_GTAProcess found.")

    pid = proc.pid
    handle = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not handle:
        raise RuntimeError("OpenProcess failed (admin needed).")

    mbi = MEMORY_BASIC_INFORMATION_LOCAL()
    addr = 0
    min_size = 1_000
    max_size = 60_000_000

    try:
        while not stop_event.is_set():
            ret = VirtualQueryEx(handle, _ctypes.c_void_p(addr), _ctypes.byref(mbi), _ctypes.sizeof(mbi))
            if ret == 0:
                break
            size = mbi.RegionSize
            prot, state = mbi.Protect, mbi.State
            if (state == MEM_COMMIT and not (prot & PAGE_GUARD) and (prot & (PAGE_READWRITE | PAGE_READONLY)) and (min_size <= size <= max_size)):
                buf = (_ctypes.c_char * size)()
                br = SIZE_T()
                if ReadProcessMemory(handle, mbi.BaseAddress, buf, size, _ctypes.byref(br)):
                    data = bytes(buf[: br.value])
                    for m in _re.finditer(rb"(?:http://)?((?:\d{1,3}\.){3}\d{1,3}):(\d{1,5})", data):
                        if stop_event.is_set():
                            break
                        ip = m.group(1).decode("ascii", "ignore")
                        port = m.group(2).decode("ascii", "ignore")
                        try:
                            if not all(0 <= int(x) <= 255 for x in ip.split(".")):
                                continue
                            if not (1 <= int(port) <= 65535):
                                continue
                        except Exception:
                            continue
                        full_ip = f"{ip}:{port}"
                        _threading.Thread(target=test_ip, args=(full_ip,), daemon=True).start()
            addr += mbi.RegionSize
    finally:
        CloseHandle(handle)

    if not match_ip["val"]:
        raise RuntimeError("No match found.")
    return match_ip["val"]

def safe_name(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name)

def check_license_on_startup() -> bool:
    return True


def get_arrow_key():
    if msvcrt.kbhit():
        key = msvcrt.getch()
        if key == b'\xe0':
            key = msvcrt.getch()
            return key
        elif key == b'\r':
            return b'\r'
        elif key == b' ':
            return b' '
        elif key in [b'\x1b', b'q', b'Q']:
            return b'\x1b'
    return None

def display_language_settings():
    current_theme = settings.get_all_settings().get("theme", DEFAULT_SETTINGS["theme"])
    current_lang = settings.get("language", "en")
    primary = current_theme['primary']
    secondary = current_theme['secondary']
    border = current_theme['border']
    highlight = current_theme['highlight']

    languages = [
        {"id": "en", "name": t("lang_en"), "desc": "English"},
        {"id": "tr", "name": t("lang_tr"), "desc": "Türkçe"},
        {"id": "es", "name": t("lang_es"), "desc": "Español"},
        {"id": "zh", "name": t("lang_zh"), "desc": "中文"},
        {"id": "back", "name": t("lang_back"), "desc": ""}
    ]

    selected_index = 0
    for i, lang in enumerate(languages):
        if lang["id"] == current_lang:
            selected_index = i
            break

    needs_refresh = True

    while True:
        if needs_refresh:
            console.clear()
            console.print(Panel.fit(f"[bold {primary}]{t('lang_title')}[/bold {primary}]\n[{secondary}]{t('lang_subtitle')}[/{secondary}]", border_style=border, padding=(1, 2)))

            lang_table = Table(box=box.SIMPLE, show_header=True, header_style=f"bold {primary}", border_style=border, padding=(0, 1), title=f"[bold {primary}]{t('lang_title')}[/bold {primary}]", title_style=f"bold {primary}")
            lang_table.add_column("", style=primary, width=3)
            lang_table.add_column("Language", style=primary, width=25)
            lang_table.add_column("Description", style=secondary, width=30)
            lang_table.add_column("Status", style=primary, width=15)

            for i, lang in enumerate(languages):
                if lang["id"] == "back":
                    status = ""
                elif lang["id"] == current_lang:
                    status = f"[{primary}]✓ Selected[/{primary}]"
                else:
                    status = ""

                if i == selected_index:
                    lang_name = f"[{highlight}] {lang['name']} [/{highlight}]"
                    lang_desc = f"[{highlight}] {lang['desc']} [/{highlight}]" if lang['desc'] else ""
                    status_display = f"[{highlight}] {status} [/{highlight}]"
                else:
                    lang_name = f" {lang['name']}"
                    lang_desc = f" {lang['desc']}" if lang['desc'] else ""
                    status_display = f" {status}"

                lang_table.add_row("▶" if i == selected_index else " ", lang_name, lang_desc, status_display)

            console.print(lang_table)
            console.print()

            footer_text = Text()
            footer_text.append(" • ", style=secondary)
            footer_text.append("↑↓", style=f"bold {primary}")
            footer_text.append(" Navigate  • ", style=secondary)
            footer_text.append("Enter", style=f"bold {primary}")
            footer_text.append(" Select  • ", style=secondary)
            footer_text.append("ESC", style=f"bold {primary}")
            footer_text.append(" Back", style=secondary)
            console.print(Panel(footer_text, border_style=border, padding=(0, 1)))
            needs_refresh = False

        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'\xe0':
                arrow_key = msvcrt.getch()
                if arrow_key == b'H':
                    selected_index = (selected_index - 1) % len(languages)
                    needs_refresh = True
                elif arrow_key == b'P':
                    selected_index = (selected_index + 1) % len(languages)
                    needs_refresh = True
            elif key == b'\r':
                selected_lang = languages[selected_index]
                if selected_lang["id"] == "back":
                    break
                else:
                    settings.set("language", selected_lang["id"])
                    current_lang = selected_lang["id"]
                    try:
                        current_dir = os.path.dirname(__file__)
                        parent_dir = os.path.dirname(current_dir)
                        sys.path.append(parent_dir)
                        from license_client import get_license_client
                        client = get_license_client()
                        client.set_language(selected_lang["id"])
                    except:
                        pass
                    console.clear()
                    console.print(f"\n[{primary}]✓ {t('lang_changed')} {selected_lang['name']}[/{primary}]")
                    time.sleep(1)
                    needs_refresh = True
            elif key == b'\x1b':
                break
        time.sleep(0.01)

def display_settings():
    current_settings = settings.get_all_settings()
    theme = current_settings.get("theme", DEFAULT_SETTINGS["theme"])

    settings_menu = [
        {"id": "multi_threading", "name": t("setting_multithreading"), "type": "toggle", "desc": t("setting_multithreading_desc")},
        {"id": "max_workers", "name": t("setting_max_workers"), "type": "number", "desc": t("setting_max_workers_desc"), "min": 1, "max": 500},
        {"id": "retry_count", "name": t("setting_retry_count"), "type": "number", "desc": t("setting_retry_count_desc"), "min": 0, "max": 20},
        {"id": "auto_cleanup", "name": t("setting_auto_cleanup"), "type": "toggle", "desc": t("setting_auto_cleanup_desc")},
        {"id": "auto_decrypt", "name": t("setting_auto_decrypt"), "type": "toggle", "desc": t("setting_auto_decrypt_desc")},
        {"id": "enable_logging", "name": t("setting_logging"), "type": "toggle", "desc": t("setting_logging_desc")},
        {"id": "download_timeout", "name": t("setting_download_timeout"), "type": "number", "desc": t("setting_download_timeout_desc"), "min": 10, "max": 300},
        {"id": "connection_timeout", "name": t("setting_connection_timeout"), "type": "number", "desc": t("setting_connection_timeout_desc"), "min": 5, "max": 120},
        {"id": "show_progress_bars", "name": t("setting_progress_bars"), "type": "toggle", "desc": t("setting_progress_bars_desc")},
        {"id": "adaptive_speed", "name": t("setting_adaptive_speed"), "type": "toggle", "desc": t("setting_adaptive_speed_desc")},
        {"id": "batch_size", "name": t("setting_batch_size"), "type": "number", "desc": t("setting_batch_size_desc"), "min": 1, "max": 500},
        {"id": "connection_pooling", "name": t("setting_connection_pooling"), "type": "toggle", "desc": t("setting_connection_pooling_desc")},
        {"id": "language_settings", "name": t("setting_language"), "type": "action", "desc": t("setting_language_desc")},
        {"id": "theme_settings", "name": t("setting_theme"), "type": "action", "desc": t("setting_theme_desc")},
        {"id": "reset", "name": t("setting_reset"), "type": "action", "desc": t("setting_reset_desc")},
        {"id": "back", "name": t("setting_back"), "type": "action", "desc": t("setting_back_desc")}
    ]

    selected_index = 0
    needs_refresh = True

    while True:
        if needs_refresh:
            console.clear()
            console.print(Panel.fit(f"[bold {theme['primary']}]{t('settings_title')}[/bold {theme['primary']}]\n[{theme['secondary']}]{t('settings_subtitle')}[/{theme['secondary']}]", border_style=theme['border'], padding=(1, 2)))

            settings_table = Table(box=box.SIMPLE, show_header=True, header_style=f"bold {theme['primary']}", border_style=theme['border'], padding=(0, 1), title=f"[bold {theme['primary']}]{t('settings_configuration')}[/bold {theme['primary']}]", title_style=f"bold {theme['primary']}")
            settings_table.add_column("", style=theme['primary'], width=3)
            settings_table.add_column("Setting", style=theme['primary'], width=25)
            settings_table.add_column("Value", style=theme['secondary'], width=20)
            settings_table.add_column("Status", style=theme['primary'], width=15)
            settings_table.add_column("Description", style=theme['secondary'], width=35)

            for i, item in enumerate(settings_menu):
                if item["type"] == "action":
                    value_str = "→"
                    status = f"[{theme['primary']}]{t('action')}[/{theme['primary']}]"
                    setting_name = item['name']
                else:
                    value = current_settings.get(item["id"], "")
                    if item["type"] == "toggle":
                        value_str = t("enabled") if value else t("disabled")
                        status = f"[{theme['primary']}]{t('value_on')}[/{theme['primary']}]" if value else f"[{theme['secondary']}]{t('value_off')}[/{theme['secondary']}]"
                    else:
                        value_str = str(value)
                        status = f"[{theme['primary']}]{value}[/{theme['primary']}]"
                    setting_name = item["name"]

                if i == selected_index:
                    setting_name = f"[{theme['highlight']}] {setting_name} [/{theme['highlight']}]"
                    value_str = f"[{theme['highlight']}] {value_str} [/{theme['highlight']}]"
                    status = f"[{theme['highlight']}] {status} [/{theme['highlight']}]"
                else:
                    setting_name = f" {setting_name}"
                    value_str = f" {value_str}"
                    status = f" {status}"

                settings_table.add_row("▶" if i == selected_index else " ", setting_name, value_str, status, item["desc"])

            console.print(settings_table)
            console.print()

            footer_text = Text()
            footer_text.append(" • ", style=theme['secondary'])
            footer_text.append("↑↓", style=f"bold {theme['primary']}")
            footer_text.append(" Navigate  • ", style=theme['secondary'])
            footer_text.append("Enter", style=f"bold {theme['primary']}")
            footer_text.append(" Select  • ", style=theme['secondary'])
            footer_text.append("Space", style=f"bold {theme['primary']}")
            footer_text.append(" Toggle  • ", style=theme['secondary'])
            footer_text.append("ESC", style=f"bold {theme['primary']}")
            footer_text.append(" Cancel", style=theme['secondary'])
            console.print(Panel(footer_text, border_style=theme['border'], padding=(0, 1)))
            needs_refresh = False

        key = get_arrow_key()

        if key == b'H':
            selected_index = (selected_index - 1) % len(settings_menu)
            needs_refresh = True
        elif key == b'P':
            selected_index = (selected_index + 1) % len(settings_menu)
            needs_refresh = True
        elif key == b'\r':
            selected_item = settings_menu[selected_index]

            if selected_item["id"] == "back":
                if settings.save_settings():
                    console.clear()
                    console.print(f"\n[{theme['primary']}]{t('save_settings_success')}[/{theme['primary']}]")
                    time.sleep(1)
                break
            elif selected_item["id"] == "reset":
                console.clear()
                if Confirm.ask(f"\n[bold {theme['primary']}]{t('reset_defaults_confirm')}[/bold {theme['primary']}]"):
                    if settings.reset_to_defaults():
                        current_settings = settings.get_all_settings()
                        theme = current_settings.get("theme", DEFAULT_SETTINGS["theme"])
                        console.print(f"\n[{theme['primary']}]{t('reset_defaults_success')}[/{theme['primary']}]")
                        time.sleep(1)
                needs_refresh = True
            elif selected_item["id"] == "language_settings":
                display_language_settings()
                current_settings = settings.get_all_settings()
                needs_refresh = True
            elif selected_item["id"] == "theme_settings":
                display_theme_settings()
                current_settings = settings.get_all_settings()
                theme = current_settings.get("theme", DEFAULT_SETTINGS["theme"])
                needs_refresh = True
            elif selected_item["type"] == "toggle":
                current = current_settings.get(selected_item["id"], False)
                new_value = not current
                current_settings[selected_item["id"]] = new_value
                settings.set(selected_item["id"], new_value)
                status = t("enabled") if new_value else t("disabled")
                console.clear()
                console.print(f"\n[{theme['primary']}]✓ {selected_item['name']} {status}[/{theme['primary']}]")
                time.sleep(0.5)
                needs_refresh = True
            elif selected_item["type"] == "number":
                console.clear()
                console.print(Panel.fit(f"[bold {theme['primary']}]Configure {selected_item['name']}[/bold {theme['primary']}]\n[{theme['secondary']}]{selected_item['desc']}[/{theme['secondary']}]", border_style=theme['border']))
                current_val = current_settings.get(selected_item["id"], 0)
                try:
                    new_value = IntPrompt.ask(f"\n[bold {theme['primary']}]{t('enter_value')} ({selected_item['min']}-{selected_item['max']})[/bold {theme['primary']}]", default=current_val, show_default=True)
                    if selected_item['min'] <= new_value <= selected_item['max']:
                        current_settings[selected_item["id"]] = new_value
                        settings.set(selected_item["id"], new_value)
                        console.clear()
                        console.print(f"\n[{theme['primary']}]✓ {selected_item['name']} set to {new_value}[/{theme['primary']}]")
                        time.sleep(1)
                    else:
                        console.print(f"[{theme['secondary']}]{t('must_be_between')} {selected_item['min']} {t('and')} {selected_item['max']}[/{theme['secondary']}]")
                        time.sleep(2)
                except:
                    pass
                needs_refresh = True
        elif key == b' ':
            selected_item = settings_menu[selected_index]
            if selected_item["type"] == "toggle":
                current = current_settings.get(selected_item["id"], False)
                new_value = not current
                current_settings[selected_item["id"]] = new_value
                settings.set(selected_item["id"], new_value)
                status = t("enabled") if new_value else t("disabled")
                console.clear()
                console.print(f"\n[{theme['primary']}]✓ {selected_item['name']} {status}[/{theme['primary']}]")
                time.sleep(0.5)
                needs_refresh = True
        elif key == b'\x1b':
            console.clear()
            console.print(f"\n[{theme['secondary']}]{t('changes_cancelled')}[/{theme['secondary']}]")
            time.sleep(1)
            break
        time.sleep(0.01)

def display_theme_settings():
    current_theme = settings.get_all_settings().get("theme", DEFAULT_SETTINGS["theme"].copy())
    theme_colors = [
        {"id": "primary", "name": t("color_primary"), "desc": t("color_primary_desc"), "default": "grey70"},
        {"id": "secondary", "name": t("color_secondary"), "desc": t("color_secondary_desc"), "default": "grey50"},
        {"id": "accent", "name": t("color_accent"), "desc": t("color_accent_desc"), "default": "cyan"},
        {"id": "success", "name": t("color_success"), "desc": t("color_success_desc"), "default": "green"},
        {"id": "warning", "name": t("color_warning"), "desc": t("color_warning_desc"), "default": "yellow"},
        {"id": "error", "name": t("color_error"), "desc": t("color_error_desc"), "default": "red"},
        {"id": "highlight", "name": t("color_highlight"), "desc": t("color_highlight_desc"), "default": "reverse grey70"},
        {"id": "border", "name": t("color_border"), "desc": t("color_border_desc"), "default": "grey50"},
        {"id": "category", "name": t("color_category"), "desc": t("color_category_desc"), "default": "bold cyan"},
        {"id": "resource_index", "name": t("color_resource_index"), "desc": t("color_resource_index_desc"), "default": "bold white"},
        {"id": "resource_name", "name": t("color_resource_name"), "desc": t("color_resource_name_desc"), "default": "white"},
        {"id": "file_count", "name": t("color_file_count"), "desc": t("color_file_count_desc"), "default": "yellow"},
        {"id": "size_estimate", "name": t("color_size_estimate"), "desc": t("color_size_estimate_desc"), "default": "magenta"}
    ]

    selected_index = 0
    needs_refresh = True

    while True:
        if needs_refresh:
            console.clear()
            console.print(Panel.fit(f"[bold {current_theme['primary']}]{t('theme_title')}[/bold {current_theme['primary']}]\n[{current_theme['secondary']}]{t('theme_subtitle')}[/{current_theme['secondary']}]", border_style=current_theme['border'], padding=(1, 2)))

            colors_table = Table(box=box.SIMPLE, show_header=True, header_style=f"bold {current_theme['primary']}", border_style=current_theme['border'], padding=(0, 1), title=f"[bold {current_theme['primary']}]{t('theme_color_settings')}[/bold {current_theme['primary']}]", title_style=f"bold {current_theme['primary']}")
            colors_table.add_column("", style=current_theme['primary'], width=3)
            colors_table.add_column("Color", style=current_theme['primary'], width=25)
            colors_table.add_column("Current Value", style=current_theme['secondary'], width=20)
            colors_table.add_column("Preview", style=current_theme['primary'], width=15)
            colors_table.add_column("Description", style=current_theme['secondary'], width=35)

            for i, color in enumerate(theme_colors):
                current_value = current_theme.get(color["id"], color["default"])
                if color["id"] in ["category", "resource_index", "resource_name", "file_count", "size_estimate"]:
                    preview = f"[{current_value}]████████[/{current_value}]"
                else:
                    preview = f"[{current_value}]████████[/{current_value}]"

                if i == selected_index:
                    color_name = f"[{current_theme['highlight']}] {color['name']} [/{current_theme['highlight']}]"
                    value_display = f"[{current_theme['highlight']}] {current_value} [/{current_theme['highlight']}]"
                    preview_display = f"[{current_theme['highlight']}] {preview} [/{current_theme['highlight']}]"
                else:
                    color_name = f" {color['name']}"
                    value_display = f" {current_value}"
                    preview_display = f" {preview}"

                colors_table.add_row("▶" if i == selected_index else " ", color_name, value_display, preview_display, color["desc"])

            console.print(colors_table)
            console.print()

            preview_panel = Panel.fit(
                f"[{current_theme['primary']}]Primary Text[/{current_theme['primary']}] • "
                f"[{current_theme['secondary']}]Secondary Text[/{current_theme['secondary']}]\n"
                f"[{current_theme['accent']}]Accent Color[/{current_theme['accent']}] • "
                f"[{current_theme['success']}]Success[/{current_theme['success']}] • "
                f"[{current_theme['warning']}]Warning[/{current_theme['warning']}] • "
                f"[{current_theme['error']}]Error[/{current_theme['error']}]\n"
                f"[{current_theme['category']}]Category[/{current_theme['category']}] • "
                f"[{current_theme['resource_index']}]Index[/{current_theme['resource_index']}] • "
                f"[{current_theme['resource_name']}]Name[/{current_theme['resource_name']}] • "
                f"[{current_theme['file_count']}]File Count[/{current_theme['file_count']}] • "
                f"[{current_theme['size_estimate']}]Size Estimate[/{current_theme['size_estimate']}]",
                title=f"[bold {current_theme['primary']}]{t('live_preview')}[/bold {current_theme['primary']}]",
                border_style=current_theme['border']
            )
            console.print(preview_panel)
            console.print()

            footer_text = Text()
            footer_text.append(" • ", style=current_theme['secondary'])
            footer_text.append("↑↓", style=f"bold {current_theme['primary']}")
            footer_text.append(" Navigate  • ", style=current_theme['secondary'])
            footer_text.append("Enter", style=f"bold {current_theme['primary']}")
            footer_text.append(" Edit  • ", style=current_theme['secondary'])
            footer_text.append("R", style=f"bold {current_theme['primary']}")
            footer_text.append(" Reset Color  • ", style=current_theme['secondary'])
            footer_text.append("ESC", style=f"bold {current_theme['primary']}")
            footer_text.append(" Back", style=current_theme['secondary'])
            console.print(Panel(footer_text, border_style=current_theme['border'], padding=(0, 1)))
            needs_refresh = False

        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'\xe0':
                arrow_key = msvcrt.getch()
                if arrow_key == b'H':
                    selected_index = (selected_index - 1) % len(theme_colors)
                    needs_refresh = True
                elif arrow_key == b'P':
                    selected_index = (selected_index + 1) % len(theme_colors)
                    needs_refresh = True
            elif key == b'\r':
                selected_color = theme_colors[selected_index]
                console.clear()
                console.print(Panel.fit(f"[bold {current_theme['primary']}]Edit {selected_color['name']}[/bold {current_theme['primary']}]\n[{current_theme['secondary']}]{selected_color['desc']}[/{current_theme['secondary']}]", border_style=current_theme['border']))

                common_colors = ["white", "black", "red", "green", "yellow", "blue", "magenta", "cyan", "grey70", "grey50", "grey30", "bright_white", "bright_red", "bright_green", "bright_yellow", "bright_blue", "bright_magenta", "bright_cyan"]
                console.print(f"\n[{current_theme['primary']}]{t('common_colors')}[/{current_theme['primary']}]")
                color_grid = []
                for i in range(0, len(common_colors), 3):
                    row = common_colors[i:i+3]
                    color_line = ""
                    for col in row:
                        color_line += f"[{col}]{col:20}[/{col}]"
                    color_grid.append(color_line)
                for line in color_grid:
                    console.print(line)

                console.print(f"\n[{current_theme['primary']}]{t('special_formats')}[/{current_theme['primary']}]")
                console.print(f"[{current_theme['primary']}]{t('examples')}[/{current_theme['primary']}]")

                current_value = current_theme.get(selected_color["id"], selected_color["default"])
                new_value = Prompt.ask(f"\n[bold {current_theme['primary']}]{t('enter_color_value')}[/bold {current_theme['primary']}]", default=current_value).strip()

                if new_value:
                    settings.set_theme(selected_color["id"], new_value)
                    current_theme[selected_color["id"]] = new_value
                    console.clear()
                    console.print(f"\n[{current_theme['primary']}]✓ {t('color_updated').format(name=selected_color['name'])}[/{current_theme['primary']}]")
                    time.sleep(1)
                needs_refresh = True
            elif key in [b'r', b'R']:
                selected_color = theme_colors[selected_index]
                console.clear()
                if Confirm.ask(f"\n[bold {current_theme['primary']}]{t('reset_color_confirm').format(name=selected_color['name'], default=selected_color['default'])}[/bold {current_theme['primary']}]"):
                    settings.set_theme(selected_color["id"], selected_color["default"])
                    current_theme[selected_color["id"]] = selected_color["default"]
                    console.print(f"\n[{current_theme['primary']}]✓ {t('color_reset_success').format(name=selected_color['name'])}[/{current_theme['primary']}]")
                    time.sleep(1)
                needs_refresh = True
            elif key == b'\x1b':
                break
        time.sleep(0.01)

def categorize_resource(resource_name: str) -> str:
    name_lower = resource_name.lower()
    clothing_keywords = ['cloth', 'outfit', 'accessory', 'mask', 'hat', 'shirt', 'pants', 'shoes', 'bag', 'glove', 'vest', 'jacket', 'tattoo']
    if any(keyword in name_lower for keyword in clothing_keywords):
        return "Clothes"
    vehicle_keywords = ['vehicle', 'car', 'bike', 'motor', 'truck', 'plane', 'heli', 'boat', 'train', 'bicycle', 'sport', 'race', 'drift']
    if any(keyword in name_lower for keyword in vehicle_keywords):
        return "Vehicles"
    map_keywords = ['map', 'mapping', 'interior', 'exterior', 'world', 'island', 'location', 'zone', 'area', 'region', 'terrain']
    if any(keyword in name_lower for keyword in map_keywords):
        return "Maps"
    script_keywords = ['script', 'menu', 'ui', 'hud', 'system', 'framework', 'core', 'base', 'essential', 'required']
    if any(keyword in name_lower for keyword in script_keywords):
        return "Scripts"
    return "Other"

class ResourceManager:
    @staticmethod
    def group_resources(resources):
        categorized = defaultdict(list)
        for i, res in enumerate(resources):
            category = categorize_resource(res["name"])
            categorized[category].append((i, res))
        return categorized

    @staticmethod
    def display_resources_by_category(resources):
        categorized = ResourceManager.group_resources(resources)
        category_color = settings.get_theme("category")
        index_color = settings.get_theme("resource_index")
        name_color = settings.get_theme("resource_name")
        file_count_color = settings.get_theme("file_count")
        size_color = settings.get_theme("size_estimate")
        console.print("\n" + "="*80)
        console.print(f"[{category_color}]Available Resources (Grouped by Category)[/{category_color}]")
        console.print("="*80 + "\n")
        category_order = ["Scripts", "Maps", "Vehicles", "Clothes", "Other"]
        for category in category_order:
            if category in categorized:
                console.print(f"[{category_color}]=== {category.upper()} ===[/{category_color}]")
                console.print("-" * 40)
                for idx, res in categorized[category]:
                    file_count = len(res.get("files", {}))
                    stream_count = len(res.get("streamFiles", {}))
                    total_files = file_count + stream_count
                    size_estimate = total_files * 500
                    resource_line = f"[{index_color}][{idx:03d}][/{index_color}] [{name_color}]{res['name'][:30]:<30}[/{name_color}] [{file_count_color}]{total_files:>4} files[/{file_count_color}] [{size_color}]~{format_size(size_estimate * 1024)}[/{size_color}]"
                    console.print(resource_line)
                console.print("")
        console.print("="*80)
        return categorized

class ProgressTracker:
    def __init__(self):
        self.progress = None
        self.main_task_id = None
        self.resource_tasks = {}
        self.lock = threading.Lock()

    def start_main_progress(self, total_resources: int):
        if not settings.get("show_progress_bars"):
            return
        self.progress = Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(bar_width=40), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"), TextColumn("•"), TextColumn(f"[{settings.get_theme('accent')}]{{task.completed}}/{{task.total}} resources[/{settings.get_theme('accent')}]"), TextColumn("•"), TimeRemainingColumn(), console=console, transient=False)
        self.progress.start()
        self.main_task_id = self.progress.add_task(f"[bold {settings.get_theme('primary')}]Starting dump...[/bold {settings.get_theme('primary')}]", total=total_resources)
        return self.main_task_id

    def update_main_progress(self, completed: int, description: str = None):
        if not settings.get("show_progress_bars") or not self.progress or self.main_task_id is None:
            return
        update_args = {"advance": completed}
        if description:
            update_args["description"] = description
        self.progress.update(self.main_task_id, **update_args)

    def add_resource_task(self, resource_name: str, total_files: int, resource_idx: int, total_resources_count: int):
        if not settings.get("show_progress_bars") or not self.progress:
            return None
        task_id = self.progress.add_task(f"[{settings.get_theme('primary')}][{resource_idx+1}/{total_resources_count}] {resource_name[:25]:<25}[/{settings.get_theme('primary')}]", total=total_files, visible=True)
        with self.lock:
            self.resource_tasks[resource_name] = task_id
        return task_id

    def update_resource_task(self, resource_name: str, advance: int = 1, description: str = None):
        if not settings.get("show_progress_bars") or not self.progress:
            return
        with self.lock:
            if resource_name in self.resource_tasks:
                update_args = {"advance": advance}
                if description:
                    update_args["description"] = description
                self.progress.update(self.resource_tasks[resource_name], **update_args)

    def remove_resource_task(self, resource_name: str):
        if not settings.get("show_progress_bars") or not self.progress:
            return
        with self.lock:
            if resource_name in self.resource_tasks:
                self.progress.remove_task(self.resource_tasks[resource_name])
                del self.resource_tasks[resource_name]

    def stop(self):
        if self.progress:
            self.progress.stop()
            self.progress = None
            self.main_task_id = None
            self.resource_tasks.clear()

class ConnectionManager:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token
        self.sessions = {}
        self.lock = threading.Lock()
        self.error_count = 0
        self.success_count = 0
        self.adaptive_workers = settings.get("max_workers")

    def get_session(self, resource_name: str):
        with self.lock:
            if resource_name not in self.sessions:
                session = requests.Session()
                session.verify = False
                session.headers.update({"X-CitizenFX-Token": self.token, "User-Agent": "CitizenFX/1", "Accept": "*/*", "Accept-Encoding": "gzip, deflate", "Connection": "keep-alive", "Cache-Control": "no-cache", "Pragma": "no-cache"})
                # Increased pool_maxsize to handle up to 500 concurrent workers
                pool_size = max(settings.get("max_workers") * 2, 1000)
                adapter = requests.adapters.HTTPAdapter(pool_connections=pool_size, pool_maxsize=pool_size, max_retries=3, pool_block=False)
                session.mount('http://', adapter)
                session.mount('https://', adapter)
                self.sessions[resource_name] = session
            return self.sessions[resource_name]

    def adaptive_adjust(self, success: bool):
        with self.lock:
            if success:
                self.success_count += 1
                self.error_count = max(0, self.error_count - 1)
                if self.success_count >= 10 and self.adaptive_workers < settings.get("max_workers"):
                    self.adaptive_workers = min(self.adaptive_workers + 2, settings.get("max_workers"))
                    self.success_count = 0
                    Logger.info(f"Adaptive speed: Increased workers to {self.adaptive_workers}")
            else:
                self.error_count += 1
                self.success_count = max(0, self.success_count - 1)
                if self.error_count >= 5 and self.adaptive_workers > 3:
                    self.adaptive_workers = max(3, self.adaptive_workers - 2)
                    self.error_count = 0
                    Logger.warning(f"Adaptive speed: Reduced workers to {self.adaptive_workers} due to errors")

    def close_all(self):
        with self.lock:
            for session in self.sessions.values():
                session.close()
            self.sessions.clear()

class FiveMDumper:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token
        self.connection_manager = ConnectionManager(base_url, token)
        self.max_workers = settings.get("max_workers")
        self.use_multi_threading = settings.get("multi_threading")
        self.retry_count = settings.get("retry_count")
        self.download_timeout = settings.get("download_timeout")
        self.connection_timeout = settings.get("connection_timeout")
        self.batch_size = settings.get("batch_size")
        self.adaptive_speed = settings.get("adaptive_speed")
        self.progress_tracker = ProgressTracker()

    def xor_bytes(self, data: bytes) -> bytes:
        key = bytes([0x69] * 16)
        return bytes(b ^ key[i % 16] for i, b in enumerate(data[:32]))

    def get_configuration(self):
        url = f"{self.base_url}/client"
        data = {"method": "getConfiguration"}
        try:
            session = self.connection_manager.get_session("config")
            resp = session.post(url, data=data, timeout=self.connection_timeout)
            resp.raise_for_status()
            js = resp.json()
            os.makedirs("Resources", exist_ok=True)
            grants_path = "Resources/Grants.txt"
            with open(grants_path, "w", encoding="utf-8") as f:
                f.write(js.get("grants_token", ""))
            Logger.success(f"Saved grants token to {grants_path}")
            total_size_estimate = 0
            total_files = 0
            for res in js.get("resources", []):
                file_count = len(res.get("files", {}))
                stream_count = len(res.get("streamFiles", {}))
                total_files += file_count + stream_count
                total_size_estimate += (file_count + stream_count) * 500 * 1024
            Logger.info(f"Total resources: {len(js.get('resources', []))}")
            Logger.info(f"Total files: {total_files}")
            Logger.info(f"Estimated download size: {format_size(total_size_estimate)}")
            return js.get("resources", []), total_size_estimate
        except Exception as e:
            Logger.error(f"Failed to get configuration: {e}")
            raise

    def download_with_retry(self, url: str, key: bytes, iv: bytes, out_path: str, resource_name: str, filename: str, retries: int = None):
        if retries is None:
            retries = self.retry_count
        last_error = None
        session = self.connection_manager.get_session(resource_name)
        for attempt in range(retries + 1):
            try:
                if attempt > 0:
                    delay = min(2 ** attempt, 15)
                    time.sleep(delay)
                resp = session.get(url, timeout=self.download_timeout, stream=True)
                resp.raise_for_status()
                content_chunks = []
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        content_chunks.append(chunk)
                content = b"".join(content_chunks)
                decrypted = None
                decryption_errors = []
                try:
                    cipher = ChaCha20.new(key=key, nonce=iv)
                    decrypted = cipher.decrypt(content)
                except Exception as e1:
                    decryption_errors.append(f"Standard: {e1}")
                    try:
                        cipher = ChaCha20.new(key=key, nonce=iv[:8])
                        decrypted = cipher.decrypt(content)
                    except Exception as e2:
                        decryption_errors.append(f"8-byte nonce: {e2}")
                        try:
                            alt_key = hashlib.sha256(key).digest()[:32]
                            cipher = ChaCha20.new(key=alt_key, nonce=iv)
                            decrypted = cipher.decrypt(content)
                        except Exception as e3:
                            decryption_errors.append(f"Alt key: {e3}")
                            raise RuntimeError(f"All decryption methods failed: {decryption_errors}")
                if out_path.lower().endswith(".rpf") and not decrypted.startswith(b"RPF"):
                    if attempt < retries:
                        continue
                    raise ValueError(f"Invalid RPF header after {retries} attempts")
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "wb") as f:
                    f.write(decrypted)
                file_size = len(decrypted)
                if self.adaptive_speed:
                    self.connection_manager.adaptive_adjust(True)
                return out_path, file_size
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, ConnectionResetError, OSError) as e:
                last_error = e
                if self.adaptive_speed:
                    self.connection_manager.adaptive_adjust(False)
                if attempt < retries:
                    continue
                if isinstance(e, ConnectionResetError):
                    Logger.warning(f"Connection reset for {filename}, server may be rate limiting")
                elif isinstance(e, requests.exceptions.Timeout):
                    Logger.warning(f"Timeout for {filename}, server may be slow")
                raise Exception(f"Failed after {retries + 1} attempts: {str(e)[:100]}")
            except Exception as e:
                last_error = e
                if attempt < retries:
                    continue
                raise
        raise Exception(f"Failed to download {filename}: {last_error}")

    def unpack_rpf(self, rpf_path: str, out_dir: str) -> bool:
        # Use relative path to Bin, which is robust if CWD is the project root
        unpacker = os.path.abspath("Bin/Unpacker.exe")
        if not os.path.exists(unpacker):
            # Fallback for packaged mode if Bin is in Resources
            resources_bin = os.path.join(os.path.dirname(sys.executable), "Bin", "Unpacker.exe")
            if os.path.exists(resources_bin):
                unpacker = resources_bin
            else:
                # Last resort: check next to the script
                tools_dir = os.path.dirname(os.path.abspath(__file__))
                root_dir = os.path.dirname(tools_dir)
                script_bin = os.path.join(root_dir, "Bin", "Unpacker.exe")
                if os.path.exists(script_bin):
                    unpacker = script_bin

        rpf_path = os.path.abspath(rpf_path)
        out_dir = os.path.abspath(out_dir)
        os.makedirs(out_dir, exist_ok=True)
        Logger.dump(f"Unpacking {os.path.basename(rpf_path)}")
        try:
            proc = subprocess.run(f'"{unpacker}" "{rpf_path}" "{out_dir}"', shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore")
            if proc.returncode == 0 or "Extraído:" in proc.stdout or "Extracted:" in proc.stdout:
                Logger.success(f"Unpacked {os.path.basename(rpf_path)}")
                return True
            else:
                Logger.warning(f"Unpacker warning for {os.path.basename(rpf_path)}")
                return False
        except Exception as e:
            Logger.error(f"Failed to unpack {os.path.basename(rpf_path)}: {e}")
            return False

    def download_batch(self, batch_files: List[Tuple], res_name: str, resource_idx: int, total_resources_count: int, current_batch: int, total_batches: int):
        successful = 0
        failed = 0
        rpf_files = []
        downloaded_size = 0
        batch_size = len(batch_files)
        current_workers = self.connection_manager.adaptive_workers if self.adaptive_speed else self.max_workers

        if self.use_multi_threading and batch_size > 1:
            completed_files = 0
            file_completion_lock = threading.Lock()

            def download_file_wrapper(url, key, iv, out_path, fname):
                nonlocal successful, failed, downloaded_size, completed_files
                try:
                    downloaded_path, file_size = self.download_with_retry(url, key, iv, out_path, res_name, fname)
                    if downloaded_path:
                        with file_completion_lock:
                            successful += 1
                            downloaded_size += file_size
                            successful_files.append(fname)
                            if fname.endswith(".rpf"):
                                rpf_files.append(downloaded_path)
                            completed_files += 1
                            progress_text = f"[{settings.get_theme('primary')}][{resource_idx+1}/{total_resources_count}] {res_name[:20]:<20} (Batch {current_batch}/{total_batches}, {completed_files}/{batch_size})[/{settings.get_theme('primary')}]"
                            self.progress_tracker.update_resource_task(res_name, 1, progress_text)
                    else:
                        with file_completion_lock:
                            failed += 1
                            failed_files.append(fname)
                            completed_files += 1
                except Exception as e:
                    with file_completion_lock:
                        failed += 1
                        failed_files.append(fname)
                        completed_files += 1
                        error_msg = str(e)[:80]
                        if "ConnectionResetError" in error_msg or "10054" in error_msg:
                            Logger.warning(f"Connection reset downloading {fname}")
                        else:
                            Logger.warning(f"Error downloading {fname}: {error_msg}")

            with ThreadPoolExecutor(max_workers=current_workers) as executor:
                futures = []
                for url, key, iv, out_path, fname in batch_files:
                    future = executor.submit(download_file_wrapper, url, key, iv, out_path, fname)
                    futures.append(future)
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        Logger.error(f"Unexpected error in download thread: {e}")
        else:
            for i, (url, key, iv, out_path, fname) in enumerate(batch_files):
                try:
                    downloaded_path, file_size = self.download_with_retry(url, key, iv, out_path, res_name, fname)
                    if downloaded_path:
                        successful += 1
                        downloaded_size += file_size
                        successful_files.append(fname)
                        if fname.endswith(".rpf"):
                            rpf_files.append(downloaded_path)
                    else:
                        failed += 1
                        failed_files.append(fname)
                    progress_text = f"[{settings.get_theme('primary')}][{resource_idx+1}/{total_resources_count}] {res_name[:15]:<15} (Batch {current_batch}/{total_batches}, {i+1}/{batch_size})[/{settings.get_theme('primary')}]"
                    self.progress_tracker.update_resource_task(res_name, 1, progress_text)
                except Exception as e:
                    failed += 1
                    failed_files.append(fname)
                    progress_text = f"[{settings.get_theme('primary')}][{resource_idx+1}/{total_resources_count}] {res_name[:15]:<15} (Batch {current_batch}/{total_batches}, {i+1}/{batch_size})[/{settings.get_theme('primary')}]"
                    self.progress_tracker.update_resource_task(res_name, 1, progress_text)
                    error_msg = str(e)[:80]
                    if "ConnectionResetError" in error_msg or "10054" in error_msg:
                        Logger.warning(f"Connection reset downloading {fname}")
                    else:
                        Logger.warning(f"Error downloading {fname}: {error_msg}")
        return successful, failed, rpf_files, downloaded_size

    def download_resource_files(self, files_to_download: List[Tuple], res_name: str, resource_idx: int, total_resources_count: int):
        successful = 0
        failed = 0
        rpf_files = []
        downloaded_size = 0
        total_files_in_resource = len(files_to_download)
        self.progress_tracker.add_resource_task(res_name, total_files_in_resource, resource_idx, total_resources_count)
        batch_size = self.batch_size
        batches = []
        for i in range(0, len(files_to_download), batch_size):
            batches.append(files_to_download[i:i + batch_size])
        total_batches = len(batches)
        for batch_num, batch in enumerate(batches, 1):
            batch_successful, batch_failed, batch_rpf_files, batch_downloaded = self.download_batch(batch, res_name, resource_idx, total_resources_count, batch_num, total_batches)
            successful += batch_successful
            failed += batch_failed
            rpf_files.extend(batch_rpf_files)
            downloaded_size += batch_downloaded
            if batch_num < total_batches:
                time.sleep(0.1)
        self.progress_tracker.remove_resource_task(res_name)
        self.progress_tracker.update_main_progress(1, f"[bold {settings.get_theme('primary')}]Dumping... [{resource_idx+1}/{total_resources_count}][/bold {settings.get_theme('primary')}]")
        return successful, failed, rpf_files, downloaded_size

    def fetch_resource(self, res: Dict, resource_idx: int, total_resources_count: int):
        global current_resource_index, total_downloaded_size
        current_resource_index = resource_idx + 1
        uri = base64.b64decode(res["uri"].split("#")[1])
        xored_key = uri[19:]
        iv = uri[53:61]
        hmac_key = self.xor_bytes(xored_key)[:32]
        res_name = safe_name(res["name"])
        Logger.info(f"Processing resource [{resource_idx+1}/{total_resources_count}]: {res_name}")
        temp_dir = os.path.join("Temp", res_name)
        unpacked_dir = os.path.join("Unpacked", res_name)
        files_to_download = []
        for fname, hsh in (res.get("files") or {}).items():
            url = f"{res.get('fileServer') or self.base_url + '/files'}/{res['name']}/{quote(fname)}?hash={hsh}"
            rpf_key = hmac.new(hmac_key, fname.encode(), hashlib.sha256).digest()
            out_path = os.path.join(temp_dir if fname.endswith(".rpf") else unpacked_dir, fname)
            files_to_download.append((url, rpf_key, iv, out_path, fname))
        for fname, body in (res.get("streamFiles") or {}).items():
            url = f"{res.get('fileServer') or self.base_url + '/files'}/{res['name']}/{quote(fname)}?hash={body['hash']}"
            s_key = hmac.new(hmac_key, fname.encode(), hashlib.sha256).digest()
            out_path = os.path.join(unpacked_dir, "stream", fname)
            files_to_download.append((url, s_key, iv, out_path, fname))
        successful, failed, rpf_files, downloaded_size = self.download_resource_files(files_to_download, res_name, resource_idx, total_resources_count)
        total_downloaded_size += downloaded_size
        unpacked_count = 0
        for rpf_path in rpf_files:
            if self.unpack_rpf(rpf_path, unpacked_dir):
                unpacked_count += 1
        Logger.success(f"Resource {res_name}: {successful}/{len(files_to_download)} files downloaded, {unpacked_count} RPF files unpacked")
        if failed > 0:
            Logger.warning(f"Failed to download {failed} files for {res_name}")
        return successful, failed

    def run(self, selected_indices=None):
        global total_resources, log_counter
        log_counter = 1
        resources, estimated_size = self.get_configuration()
        total_resources = len(resources)
        categorized = ResourceManager.display_resources_by_category(resources)
        if selected_indices is None:
            console.print(f"\n[bold {settings.get_theme('accent')}]Selection Options:[/bold {settings.get_theme('accent')}]")
            console.print(f"[{settings.get_theme('primary')}]Enter specific indices (e.g., 1,5,7)[/{settings.get_theme('primary')}]")
            console.print(f"[{settings.get_theme('primary')}]Enter 'all' for all resources[/{settings.get_theme('primary')}]")
            console.print(f"[{settings.get_theme('primary')}]Enter category (e.g., 'clothes', 'vehicles', 'maps', 'scripts', 'other')[/{settings.get_theme('primary')}]")
            console.print()
            choice = Prompt.ask(f"[bold {settings.get_theme('success')}]Enter selection[/bold {settings.get_theme('success')}]").strip()
            if choice.lower() == 'all':
                selected_indices = list(range(len(resources)))
            elif choice.lower() in ['clothes', 'vehicles', 'maps', 'scripts', 'other']:
                category = choice.lower().capitalize()
                if category in categorized:
                    selected_indices = [idx for idx, _ in categorized[category]]
                else:
                    Logger.warning(f"No resources found in category: {category}")
                    return
            else:
                try:
                    selected_indices = [int(x.strip()) for x in choice.split(",") if x.strip().isdigit()]
                except:
                    Logger.error("Invalid input format")
                    return
        selected_indices = sorted(set(selected_indices))
        selected_indices = [idx for idx in selected_indices if 0 <= idx < len(resources)]
        if not selected_indices:
            Logger.error("No valid resources selected")
            return
        console.print(f"\n[bold {settings.get_theme('accent')}]Selected {len(selected_indices)} resources:[/bold {settings.get_theme('accent')}]")
        selection_display = []
        for idx in selected_indices:
            selection_display.append(f"  [{idx:03d}] {resources[idx]['name']}")
        col_width = 40
        num_cols = 3
        for i in range(0, len(selection_display), num_cols):
            row = selection_display[i:i+num_cols]
            padded_row = [col.ljust(col_width) for col in row]
            console.print("".join(padded_row))
        console.print()
        if not Confirm.ask(f"\n[bold {settings.get_theme('error')}]Proceed with dump?[/bold {settings.get_theme('error')}]"):
            Logger.info("Dump cancelled")
            return
        console.print("\n" + "="*80)
        console.print(f"[{settings.get_theme('category')}]Starting Dump Process[/{settings.get_theme('category')}]")
        console.print("="*80)
        console.print()
        total_successful = 0
        total_failed = 0
        total_files = sum(len(resources[idx].get("files", {})) + len(resources[idx].get("streamFiles", {})) for idx in selected_indices)
        global failed_files, successful_files, total_downloaded_size
        failed_files = []
        successful_files = []
        total_downloaded_size = 0
        start_time = time.time()
        self.progress_tracker.start_main_progress(len(selected_indices))
        try:
            for i, idx in enumerate(selected_indices):
                res = resources[idx]
                successful, failed = self.fetch_resource(res, i, len(selected_indices))
                total_successful += successful
                total_failed += failed
        finally:
            self.progress_tracker.stop()
            self.connection_manager.close_all()
        end_time = time.time()
        elapsed_time = end_time - start_time
        console.print("\n" + "="*80)
        console.print(f"[{settings.get_theme('category')}]Dump Complete[/{settings.get_theme('category')}]")
        console.print("="*80)
        summary_table = Table(box=box.ROUNDED, style=settings.get_theme("accent"), border_style=settings.get_theme("border"))
        summary_table.add_column("Metric", style=f"bold {settings.get_theme('primary')}", width=25)
        summary_table.add_column("Value", style=settings.get_theme("accent"), width=20, justify="right")
        summary_table.add_row("Total Successful Files", f"[{settings.get_theme('success')}]{total_successful:,}[/{settings.get_theme('success')}]")
        if total_failed > 0:
            summary_table.add_row("Total Failed Files", f"[{settings.get_theme('error')}]{total_failed:,}[/{settings.get_theme('error')}]")
        else:
            summary_table.add_row("Total Failed Files", f"[{settings.get_theme('success')}]{total_failed:,}[/{settings.get_theme('success')}]")
        summary_table.add_row("Total Downloaded Size", f"[{settings.get_theme('warning')}]{format_size(total_downloaded_size)}[/{settings.get_theme('warning')}]")
        summary_table.add_row("Elapsed Time", f"[{settings.get_theme('size_estimate')}]{elapsed_time:.1f} seconds[/{settings.get_theme('size_estimate')}]")
        if elapsed_time > 0:
            avg_speed = total_downloaded_size / elapsed_time
            summary_table.add_row("Average Speed", f"[{settings.get_theme('success')}]{format_size(avg_speed)}/s[/{settings.get_theme('success')}]")
        console.print(summary_table)
        console.print()
        if failed_files:
            console.print(f"[bold {settings.get_theme('warning')}]Failed files ({len(failed_files)}):[/bold {settings.get_theme('warning')}]")
            failed_table = Table(box=box.SIMPLE, show_header=False, style=f"dim {settings.get_theme('secondary')}")
            failed_table.add_column("", style=settings.get_theme("error"), width=4)
            failed_table.add_column("Filename", style=settings.get_theme("primary"))
            for i, fname in enumerate(failed_files[:10]):
                failed_table.add_row(f"X", fname)
            if len(failed_files) > 10:
                failed_table.add_row("...", f"[{settings.get_theme('secondary')}]and {len(failed_files) - 10} more[/{settings.get_theme('secondary')}]")
            console.print(failed_table)
            console.print()
        self.save_dump_log(selected_indices, resources, total_successful, total_failed, elapsed_time)
        return total_successful, total_failed

    def save_dump_log(self, indices, resources, successful, failed, elapsed_time):
        if not settings.get("enable_logging"):
            return
        log_dir = "Logs"
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"dump_{timestamp}.log")
        with open(log_file, "w", encoding="utf-8") as f:
            for entry in dump_log:
                f.write(f"{entry}\n")
        Logger.info(f"Dump log saved to: {log_file}")

class FiveMDecryptor:
    def __init__(self):
        self.DefaultKey = bytes([0xB3, 0xCB, 0x2E, 0x04, 0x87, 0x94, 0xD6, 0x73, 0x08, 0x23, 0xC4, 0x93, 0x7A, 0xBD, 0x18, 0xAD, 0x6B, 0xE6, 0xDC, 0xB3, 0x91, 0x43, 0x0D, 0x28, 0xF9, 0x40, 0x9D, 0x48, 0x37, 0xB9, 0x38, 0xFB])
        self.HeaderToVerify = b"FXAP"
        self.AesKey = bytes([0x7A, 0xBA, 0x8D, 0x53, 0x25, 0x5B, 0x0E, 0xFD, 0x16, 0xBD, 0x35, 0x22, 0xA0, 0xB9, 0x26, 0xA5, 0x61, 0x83, 0x2E, 0xEC, 0xA2, 0x4B, 0xFD, 0x56, 0x9E, 0xC0, 0x1D, 0x8F, 0x38, 0x40, 0x54, 0x6D])
        self.LuaHeaderHex = "1b4c7561540019930d0a1a0a040808785"
        self.OutputDir = "Output"
        self.TempDir = "TempCompiled"
        self.use_multi_threading = settings.get("multi_threading")
        self.max_workers = settings.get("max_workers")
        self._progress_active = False

    def file_to_bytes(self, fp: str) -> bytes:
        with open(fp, "rb") as f:
            return f.read()

    def scan_for_id(self, buf: bytes) -> int:
        return int(buf[74:78].hex(), 16)

    def verify_encrypted(self, path: str) -> bool:
        buf = self.file_to_bytes(path)
        return buf[:4] == self.HeaderToVerify

    def decrypt_file(self, path: str, key: bytes) -> Optional[bytes]:
        buf = self.file_to_bytes(path)
        if buf[:4] != self.HeaderToVerify:
            return None
        iv = buf[74:86]
        enc = buf[86:]
        return self._chacha_decrypt(enc, key, iv)

    def decrypt_buffer(self, hexdata: bytes, key: bytes, bufferPtr=None, ivPtr=None) -> Optional[bytes]:
        if not hexdata:
            return None
        if bufferPtr is not None and ivPtr is not None:
            iv = hexdata[ivPtr:ivPtr + 12]
            enc = hexdata[bufferPtr:]
            return self._chacha_decrypt(enc, key, iv)
        possible_iv_positions = [80, 74, 86, 92]
        for iv_pos in possible_iv_positions:
            if iv_pos + 12 <= len(hexdata):
                iv = hexdata[iv_pos:iv_pos + 12]
                enc = hexdata[iv_pos + 12:]
                try:
                    return self._chacha_decrypt(enc, key, iv)
                except:
                    continue
        if len(hexdata) > 92:
            iv = hexdata[80:92]
            enc = hexdata[92:]
            return self._chacha_decrypt(enc, key, iv)
        return None

    def _chacha_decrypt(self, enc: bytes, key: bytes, iv: bytes) -> bytes:
        if len(iv) == 16:
            iv = iv[:12]
        elif len(iv) == 8:
            pass
        elif len(iv) != 12:
            if len(iv) > 12:
                iv = iv[:12]
            elif len(iv) < 8:
                iv = iv + b'\x00' * (8 - len(iv))
        try:
            cipher = ChaCha20.new(key=key, nonce=iv)
            return cipher.decrypt(enc)
        except ValueError as e:
            for iv_len in [8, 12, 16]:
                if iv_len <= len(iv):
                    try:
                        cipher = ChaCha20.new(key=key, nonce=iv[:iv_len])
                        return cipher.decrypt(enc)
                    except:
                        continue
            raise RuntimeError(f"ChaCha20 decrypt failed: {e}")

    def calculate_client_key(self, grants_clk: bytes) -> bytes:
        if not grants_clk or len(grants_clk) < 32:
            return grants_clk
        try:
            iv = grants_clk[:16]
            enc = grants_clk[16:]
            if len(enc) % 16 != 0:
                padding_len = 16 - (len(enc) % 16)
                enc = enc + b'\x00' * padding_len
            cipher = AES.new(self.AesKey, AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(enc)
            try:
                return unpad(decrypted, AES.block_size)
            except ValueError:
                return decrypted
        except Exception as e:
            Logger.warning(f"AES decryption failed: {e}")
            return grants_clk

    def find_decryption_offsets(self, encrypted_blob: bytes, key: bytes) -> tuple[Optional[int], Optional[int]]:
        max_search = min(len(encrypted_blob), 256)
        for data_start in range(12, max_search):
            iv = encrypted_blob[data_start-12:data_start]
            data = encrypted_blob[data_start:]
            try:
                decrypted = self._chacha_decrypt(data, key, iv)
                if len(decrypted) >= 4 and decrypted[:4].hex() == '1b4c7561':
                    return data_start - 12, data_start
            except Exception:
                continue
        return None, None

    def process_lua_file(self, decrypted_buffer: bytes, output_path: str, resourceName: str, file_rel: str):
        tmp_path = os.path.join(self.TempDir, resourceName, file_rel + 'c')
        os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
        with open(tmp_path, "wb") as f:
            f.write(decrypted_buffer)

        final_path = output_path
        os.makedirs(os.path.dirname(final_path), exist_ok=True)

        decompiler_path = os.path.join("Tools", "Decompile", "unluac54.jar")
        if not os.path.exists(decompiler_path):
            Logger.error(f"Decompiler not found at {decompiler_path}")
            raw_path = final_path.replace('.lua', '.raw.luac')
            with open(raw_path, "wb") as f:
                f.write(decrypted_buffer)
            return

        try:
            cmd = f'java -jar "{decompiler_path}" "{tmp_path}"'
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if proc.returncode != 0:
                raw_path = final_path.replace('.lua', '.raw.luac')
                with open(raw_path, "wb") as f:
                    f.write(decrypted_buffer)
                err_path = os.path.join(os.path.dirname(final_path), f"error_{os.path.splitext(os.path.basename(final_path))[0]}_unluac.txt")
                with open(err_path, "w", encoding="utf-8", errors="ignore") as ef:
                    ef.write(proc.stderr or proc.stdout or "Unknown error")
                Logger.warning(f"unluac failed for {file_rel}, saved raw and error log")
            else:
                with open(final_path, "w", encoding="utf-8", errors="ignore") as out:
                    out.write(proc.stdout)
                Logger.dump(f"Decompiled {file_rel}")
        except Exception as e:
            raw_path = final_path.replace('.lua', '.raw.luac')
            with open(raw_path, "wb") as f:
                f.write(decrypted_buffer)
            Logger.error(f"Decompiler error for {final_path}: {e}")

    def get_all_files(self, dirpath: str) -> List[str]:
        results = []
        for root, _, files in os.walk(dirpath):
            for f in files:
                results.append(os.path.join(root, f))
        return results

    def decrypt_resource_file(self, resourcePath: str, relativeFile: str, decryptKey: Optional[bytes], resourceName: str, grants_clk: bytes) -> bool:
        """
        Returns True if a fallback occurred (original encrypted file saved), False otherwise.
        """
        full_path = os.path.join(resourcePath, relativeFile)
        output_path = os.path.join(self.OutputDir, resourceName, relativeFile)
        if not os.path.exists(full_path):
            return False
        if not self.verify_encrypted(full_path):
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            try:
                with open(full_path, "rb") as inf, open(output_path, "wb") as outf:
                    outf.write(inf.read())
            except Exception as e:
                Logger.error(f"Failed to copy {relativeFile}: {e}")
            return False

        decrypted_file = self.decrypt_file(full_path, self.DefaultKey)
        if not decrypted_file:
            Logger.warning(f"Failed to decrypt {relativeFile} with DefaultKey")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            try:
                with open(full_path, "rb") as inf, open(output_path, "wb") as outf:
                    outf.write(inf.read())
            except Exception as e:
                Logger.error(f"Failed to copy {relativeFile}: {e}")
            return False

        if relativeFile.lower().endswith('.lua'):
            decrypted_buffer = None

            if decryptKey is not None:
                offsets = self.find_decryption_offsets(decrypted_file, decryptKey)
                if offsets:
                    try:
                        buf = self.decrypt_buffer(decrypted_file, decryptKey, bufferPtr=offsets[1], ivPtr=offsets[0])
                        if buf and len(buf) >= 4 and buf[:4].hex() == self.LuaHeaderHex:
                            decrypted_buffer = buf
                    except Exception:
                        pass
                if decrypted_buffer is None:
                    try:
                        buf = self.decrypt_buffer(decrypted_file, decryptKey)
                        if buf and len(buf) >= 4 and buf[:4].hex() == self.LuaHeaderHex:
                            decrypted_buffer = buf
                    except Exception:
                        pass

            if decrypted_buffer is None and grants_clk:
                alt_key = self.calculate_client_key(grants_clk)
                offsets = self.find_decryption_offsets(decrypted_file, alt_key)
                if offsets:
                    try:
                        buf = self.decrypt_buffer(decrypted_file, alt_key, bufferPtr=offsets[1], ivPtr=offsets[0])
                        if buf and len(buf) >= 4 and buf[:4].hex() == self.LuaHeaderHex:
                            decrypted_buffer = buf
                    except Exception:
                        pass
                if decrypted_buffer is None:
                    try:
                        buf = self.decrypt_buffer(decrypted_file, alt_key)
                        if buf and len(buf) >= 4 and buf[:4].hex() == self.LuaHeaderHex:
                            decrypted_buffer = buf
                    except Exception:
                        pass

            if decrypted_buffer:
                self.process_lua_file(decrypted_buffer, output_path, resourceName, relativeFile)
                return False
            else:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as f:
                    with open(full_path, "rb") as orig:
                        f.write(orig.read())
                Logger.success(f"Saved original encrypted file for {relativeFile}")

                resource_readme = os.path.join(self.OutputDir, resourceName, "README.txt")
                if not os.path.exists(resource_readme):
                    with open(resource_readme, "w", encoding="utf-8") as rf:
                        rf.write("""\
Some Lua files in this resource could not be decrypted locally because they use the new double encryption method.

To decrypt these files, please use our Discord bot. As a client, you are entitled to unlimited credits, so you can run the decryption there without worry.

After obtaining the decrypted Lua code, you may want to clean and deobfuscate it. We recommend using DeepSeek AI or Claude AI with the following prompt:

Clean and deobfuscate this Lua code 
Keep full functionality. Remove obfuscation. Improve naming. Keep syntax valid.

Rules:
Keep all functionality intact,
Use clear, descriptive variable names,
Remove obfuscation techniques,
Maintain proper Lua syntax,
Remove unnecessary whitespace and formatting issues,
Keep comments that add value,
Ensure the chunk can be properly merged with other chunks,

Return only the cleaned Lua code:

Simply paste the decrypted Lua code after the prompt.
""")
                return True
        else:
            # Non‑Lua files: try with decryptKey first, then fallback to grants_clk
            # This includes map files (.ytyp, .ymap, etc.) – they are handled by the same generic decryption.
            if decryptKey is not None:
                decrypted_buffer = self.decrypt_buffer(decrypted_file, decryptKey)
                if decrypted_buffer:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, "wb") as out:
                        out.write(decrypted_buffer)
                    return False

            if grants_clk:
                alt_key = self.calculate_client_key(grants_clk)
                decrypted_buffer = self.decrypt_buffer(decrypted_file, alt_key)
                if decrypted_buffer:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, "wb") as out:
                        out.write(decrypted_buffer)
                    return False

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as out:
                out.write(decrypted_file)
            Logger.dump(f"Saved {relativeFile} as-is (no valid decryption key)")
            return False

    def decrypt_resource(self, resourcePath: str, resourceName: str, grants_token: Optional[str] = None):
        Logger.info(f"Decrypting resource: {resourceName}")
        fxap_file = os.path.join(resourcePath, ".fxap")
        if not os.path.exists(fxap_file):
            for file_full in self.get_all_files(resourcePath):
                relative = os.path.relpath(file_full, resourcePath).replace("\\", "/")
                output_path = os.path.join(self.OutputDir, resourceName, relative)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                try:
                    with open(file_full, "rb") as inf, open(output_path, "wb") as outf:
                        outf.write(inf.read())
                except Exception as e:
                    Logger.error(f"Failed to copy {relative}: {e}")
            Logger.success(f"Copied unencrypted resource: {resourceName}")
            return
        fxap_buffer = self.decrypt_file(fxap_file, self.DefaultKey)
        if not fxap_buffer:
            Logger.error(f"Failed to decrypt .fxap for {resourceName}")
            for file_full in self.get_all_files(resourcePath):
                if file_full.endswith(".fxap"):
                    continue
                relative = os.path.relpath(file_full, resourcePath).replace("\\", "/")
                output_path = os.path.join(self.OutputDir, resourceName, relative)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                try:
                    with open(file_full, "rb") as inf, open(output_path, "wb") as outf:
                        outf.write(inf.read())
                except Exception as e:
                    Logger.error(f"Failed to copy {relative}: {e}")
            return
        resource_id = self.scan_for_id(fxap_buffer)
        decrypt_key = None
        grants_clk = b""
        if grants_token is None:
            grants_path = os.path.join("Resources", "Grants.txt")
            if os.path.exists(grants_path):
                with open(grants_path, "r", encoding="utf-8") as f:
                    grants_token = f.read().strip()
            else:
                Logger.warning(f"No Grants.txt found for {resourceName}, will use DefaultKey only")
                grants_token = ""
        if grants_token:
            try:
                payload_part = grants_token.split(".")[1]
                payload_part += "=" * (-len(payload_part) % 4)
                payload = json.loads(base64.b64decode(payload_part).decode("utf-8"))
                if str(resource_id) in payload.get("grants", {}):
                    decrypt_key = bytes.fromhex(payload["grants"][str(resource_id)])
                    grants_clk_hex = payload["grants_clk"].get(str(resource_id))
                    if grants_clk_hex:
                        grants_clk = bytes.fromhex(grants_clk_hex)
                    Logger.info(f"Found grant for {resourceName} (ID: {resource_id})")
                else:
                    Logger.warning(f"No grant found for {resourceName} (ID {resource_id}) — using DefaultKey only")
            except Exception as e:
                Logger.error(f"Failed to parse grants token for {resourceName}: {e}")
                decrypt_key = None
                grants_clk = b""
        else:
            Logger.warning(f"No grants token available for {resourceName} — using DefaultKey only")
        Logger.info(f"Decrypting: {resourceName} (ID: {resource_id})")
        files = self.get_all_files(resourcePath)
        total_files = len(files) - 1
        if total_files <= 0:
            Logger.warning(f"No files found in {resourceName}")
            return

        had_fallback = False  # Track if any file required fallback

        if self.use_multi_threading and total_files > 5 and not self._progress_active:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for file_full in files:
                    if file_full.endswith(".fxap"):
                        continue
                    relative = os.path.relpath(file_full, resourcePath).replace("\\", "/")
                    futures.append(executor.submit(self.decrypt_resource_file, resourcePath, relative, decrypt_key, resourceName, grants_clk))
                with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(bar_width=40), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"), TimeRemainingColumn(), console=console, transient=True) as progress:
                    task = progress.add_task(f"[{settings.get_theme('accent')}]Decrypting {resourceName}...[/{settings.get_theme('accent')}]", total=total_files)
                    for future in as_completed(futures):
                        fallback = future.result()
                        if fallback:
                            had_fallback = True
                        progress.update(task, advance=1)
        else:
            decrypted_count = 0
            console.print(f"[{settings.get_theme('secondary')}]  Processing {total_files} files for {resourceName}...[/{settings.get_theme('secondary')}]")
            for idx, file_full in enumerate(files):
                if file_full.endswith(".fxap"):
                    continue
                relative = os.path.relpath(file_full, resourcePath).replace("\\", "/")
                try:
                    fallback = self.decrypt_resource_file(resourcePath, relative, decrypt_key, resourceName, grants_clk)
                    if fallback:
                        had_fallback = True
                    decrypted_count += 1
                    if idx % 10 == 0:
                        console.print(f"[{settings.get_theme('secondary')}]    Progress: {idx}/{total_files} files[/{settings.get_theme('secondary')}]", end="\r")
                except Exception as e:
                    Logger.error(f"Error decrypting {relative}: {e}")
            console.print(f"[{settings.get_theme('secondary')}]    Progress: {total_files}/{total_files} files[/{settings.get_theme('secondary')}]")

        # Only copy the original .fxap if at least one file required fallback
        if had_fallback:
            fxap_output = os.path.join(self.OutputDir, resourceName, ".fxap")
            os.makedirs(os.path.dirname(fxap_output), exist_ok=True)
            shutil.copy2(fxap_file, fxap_output)
            Logger.dump(f"Copied .fxap to {fxap_output} (needed for fallback files)")
        else:
            Logger.dump(f"No fallback files in {resourceName}, .fxap not copied")

        Logger.success(f"Processed resource: {resourceName}")

    def decrypt_all_resources(self):
        Logger.info("Starting resource decryption...")
        resource_dirs = []
        resources_root = "Unpacked"
        if not os.path.isdir(resources_root):
            Logger.error("No Unpacked/ directory found - run the dumper first")
            return
        for entry in os.listdir(resources_root):
            full = os.path.join(resources_root, entry)
            if os.path.isdir(full):
                resource_dirs.append(full)
        total_resources = len(resource_dirs)
        if total_resources == 0:
            Logger.error("No resources found in Unpacked directory")
            return
        Logger.info(f"Found {total_resources} resources to decrypt")
        self._progress_active = True
        try:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(bar_width=40), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"), TextColumn("•"), TextColumn(f"[{settings.get_theme('accent')}]{{task.completed}}/{{task.total}} resources[/{settings.get_theme('accent')}]"), TextColumn("•"), TimeRemainingColumn(), TimeElapsedColumn(), console=console, transient=False) as progress:
                task = progress.add_task(f"[bold {settings.get_theme('accent')}]Decrypting all resources...[/bold {settings.get_theme('accent')}]", total=total_resources)
                for idx, resource_dir in enumerate(resource_dirs):
                    resource_name = os.path.basename(resource_dir)
                    self.decrypt_resource(resource_dir, resource_name)
                    progress.update(task, advance=1)
        finally:
            self._progress_active = False
        Logger.success(f"Decryption completed! All files saved to {self.OutputDir}/")
        if os.path.exists(self.OutputDir):
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(self.OutputDir):
                for filename in filenames:
                    try:
                        total_size += os.path.getsize(os.path.join(dirpath, filename))
                    except:
                        pass
            Logger.info(f"Total decrypted size: {format_size(total_size)}")

def display_main_menu():
    theme = settings.get_all_settings().get("theme", DEFAULT_SETTINGS["theme"])
    primary = theme['primary']
    secondary = theme['secondary']
    border = theme['border']
    highlight = theme['highlight']

    menu_options = [
        {"id": "dump_cfx", "name": t("menu_dump_cfx"), "desc": t("menu_dump_cfx_desc"), "key": "1"},
        {"id": "dump_ip", "name": t("menu_dump_ip"), "desc": t("menu_dump_ip_desc"), "key": "2"},
        {"id": "manual_token", "name": t("menu_manual_token"), "desc": t("menu_manual_token_desc"), "key": "3"},
        {"id": "dump_domain", "name": t("menu_dump_domain"), "desc": t("menu_dump_domain_desc"), "key": "4"},
        {"id": "decrypt", "name": t("menu_decrypt"), "desc": t("menu_decrypt_desc"), "key": "5"},
        {"id": "manage_cache", "name": t("menu_manage_cache"), "desc": t("menu_manage_cache_desc"), "key": "6"},
        {"id": "view_logs", "name": t("menu_view_logs"), "desc": t("menu_view_logs_desc"), "key": "7"},
        {"id": "settings", "name": t("menu_settings"), "desc": t("menu_settings_desc"), "key": "8"},
        {"id": "exit", "name": t("menu_exit"), "desc": t("menu_exit_desc"), "key": "9"}
    ]

    selected_index = 0
    needs_refresh = True

    while True:
        if needs_refresh:
            console.clear()
            for _ in range(2):
                console.print()
            console.print(Panel.fit(f"[bold {primary}]{t('main_menu_title')}[/bold {primary}]\n[{secondary}]{t('main_menu_subtitle')}[/{secondary}]", border_style=border, padding=(1, 2)))

            status_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
            status_table.add_column("", style=primary, width=15)
            status_table.add_column("", style=primary, width=20)
            if os.path.exists("Resources/Grants.txt"):
                status_table.add_row(t("status_grants_file"), f"[{primary}]{t('ready')}[/{primary}]")
            else:
                status_table.add_row(t("status_grants_file"), f"[{secondary}]{t('not_found')}[/{secondary}]")
            if os.path.exists("Output"):
                output_size = sum(os.path.getsize(os.path.join(dirpath, filename)) for dirpath, dirnames, filenames in os.walk("Output") for filename in filenames)
                status_table.add_row(t("status_output_size"), f"[{primary}]{format_size(output_size)}[/{primary}]")
            threading_status = t("enabled") if settings.get('multi_threading') else t("disabled")
            status_color = primary if settings.get('multi_threading') else secondary
            status_table.add_row(t("status_multi_threading"), f"[{status_color}]{threading_status}[/{status_color}]")
            console.print(Panel(status_table, title=f"[bold {primary}]STATUS[/bold {primary}]", border_style=border))
            console.print()

            menu_table = Table(box=box.SIMPLE, show_header=True, header_style=f"bold {primary}", border_style=border, padding=(0, 1), title=f"[bold {primary}]MAIN MENU[/bold {primary}]", title_style=f"bold {primary}")
            menu_table.add_column("", style=primary, width=3)
            menu_table.add_column("Key", style=primary, width=4)
            menu_table.add_column("Option", style=primary, width=25)
            menu_table.add_column("Description", style=secondary, width=40)

            for i, option in enumerate(menu_options):
                if i == selected_index:
                    option_name = f"[{highlight}] {option['name']} [/{highlight}]"
                    description = f"[{highlight}] {option['desc']} [/{highlight}]"
                    key_display = f"[{highlight}] {option['key']} [/{highlight}]"
                else:
                    option_name = f" {option['name']}"
                    description = f" {option['desc']}"
                    key_display = f" {option['key']}"
                menu_table.add_row("▶" if i == selected_index else " ", key_display, option_name, description)
            console.print(menu_table)
            console.print()

            footer_text = Text()
            footer_text.append(" • ", style=secondary)
            footer_text.append("↑↓", style=f"bold {primary}")
            footer_text.append(" Navigate  • ", style=secondary)
            footer_text.append("Enter", style=f"bold {primary}")
            footer_text.append(" Select  • ", style=secondary)
            footer_text.append("1-9", style=f"bold {primary}")
            footer_text.append(" Quick Select  • ", style=secondary)
            footer_text.append("ESC", style=f"bold {primary}")
            footer_text.append(" Exit", style=secondary)

            console.print(Panel(footer_text, border_style=border, padding=(0, 1)))

            needs_refresh = False

        if msvcrt.kbhit():
            key = msvcrt.getch()

            if key == b'\xe0':
                arrow_key = msvcrt.getch()
                if arrow_key == b'H':
                    selected_index = (selected_index - 1) % len(menu_options)
                    needs_refresh = True
                elif arrow_key == b'P':
                    selected_index = (selected_index + 1) % len(menu_options)
                    needs_refresh = True

            elif key == b'\r':
                return menu_options[selected_index]["key"]

            elif key == b'\x1b':
                return "9"

            elif key in [b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'9']:
                return key.decode()

            elif key in [b'q', b'Q']:
                return "9"

        time.sleep(0.01)

def view_logs_menu():
    theme = settings.get_all_settings().get("theme", DEFAULT_SETTINGS["theme"])
    primary = theme['primary']
    secondary = theme['secondary']
    border = theme['border']
    highlight = theme['highlight']

    log_dir = "Logs"

    if not os.path.exists(log_dir):
        console.clear()
        console.print(Panel.fit(
            f"[bold {primary}]VIEW LOGS[/bold {primary}]\n[{secondary}]No logs directory found[/{secondary}]",
            border_style=border,
            padding=(1, 2)
        ))
        console.print()
        Prompt.ask(f"[bold {primary}]{t('press_enter_continue')}[/bold {primary}]")
        return

    log_files = sorted([f for f in os.listdir(log_dir) if f.endswith('.log')], reverse=True)

    if not log_files:
        console.clear()
        console.print(Panel.fit(
            f"[bold {primary}]VIEW LOGS[/bold {primary}]\n[{secondary}]No dump logs found[/{secondary}]",
            border_style=border,
            padding=(1, 2)
        ))
        console.print()
        Prompt.ask(f"[bold {primary}]{t('press_enter_continue')}[/bold {primary}]")
        return

    menu_items = []
    for log_file in log_files[:20]:
        log_path = os.path.join(log_dir, log_file)
        size = os.path.getsize(log_path)
        stat = os.stat(log_path)
        date = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

        menu_items.append({
            "file": log_file,
            "path": log_path,
            "size": size,
            "date": date,
            "display": f"{log_file[:30]:<30} {format_size(size):>10}  {date}"
        })

    menu_items.append({"file": "back", "display": "← Back to Main Menu"})

    selected_index = 0
    needs_refresh = True

    while True:
        if needs_refresh:
            console.clear()

            console.print(Panel.fit(
                f"[bold {primary}]VIEW LOGS[/bold {primary}]\n[{secondary}]Browse and view dump logs[/{secondary}]",
                border_style=border,
                padding=(1, 2)
            ))

            stats_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
            stats_table.add_column("", style=primary, width=20)
            stats_table.add_column("", style=primary, width=30)

            stats_table.add_row("Total Logs", f"[{primary}]{len(log_files)}[/{primary}]")
            total_size = sum(os.path.getsize(os.path.join(log_dir, f)) for f in log_files)
            stats_table.add_row("Total Size", f"[{primary}]{format_size(total_size)}[/{primary}]")
            newest = datetime.fromtimestamp(os.stat(os.path.join(log_dir, log_files[0])).st_mtime) if log_files else "N/A"
            oldest = datetime.fromtimestamp(os.stat(os.path.join(log_dir, log_files[-1])).st_mtime) if log_files else "N/A"
            stats_table.add_row("Newest", f"[{primary}]{newest.strftime('%Y-%m-%d') if log_files else 'N/A'}[/{primary}]")
            stats_table.add_row("Oldest", f"[{primary}]{oldest.strftime('%Y-%m-%d') if log_files else 'N/A'}[/{primary}]")

            console.print(Panel(stats_table, title=f"[bold {primary}]LOG STATISTICS[/bold {primary}]", border_style=border))
            console.print()

            logs_table = Table(
                box=box.SIMPLE,
                show_header=True,
                header_style=f"bold {primary}",
                border_style=border,
                padding=(0, 1),
                title=f"[bold {primary}]AVAILABLE LOGS[/bold {primary}]",
                title_style=f"bold {primary}"
            )

            logs_table.add_column("", style=primary, width=3)
            logs_table.add_column("Log File", style=primary, width=32)
            logs_table.add_column("Size", style=primary, width=12)
            logs_table.add_column("Date", style=primary, width=19)

            for i, item in enumerate(menu_items):
                if i == len(menu_items) - 1:
                    if i == selected_index:
                        display = f"[{highlight}] {item['display']} [/{highlight}]"
                    else:
                        display = f" {item['display']}"
                    logs_table.add_row(
                        "▶" if i == selected_index else " ",
                        display,
                        "",
                        ""
                    )
                else:
                    if i == selected_index:
                        log_name = f"[{highlight}] {item['file'][:30]:<30} [/{highlight}]"
                        size_str = f"[{highlight}] {format_size(item['size']):>10} [/{highlight}]"
                        date_str = f"[{highlight}] {item['date']} [/{highlight}]"
                    else:
                        log_name = f" {item['file'][:30]:<30}"
                        size_str = f" {format_size(item['size']):>10}"
                        date_str = f" {item['date']}"

                    logs_table.add_row(
                        "▶" if i == selected_index else " ",
                        log_name,
                        size_str,
                        date_str
                    )

            console.print(logs_table)
            console.print()

            footer_text = Text()
            footer_text.append(" • ", style=secondary)
            footer_text.append("↑↓", style=f"bold {primary}")
            footer_text.append(" Navigate  • ", style=secondary)
            footer_text.append("Enter", style=f"bold {primary}")
            footer_text.append(" View  • ", style=secondary)
            footer_text.append("D", style=f"bold {primary}")
            footer_text.append(" Delete  • ", style=secondary)
            footer_text.append("ESC", style=f"bold {primary}")
            footer_text.append(" Back", style=secondary)

            console.print(Panel(footer_text, border_style=border, padding=(0, 1)))

            needs_refresh = False

        if msvcrt.kbhit():
            key = msvcrt.getch()

            if key == b'\xe0':
                arrow_key = msvcrt.getch()
                if arrow_key == b'H':
                    selected_index = (selected_index - 1) % len(menu_items)
                    needs_refresh = True
                elif arrow_key == b'P':
                    selected_index = (selected_index + 1) % len(menu_items)
                    needs_refresh = True

            elif key == b'\r':
                selected_item = menu_items[selected_index]

                if selected_item["file"] == "back":
                    break

                console.clear()
                try:
                    with open(selected_item["path"], "r", encoding="utf-8") as f:
                        content = f.read()

                    header_panel = Panel.fit(
                        f"[bold {primary}]{selected_item['file']}[/bold {primary}]\n"
                        f"[{secondary}]Size: {format_size(selected_item['size'])}  •  "
                        f"Modified: {selected_item['date']}[/{secondary}]",
                        border_style=border,
                        padding=(1, 2)
                    )
                    console.print(header_panel)
                    console.print()

                    lines = content.split('\n')
                    current_line = 0
                    page_size = console.height - 10

                    while current_line < len(lines):
                        console.clear()
                        console.print(header_panel)
                        console.print()

                        page_content = '\n'.join(lines[current_line:current_line + page_size])
                        syntax = Syntax(page_content, "text", theme="monokai", line_numbers=True)
                        console.print(syntax)

                        if len(lines) > page_size:
                            page_info = f"Page {current_line // page_size + 1}/{(len(lines) + page_size - 1) // page_size}"
                            console.print(f"\n[{secondary}]{page_info} - Press SPACE for next page, B for previous, ESC to return[/{secondary}]")

                        while True:
                            if msvcrt.kbhit():
                                page_key = msvcrt.getch()
                                if page_key == b' ':
                                    current_line += page_size
                                    if current_line >= len(lines):
                                        current_line = 0
                                    break
                                elif page_key in [b'b', b'B']:
                                    current_line -= page_size
                                    if current_line < 0:
                                        current_line = max(0, len(lines) - page_size)
                                    break
                                elif page_key == b'\x1b':
                                    current_line = len(lines)
                                    break
                            time.sleep(0.01)

                    needs_refresh = True

                except Exception as e:
                    console.print(f"[{theme['error']}]Error reading log: {e}[/{theme['error']}]")
                    console.print()
                    Prompt.ask(f"[bold {primary}]{t('press_enter_continue')}[/bold {primary}]")
                    needs_refresh = True

            elif key in [b'd', b'D'] and selected_index < len(menu_items) - 1:
                selected_item = menu_items[selected_index]
                console.clear()

                confirm_panel = Panel.fit(
                    f"[bold {primary}]DELETE LOG FILE[/bold {primary}]\n\n"
                    f"[{primary}]File:[/{primary}] {selected_item['file']}\n"
                    f"[{primary}]Size:[/{primary}] {format_size(selected_item['size'])}\n"
                    f"[{primary}]Date:[/{primary}] {selected_item['date']}\n\n"
                    f"[{secondary}]Are you sure you want to delete this log file?[/{secondary}]",
                    border_style=border,
                    padding=(1, 2)
                )
                console.print(confirm_panel)
                console.print()

                if Confirm.ask(f"[bold {primary}]Delete this log file?[/bold {primary}]"):
                    try:
                        os.remove(selected_item["path"])
                        console.print(f"\n[{primary}]✓ Deleted: {selected_item['file']}[/{primary}]")
                        time.sleep(1)
                        log_files = sorted([f for f in os.listdir(log_dir) if f.endswith('.log')], reverse=True)
                        if not log_files:
                            break
                        menu_items = []
                        for log_file in log_files[:20]:
                            log_path = os.path.join(log_dir, log_file)
                            size = os.path.getsize(log_path)
                            stat = os.stat(log_path)
                            date = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                            menu_items.append({
                                "file": log_file,
                                "path": log_path,
                                "size": size,
                                "date": date,
                                "display": f"{log_file[:30]:<30} {format_size(size):>10}  {date}"
                            })
                        menu_items.append({"file": "back", "display": "← Back to Main Menu"})
                        selected_index = min(selected_index, len(menu_items) - 1)
                    except Exception as e:
                        console.print(f"\n[{theme['error']}]✗ Error deleting file: {e}[/{theme['error']}]")
                        time.sleep(2)
                needs_refresh = True

            elif key == b'\x1b':
                break

        time.sleep(0.01)

def process_option(ip: str, token: str):
    working_url, is_connected = test_server_connection(ip, settings.get("connection_timeout"))

    if not is_connected:
        Logger.error(f"Cannot connect to server at {ip}")
        Logger.info("Possible reasons:")
        Logger.info("  1. Server is offline or restarting")
        Logger.info("  2. Server is using Cloudflare protection")
        Logger.info("  3. You're being rate-limited (try waiting 30 seconds)")
        Logger.info("  4. The server requires HTTPS with a specific certificate")
        console.print()
        Prompt.ask(f"[bold {settings.get_theme('warning')}]Press Enter to continue...[/bold {settings.get_theme('warning')}]")
        return

    base_url = working_url

    try:
        Logger.info(f"Testing connection to {base_url}...")

        if token:
            test_response = requests.get(
                f"{base_url}/client",
                timeout=settings.get("connection_timeout"),
                headers={
                    "X-CitizenFX-Token": token,
                    "User-Agent": "CitizenFX/1",
                    "Connection": "close"
                },
                verify=False
            )

            if test_response.status_code == 401:
                Logger.error("Invalid token - server rejected authentication")
                console.print()
                Prompt.ask(f"[bold {settings.get_theme('warning')}]Press Enter to continue...[/bold {settings.get_theme('warning')}]")
                return

        threading_status = t("enabled") if settings.get("multi_threading") else t("disabled")
        Logger.info(f"{t('status_multi_threading')} {threading_status}")
        Logger.info(f"Max workers: {settings.get('max_workers')}")
        Logger.info(f"Adaptive speed: {'Enabled' if settings.get('adaptive_speed') else 'Disabled'}")
        Logger.info(f"Batch size: {settings.get('batch_size')}")

        dumper = FiveMDumper(base_url, token)
        dumper.run()

        if settings.get("auto_decrypt"):
            Logger.info("Auto-decrypt enabled, starting decryption...")
            decryptor = FiveMDecryptor()
            decryptor.decrypt_all_resources()
        elif Confirm.ask(f"[bold {settings.get_theme('primary')}]Do you want to decrypt the downloaded resources?[/bold {settings.get_theme('primary')}]"):
            decryptor = FiveMDecryptor()
            decryptor.decrypt_all_resources()

        if settings.get("auto_cleanup"):
            Logger.info("Auto-cleanup enabled, cleaning temporary directories...")
            for folder in ["Unpacked", "Resources", "Temp", "TempCompiled"]:
                if os.path.isdir(folder):
                    try:
                        shutil.rmtree(folder)
                        Logger.info(f"Cleaned up {folder}/")
                    except Exception as e:
                        Logger.error(f"Failed to clean up {folder}: {e}")
        elif Confirm.ask(f"[bold {settings.get_theme('warning')}]Clean up temporary directories?[/bold {settings.get_theme('warning')}]"):
            for folder in ["Unpacked", "Resources", "Temp", "TempCompiled"]:
                if os.path.isdir(folder):
                    try:
                        shutil.rmtree(folder)
                        Logger.info(f"Cleaned up {folder}/")
                    except Exception as e:
                        Logger.error(f"Failed to clean up {folder}: {e}")

        console.print()
        Prompt.ask(f"[bold {settings.get_theme('accent')}]Press Enter to continue...[/bold {settings.get_theme('accent')}]")

    except Exception as e:
        Logger.error(f"Operation failed: {e}")

        if "Remote end closed connection" in str(e):
            Logger.info("The server actively refused the connection. This often means:")
            Logger.info("  • Server is using Cloudflare DDoS protection")
            Logger.info("  • Server is offline or under maintenance")
            Logger.info("  • You've been temporarily banned or rate-limited")
            Logger.info("  • The server requires a specific User-Agent")

        console.print()
        Prompt.ask(f"[bold {settings.get_theme('warning')}]Press Enter to continue...[/bold {settings.get_theme('warning')}]")

def main():
    if not check_license_on_startup():
        console.print("[red]Exiting due to license validation failure.[/red]")
        console.print()
        Prompt.ask("[bold yellow]Press Enter to exit...[/bold yellow]")
        return

    for folder in ["Output", "Logs"]:
        os.makedirs(folder, exist_ok=True)

    while True:
        choice = display_main_menu()

        if choice == '1':
            console.print()
            link = Prompt.ask(f"[bold {settings.get_theme('primary')}]Enter cfx.re link (e.g., cfx.re/join/5zedy7 or just 5zedy7)[/bold {settings.get_theme('primary')}]").strip()
            normalized_link = normalize_cfx_link(link)

            if "cfx.re/join/" not in normalized_link:
                Logger.error("Invalid cfx.re link format. Expected format: cfx.re/join/CODE or just CODE")
                console.print()
                Prompt.ask(f"[bold {settings.get_theme('warning')}]Press Enter to continue...[/bold {settings.get_theme('warning')}]")
                continue

            try:
                with console.status(f"[bold {settings.get_theme('primary')}]Parsing Server IP...[/bold {settings.get_theme('primary')}]", spinner="dots"):
                    ip = get_ip_from_cfx(normalized_link)
                Logger.success(f"Found IP: {ip}")
            except Exception as e:
                Logger.error(f"Error getting IP: {e}")
                console.print()
                Prompt.ask(f"[bold {settings.get_theme('warning')}]Press Enter to continue...[/bold {settings.get_theme('warning')}]")
                continue

            try:
                with console.status(f"[bold {settings.get_theme('primary')}]Getting token...[/bold {settings.get_theme('primary')}]", spinner="dots"):
                    raw_token = get_token()
                    token = re.split(r'[\r\n]', raw_token)[0].strip()

                if not token:
                    Logger.error("Error 67. Make sure FiveM is running and connected to the server.")
                    console.print()
                    Prompt.ask(f"[bold {settings.get_theme('warning')}]Press Enter to continue...[/bold {settings.get_theme('warning')}]")
                    continue

                process_option(ip, token)

            except Exception as e:
                Logger.error(f"Error getting token: {e}")
                console.print()
                Prompt.ask(f"[bold {settings.get_theme('warning')}]Press Enter to continue...[/bold {settings.get_theme('warning')}]")
                continue

        elif choice == '2':
            console.print()
            ip = Prompt.ask(f"[bold {settings.get_theme('primary')}]Enter server IP (e.g., 127.0.0.1:30120)[/bold {settings.get_theme('primary')}]").strip()

            try:
                with console.status(f"[bold {settings.get_theme('primary')}]Getting token...[/bold {settings.get_theme('primary')}]", spinner="dots"):
                    raw_token = get_token()
                    token = re.split(r'[\r\n]', raw_token)[0].strip()

                if not token:
                    Logger.error("Error 67. Make sure FiveM is running and connected to the server.")
                    console.print()
                    Prompt.ask(f"[bold {settings.get_theme('warning')}]Press Enter to continue...[/bold {settings.get_theme('warning')}]")
                    continue

                process_option(ip, token)

            except Exception as e:
                Logger.error(f"Error getting token: {e}")
                console.print()
                Prompt.ask(f"[bold {settings.get_theme('warning')}]Press Enter to continue...[/bold {settings.get_theme('warning')}]")
                continue

        elif choice == '3':
            console.print()
            ip = Prompt.ask(f"[bold {settings.get_theme('primary')}]Enter server IP (e.g., 127.0.0.1:30120)[/bold {settings.get_theme('primary')}]").strip()
            token = Prompt.ask(f"[bold {settings.get_theme('primary')}]Enter token manually[/bold {settings.get_theme('primary')}]").strip()
            process_option(ip, token)

        elif choice == '4':
            console.print()
            domain = Prompt.ask(f"[bold {settings.get_theme('primary')}]Enter website/domain (e.g., example.com:30120)[/bold {settings.get_theme('primary')}]").strip()

            try:
                with console.status(f"[bold {settings.get_theme('primary')}]Getting token...[/bold {settings.get_theme('primary')}]", spinner="dots"):
                    raw_token = get_token()
                    token = re.split(r'[\r\n]', raw_token)[0].strip()

                if not token:
                    Logger.error("Error 67. Make sure FiveM is running and connected to the server.")
                    console.print()
                    Prompt.ask(f"[bold {settings.get_theme('warning')}]Press Enter to continue...[/bold {settings.get_theme('warning')}]")
                    continue

                process_option(domain, token)

            except Exception as e:
                Logger.error(f"Error getting token: {e}")
                console.print()
                Prompt.ask(f"[bold {settings.get_theme('warning')}]Press Enter to continue...[/bold {settings.get_theme('warning')}]")
                continue

        elif choice == '5':
            if not os.path.exists("Resources/Grants.txt"):
                Logger.error("No Grants.txt found. Run option 1-4 first to download resources.")
                console.print()
                Prompt.ask(f"[bold {settings.get_theme('warning')}]Press Enter to continue...[/bold {settings.get_theme('warning')}]")
                continue

            Logger.info("Starting decryption with saved grants...")
            decryptor = FiveMDecryptor()
            decryptor.decrypt_all_resources()
            console.print()
            Prompt.ask(f"[bold {settings.get_theme('warning')}]Press Enter to continue...[/bold {settings.get_theme('warning')}]")

        elif choice == '6':
            display_cache_menu()

        elif choice == '7':
            view_logs_menu()

        elif choice == '8':
            display_settings()

        elif choice == '9':
            console.clear()
            console.print(Panel.fit(
                f"[bold {settings.get_theme('primary')}]{t('thank_you')}[/bold {settings.get_theme('primary')}]",
                border_style=settings.get_theme('border'),
                padding=(2, 4)
            ))
            time.sleep(1)
            break

        else:
            console.print(f"[{settings.get_theme('error')}]Invalid choice. Please enter 1-9.[/{settings.get_theme('error')}]")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print(f"\n\n[{settings.get_theme('warning')}{t('program_interrupted')}[/{settings.get_theme('warning')}]")
    except Exception as e:
        console.print(f"\n[{settings.get_theme('error')}{t('unexpected_error')}: {e}[/{settings.get_theme('error')}]")
        console.print()
        Prompt.ask(f"[bold {settings.get_theme('warning')}]Press Enter to exit...[/bold {settings.get_theme('warning')}]")
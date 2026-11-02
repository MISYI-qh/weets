[app]
title = Weets
package.name = weets
package.domain = id.misyi
source.dir = .
source.include_exts = py,png,svg,html,json,wt
source.exclude_dirs = tests,pelatihan,.github,bin,.buildozer,src_android
version = 2.1.0
requirements = python3,numpy,android,pyjnius
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png
android.presplash_color = #fafaf8

# WebView membuka http://127.0.0.1:5000 (server Python di dalam aplikasi)
p4a.bootstrap = webview
p4a.port = 5000
android.archs = arm64-v8a
android.minapi = 24
android.api = 34
android.build_tools_version = 34.0.0
android.accept_sdk_license = True
android.permissions = INTERNET,FOREGROUND_SERVICE,FOREGROUND_SERVICE_DATA_SYNC,WAKE_LOCK,POST_NOTIFICATIONS,REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,RECEIVE_BOOT_COMPLETED
android.extra_manifest_application_arguments = ./src_android/extra_manifest_application_arguments.xml
# layanan belajar di latar belakang (dihidupkan/dibatalkan pengguna di dalam aplikasi)
services = weets:service.py:foreground
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1

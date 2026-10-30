[app]
title = Weets
package.name = weets
package.domain = id.misyi
source.dir = .
source.include_exts = py,html,json,svg,png,wt,jsonl
version = 1.6.0
requirements = python3,numpy,pyjnius,android
icon.filename = %(source.dir)s/icon.png
orientation = portrait
android.permissions = INTERNET,FOREGROUND_SERVICE,POST_NOTIFICATIONS,WAKE_LOCK,RECEIVE_BOOT_COMPLETED,REQUEST_IGNORE_BATTERY_OPTIMIZATIONS
android.archs = arm64-v8a
android.presplash_color = #FFFFFF
android.api = 33
android.minapi = 24
android.accept_sdk_license = True
source.exclude_dirs = tests, bin, bin-boot, .buildozer, .github, weets_home, android_src
presplash.filename = %(source.dir)s/presplash.png
services = weets:service.py:foreground:sticky
android.extra_manifest_application_arguments = ./extra_manifest_application_arguments.xml
p4a.bootstrap = webview
android.port = 5000

[buildozer]
log_level = 2

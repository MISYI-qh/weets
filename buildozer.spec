[app]
title = WEETS
package.name = weets
package.domain = id.misyi
source.dir = .
source.include_exts = py,html,json,svg,png,wt,jsonl
version = 1.1.0
requirements = python3,numpy
icon.filename = %(source.dir)s/icon.png
orientation = portrait
android.permissions = INTERNET
android.archs = arm64-v8a
android.presplash_color = #FFFFFF
p4a.bootstrap = webview
android.port = 5000

[buildozer]
log_level = 2

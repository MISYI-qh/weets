"""Dijalankan workflow GitHub setelah build pertama: menambahkan BootReceiver ke dist p4a lalu build ulang dengan gradle."""
import glob, os, re, shutil, sys
dists = glob.glob(".buildozer/android/platform/build-*/dists/weets")
if not dists:
    sys.exit("dist weets tidak ditemukan")
d = dists[0]
man = os.path.join(d, "src/main/AndroidManifest.xml")
xml = open(man, encoding="utf-8").read()
if "BootReceiver" not in xml:
    rec = ('<receiver android:name="id.misyi.weets.BootReceiver" android:enabled="true" android:exported="true">'
           '<intent-filter><action android:name="android.intent.action.BOOT_COMPLETED"/>'
           '<action android:name="android.intent.action.MY_PACKAGE_REPLACED"/></intent-filter></receiver>')
    xml = xml.replace("</application>", rec + "</application>", 1)
    open(man, "w", encoding="utf-8").write(xml)
jd = os.path.join(d, "src/main/java/id/misyi/weets")
os.makedirs(jd, exist_ok=True)
shutil.copy("android_src/BootReceiver.java", os.path.join(jd, "BootReceiver.java"))
print("patched", d)

[app]
title = PremiumPOS
package.name = premiumpos
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,json
version = 1.0
requirements = python3,kivy
# Для Android 4.0.3 (API 15) это критические настройки:
android.api = 24
android.minapi = 15
android.sdk = 24
android.ndk = 19b
android.archs = armeabi-v7a
fullscreen = 1
orientation = landscape
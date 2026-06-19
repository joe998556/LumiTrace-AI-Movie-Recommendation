# LumiTrace Android v1.0.7

This release fixes a real-device install issue where the APK could show:

`java.lang.Class cannot be cast to java.lang.reflect.ParameterizedType`

## Fixes

- Disabled release R8 minification and resource shrinking for the public APK.
- Keeps the v1.0.6 hardened JSON parser for BERT recommendation responses.
- Keeps the MovieLens hybrid recommendation request payload from v1.0.5.

## Why

The app worked from Android Studio but failed after installing the GitHub release APK on a physical phone. That points to release-time minification removing or rewriting reflection metadata used by the Android networking stack. This build prioritizes stable public testing over APK size.

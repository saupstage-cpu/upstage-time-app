# Mobile app packaging

## What is included now

This package now includes:
- installable PWA support (manifest + service worker)
- Upstage-branded icons and logo placeholders
- admin-editable company branding fields
- Capacitor mobile-shell scaffolding for Android and iOS packaging

## What this gives you immediately

Employees can use the hosted app as a home-screen mobile app on iPhone and Android.
Camera capture and location prompts still work in the mobile browser/PWA flow.

## What is still required for store binaries

Capacitor supports building native iOS, Android, and PWA apps from web technology [Capacitor](https://capacitorjs.com/) [PWA guide](https://capacitorjs.com/docs/web/progressive-web-apps).
For Android, create and sign a release build before distribution [Android Developers](https://developer.android.com/build/build-for-release) [Android app signing](https://developer.android.com/studio/publish/app-signing).
For iOS, Capacitor requires Xcode and Apple distribution requires Apple Developer membership [Capacitor iOS](https://capacitorjs.com/docs/ios) [Apple Developer Program](https://developer.apple.com/programs/).

## Branding

Current default branding is Upstage blue. You can change:
- company name
- primary color
- secondary color
- logo upload

from the Admin Settings page.


## Regional GPS support

Approved geofence support now includes default sites for Sydney, Australia and Cebu, Philippines so your AU and PH teams can clock in within their own regions.


Country-wide GPS allowlist is now enabled for anywhere in Australia and anywhere in the Philippines, including Cebu.

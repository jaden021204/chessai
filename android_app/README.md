# ChessAI Android app

This Flutter client connects to the existing ChessAI server on your Pi.
The Pi still performs camera detection, board alignment, move validation and
Pikafish analysis. Android and the web page control the same game. Starting a
new game in either interface replaces that shared game.

The app is portrait-only. Its default dark wood effect is drawn by Flutter,
and it uses the device font. The provided font and texture were not included:
their redistribution permissions are not known. See the optional styling
section below if you have permission to use them.

**Status:** this project has not yet been built or tested on an Android device.
The generated Android platform folder is intentionally not committed; the steps
below generate it with your locally installed Flutter SDK.

## 1. Update and start the Pi

On the Pi, stop the old app with Ctrl+C. Then:

```bash
cd ~/chessai
git status
git fetch origin android-flutter-preview
git switch android-flutter-preview
git pull --ff-only origin android-flutter-preview
source .venv/bin/activate
ENGINE_PATH="/home/jaden021204/Pikafish/src/pikafish" python -m chessai.app --run_app
```

If Git says a local file would be overwritten, stop and resolve the local
changes before pulling. The phone needs the updated Pi server for its three
separate debug images. In a second Pi terminal, run:

```bash
hostname -I
```

Note the Pi's local IP address, for example `192.168.1.10`. Keep the Pi and
phone on the same trusted Wi-Fi network. The existing server uses unencrypted
HTTP with no authentication; do not expose port 5678 to the internet or use
this on an untrusted network.

## 2. Install Flutter and Android Studio on your build computer

Flutter supports building Android apps. Follow the official instructions at
https://docs.flutter.dev/get-started/install and select your computer's
operating system and Android target. Install the Android SDK and accept its
licenses as described there. In a terminal, run:

```bash
flutter doctor
flutter doctor --android-licenses
```

Resolve any Android toolchain errors shown by `flutter doctor`. An Android
phone with USB debugging enabled, or an Android emulator, is needed to run it.
This build computer may be separate from the Pi. If it does not already have
the repository, clone the preview branch in its terminal:

```bash
git clone --branch android-flutter-preview https://github.com/jaden021204/chessai.git
cd chessai
```

## 3. Generate Android files and allow local HTTP

In the terminal on your **build computer**, from the repository root:

```bash
cd android_app
flutter create --platforms=android --project-name=chessai_android .
```

Do **not** add `--overwrite`: it would replace project files. In the generated
`android_app/android/app/src/main/AndroidManifest.xml`, edit only these
sections:

1. Immediately after the opening `<manifest ...>` line, insert:

   ```xml
   <uses-permission android:name="android.permission.INTERNET"/>
   ```

2. In the existing `<application ...>` opening tag, add:

   ```xml
   android:usesCleartextTraffic="true"
   ```

   This is required for the Pi's current HTTP server. Keep the existing
   attributes and closing `>`; do not add another `<application>` tag.

3. In the existing `<activity ...>` opening tag for `.MainActivity`, add:

   ```xml
   android:screenOrientation="portrait"
   ```

   Keep the existing activity attributes and closing `>`.

The generated `android_app/android/` directory is ignored by Git. If it is
regenerated, repeat these manifest edits.

## 4. Build and install

Still in `android_app` on the build computer:

```bash
flutter pub get
flutter analyze
flutter test
flutter devices
flutter run
```

Choose the phone or emulator if Flutter asks. For an installable release APK:

```bash
flutter build apk --release
```

The output is `android_app/build/app/outputs/flutter-apk/app-release.apk`.
Use an appropriately signed build before distributing it.

## 5. Connect and test

1. On the main screen tap the gear icon. Enter `http://<pi-ip>:5678`,
   replacing `<pi-ip>` with the address from step 1. The address lasts until
   the app is closed; enter it again next time. `raspberrypi.local` is only a
   default and may not resolve on every phone.
2. Tap **Debug View** and check the camera, aligned board/detections, and
   camera/ARUCO markers. They are refreshed approximately once per second.
3. Open its menu, tap **Play**, and choose Analyzer, your color, a board
   position and difficulty. **vs Robot** is disabled. Android's **Master**
   uses the existing web **Expert** preset (depth 8).
4. Tap **Start**. Your pieces must appear at the bottom of the detected board.
   Red goes first. On your turn move a piece and tap **END TURN**. Follow
   COM's arrow. Use the board menu for **Hint**, **Move List**, **Debug View**
   and **Main Menu**. The newest move is at the top of the list.
5. Test both colors, an invalid move and an incorrect COM placement. Check
   the warning, and that it repeats five seconds after dismissal if the
   detected position remains wrong. **NEW GAME** opens the options again.

The existing game limitations remain: a side with no legal moves loses, but
repetition and other history-dependent outcomes are not adjudicated.
If the phone cannot connect, check the address, Wi-Fi, that the Pi app is
running and that `http://<pi-ip>:5678` opens in the phone's browser. If debug
images fail but the board works, ensure the Pi was updated and restarted.

## Optional: use your own font and texture

Only do this if you have permission to use and distribute both files. They
will be packaged into the APK. On the **build computer**, create
`android_app/assets/` and copy your files there as `golden_bell.ttf` and
`wood.jpg`. These files are ignored by Git.

In `android_app/pubspec.yaml`, add these sections **under the existing
`flutter:` section**, keeping `uses-material-design: true`:

```yaml
  assets:
    - assets/wood.jpg
  fonts:
    - family: GoldenBell
      fonts:
        - asset: assets/golden_bell.ttf
```

In `android_app/lib/main.dart`, edit only the theme section: find
`theme: ThemeData(` and insert the following line immediately below it:

```dart
          fontFamily: 'GoldenBell',
```

In the same file, replace only this line:

```dart
          const Positioned.fill(child: CustomPaint(painter: WoodPainter())),
```

with:

```dart
          Positioned.fill(
            child: Image.asset(
              'assets/wood.jpg',
              fit: BoxFit.cover,
              color: Colors.black45,
              colorBlendMode: BlendMode.darken,
            ),
          ),
```

Then run `flutter pub get` and rebuild. If an asset is missing or cannot be
used, undo those two section edits and remove the added `assets` and `fonts`
sections from `pubspec.yaml` to return to the default styling.

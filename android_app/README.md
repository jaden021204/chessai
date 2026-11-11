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
flutter pub add dev:flutter_lints
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
   position, difficulty and timer. **vs Robot** is disabled. Android's
   **Master** uses the existing web **Expert** preset (depth 8). Timers are
   5 or 10 minutes, with optional 5-second increments.
4. Tap **Start**. Your pieces must appear at the bottom of the detected board.
   Red goes first. On your turn move a piece and tap **END TURN**. Follow
   COM's arrow. Use the board menu for **Hint**, **Move List**, **Debug View**
   and **Main Menu**. The newest move is at the top of the list.
5. Test both colors, an invalid move and an incorrect COM placement. Check
   that dismissing the warning on either interface dismisses it on the other,
   and that it repeats five seconds later if the detected position remains
   wrong. **NEW GAME** opens the options again.
   The Pi keeps the clocks running during move validation and while waiting
   for COM's physical move; the active side loses at zero. The game and clocks
   are lost if ChessAI stops.

The existing game limitations remain: a side with no legal moves loses, but
repetition and other history-dependent outcomes are not adjudicated.
If the phone cannot connect, check the address, Wi-Fi, that the Pi app is
running and that `http://<pi-ip>:5678` opens in the phone's browser. If debug
images fail but the board works, ensure the Pi was updated and restarted.

## Optional: start and stop ChessAI from Android

The Pi must already be powered on, connected to the same trusted network, and
running a small controller service. This controls the ChessAI program, not
the Pi's power. Stopping ChessAI ends the current game. The controller and
game API use unencrypted HTTP: the controller token and game data can be
observed on the network. Do not expose ports 5678 or 5679 to the internet or
use an untrusted Wi-Fi network. The existing game API is not authenticated;
the token protects only the separate controller.

On the Pi, stop any manually launched ChessAI process with Ctrl+C. The
following examples assume the Pi username `jaden021204`, the repository path
`/home/jaden021204/chessai`, and the Pikafish path used earlier. If your paths
are different, change them in **both service files** below. Use full paths;
systemd does not expand `~` in these fields.

1. In a Pi terminal, make a private token and the systemd user directory:

   ```bash
   mkdir -p ~/.config/systemd/user ~/.config/chessai
   chmod 700 ~/.config/chessai
   python3 -c 'import os,pathlib,secrets; p=pathlib.Path.home()/".config/chessai/controller-token"; fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); os.write(fd,(secrets.token_hex(32)+"\n").encode()); os.close(fd)'
   ```

   This refuses to overwrite an existing token. Do not commit the token or
   share it outside your trusted devices. To see it for entry on the phone,
   run `cat ~/.config/chessai/controller-token` privately on the Pi.

2. Create the whole file `~/.config/systemd/user/chessai.service`:

   ```ini
   [Unit]
   Description=ChessAI game and camera server
   After=network.target

   [Service]
   Type=simple
   WorkingDirectory=/home/jaden021204/chessai
   Environment=ENGINE_PATH=/home/jaden021204/Pikafish/src/pikafish
   ExecStart=/home/jaden021204/chessai/.venv/bin/python -m chessai.app --run_app
   Restart=no
   TimeoutStopSec=15

   [Install]
   WantedBy=default.target
   ```

3. Create the whole file `~/.config/systemd/user/chessai-control.service`:

   ```ini
   [Unit]
   Description=ChessAI local network controller
   After=network.target

   [Service]
   Type=simple
   WorkingDirectory=/home/jaden021204/chessai
   Environment=CHESSAI_CONTROL_TOKEN_FILE=/home/jaden021204/.config/chessai/controller-token
   ExecStart=/home/jaden021204/chessai/.venv/bin/python -m chessai.remote_control
   Restart=on-failure

   [Install]
   WantedBy=default.target
   ```

4. Enable the controller at boot, even when you have not logged in:

   ```bash
   sudo loginctl enable-linger jaden021204
   systemctl --user daemon-reload
   systemctl --user enable --now chessai-control.service
   systemctl --user status chessai-control.service --no-pager
   ```

   The command requires administrator approval. It changes the Pi's startup
   configuration. The game service is not enabled at boot by these commands;
   the controller starts it on request.

5. Rebuild and install the updated Android app. Set the Pi address using the
   gear icon, then tap **Start / Stop ChessAI** and enter the token. Choose
   **Start**, **Status**, or **Stop**. Stop asks for confirmation because the
   game is not saved. The token remains only in app memory; enter it again
   after restarting the app or changing the Pi address.

To troubleshoot, on the Pi run `systemctl --user status chessai.service
--no-pager` and `journalctl --user -u chessai.service -n 50 --no-pager`.
For controller problems replace `chessai.service` with
`chessai-control.service`. If the service says active but the app cannot yet
connect, allow time for camera and model initialization.

To disable the optional controller at any time:

```bash
systemctl --user disable --now chessai-control.service
```

This leaves the game service, token file and linger setting in place. To
disable lingering as well, run `sudo loginctl disable-linger jaden021204` only
if you do not need it for other user services.

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

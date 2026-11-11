import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

const red = Color(0xffff160c);
const cream = Color(0xffffc99d);

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
  runApp(const ChessApp());
}

class ChessApp extends StatelessWidget {
  const ChessApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'XiangQi GUI',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: red),
          textTheme: ThemeData.light().textTheme.apply(
                bodyColor: red,
                displayColor: red,
              ),
        ),
        home: const Home(),
      );
}

class ApiException implements Exception {
  ApiException(this.message);
  final String message;

  @override
  String toString() => message;
}

class PiApi {
  PiApi(this.base);
  final Uri base;
  final HttpClient _client = HttpClient()
    ..connectionTimeout = const Duration(seconds: 5);

  Uri uri(String path) => base.replace(path: path, query: null, fragment: null);

  Future<Uint8List> _request(String path,
      {Map<String, String>? body, Duration timeout = const Duration(seconds: 10)}) async {
    try {
      final request = body == null
          ? await _client.getUrl(uri(path)).timeout(timeout)
          : await _client.postUrl(uri(path)).timeout(timeout);
      if (body != null) {
        request.headers.contentType = ContentType.json;
        request.write(jsonEncode(body));
      }
      final response = await request.close().timeout(timeout);
      final bytes = await response.fold<BytesBuilder>(
        BytesBuilder(),
        (builder, chunk) => builder..add(chunk),
      ).timeout(timeout);
      final data = bytes.takeBytes();
      if (response.statusCode < 200 || response.statusCode >= 300) {
        String message = 'Pi returned HTTP ${response.statusCode}.';
        try {
          final decoded = jsonDecode(utf8.decode(data));
          if (decoded is Map && decoded['detail'] is String) {
            message = decoded['detail'] as String;
          }
        } on FormatException {
          // Keep the HTTP status when the server does not return JSON.
        }
        throw ApiException(message);
      }
      return data;
    } on TimeoutException {
      throw ApiException('The Pi did not respond in time.');
    } on SocketException catch (error) {
      throw ApiException('Cannot connect to the Pi: ${error.message}');
    } on HttpException catch (error) {
      throw ApiException('Network error: ${error.message}');
    }
  }

  Future<Map<String, dynamic>> json(String path,
      {Map<String, String>? body, bool longRunning = false}) async {
    final bytes = await _request(path,
        body: body,
        timeout: Duration(seconds: longRunning ? 180 : 15));
    try {
      final value = jsonDecode(utf8.decode(bytes));
      if (value is! Map<String, dynamic>) {
        throw ApiException('The Pi returned an unexpected response.');
      }
      return value;
    } on FormatException {
      throw ApiException('The Pi returned invalid JSON.');
    }
  }

  Future<Uint8List> image(String path) => _request(path);

  void close() => _client.close(force: true);
}

enum Screen { main, setup, board, debug }

class Home extends StatefulWidget {
  const Home({super.key});

  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> {
  PiApi api = PiApi(Uri.parse('http://raspberrypi.local:5678'));
  Screen screen = Screen.main;
  String player = 'r';
  String position = 'current';
  String difficulty = 'medium';
  Map<String, dynamic> game = {'is_playing': false};
  Map<String, Uint8List> images = {};
  String? connectionError;
  bool polling = false;
  bool loadingImages = false;
  bool actionRunning = false;
  bool dialogOpen = false;
  DateTime warningAfter = DateTime.fromMillisecondsSinceEpoch(0);
  String? announcedWinner;
  int connectionVersion = 0;
  int actionVersion = 0;
  Timer? timer;

  @override
  void initState() {
    super.initState();
    timer = Timer.periodic(const Duration(seconds: 1), (_) => refresh());
    refresh();
  }

  @override
  void dispose() {
    timer?.cancel();
    api.close();
    super.dispose();
  }

  void refresh() {
    refreshGame();
    refreshImages();
  }

  Future<void> refreshGame() async {
    if (!polling && !actionRunning) {
      polling = true;
      final version = connectionVersion;
      final currentAction = actionVersion;
      try {
        final data = await api.json('/api/xiangqi/game_snapshot',
            longRunning: true);
        if (mounted && version == connectionVersion &&
            currentAction == actionVersion && !actionRunning) {
          setState(() {
            game = data;
            connectionError = null;
          });
          showGameNotice();
        }
      } catch (error) {
        if (mounted && version == connectionVersion) {
          setState(() => connectionError = error.toString());
        }
      } finally {
        polling = false;
      }
    }
  }

  Future<void> refreshImages() async {
    if (!mounted || loadingImages ||
        (screen != Screen.board && screen != Screen.debug)) return;
    loadingImages = true;
    final version = connectionVersion;
    final imageScreen = screen;
    final paths = screen == Screen.board
        ? ['/api/vision/visualization_frame']
        : [
            '/api/vision/original_snapshot',
            '/api/vision/debug_aligned_frame',
            '/api/vision/debug_markers_frame',
          ];
    try {
      final results = await Future.wait(paths.map(api.image));
      if (mounted && version == connectionVersion && screen == imageScreen) {
        setState(() {
          images = Map.fromIterables(paths, results);
        });
      }
    } catch (error) {
      if (mounted && version == connectionVersion) {
        setState(() => connectionError = error.toString());
      }
    } finally {
      loadingImages = false;
    }
  }

  Future<void> showMessage(String title, String message) async {
    if (!mounted || dialogOpen) return;
    dialogOpen = true;
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
    dialogOpen = false;
  }

  Future<void> showGameNotice() async {
    if (dialogOpen || game['is_playing'] != true) return;
    final winner = game['winner'];
    if (winner is String && winner != announcedWinner) {
      announcedWinner = winner;
      await showMessage('Game over',
          winner == game['player'] ? 'You win.' : 'COM wins.');
      return;
    }
    final warning = game['warning'];
    if (warning is String && DateTime.now().isAfter(warningAfter)) {
      await showMessage('Please check the board', warning);
      warningAfter = DateTime.now().add(const Duration(seconds: 5));
    }
  }

  Future<void> runAction(Future<void> Function() action) async {
    if (actionRunning) return;
    actionVersion++;
    setState(() => actionRunning = true);
    try {
      await action();
    } catch (error) {
      await showMessage('Unable to continue', error.toString());
    } finally {
      if (mounted) setState(() => actionRunning = false);
    }
    if (mounted) refresh();
  }

  Future<void> startGame() => runAction(() async {
        final result = await api.json('/api/xiangqi/new_game',
            body: {
              'next_player': player,
              'position': position,
              'difficulty': difficulty,
              'mode': 'analyzer',
            },
            longRunning: true);
        if (!mounted) return;
        setState(() {
          game = result;
          announcedWinner = null;
          warningAfter = DateTime.fromMillisecondsSinceEpoch(0);
          screen = Screen.board;
          images = {};
        });
      });

  Future<void> endTurn() => runAction(() async {
        final result = await api.json('/api/xiangqi/play',
            body: {}, longRunning: true);
        if (mounted) setState(() => game = result);
      });

  Future<void> hint() => runAction(() async {
        final result = await api.json('/api/xiangqi/get_hint',
            longRunning: true);
        if (mounted) {
          await showMessage('Hint',
              result['best_move'] == null ? 'No move returned.' : 'Move: ${result['best_move']}');
        }
      });

  Future<void> changeAddress() async {
    final controller = TextEditingController(text: api.base.toString());
    final input = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Raspberry Pi address'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.url,
          decoration: const InputDecoration(
            labelText: 'Address',
            hintText: 'http://192.168.1.10:5678',
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(context, controller.text.trim()),
              child: const Text('Connect')),
        ],
      ),
    );
    controller.dispose();
    if (input == null || !mounted) return;
    final address = Uri.tryParse(input);
    if (address == null || address.scheme != 'http' || address.host.isEmpty ||
        address.userInfo.isNotEmpty || (address.path.isNotEmpty && address.path != '/') ||
        address.hasQuery || address.hasFragment) {
      await showMessage('Invalid address', 'Enter an address such as http://192.168.1.10:5678.');
      return;
    }
    connectionVersion++;
    api.close();
    setState(() {
      api = PiApi(address);
      game = {'is_playing': false};
      images = {};
      connectionError = null;
      announcedWinner = null;
      screen = Screen.main;
    });
    refresh();
  }

  void navigate(Screen target) {
    setState(() {
      screen = target;
      images = {};
    });
    refresh();
  }

  @override
  Widget build(BuildContext context) {
    final yourTurn = game['is_playing'] == true &&
        game['next_player'] == game['player'] && game['winner'] == null;
    return Scaffold(
      body: Stack(
        children: [
          const Positioned.fill(child: CustomPaint(painter: WoodPainter())),
          SafeArea(
            child: Column(
              children: [
                if (connectionError != null)
                  Material(
                    color: Colors.black87,
                    child: Padding(
                      padding: const EdgeInsets.all(6),
                      child: Text(connectionError!, style: const TextStyle(color: Colors.white)),
                    ),
                  ),
                Expanded(
                  child: switch (screen) {
                    Screen.main => mainMenu(),
                    Screen.setup => setupMenu(),
                    Screen.board => boardPage(yourTurn),
                    Screen.debug => debugPage(),
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget mainMenu() => Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Align(
              alignment: Alignment.topRight,
              child: IconButton(
                tooltip: 'Pi address',
                onPressed: actionRunning ? null : changeAddress,
                icon: const Icon(Icons.settings, color: cream),
              ),
            ),
            const Expanded(
              child: Column(
                children: [
                  Expanded(child: Center(child: FittedBox(child: Text('XiangQi',
                      style: TextStyle(color: red, fontWeight: FontWeight.bold, fontSize: 100))))),
                  Expanded(child: Center(child: FittedBox(child: Text('GUI',
                      style: TextStyle(color: red, fontWeight: FontWeight.bold, fontSize: 100))))),
                ],
              ),
            ),
            ActionButton(label: 'Play', onPressed: () => navigate(Screen.setup)),
            const SizedBox(height: 12),
            ActionButton(label: 'Debug View', onPressed: () => navigate(Screen.debug)),
          ],
        ),
      );

  Widget setupMenu() => LayoutBuilder(builder: (context, constraints) {
        final unit = constraints.maxHeight / 13;
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Column(
            children: [
              SizedBox(height: unit, child: Row(children: [
                IconButton(onPressed: () => navigate(Screen.main),
                    icon: const Icon(Icons.arrow_back, color: cream)),
                const Expanded(child: Center(child: Text('New Game',
                    style: TextStyle(color: red, fontSize: 24, fontWeight: FontWeight.bold)))),
                const SizedBox(width: 48),
              ])),
              Expanded(child: optionGroup('Mode', [
                choice('Analyzer', true, () {}),
                choice('vs Robot', false, null),
              ])),
              Expanded(child: optionGroup('Your side', [
                choice('Red', player == 'r', () => setState(() => player = 'r')),
                choice('Black', player == 'b', () => setState(() => player = 'b')),
              ])),
              Expanded(child: optionGroup('Position', [
                choice('Starting Board', position == 'starting',
                    () => setState(() => position = 'starting')),
                choice('Current Board', position == 'current',
                    () => setState(() => position = 'current')),
              ])),
              Expanded(child: optionGroup('Difficulty', [
                choice('Easy', difficulty == 'easy', () => setState(() => difficulty = 'easy')),
                choice('Medium', difficulty == 'medium', () => setState(() => difficulty = 'medium')),
                choice('Hard', difficulty == 'hard', () => setState(() => difficulty = 'hard')),
                choice('Master', difficulty == 'expert', () => setState(() => difficulty = 'expert')),
              ])),
              SizedBox(
                height: math.max(45.0, unit * 1.3),
                child: ActionButton(label: actionRunning ? 'Starting...' : 'Start',
                    onPressed: actionRunning ? null : startGame),
              ),
              const SizedBox(height: 8),
            ],
          ),
        );
      });

  Widget optionGroup(String title, List<Widget> choices) => Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          FittedBox(child: Text(title, style: const TextStyle(
              color: red, fontWeight: FontWeight.bold, fontSize: 21))),
          const SizedBox(height: 4),
          SizedBox(height: 44, child: Row(
              children: choices.map((widget) => Expanded(child: widget)).toList())),
        ],
      );

  Widget choice(String label, bool selected, VoidCallback? onPressed) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 2),
        child: OutlinedButton(
          onPressed: onPressed,
          style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 2),
            backgroundColor: selected ? red : cream,
            foregroundColor: Colors.black,
            disabledBackgroundColor: Colors.grey,
            disabledForegroundColor: Colors.black54,
            side: const BorderSide(color: Colors.black, width: 2),
          ),
          child: FittedBox(child: Text(label, maxLines: 1,
              style: const TextStyle(fontWeight: FontWeight.bold))),
        ),
      );

  Widget boardPage(bool yourTurn) => LayoutBuilder(builder: (context, constraints) {
        final boardWidth = math.min(constraints.maxWidth, constraints.maxHeight * .54);
        final square = boardWidth / 8;
        return Column(
          children: [
            SizedBox(
              height: 52,
              child: Stack(alignment: Alignment.center, children: [
                Text(game['winner'] != null ? 'GAME OVER' :
                    'YOU ${yourTurn ? "●" : ""} | COM ${!yourTurn ? "●" : ""}',
                    style: const TextStyle(color: red, fontWeight: FontWeight.bold, fontSize: 22)),
                Align(alignment: Alignment.centerRight, child: boardMenu()),
              ]),
            ),
            const Spacer(),
            SizedBox(width: boardWidth, height: boardWidth * 1.12,
                child: imageBox('/api/vision/visualization_frame', 'Waiting for board')),
            const SizedBox(height: 8),
            SizedBox(
              width: square * 6,
              height: square * 2,
              child: ActionButton(label: actionRunning ? 'Analyzing...' : 'END TURN',
                  onPressed: yourTurn && !actionRunning ? endTurn : null),
            ),
            const Spacer(flex: 2),
            SizedBox(
              width: double.infinity,
              height: square,
              child: ActionButton(label: 'NEW GAME',
                  onPressed: actionRunning ? null : () => navigate(Screen.setup)),
            ),
          ],
        );
      });

  Widget boardMenu() => PopupMenuButton<String>(
        tooltip: 'Menu',
        icon: const Icon(Icons.menu, color: cream),
        onSelected: (value) {
          if (value == 'main') navigate(Screen.main);
          if (value == 'debug') navigate(Screen.debug);
          if (value == 'history') showHistory();
          if (value == 'hint') hint();
        },
        itemBuilder: (context) => [
          const PopupMenuItem(value: 'main', child: Text('Main Menu')),
          const PopupMenuItem(value: 'debug', child: Text('Debug View')),
          const PopupMenuItem(value: 'history', child: Text('Move List')),
          PopupMenuItem(value: 'hint', enabled: !actionRunning &&
              game['next_player'] == game['player'] && game['winner'] == null,
              child: const Text('Hint')),
        ],
      );

  Future<void> showHistory() async {
    final moves = game['moves'];
    final list = moves is List ? moves : [];
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Move List'),
        content: SizedBox(
          width: double.maxFinite,
          child: list.isEmpty ? const Text('No moves yet.') : ListView.builder(
            shrinkWrap: true,
            itemCount: list.length,
            itemBuilder: (context, index) {
              final number = list.length - index;
              return Text('$number. ${list[number - 1]}');
            },
          ),
        ),
        actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('Close'))],
      ),
    );
  }

  Widget debugPage() => Column(
        children: [
          SizedBox(height: 52, child: Row(children: [
            PopupMenuButton<String>(
              tooltip: 'Menu',
              icon: const Icon(Icons.menu, color: cream),
              onSelected: (value) => navigate(value == 'play' ? Screen.setup : Screen.main),
              itemBuilder: (context) => [
                const PopupMenuItem(value: 'play', child: Text('Play')),
                const PopupMenuItem(value: 'main', child: Text('Main Menu')),
              ],
            ),
            const Expanded(child: Text('Debug View', textAlign: TextAlign.center,
                style: TextStyle(color: red, fontWeight: FontWeight.bold, fontSize: 24))),
            const SizedBox(width: 48),
          ])),
          Expanded(child: debugImage('Camera', '/api/vision/original_snapshot')),
          Expanded(child: debugImage('Aligned board / detections', '/api/vision/debug_aligned_frame')),
          Expanded(child: debugImage('Camera / markers', '/api/vision/debug_markers_frame')),
        ],
      );

  Widget debugImage(String label, String path) => Column(
        children: [
          Text(label, style: const TextStyle(color: cream, fontWeight: FontWeight.bold)),
          Expanded(child: imageBox(path, 'Waiting for $label')),
        ],
      );

  Widget imageBox(String path, String placeholder) {
    final bytes = images[path];
    return bytes == null
        ? Center(child: Text(placeholder, style: const TextStyle(color: cream)))
        : Image.memory(bytes, fit: BoxFit.contain, gaplessPlayback: true,
            errorBuilder: (_, __, ___) => Center(child: Text('Invalid image: $path')));
  }
}

class ActionButton extends StatelessWidget {
  const ActionButton({super.key, required this.label, required this.onPressed});
  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: double.infinity,
        height: 58,
        child: OutlinedButton(
          onPressed: onPressed,
          style: OutlinedButton.styleFrom(
            backgroundColor: cream,
            foregroundColor: Colors.black,
            disabledBackgroundColor: Colors.grey,
            disabledForegroundColor: Colors.black54,
            side: const BorderSide(color: Colors.black, width: 2),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          ),
          child: FittedBox(child: Text(label,
              style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold))),
        ),
      );
}

class WoodPainter extends CustomPainter {
  const WoodPainter();

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(Offset.zero & size, Paint()..color = const Color(0xff563320));
    final paint = Paint()
      ..strokeWidth = 1
      ..style = PaintingStyle.stroke;
    for (var x = 0; x < size.width; x += 3) {
      final alpha = 15 + ((x * 37) % 35);
      paint.color = Color.fromARGB(alpha, 15, 5, 0);
      final path = Path()..moveTo(x.toDouble(), 0);
      for (var y = 0; y <= size.height; y += 12) {
        path.lineTo(x.toDouble() + math.sin(y / 85 + x / 25) * 3, y.toDouble());
      }
      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(covariant WoodPainter oldDelegate) => false;
}

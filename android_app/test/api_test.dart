import 'dart:convert';
import 'dart:io';

import 'package:chessai_android/main.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('accepts Pi IP addresses before the game server is running', () {
    expect(parsePiAddress('192.168.1.10').toString(), 'http://192.168.1.10:5678');
    expect(parsePiAddress('http://192.168.1.10:5678').toString(), 'http://192.168.1.10:5678');
    expect(parsePiAddress('raspberrypi.local:6000').toString(), 'http://raspberrypi.local:6000');
    expect(parsePiAddress('https://192.168.1.10'), isNull);
    expect(parsePiAddress('http://user@192.168.1.10'), isNull);
    expect(parsePiAddress('192.168.1.10/path'), isNull);
    expect(parsePiAddress('192.168.1.10:99999'), isNull);
    expect(parsePiAddress(''), isNull);
  });

  test('sends setup and reports server errors', () async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    final received = <Map<String, dynamic>>[];
    server.listen((request) async {
      if (request.uri.path == '/api/xiangqi/new_game') {
        received.add(jsonDecode(await utf8.decoder.bind(request).join()) as Map<String, dynamic>);
        request.response.headers.contentType = ContentType.json;
        request.response.write('{"is_playing":true}');
      } else {
        request.response.statusCode = 422;
        request.response.headers.contentType = ContentType.json;
        request.response.write('{"detail":"No piece moved."}');
      }
      await request.response.close();
    });
    final api = PiApi(Uri.parse('http://127.0.0.1:${server.port}'));
    try {
      final result = await api.json('/api/xiangqi/new_game',
          body: {'difficulty': 'expert', 'next_player': 'b'});
      expect(result['is_playing'], true);
      expect(received.single['difficulty'], 'expert');
      await expectLater(api.json('/api/xiangqi/play', body: {}),
          throwsA(isA<ApiException>().having((e) => e.message, 'message', 'No piece moved.')));
    } finally {
      api.close();
      await server.close(force: true);
    }
  });

  test('controller sends authorization before authenticated POST body', () async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    final requests = <String>[];
    server.listen((request) async {
      final authorization = request.headers.value(HttpHeaders.authorizationHeader);
      final body = await utf8.decoder.bind(request).join();
      requests.add('${request.method} ${request.uri.path}');
      request.response.headers.contentType = ContentType.json;
      if (authorization != 'Bearer test-token') {
        request.response.statusCode = 401;
        request.response.write('{"detail":"Invalid controller token."}');
      } else if (request.method == 'POST' && body != '{}') {
        request.response.statusCode = 400;
        request.response.write('{"detail":"Invalid body."}');
      } else {
        request.response.write('{"running":${request.uri.path == '/start'}}');
      }
      await request.response.close();
    });
    final api = PiApi(Uri.parse('http://127.0.0.1:${server.port}'));
    try {
      expect((await api.json('/status', token: 'test-token'))['running'], false);
      expect((await api.json('/start', token: 'test-token', body: {}))['running'], true);
      expect((await api.json('/stop', token: 'test-token', body: {}))['running'], false);
      await expectLater(api.json('/start', token: 'wrong-token', body: {}),
          throwsA(isA<ApiException>().having((e) => e.message, 'message', 'Invalid controller token.')));
      expect(requests, ['GET /status', 'POST /start', 'POST /stop', 'POST /start']);
    } finally {
      api.close();
      await server.close(force: true);
    }
  });
}

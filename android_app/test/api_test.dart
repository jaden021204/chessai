import 'dart:convert';
import 'dart:io';

import 'package:chessai_android/main.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
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
}

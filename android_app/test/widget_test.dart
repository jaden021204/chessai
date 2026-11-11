import 'package:chessai_android/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('main menu shows requested navigation', (tester) async {
    await tester.pumpWidget(const ChessApp());
    expect(find.text('XiangQi'), findsOneWidget);
    expect(find.text('GUI'), findsOneWidget);
    expect(find.text('Play'), findsOneWidget);
    expect(find.text('Debug View'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });
}

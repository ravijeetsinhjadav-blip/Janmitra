import 'package:flutter_test/flutter_test.dart';
import 'package:janmitra_assist/main.dart';
import 'package:janmitra_assist/core/constants/app_constants.dart';

void main() {
  testWidgets('JanMitra Assist launch and home screen verification test', (WidgetTester tester) async {
    // Build the app and trigger a frame.
    await tester.pumpWidget(const JanMitraApp());

    // Verify that the application title appears.
    expect(find.text(AppConstants.appName), findsWidgets);

    // Verify that the Phase 1 placeholder message is present.
    expect(find.text(AppConstants.placeholderMessage), findsOneWidget);
  });
}

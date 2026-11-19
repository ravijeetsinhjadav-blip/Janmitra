import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:janmitra_assist/features/auth/presentation/screens/reset_password_screen.dart';
import 'package:janmitra_assist/main.dart';

void main() {
  testWidgets('ResetPasswordScreen renders form fields and buttons', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: ResetPasswordScreen(),
      ),
    );

    expect(find.text('Reset Password'), findsOneWidget);
    expect(find.text('Choose New Password'), findsOneWidget);
    expect(find.text('Reset Token'), findsOneWidget);
    expect(find.text('New Password'), findsOneWidget);
    expect(find.text('Confirm New Password'), findsOneWidget);
    expect(find.text('Update Password'), findsOneWidget);
    expect(find.text('Back to Sign In'), findsOneWidget);
  });

  testWidgets('ResetPasswordScreen displays prefilled token when provided', (WidgetTester tester) async {
    const testToken = 'abc123securetokenxyz';
    await tester.pumpWidget(
      const MaterialApp(
        home: ResetPasswordScreen(initialToken: testToken),
      ),
    );

    expect(find.text(testToken), findsOneWidget);
    expect(find.text('Token loaded from secure reset link'), findsOneWidget);
  });

  testWidgets('ResetPasswordScreen validates empty fields on submit', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: ResetPasswordScreen(),
      ),
    );

    // Tap Update Password with empty fields
    await tester.tap(find.text('Update Password'));
    await tester.pumpAndSettle();

    expect(find.text('Reset token is required'), findsOneWidget);
    expect(find.text('Password is required'), findsOneWidget);
  });

  testWidgets('ResetPasswordScreen validates password matching and length', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: ResetPasswordScreen(initialToken: 'validtoken123'),
      ),
    );

    // Enter short password and mismatch
    await tester.enterText(find.widgetWithText(TextFormField, 'New Password'), 'Short1!');
    await tester.enterText(find.widgetWithText(TextFormField, 'Confirm New Password'), 'Mismatch2@');

    await tester.tap(find.text('Update Password'));
    await tester.pumpAndSettle();

    expect(find.text('Password must be at least 10 characters'), findsOneWidget);
    expect(find.text('Passwords do not match'), findsOneWidget);
  });

  testWidgets('ResetPasswordScreen validates password complexity rules', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: ResetPasswordScreen(initialToken: 'validtoken123'),
      ),
    );

    // Enter 10-char password missing digit
    await tester.enterText(find.widgetWithText(TextFormField, 'New Password'), 'AlllettersOnly!');
    await tester.enterText(find.widgetWithText(TextFormField, 'Confirm New Password'), 'AlllettersOnly!');
    await tester.tap(find.text('Update Password'));
    await tester.pumpAndSettle();
    expect(find.text('Must contain at least one number'), findsOneWidget);

    // Enter 10-char password missing symbol
    await tester.enterText(find.widgetWithText(TextFormField, 'New Password'), 'Allletters123');
    await tester.enterText(find.widgetWithText(TextFormField, 'Confirm New Password'), 'Allletters123');
    await tester.tap(find.text('Update Password'));
    await tester.pumpAndSettle();
    expect(find.text('Must contain at least one special character'), findsOneWidget);

    // Enter 10-char password missing uppercase
    await tester.enterText(find.widgetWithText(TextFormField, 'New Password'), 'lowercase123!');
    await tester.enterText(find.widgetWithText(TextFormField, 'Confirm New Password'), 'lowercase123!');
    await tester.tap(find.text('Update Password'));
    await tester.pumpAndSettle();
    expect(find.text('Must contain at least one uppercase letter'), findsOneWidget);
  });

  testWidgets('JanMitraApp deep link route /reset-password?token=... resolves with prefilled token', (WidgetTester tester) async {
    await tester.pumpWidget(const JanMitraApp(homeOverride: SizedBox()));
    await tester.pump();

    final navigator = tester.state<NavigatorState>(find.byType(Navigator));
    navigator.pushNamed('/reset-password?token=deep_link_auto_token_456');
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('deep_link_auto_token_456'), findsOneWidget);
    expect(find.text('Token loaded from secure reset link'), findsOneWidget);
  });

  testWidgets('JanMitraApp custom scheme deep link janmitra://reset-password?token=... resolves properly', (WidgetTester tester) async {
    await tester.pumpWidget(const JanMitraApp(homeOverride: SizedBox()));
    await tester.pump();

    final navigator = tester.state<NavigatorState>(find.byType(Navigator));
    navigator.pushNamed('janmitra://reset-password?token=custom_scheme_token_789');
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('custom_scheme_token_789'), findsOneWidget);
    expect(find.text('Token loaded from secure reset link'), findsOneWidget);
  });
}

import 'package:flutter_test/flutter_test.dart';
import 'package:janmitra_assist/main.dart';
import 'package:janmitra_assist/core/constants/app_constants.dart';
import 'package:janmitra_assist/features/home/presentation/screens/home_screen.dart';
import 'package:janmitra_assist/features/auth/presentation/screens/login_screen.dart';
import 'package:janmitra_assist/features/auth/presentation/screens/splash_screen.dart';

void main() {
  testWidgets('JanMitra Assist launch and splash screen verification test', (WidgetTester tester) async {
    // Build the app with zero splash delay for isolated widget testing
    await tester.pumpWidget(const JanMitraApp(
      homeOverride: SplashScreen(delay: Duration.zero),
    ));

    // Verify that the application title appears on splash screen.
    expect(find.text(AppConstants.appName), findsWidgets);
    await tester.pump(const Duration(milliseconds: 100));
  });

  testWidgets('LoginScreen citizen sign-in verification test', (WidgetTester tester) async {
    await tester.pumpWidget(const JanMitraApp(homeOverride: LoginScreen()));

    // Verify login screen elements
    expect(find.text('Citizen Sign In'), findsOneWidget);
    expect(find.text('Get OTP'), findsOneWidget);
    expect(find.text('Citizen Privacy Commitment'), findsOneWidget);
  });

  testWidgets('HomeScreen Phase 3 citizen status verification test', (WidgetTester tester) async {
    await tester.pumpWidget(const JanMitraApp(homeOverride: HomeScreen()));

    // Verify home screen elements
    expect(find.text(AppConstants.appName), findsWidgets);
    expect(find.text('Citizen User'), findsOneWidget);
    expect(find.text(AppConstants.placeholderMessage), findsOneWidget);
  });
}

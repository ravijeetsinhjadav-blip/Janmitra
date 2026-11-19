import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'core/constants/app_constants.dart';
import 'core/theme/app_theme.dart';
import 'features/auth/presentation/screens/login_screen.dart';
import 'features/auth/presentation/screens/register_screen.dart';
import 'features/auth/presentation/screens/reset_password_screen.dart';
import 'features/auth/presentation/screens/splash_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const JanMitraApp());
}

class JanMitraApp extends StatelessWidget {
  final Widget? homeOverride;

  const JanMitraApp({super.key, this.homeOverride});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: AppConstants.appName,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      home: homeOverride ?? const SplashScreen(),
      onGenerateRoute: (settings) {
        final uri = Uri.parse(settings.name ?? '/');
        if (uri.path == '/reset-password' || (uri.scheme == 'janmitra' && uri.host == 'reset-password')) {
          final queryToken = uri.queryParameters['token'] ??
              (kIsWeb ? Uri.base.queryParameters['token'] : null);
          final argToken = settings.arguments is String ? settings.arguments as String : null;
          final token = queryToken ?? argToken;
          return MaterialPageRoute(
            builder: (_) => ResetPasswordScreen(initialToken: token),
            settings: settings,
          );
        }
        if (uri.path == '/login') {
          return MaterialPageRoute(
            builder: (_) => const LoginScreen(),
            settings: settings,
          );
        }
        if (uri.path == '/register') {
          return MaterialPageRoute(
            builder: (_) => const RegisterScreen(),
            settings: settings,
          );
        }
        return null;
      },
    );
  }
}

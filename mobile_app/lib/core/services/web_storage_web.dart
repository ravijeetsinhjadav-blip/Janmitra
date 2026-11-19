// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use
import 'dart:html' as html;

/// Web implementation for non-sensitive browser storage.
/// Strictly enforces security boundary: sensitive authentication tokens
/// (access_token, refresh_token) are NEVER persisted in browser localStorage.
class WebStorageHelper {
  static const Set<String> _sensitiveKeys = {
    'janmitra_access_token',
    'janmitra_refresh_token',
  };

  static void setItem(String key, String value) {
    if (_sensitiveKeys.contains(key)) {
      // Prohibit sensitive JWT credentials from being stored in localStorage
      return;
    }
    try {
      html.window.localStorage[key] = value;
    } catch (_) {}
  }

  static String? getItem(String key) {
    if (_sensitiveKeys.contains(key)) {
      return null;
    }
    try {
      return html.window.localStorage[key];
    } catch (_) {
      return null;
    }
  }

  static void removeItem(String key) {
    try {
      html.window.localStorage.remove(key);
    } catch (_) {}
  }
}

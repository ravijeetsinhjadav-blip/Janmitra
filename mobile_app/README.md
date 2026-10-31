# JanMitra Assist - Mobile Application (Flutter)

Citizen-facing mobile client for **JanMitra Assist – AI-Powered Government Service Eligibility and Document Intelligence System**.

## Prerequisites

1. **Flutter SDK**: Version 3.24.0 or newer ([flutter.dev](https://flutter.dev/docs/get-started/install/windows)).
2. **Android SDK / Android Studio**: Android Studio with Android SDK Platform 34 and Android Emulator.
3. **Dart SDK**: Included with Flutter SDK.

## Project Structure

```
mobile_app/
├── android/            # Native Android platform configuration
├── assets/             # Images, icons, and static assets
├── lib/
│   ├── main.dart       # App entry point
│   ├── core/           # App-wide themes, constants, network configs
│   │   ├── constants/
│   │   ├── network/
│   │   └── theme/
│   └── features/       # Feature modules
│       ├── home/       # Launch and home screen
│       ├── schemes/    # Phase 2 module
│       ├── documents/  # Phase 3 module
│       ├── eligibility/# Phase 4 module
│       └── readiness/  # Phase 5 module
├── test/               # Widget and unit tests
├── pubspec.yaml        # Flutter project dependencies
└── .env.example        # Environment variable template
```

## Running the App

### 1. Install dependencies
```powershell
flutter pub get
```

### 2. Verify environment
```powershell
flutter doctor
```

### 3. Run on connected Android device / emulator
```powershell
flutter run
```

### 4. Run tests
```powershell
flutter test
```

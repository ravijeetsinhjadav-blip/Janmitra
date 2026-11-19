import 'package:flutter_test/flutter_test.dart';
import 'package:janmitra_assist/main.dart';
import 'package:janmitra_assist/features/home/presentation/screens/home_screen.dart';
import 'package:janmitra_assist/features/schemes/models/scheme_models.dart';
import 'package:janmitra_assist/features/schemes/presentation/eligibility_result_screen.dart';
import 'package:janmitra_assist/features/schemes/presentation/scheme_details_screen.dart';
import 'package:janmitra_assist/features/schemes/presentation/scheme_discovery_screen.dart';

void main() {
  final sampleScheme = SchemeModel(
    id: '11111111-1111-1111-1111-111111111111',
    schemeName: '[DEMO] Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)',
    shortDescription:
        'Direct income support of ₹6,000 per year for farmer families.',
    description:
        'PM-KISAN is a central sector scheme to augment the income of landholding farmers.',
    department: 'Ministry of Agriculture and Farmers Welfare',
    category: 'Agriculture',
    stateApplicability: 'All India',
    eligibilitySummary:
        'All landholding farmer families having cultivable land in their names.',
    benefits: [
      'Financial benefit of ₹6,000 per year per family',
      'Paid in three equal installments of ₹2,000 every 4 months',
    ],
    eligibilityCriteria: [
      EligibilityConditionModel(
        conditionName: 'Agricultural Occupation',
        field: 'occupation',
        operator: 'contains',
        expectedValue: 'farmer',
        explanation: 'Must be engaged in farming cultivation.',
      ),
    ],
    requiredProfileFields: ['occupation', 'state', 'residence_type'],
    applicationProcess: [
      'Visit the official PM-KISAN portal',
      'Complete Farmer Corner registration',
    ],
    requiredDocuments: [
      'Landholding ownership records (Khata/Khasra)',
      'Bank passbook copy',
    ],
    officialSourceUrl: 'https://pmkisan.gov.in/',
    officialApplicationUrl: 'https://pmkisan.gov.in/RegistrationFormNew.aspx',
    status: 'active',
    isDemoData: true,
  );

  final sampleAssessment = AssessmentResultModel(
    assessmentId: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    schemeId: sampleScheme.id,
    schemeName: sampleScheme.schemeName,
    category: sampleScheme.category,
    overallStatus: 'Potentially Eligible',
    criteriaMatchPercentage: 100.0,
    overallReadinessScore: 100.0,
    scoreInterpretation:
        'Criteria Match Percentage indicates that 1 of 1 conditions (100.0%) are satisfied.',
    conditionsBreakdown: [
      ConditionEvaluationModel(
        conditionName: 'Agricultural Occupation',
        field: 'occupation',
        operator: 'contains',
        expectedValue: 'farmer',
        actualValue: 'Agricultural farmer',
        status: 'satisfied',
        explanation: 'Must be engaged in farming cultivation.',
      ),
    ],
    satisfiedCount: 1,
    notSatisfiedCount: 0,
    unknownCount: 0,
    missingFields: [],
    officialSourceUrl: sampleScheme.officialSourceUrl,
    officialApplicationUrl: sampleScheme.officialApplicationUrl,
    evaluatedAt: '2026-10-31T14:00:00Z',
    advisoryDisclaimer:
        'This assessment is strictly advisory and does not constitute official government approval or rejection.',
  );

  testWidgets('SchemeDiscoveryScreen UI elements test',
      (WidgetTester tester) async {
    await tester
        .pumpWidget(const JanMitraApp(homeOverride: SchemeDiscoveryScreen()));
    await tester.pump();

    // Verify search and category controls
    expect(find.text('Government Schemes'), findsOneWidget);
    expect(find.text('State Scope:'), findsOneWidget);
    expect(
        find.text('Search schemes by keyword or ministry...'), findsOneWidget);
  });

  testWidgets(
      'SchemeDetailsScreen displays complete information and check button',
      (WidgetTester tester) async {
    await tester.pumpWidget(JanMitraApp(
      homeOverride: SchemeDetailsScreen(scheme: sampleScheme),
    ));
    await tester.pump();

    // Verify scheme details
    expect(find.text(sampleScheme.schemeName), findsWidgets);
    expect(find.text(sampleScheme.department), findsOneWidget);
    expect(find.text('Agriculture'), findsOneWidget);
    expect(find.text('All India'), findsOneWidget);
    expect(find.text('Key Benefits'), findsOneWidget);
    expect(find.text('Check My Eligibility'), findsOneWidget);
  });

  testWidgets(
      'EligibilityResultScreen displays advisory determination and breakdown',
      (WidgetTester tester) async {
    await tester.pumpWidget(JanMitraApp(
      homeOverride: EligibilityResultScreen(assessment: sampleAssessment),
    ));
    await tester.pump();

    // Verify result screen
    expect(find.text('Advisory Eligibility Result'), findsOneWidget);
    expect(find.text('Potentially Eligible'), findsOneWidget);
    expect(find.text(sampleAssessment.advisoryDisclaimer), findsOneWidget);
    expect(find.text('100%'), findsOneWidget);
    expect(find.text('Agricultural Occupation'), findsOneWidget);
    expect(find.text('Official Government Portal'), findsOneWidget);
  });

  testWidgets('HomeScreen Phase 4 scheme discovery card verification test',
      (WidgetTester tester) async {
    await tester.pumpWidget(const JanMitraApp(homeOverride: HomeScreen()));
    await tester.pump();

    // Verify Phase 4 active card on home screen
    expect(find.text('Explore Welfare Schemes'), findsOneWidget);
    expect(find.text('Browse All Schemes'), findsOneWidget);
    expect(find.text('My Matches'), findsOneWidget);
    expect(find.text('Assessments'), findsOneWidget);
  });
}

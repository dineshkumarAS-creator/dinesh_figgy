import 'package:flutter/material.dart';
import 'package:figgy_app/theme/registration_theme.dart';
import 'package:figgy_app/app/main_wrapper.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:razorpay_flutter/razorpay_flutter.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:figgy_app/config/api_base_url.dart';
// Removed dart:js import
import 'package:figgy_app/services/wallet_service.dart';
import 'package:figgy_app/services/razorpay_web_checkout.dart';

class RegistrationScreen extends StatefulWidget {
  final int initialStep;
  final bool isReactivation;
  const RegistrationScreen({super.key, this.initialStep = 0, this.isReactivation = false});

  @override
  State<RegistrationScreen> createState() => _RegistrationScreenState();
}

class _RegistrationScreenState extends State<RegistrationScreen> {
  final PageController _pageController = PageController();
  int _currentStep = 0;
  Razorpay? _razorpay;

  // Step 1: Language
  String _selectedLanguage = 'English';
  bool _locationConsent = false;

  // Step 2: Existing Form
  final TextEditingController _swiggyIdController = TextEditingController();
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _phoneController = TextEditingController();
  final TextEditingController _deliveriesController = TextEditingController();
  final TextEditingController _earningsController = TextEditingController();
  
  String _selectedPlatform = 'Swiggy';
  String _selectedZone = 'North';
  double _workingHours = 8.0;
  bool _isLoading = false;
  bool _isVerifying = false;
  bool _isVerified = false;

  // Step 2 Additions: UPI
  final TextEditingController _upiController = TextEditingController();
  bool _isUpiVerifying = false;
  bool _isUpiVerified = false;

  // Step 3: Tiers
  String _selectedTier = 'Smart'; // 'Lite', 'Smart', 'Elite'

  // Step 4: Terms
  bool _termsAgreed = false;
  List<dynamic> _termsSections = [];
  bool _isLoadingTerms = false;

  final String _baseUrl = figgyApiBaseUrl;

  static const Map<String, Map<String, String>> _dict = {
    'English': {
      'title': 'WORKER REGISTRATION',
      'hero_title': 'Protect Earnings',
      'hero_sub': 'Rain, heat & pollution cover for gig workers – just ₹80/week!',
      'select_lang': 'Select your preferred language',
      'enable_loc': 'Enable Location Access',
      'req_loc': 'Required to track local weather correctly',
      'continue': 'CONTINUE',
      'verify_ident': 'Verify Identity',
      'swiggy_id': 'SWIGGY ID / PHONE',
      'verify_btn': 'VERIFY',
      'verified_btn': 'VERIFIED',
      'acct_info': 'Account Information',
      'full_name': 'FULL NAME',
      'phone_num': 'PHONE NUMBER',
      'del_plat': 'DELIVERY PLATFORM',
      'zone': 'PRIMARY WORKING ZONE',
      'hours': 'DAILY WORKING HOURS',
      'deliv': 'WEEKLY DELIVERIES',
      'earn': 'WEEKLY EARNINGS',
      'pay_claim': 'Payout & Claims',
      'upi_id': 'UPI ID (For Instant Payouts)',
      'linked': 'LINKED',
      'test_1': 'TEST ₹1',
      'continue_plans': 'CONTINUE TO PLANS',
      'ai_rec': 'AI recommends the Smart Tier based on your',
      'ai_rec2': 'zone weather forecast.',
      'one_tap': 'ONE-TAP ACTIVATE',
      'hr': 'hrs',
      'terms_title': 'Terms & Conditions',
      'terms_sub': 'GigShield Weekly Insurance',
      'terms_intro': 'This is a parametric insurance that provides income protection during extreme conditions.',
      'agree_terms': 'I agree to the Terms & Conditions',
      'pay_activate': 'Pay & Activate',
      'download_pdf': 'Download PDF',
      'trust_note': 'Powered by verified weather & data sources',
      'continue_terms': 'CONTINUE TO TERMS',
      'i_agree': 'I agree',
      'activate_policy': 'Activate Policy',
      'final_step': 'Final Step',
      'payout_info': 'Setup Payout Method',
      'enter_upi': 'Enter your UPI ID to activate the policy',
      'secure_activation': 'Secure Activation',
      'activate_now': 'ACTIVATE NOW',
      'success_title': 'Policy Activated!',
      'success_sub': 'Your coverage is now live.',
      'terms_full_header': 'GIGSHIELD PARAMETRIC INSURANCE TERMS AND CONDITIONS',
      'effective_date': 'Effective Date: March 2026',
      'version_txt': 'Version: 1.0',
    },
    'Hindi': {
      'title': 'कार्यकर्ता पंजीकरण',
      'hero_title': 'कमाई सुरक्षित करें',
      'hero_sub': 'गिग वर्कर्स के लिए बारिश, गर्मी और प्रदूषण कवर - मात्र ₹80/सप्ताह!',
      'select_lang': 'अपनी पसंदीदा भाषा चुनें',
      'enable_loc': 'स्थान पहुंच सक्षम करें',
      'req_loc': 'स्थानीय मौसम ट्रैक करने के लिए आवश्यक',
      'continue': 'जारी रखें',
      'verify_ident': 'पहचान सत्यापित करें',
      'swiggy_id': 'स्विगी आईडी / फोन',
      'verify_btn': 'सत्यापित करें',
      'verified_btn': 'सत्यापित',
      'acct_info': 'खाता जानकारी',
      'full_name': 'पूरा नाम',
      'phone_num': 'फ़ोन नंबर',
      'del_plat': 'डिलीवरी प्लेटफॉर्म',
      'zone': 'प्राथमिक कार्य क्षेत्र',
      'hours': 'दैनिक कार्य के घंटे',
      'deliv': 'साप्ताहिक डिलीवरी',
      'earn': 'साप्ताहिक कमाई',
      'pay_claim': 'भुगतान और दावे',
      'upi_id': 'यूपीआई आईडी',
      'linked': 'लिंक किया गया',
      'test_1': 'टेस्ट ₹1',
      'continue_plans': 'प्लान पर जारी रखें',
      'ai_rec': 'AI आपके',
      'ai_rec2': 'क्षेत्र के मौसम के आधार पर स्मार्ट टियर की सिफारिश करता है।',
      'one_tap': 'वन-टैप चालू करें',
      'hr': 'घंटे',
      'terms_title': 'नियम और शर्तें',
      'terms_sub': 'GigShield साप्ताहिक बीमा',
      'agree_terms': 'मैं नियमों और शर्तों से सहमत हूँ',
      'pay_activate': 'भुगतान करें और सक्रिय करें',
      'download_pdf': 'पीडीएफ डाउनलोड करें',
      'trust_note': 'सत्यापित मौसम और डेटा स्रोतों द्वारा संचालित',
      'continue_terms': 'शर्तों पर जारी रखें',
      'i_agree': 'मैं सहमत हूँ',
      'activate_policy': 'बीमा सक्रिय करें',
      'final_step': 'अंतिम चरण',
      'payout_info': 'पेआउट विधि सेटअप करें',
      'enter_upi': 'पॉलिसी सक्रिय करने के लिए अपना यूपीआई आईडी दर्ज करें',
      'secure_activation': 'सुरक्षित सक्रियण',
      'activate_now': 'अभी सक्रिय करें',
      'success_title': 'बीमा सक्रिय हो गया!',
      'success_sub': 'आपका कवरेज अब लाइव है।',
      'terms_full_header': 'GIGSHIELD पैरामेट्रिक बीमा नियम और शर्तें',
      'effective_date': 'प्रभावी तिथि: मार्च 2026',
      'version_txt': 'संस्करण: 1.0',
    },
    'Marathi': {
      'title': 'कामगार नोंदणी',
      'hero_title': 'कमाई सुरक्षित करा',
      'hero_sub': 'पाऊस, उष्णता आणि प्रदूषण कव्हर - फक्त ₹80/आठवडा!',
      'select_lang': 'तुमची आवडती भाषा निवडा',
      'enable_loc': 'स्थान प्रवेश सक्षम करा',
      'req_loc': 'हवामानाचा मागोवा घेण्यासाठी आवश्यक',
      'continue': 'पुढे जा',
      'verify_ident': 'ओळख सत्यापित करा',
      'swiggy_id': 'स्विगी आयडी / फोन',
      'verify_btn': 'सत्यापित करा',
      'verified_btn': 'सत्यापित',
      'acct_info': 'खाते माहिती',
      'full_name': 'पूर्ण नाव',
      'phone_num': 'फोन नंबर',
      'del_plat': 'डिलिव्हरी प्लॅटफॉर्म',
      'zone': 'प्राथमिक कार्य क्षेत्र',
      'hours': 'दैनिक कामाचे तास',
      'deliv': 'साप्ताहिक वितरण',
      'earn': 'साप्ताहिक कमाई',
      'pay_claim': 'पेआउट आणि दावे',
      'upi_id': 'UPI आयडी (झटपट पेआउटसाठी)',
      'linked': 'लिंक केले',
      'test_1': 'चाचणी ₹1',
      'continue_plans': 'प्लॅनवर पुढे जा',
      'ai_rec': 'AI तुमच्या',
      'ai_rec2': 'हवामानाच्या अंदाजानुसार स्मार्ट टियर सुचवतो.',
      'one_tap': 'वन-टॅप सक्रिय करा',
      'hr': 'तास',
      'terms_title': 'नियम आणि अटी',
      'terms_sub': 'GigShield साप्ताहिक विमा',
      'terms_intro': 'हे एक पॅरामीट्रिक विमा आहे जो विषम परिस्थितीत उत्पन्न संरक्षण प्रदान करतो.',
      'agree_terms': 'मी नियम आणि अटींशी सहमत आहे',
      'pay_activate': 'देय द्या आणि सक्रिय करा',
      'download_pdf': 'पीडीएफ डाउनलोड करा',
      'trust_note': 'सत्यापित हवामान आणि डेटा स्रोतांद्वारे समर्थित',
      'continue_terms': 'अटींवर पुढे जा',
    },
    'Tamil': {
      'title': 'பணியாளர் பதிவு',
      'hero_title': 'வருமானத்தைப் பாதுகாக்கவும்',
      'hero_sub': 'மழை, வெப்பம் மற்றும் மாசு காப்பீடு - ₹80/வாரம்!',
      'select_lang': 'தங்கள் மொழியைத் தேர்ந்தெடுக்கவும்',
      'enable_loc': 'இருப்பிட அணுகலை இயக்கு',
      'req_loc': 'வானிலையைக் கண்காணிக்க தேவை',
      'continue': 'தொடரவும்',
      'verify_ident': 'அடையாளத்தை சரிபார்க்கவும்',
      'swiggy_id': 'ஸ்விக்கி ஐடி / தொலைபேசி',
      'verify_btn': 'சரிபார்க்கவும்',
      'verified_btn': 'சரிபார்க்கப்பட்டது',
      'acct_info': 'கணக்கு தகவல்',
      'full_name': 'முழு பெயர்',
      'phone_num': 'தொலைபேசி எண்',
      'del_plat': 'டெலிவரி தளம்',
      'zone': 'முதன்மை வேலை மண்டலம்',
      'hours': 'தினசரி வேலை நேரம்',
      'deliv': 'வாராந்திர டெலிவரிகள்',
      'earn': 'வாராந்திர வருமானம்',
      'pay_claim': 'பணம் செலுத்துதல் & உரிமைகோரல்கள்',
      'upi_id': 'UPI ஐடி',
      'linked': 'இணைக்கப்பட்டது',
      'test_1': 'சோதனை ₹1',
      'continue_plans': 'திட்டங்களுக்குத் தொடரவும்',
      'ai_rec': 'உங்கள்',
      'ai_rec2': 'பகுதியின் அடிப்படையில் AI ஸ்மார்ட் அடுக்கை பரிந்துரைக்கிறது.',
      'one_tap': 'செயல்படுத்து',
      'hr': 'மணி',
      'terms_title': 'விதிமுறைகள் மற்றும் நிபந்தனைகள்',
      'terms_sub': 'GigShield வாராந்திர காப்பீடு',
      'terms_intro': 'இது ஒரு பாராமெட்ரிக் காப்பீடு ஆகும், இது மோசமான சூழ்நிலைகளில் வருமானப் பாதுகாப்பை வழங்குகிறது.',
      'agree_terms': 'விதிமுறைகள் மற்றும் நிபந்தனைகளை நான் ஒப்புக்கொள்கிறேன்',
      'pay_activate': 'பணம் செலுத்தி செயல்படுத்தவும்',
      'download_pdf': 'PDF பதிவிறக்கம்',
      'trust_note': 'சரிபார்க்கப்பட்ட வானிலை மற்றும் தரவு ஆதாரங்கள் மூலம் இயக்கப்படுகிறது',
      'continue_terms': 'விதிமுறைகளுக்குத் தொடரவும்',
    },
  };

  String _t(String key) {
    return _dict[_selectedLanguage]?[key] ?? _dict['English']![key]!;
  }

  String _tEn(String key) {
    return _dict['English']![key]!;
  }

  @override
  void initState() {
    super.initState();
    if (!kIsWeb) {
      _razorpay = Razorpay();
      _razorpay!.on(Razorpay.EVENT_PAYMENT_SUCCESS, _handlePaymentSuccess);
      _razorpay!.on(Razorpay.EVENT_PAYMENT_ERROR, _handlePaymentError);
      _razorpay!.on(Razorpay.EVENT_EXTERNAL_WALLET, _handleExternalWallet);
    }
    
    _currentStep = widget.isReactivation ? 2 : widget.initialStep; // Start at Plans (index 2) for reactivation
    
    if (widget.isReactivation) {
       _loadReactivationProfile();
    }

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_currentStep > 0) {
        _pageController.jumpToPage(_currentStep);
      }
    });
  }

  Future<void> _loadReactivationProfile() async {
    final prefs = await SharedPreferences.getInstance();
    final workerId = prefs.getString('worker_id') ?? '';
    if (workerId.isNotEmpty) {
      _swiggyIdController.text = workerId;
      _upiController.text = 'worker@upi'; // Mock pre-fill
      _isUpiVerified = true;
      _fetchMockData(); // Pre-load Ravi's data
    }
  }

  @override
  void dispose() {
    _razorpay?.clear();
    _pageController.dispose();
    _swiggyIdController.dispose();
    _nameController.dispose();
    _phoneController.dispose();
    _deliveriesController.dispose();
    _earningsController.dispose();
    _upiController.dispose();
    super.dispose();
  }

  void _nextStep() {
    if (_currentStep < 4) { // Step 0 to 4 (5 total)
      if (widget.isReactivation && _currentStep == 2) {
        // From Plan selection directly to Payment (Step 5 in PageView index 3)
        // Ensure price visibility
        _showTermsBottomSheet();
        return;
      }
      if (_currentStep == 1 && (!_isVerifying && !_isVerified)) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Please verify your Swiggy ID before continuing.')));
        return;
      }
      if (_currentStep == 2) {
        _showTermsBottomSheet();
        return;
      }
      setState(() => _currentStep++);
      _pageController.nextPage(duration: const Duration(milliseconds: 300), curve: Curves.easeInOut);
    }
  }

  void _prevStep() {
    if (_currentStep > 0) {
      setState(() => _currentStep--);
      _pageController.previousPage(duration: const Duration(milliseconds: 300), curve: Curves.easeInOut);
    } else {
      Navigator.pop(context);
    }
  }

  Future<void> _fetchMockData() async {
    if (_swiggyIdController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Please enter your Swiggy ID first')));
      return;
    }
    setState(() => _isVerifying = true);
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/worker/fetch'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({"swiggy_id": _swiggyIdController.text}),
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body)['data'];
        setState(() {
          _nameController.text = data['name'] ?? '';
          _phoneController.text = data['phone'] ?? '';
          _selectedPlatform = data['platform'] ?? 'Swiggy';
          _selectedZone = data['zone'] ?? 'North';
          _workingHours = (data['daily_hours'] ?? 8.0).toDouble();
          _deliveriesController.text = data['weekly_deliveries']?.toString() ?? '';
          _earningsController.text = data['weekly_earnings']?.toString() ?? '';
          _isVerified = true;
        });
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Profile Verified & Imported!'), backgroundColor: Colors.blue));
      } else {
        throw Exception('Failed to fetch profile');
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Verification Failed: $e'), backgroundColor: Colors.orange));
    } finally {
      if (mounted) setState(() => _isVerifying = false);
    }
  }

  Future<void> _verifyUpi() async {
    if (_upiController.text.isEmpty) return;
    setState(() => _isUpiVerifying = true);
    await Future.delayed(const Duration(seconds: 2));
    if (mounted) {
      setState(() { _isUpiVerifying = false; _isUpiVerified = true; });
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('₹1 Test Drop Successful! Bank Linked.'), backgroundColor: Colors.green));
    }
  }

  Future<void> _fetchTerms() async {
    setState(() => _isLoadingTerms = true);
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/terms/current?language=$_selectedLanguage'),
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body)['data'];
        setState(() {
          _termsSections = data['sections'];
        });
      }
    } catch (e) {
      debugPrint('Error fetching terms: $e');
      // Fallback handled in UI
    } finally {
      setState(() => _isLoadingTerms = false);
    }
  }

  Future<void> _initiatePayment() async {
    if (!_isVerified || !_isUpiVerified) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Please completely verify identity and UPI first.')));
      return;
    }

    setState(() => _isLoading = true);
    int price = _selectedTier == 'Lite' ? 49 : (_selectedTier == 'Smart' ? 68 : 99);

    try {
      if (kIsWeb) {
        final response = await http.post(
          Uri.parse('$_baseUrl/api/payment/create_order'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({"amount": price}),
        ).timeout(const Duration(seconds: 15));

        final responseBody = jsonDecode(response.body);
        if (response.statusCode != 200 || responseBody['status'] != 'success') {
          throw Exception(responseBody['message'] ?? 'Backend failed to create order');
        }

        final keyId = (responseBody['key_id'] ?? '').toString();
        if (keyId.isEmpty || keyId == 'rzp_test_demo_key') {
          throw Exception('Razorpay keys are not configured on backend');
        }

        if (mounted) setState(() => _isLoading = false);

        final webResult = await openRazorpayWebCheckout({
          'key': keyId,
          'amount': responseBody['amount'],
          'name': 'Figgy GigShield',
          'description': '$_selectedTier Tier Insurance',
          'order_id': responseBody['order_id'],
          'prefill': {
            'contact': _phoneController.text,
            'email': 'gigworker@figgy.com',
          },
          'theme': {'color': '#0F172A'}
        });

        await _finalizePaymentAndRegister(
          paymentId: (webResult['razorpay_payment_id'] ?? '').toString(),
          orderId: (webResult['razorpay_order_id'] ?? '').toString(),
          signature: (webResult['razorpay_signature'] ?? '').toString(),
        );
        return;
      }

      // Payment Flow (Real mode only)
      debugPrint('Initiating Payment API Call to $_baseUrl...');

      final response = await http.post(
        Uri.parse('$_baseUrl/api/payment/create_order'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({"amount": price}),
      ).timeout(const Duration(seconds: 15));

      debugPrint('Create Order Response: \${response.statusCode} - \${response.body}');
      final responseBody = jsonDecode(response.body);

      if (response.statusCode == 200 && responseBody['status'] == 'success') {
        final keyId = (responseBody['key_id'] ?? '').toString();
        // Backend returns demo key when Razorpay env keys are not configured.
        if (keyId == 'rzp_test_demo_key') {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Payment gateway not configured on backend. Add Razorpay keys and try again.'),
                backgroundColor: Colors.red,
              ),
            );
            setState(() => _isLoading = false);
          }
          return;
        }

        var options = {
          'key': keyId,
          'amount': responseBody['amount'],
          'name': 'Figgy GigShield',
          'description': '$_selectedTier Tier Insurance',
          'order_id': responseBody['order_id'],
          'prefill': {
            'contact': _phoneController.text,
            'email': 'gigworker@figgy.com'
          },
          'theme': {'color': '#0F172A'}
        };

        // Turn off spinner BEFORE opening modal to prevent infinite loading
        // if modal fails to launch or if user closes it ungracefully.
        if (mounted) setState(() => _isLoading = false);

        debugPrint('Opening Razorpay Payment interface...');
        try {
          _razorpay!.open(options);
        } catch (e) {
          throw Exception('Failed to launch checkout widget: $e');
        }
      } else {
        throw Exception(responseBody['message'] ?? 'Backend failed to create order');
      }
    } catch (e) {
      debugPrint('Create Order Error: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('API Error: $e'), backgroundColor: Colors.red));
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _handlePaymentSuccess(PaymentSuccessResponse response) async {
    debugPrint('Payment Successful! Signature: \${response.signature}');
    await _finalizePaymentAndRegister(
      paymentId: (response.paymentId ?? '').toString(),
      orderId: (response.orderId ?? '').toString(),
      signature: (response.signature ?? '').toString(),
    );
  }

  Future<void> _finalizePaymentAndRegister({
    required String paymentId,
    required String orderId,
    required String signature,
  }) async {
    setState(() => _isLoading = true);
    try {
      debugPrint('Calling verification API...');
      final verifyResponse = await http.post(
        Uri.parse('$_baseUrl/api/payment/verify'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          "razorpay_payment_id": paymentId,
          "razorpay_order_id": orderId,
          "razorpay_signature": signature,
        }),
      ).timeout(const Duration(seconds: 15));

      final verifyBody = jsonDecode(verifyResponse.body);
      debugPrint('Verify Response: \${verifyResponse.statusCode} - \${verifyResponse.body}');

      if (verifyResponse.statusCode == 200 && verifyBody['status'] == 'success') {
        final int premiumInr = _selectedTier == 'Lite' ? 49 : (_selectedTier == 'Smart' ? 68 : 99);
        await WalletService().addTransaction(
          WalletTransaction(
            id: 'premium_${orderId.isNotEmpty ? orderId : paymentId}',
            amountInr: -premiumInr,
            reason: 'GigShield premium paid ($_selectedTier)',
            category: 'premium',
            createdAt: DateTime.now(),
            refId: orderId.isNotEmpty ? orderId : paymentId,
          ),
        );
        await _handleRegistration();
      } else {
        throw Exception(verifyBody['message'] ?? 'Payment verification failed at backend.');
      }
    } catch (e) {
      debugPrint('Verification/Registration Error: $e');
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Finalization Error: $e'), backgroundColor: Colors.red));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _handlePaymentError(PaymentFailureResponse response) {
    debugPrint('Payment Sheet Failed or Dismissed: \${response.message}');
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Payment Canceled or Failed: \${response.message}'), backgroundColor: Colors.orange));
      setState(() => _isLoading = false);
    }
  }

  void _handleExternalWallet(ExternalWalletResponse response) {
    debugPrint('External Wallet Chosen: \${response.walletName}');
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('External Wallet Flow Selected: \${response.walletName}')));
      setState(() => _isLoading = false);
    }
  }

  Future<void> _handleRegistration() async {
    // Note: Called only after payment success in production
    if (!_isVerified || !_isUpiVerified) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Please completely verify identity and UPI first.')));
      return;
    }

    setState(() => _isLoading = true);

    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/worker/register'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          "name": _nameController.text,
          "phone": _phoneController.text,
          "platform": _selectedPlatform,
          "zone": _selectedZone,
          "daily_hours": _workingHours.toInt(),
          "weekly_deliveries": int.tryParse(_deliveriesController.text) ?? 100,
          "avg_daily_earnings": (int.tryParse(_earningsController.text.replaceAll(RegExp(r'[^0-9]'), '')) ?? 5000) ~/ 7,
          "weekly_earnings": int.tryParse(_earningsController.text.replaceAll(RegExp(r'[^0-9]'), '')) ?? 5000,
          "swiggy_id": _swiggyIdController.text.isEmpty ? _nameController.text.replaceAll(' ', '_') : _swiggyIdController.text,
        }),
      );

      final responseBody = jsonDecode(response.body);

      if (response.statusCode == 201) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setBool('has_onboarded', true);
        await prefs.setString('worker_id', responseBody['worker_id'] ?? '');
        await prefs.setString('selected_tier', _selectedTier);
        await prefs.setString('policy_status', 'active');
        debugPrint("Registration Success: Saved tier=$_selectedTier, status=active");
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Worker Registered Successfully! Coverage Active.'), backgroundColor: Colors.green));
          Navigator.pushAndRemoveUntil(context, MaterialPageRoute(builder: (_) => const MainWrapper()), (route) => false);
        }
      } else {
        throw Exception(responseBody['message'] ?? 'Failed to register');
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Registration Error: $e'), backgroundColor: Colors.red));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        elevation: 0,
        centerTitle: true,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: AppColors.textPrimary, size: 20),
          onPressed: _prevStep,
        ),
        title: Text(
          widget.isReactivation ? 'REACTIVATE PROTECTION' : '${_tEn('title')} (${_currentStep + 1}/4)', 
          style: AppTypography.small.copyWith(letterSpacing: 1.0, color: AppColors.textSecondary, fontWeight: FontWeight.bold)
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16.0),
            child: CircleAvatar(
              backgroundColor: AppColors.brandPrimary.withOpacity(0.1),
              radius: 18,
              child: const Icon(Icons.person, color: AppColors.brandPrimary, size: 20),
            ),
          ),
        ],
      ),
      body: LayoutBuilder(
        builder: (context, constraints) {
          final double hp = constraints.maxWidth > 600 ? constraints.maxWidth * 0.2 : 24.0;
          return PageView(
            controller: _pageController,
            physics: const NeverScrollableScrollPhysics(),
            children: [
              _buildStep1(hp),
              _buildStep2(hp),
              _buildStep3(hp),
              _buildStep5(hp), // New Step 5 (UPI Activation)
            ],
          );
        },
      ),
    );
  }

  // ─── STEP 1: LANGUAGE SELECTION ───────────────────────────────────────────
  Widget _buildStep1(double horizontalPadding) {
    return SingleChildScrollView(
      padding: EdgeInsets.symmetric(horizontal: horizontalPadding, vertical: 32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeroCard(),
          const SizedBox(height: 48),
          Text(_t('select_lang'), style: AppTypography.h3),
          const SizedBox(height: 24),
          _buildLanguageOption('English', 'English'),
          const SizedBox(height: 12),
          _buildLanguageOption('हिंदी', 'Hindi'),
          const SizedBox(height: 12),
          _buildLanguageOption('मराठी', 'Marathi'),
          const SizedBox(height: 12),
          _buildLanguageOption('தமிழ்', 'Tamil'),
          const SizedBox(height: 48),
          Container(
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: _locationConsent ? AppColors.brandPrimary : AppColors.border, width: _locationConsent ? 2 : 1),
            ),
            child: SwitchListTile(
              title: Text(_t('enable_loc'), style: AppTypography.bodyMedium.copyWith(fontWeight: FontWeight.w800)),
              subtitle: Text(_t('req_loc'), style: AppTypography.small),
              value: _locationConsent,
              onChanged: (val) => setState(() => _locationConsent = val),
              activeColor: AppColors.brandPrimary,
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            ),
          ),
          const SizedBox(height: 32),
          SizedBox(
            width: double.infinity,
            height: 60,
            child: ElevatedButton(
              onPressed: _locationConsent ? _nextStep : null,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.brandPrimary,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                elevation: 0,
              ),
              child: Text(_t('continue'), style: AppTypography.bodyLarge.copyWith(color: Colors.white, fontWeight: FontWeight.w900, letterSpacing: 1.0)),
            ),
          ),
          const SizedBox(height: 32),
          _buildFooter(),
        ],
      ),
    );
  }

  Widget _buildLanguageOption(String title, String value) {
    bool isSelected = _selectedLanguage == value;
    return InkWell(
      onTap: () => setState(() => _selectedLanguage = value),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.brandPrimary.withOpacity(0.1) : AppColors.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: isSelected ? AppColors.brandPrimary : AppColors.border),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(title, style: AppTypography.bodyLarge.copyWith(fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600, color: isSelected ? AppColors.brandPrimary : AppColors.textPrimary)),
            if (isSelected) const Icon(Icons.check_circle_rounded, color: AppColors.brandPrimary),
            if (!isSelected) Icon(Icons.circle_outlined, color: AppColors.border.withOpacity(0.8)),
          ],
        ),
      ),
    );
  }

  // ─── STEP 2: ORIGINAL FORM + UPI DROP ─────────────────────────────────────
  Widget _buildStep2(double horizontalPadding) {
    return SingleChildScrollView(
      padding: EdgeInsets.symmetric(horizontal: horizontalPadding, vertical: 32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(AppStyles.borderRadius),
              border: Border.all(color: AppColors.border),
              boxShadow: AppStyles.softShadow,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(_t('verify_ident'), style: AppTypography.h3),
                const SizedBox(height: 16),
                _buildLabel('swiggy_id'),
                Row(
                  children: [
                    Expanded(
                      child: _buildTextField(
                        controller: _swiggyIdController,
                        icon: Icons.badge_outlined,
                        hint: 'e.g. SWG12345',
                        onChanged: (val) => setState(() => _isVerified = false),
                      ),
                    ),
                    const SizedBox(width: 12),
                    SizedBox(
                      height: 54,
                      child: ElevatedButton(
                        onPressed: _isVerifying ? null : _fetchMockData,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: _isVerified ? Colors.green : AppColors.brandPrimary.withOpacity(0.1),
                          foregroundColor: _isVerified ? Colors.white : AppColors.brandPrimary,
                          elevation: 0,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        child: _isVerifying 
                          ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.brandPrimary))
                          : Text(_isVerified ? _t('verified_btn') : _t('verify_btn')),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 32),
                
                Text(_t('acct_info'), style: AppTypography.h3),
                const SizedBox(height: 24),
                
                _buildLabel('full_name'),
                _buildTextField(controller: _nameController, icon: Icons.person_outline_rounded, hint: 'e.g. Rahul Sharma'),
                const SizedBox(height: 20),

                _buildLabel('phone_num'),
                _buildTextField(controller: _phoneController, icon: Icons.phone_outlined, hint: '+91 00000 00000', keyboardType: TextInputType.phone),
                const SizedBox(height: 20),

                _buildLabel('del_plat'),
                _buildDropdownField(icon: Icons.moped_outlined, hint: _selectedPlatform, options: ['Swiggy', 'Zomato', 'Zepto', 'Dunzo'], onChanged: (val) => setState(() => _selectedPlatform = val)),
                const SizedBox(height: 20),

                _buildLabel('zone'),
                _buildDropdownField(icon: Icons.map_outlined, hint: _selectedZone, options: ['North', 'South', 'East', 'West', 'Central'], onChanged: (val) => setState(() => _selectedZone = val)),
                const SizedBox(height: 32),

                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _buildLabel('hours'),
                    Text('${_workingHours.toInt()} ${_t('hr')}', style: AppTypography.bodyLarge.copyWith(color: AppColors.brandPrimary, fontWeight: FontWeight.w900)),
                  ],
                ),
                const SizedBox(height: 8),
                SliderTheme(
                  data: SliderTheme.of(context).copyWith(
                    activeTrackColor: AppColors.brandPrimary, inactiveTrackColor: AppColors.brandPrimary.withOpacity(0.1),
                    thumbColor: AppColors.brandPrimary, overlayColor: AppColors.brandPrimary.withOpacity(0.2),
                    trackHeight: 10, thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 10),
                  ),
                  child: Slider(value: _workingHours, min: 1, max: 16, onChanged: (v) => setState(() => _workingHours = v)),
                ),
                
                const SizedBox(height: 24),
                Row(
                  children: [
                    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [_buildLabel('deliv'), _buildTextField(controller: _deliveriesController, hint: 'e.g. 150')])),
                    const SizedBox(width: 16),
                    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [_buildLabel('earn'), _buildTextField(controller: _earningsController, hint: '₹ 5,000')])),
                  ],
                ),

                const SizedBox(height: 32),
                SizedBox(
                  width: double.infinity, height: 60,
                  child: ElevatedButton(
                    onPressed: _nextStep,
                    style: ElevatedButton.styleFrom(backgroundColor: AppColors.brandPrimary, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)), elevation: 0),
                    child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                      Text(_t('continue_plans'), style: AppTypography.bodyLarge.copyWith(color: Colors.white, fontWeight: FontWeight.w900, letterSpacing: 1.0)),
                      const SizedBox(width: 12), const Icon(Icons.arrow_forward_rounded, size: 20, color: Colors.white),
                    ]),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),
          _buildFooter(),
        ],
      ),
    );
  }

  // ─── STEP 3: TIER CHECKOUT ──────────────────────────────────────────────
  Widget _buildStep3(double horizontalPadding) {
    int price = _selectedTier == 'Lite' ? 49 : (_selectedTier == 'Smart' ? 68 : 99); // Elite is 99
    
    return SingleChildScrollView(
      padding: EdgeInsets.symmetric(horizontal: horizontalPadding, vertical: 32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(color: Colors.blue.withOpacity(0.1), borderRadius: BorderRadius.circular(12)),
            child: Row(
              children: [
                const Icon(Icons.auto_awesome_rounded, color: Colors.blue),
                const SizedBox(width: 12),
                Expanded(child: Text('${_t('ai_rec')} $_selectedZone ${_t('ai_rec2')}', style: AppTypography.small.copyWith(color: Colors.blue, fontWeight: FontWeight.w800))),
              ],
            ),
          ),
          const SizedBox(height: 24),
          _buildTierCard('Lite', 49, 'Rain only', 'Max ₹800/day', 'Budget coverage for low risk zones.'),
          const SizedBox(height: 16),
          _buildTierCard('Smart', 68, 'Rain, Heat & AQI', 'Max ₹1,200/day', 'Comprehensive AI-optimized defaults. Recommended.', isRecommended: true),
          const SizedBox(height: 16),
          _buildTierCard('Elite', 99, 'All + Micro Triggers', 'Max ₹1,500/day', 'Max payout coverage with weekly bonuses.'),
          
          const SizedBox(height: 48),
          const SizedBox(height: 48),
          SizedBox(
            width: double.infinity, height: 60,
            child: ElevatedButton(
              onPressed: widget.isReactivation ? _initiatePayment : _nextStep,
              style: ElevatedButton.styleFrom(
                backgroundColor: widget.isReactivation ? AppColors.success : AppColors.brandPrimary, 
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)), 
                elevation: 0
              ),
              child: _isLoading 
                ? const SizedBox(height: 24, width: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 3))
                : Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                    Icon(widget.isReactivation ? Icons.bolt_rounded : Icons.arrow_forward_rounded, color: Colors.white),
                    const SizedBox(width: 12),
                    Text(
                      widget.isReactivation ? 'ONE-TAP ACTIVATE' : _t('continue_terms'), 
                      style: AppTypography.bodyLarge.copyWith(color: Colors.white, fontWeight: FontWeight.w900, letterSpacing: 1.0)
                    ),
                  ]),
            ),
          ),
          const SizedBox(height: 32),
          _buildFooter(),
        ],
      ),
    );
  }

  Widget _buildTierCard(String title, int price, String covers, String payout, String desc, {bool isRecommended = false}) {
    bool isSelected = _selectedTier == title;
    return InkWell(
      onTap: () => setState(() => _selectedTier = title),
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.brandPrimary.withOpacity(0.05) : AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: isSelected ? AppColors.brandPrimary : AppColors.border, width: isSelected ? 2 : 1),
          boxShadow: AppStyles.softShadow,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Icon(isSelected ? Icons.radio_button_checked : Icons.radio_button_off, color: isSelected ? AppColors.brandPrimary : AppColors.textMuted),
                    const SizedBox(width: 16),
                    Text(title, style: AppTypography.h3),
                  ],
                ),
                Text('₹$price/wk', style: AppTypography.h3.copyWith(color: AppColors.brandPrimary)),
              ],
            ),
            if (isRecommended)
              Container(
                margin: const EdgeInsets.only(top: 12, left: 40),
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(color: Colors.orange.withOpacity(0.1), borderRadius: BorderRadius.circular(6)),
                child: Text('RECOMMENDED', style: AppTypography.small.copyWith(color: Colors.orange, fontWeight: FontWeight.w900, fontSize: 10)),
              ),
            Padding(
              padding: const EdgeInsets.only(left: 40, top: 12),
              child: Text(desc, style: AppTypography.small.copyWith(color: AppColors.textSecondary, height: 1.4)),
            ),
            Padding(
              padding: const EdgeInsets.only(left: 40, top: 12),
              child: Row(
                children: [
                  const Icon(Icons.umbrella_rounded, size: 16, color: AppColors.textPrimary), const SizedBox(width: 6),
                  Text(covers, style: AppTypography.small.copyWith(fontWeight: FontWeight.w700)),
                  const SizedBox(width: 16),
                  const Icon(Icons.payments_rounded, size: 16, color: Colors.green), const SizedBox(width: 6),
                  Text(payout, style: AppTypography.small.copyWith(fontWeight: FontWeight.w700, color: Colors.green)),
                ],
              ),
            )
          ],
        ),
      ),
    );
  }

  void _showTermsBottomSheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => Container(
        height: MediaQuery.of(context).size.height * 0.9,
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(30)),
        ),
        child: Stack(
          children: [
            Column(
              children: [
                const SizedBox(height: 16),
                Center(child: Container(width: 40, height: 5, decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(5)))),
                const SizedBox(height: 24),
                
                // Header
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(_t('terms_full_header'), style: AppTypography.h3.copyWith(fontWeight: FontWeight.w800, fontSize: 18)),
                      const SizedBox(height: 8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(_t('effective_date'), style: AppTypography.small.copyWith(fontWeight: FontWeight.bold)),
                          Text(_t('version_txt'), style: AppTypography.small.copyWith(fontWeight: FontWeight.bold)),
                        ],
                      ),
                      const SizedBox(height: 16),
                      const Divider(),
                    ],
                  ),
                ),
                
                // Content
                Expanded(
                  child: ListView(
                    padding: const EdgeInsets.all(24),
                    children: _buildTermsWidgetList(),
                  ),
                ),
                
                // Footer Action
                Container(
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10, offset: const Offset(0, -5))],
                  ),
                  child: SizedBox(
                    width: double.infinity,
                    height: 56,
                    child: ElevatedButton(
                      onPressed: () {
                        Navigator.pop(context);
                        setState(() => _currentStep = 3); // Target Step 4 (Index 3)
                        _pageController.animateToPage(3, duration: const Duration(milliseconds: 300), curve: Curves.easeInOut);
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF22C55E),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
                        elevation: 0,
                      ),
                      child: Text(_t('i_agree'), style: AppTypography.bodyLarge.copyWith(color: Colors.white, fontWeight: FontWeight.w900)),
                    ),
                  ),
                ),
              ],
            ),
            
            Positioned(
              top: 24,
              right: 16,
              child: IconButton(
                icon: const Icon(Icons.close_rounded, color: AppColors.textSecondary),
                onPressed: () => Navigator.pop(context),
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildTermsWidgetList() {
    final List<Map<String, dynamic>> content = [
      {"type": "section", "title": "1. DEFINITIONS AND INTERPRETATION", "items": [
        "1.1 “GigShield” refers to the digital platform, inclusive of its mobile application and associated backend infrastructure, providing parametric insurance-linked services to registered independent contractors.",
        "1.2 “Policyholder” refers to the individual registered user who has successfully completed the onboarding process and whose premium payment has been confirmed for the active Coverage Period.",
        "1.3 “Policy” or “Certificate of Insurance” refers to the specific weekly parametric coverage terms and conditions outlined herein, which constitute the entire agreement between the Service Provider and the Policyholder.",
        "1.4 “Parametric Trigger” refers to the specific, predefined environmental and meteorological thresholds (including but not limited to rainfall volume, ambient temperature, and air quality index) which, when verified by independent data sources, initiate an automated payout process without further intervention.",
        "1.5 “Coverage Period” refers to the specific duration of seven (7) consecutive calendar days, commencing precisely at the time of policy activation following verified premium receipt."
      ]},
      {"type": "section", "title": "2. NATURE OF THE PARAMETRIC PRODUCT", "items": [
        "2.1 GigShield is strictly a parametric financial protection product designed specifically to mitigate the risk of lost earnings due to severe external environmental factors. It operates on a fixed-payout model based on objective data triggers.",
        "2.2 Unlike traditional indemnity insurance, this Policy does not necessitate proof of actual financial loss or property damage. Eligibility for payment is determined solely by the occurrence of a verified Parametric Trigger within the Policyholder's registered primary working zone.",
        "2.3 This product is explicitly intended for income protection for gig economy workers and does not substitute for, nor constitute, health, life, personal accident, or motor vehicle insurance as defined under standard insurance regulations."
      ]},
      {"type": "section", "title": "3. ELIGIBILITY AND ACCOUNT REQUIREMENTS", "items": [
        "3.1 This service is available exclusively to individuals actively engaged as delivery partners with registered platform aggregators. Unauthorized use or registration by individuals not meeting these criteria will result in immediate termination of coverage without refund.",
        "3.2 To maintain eligibility, Policyholders must ensure that all registered personal details, active working zones, and UPI payout information remain accurate and up-to-date throughout the Coverage Period.",
        "3.3 GigShield and its underwriters reserve the absolute right to verify work activity and platform engagement through secure data integrations to prevent fraudulent claims and ensure equitable distribution of benefits."
      ]},
      {"type": "section", "title": "4. COVERAGE PARAMETERS AND TRIGGERS", "items": [
        "4.1 Financial benefits under this Policy are only applicable when an official Parametric Trigger is recorded within the Policyholder's defined primary working zone during active hours of the Coverage Period.",
        "4.2 Specific trigger thresholds are established as follows: (a) Precipitation exceeding 50mm within a 24-hour cycle, (b) Ambient temperatures reaching or exceeding 43°C for at least 3 consecutive hours, or (c) Air Quality Index (AQI) readings sustained above 350 for more than 4 hours.",
        "4.3 All environmental data utilized for trigger verification is sourced from reputable third-party meteorlogical and atmospheric data providers. The decisions rendered by the automated GigShield trigger engine are final and binding.",
        "4.4 Payout amounts are predetermined based on the selected Policy Tier (Lite, Smart, or Elite) and range between a minimum of ₹600 and a maximum of ₹1,500 per triggered event."
      ]},
      {"type": "section", "title": "5. EXCLUSIONS AND LIMITATIONS", "items": [
        "5.1 This Policy explicitly excludes coverage for (a) personal medical conditions, illnesses, or pre-existing health issues; (b) accidental bodily injury, permanent disability, or death; (c) physical damage to vehicles, smartphones, or personal property; (d) voluntary cessations of work unrelated to parametric conditions; and (e) platform-specific outages or account suspensions.",
        "5.2 The maximum payout per Coverage Period is capped based on the tier limits and cannot exceed the total cumulative payout threshold regardless of the number of environmental triggers occurred."
      ]},
       {"type": "section", "title": "6. TERMINATION AND RENEWAL", "items": [
        "6.1 Coverage automatically expires at the conclusion of the seven-day period. Policyholders may opt for automatic renewal to ensure uninterrupted protection.",
        "6.2 Premium payments are non-refundable once the Coverage Period has commenced, except in cases where technical errors prevented the activation of the service."
      ]},
       {"type": "section", "title": "7. CLAIM SETTLEMENT AND PAYOUT PROCESS", "items": [
        "7.1 GigShield utilizes a 'zero-touch' claims architecture. There is no requirement for the Policyholder to file a manual claim form or submit documentation following an environmental trigger.",
        "7.2 Payouts are initiated automatically upon the confirmation of a Parametric Trigger by our data node network.",
        "7.3 Funds will be disbursed directly to the registered UPI ID of the Policyholder within 24–48 hours of trigger verification, subject to banking system availability."
      ]},
    ];

    return content.expand<Widget>((sec) => [
      Text(sec['title'], style: AppTypography.bodyLarge.copyWith(fontWeight: FontWeight.w900, fontSize: 13, color: AppColors.textPrimary)),
      const SizedBox(height: 12),
      ...(sec['items'] as List).cast<String>().map((item) => Padding(
        padding: const EdgeInsets.only(bottom: 16.0),
        child: Text(
          item,
          style: AppTypography.bodySmall.copyWith(height: 1.6, color: AppColors.textPrimary),
          textAlign: TextAlign.justify,
        ),
      )),
      const SizedBox(height: 24),
    ]).toList();
  }

  // ─── STEP 5: FINAL UPI ACTIVATION ─────────────────────────────────────────
  Widget _buildStep5(double hp) {
    int price = _selectedTier == 'Lite' ? 49 : (_selectedTier == 'Smart' ? 68 : 99); // Elite is 99
    
    return SingleChildScrollView(
      padding: EdgeInsets.symmetric(horizontal: hp, vertical: 32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.verified_rounded, color: Colors.green, size: 28),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(_t('final_step'), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: Color(0xFF94A3B8))),
                  Text(_t('activate_policy'), style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w600, color: Color(0xFF0F172A), letterSpacing: -0.2)),
                ],
              ),
            ],
          ),
          const SizedBox(height: 32),
          
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFE2E8F0)),
              boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 20, offset: const Offset(0, 4))],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(_selectedTier, style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: AppColors.brandPrimary)),
                    Text('₹$price', style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
                  ],
                ),
                const SizedBox(height: 8),
                Text(_t('terms_sub'), style: const TextStyle(fontSize: 13, color: Color(0xFF94A3B8))),
                const Divider(height: 48, color: Color(0xFFE2E8F0)),
                RichText(
                  text: TextSpan(
                    style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w400, color: Color(0xFF475569), height: 1.5, fontFamily: 'Inter'),
                    children: [
                      const TextSpan(text: 'You will be charged '),
                      TextSpan(text: '₹$price', style: const TextStyle(fontWeight: FontWeight.w600, color: Color(0xFF0F172A))),
                      const TextSpan(text: ' via your saved UPI now. Coverage will start '),
                      const TextSpan(text: 'immediately', style: TextStyle(fontWeight: FontWeight.w600, color: Color(0xFF0F172A))),
                      const TextSpan(text: ' after successful payment.'),
                    ],
                  ),
                ),
                const SizedBox(height: 24),
                const Text("UPI ID", style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: Color(0xFF64748B))),
                const SizedBox(height: 20),
                
                Row(
                  children: [
                    Expanded(
                      child: _buildTextField(
                        controller: _upiController,
                        icon: Icons.account_balance_wallet_outlined,
                        hint: 'mobile@upi',
                        onChanged: (val) => setState(() => _isUpiVerified = false),
                      ),
                    ),
                    const SizedBox(width: 12),
                    SizedBox(
                      height: 54,
                      child: ElevatedButton(
                        onPressed: _isUpiVerifying ? null : _verifyUpi,
                        style: OutlinedButton.styleFrom(
                          side: BorderSide(color: _isUpiVerified ? Colors.green : AppColors.brandPrimary.withOpacity(0.5)),
                          foregroundColor: _isUpiVerified ? Colors.green : AppColors.brandPrimary,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                        child: _isUpiVerifying 
                          ? SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.brandPrimary))
                          : Text(_isUpiVerified ? _t('linked') : _t('test_1'), style: const TextStyle(fontWeight: FontWeight.w600)),
                      ),
                    ),
                  ],
                ),
                
                const SizedBox(height: 40),
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: ElevatedButton(
                    onPressed: (_isUpiVerified && !_isLoading) ? _initiatePayment : null,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.brandPrimary,
                      disabledBackgroundColor: const Color(0xFFE2E8F0),
                      disabledForegroundColor: const Color(0xFF94A3B8),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      elevation: 0,
                    ),
                    child: _isLoading 
                      ? const SizedBox(height: 24, width: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 3))
                      : Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.shield_rounded, size: 18, color: Colors.white),
                            const SizedBox(width: 8),
                            Expanded(child: Text('Pay ₹$price & Activate Now', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.white, letterSpacing: 0.3), textAlign: TextAlign.center, overflow: TextOverflow.ellipsis, maxLines: 1)),
                          ],
                        ),
                  ),
                ),
                const SizedBox(height: 16),
                Center(
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.lock_outline_rounded, size: 16, color: Color(0xFF64748B)),
                      const SizedBox(width: 6),
                      const Text("Secure Activation", style: TextStyle(fontSize: 13, color: Color(0xFF64748B), fontWeight: FontWeight.w500)),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                if (kIsWeb)
                  Center(
                    child: TextButton(
                      onPressed: _handleRegistration,
                      child: Text("DEBUG: SKIP TO DASHBOARD", style: TextStyle(color: Colors.blue.withOpacity(0.5), fontSize: 12, fontWeight: FontWeight.bold)),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 40),
          _buildFooter(),
        ],
      ),
    );
  }

  // Original fallback T&C structure for legacy ref
  List<Widget> _buildAccordionList() {
    return _termsSections.map((s) => _buildAccordion(s['title'], s['content'])).toList();
  }

  Widget _buildAccordion(String title, String content) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border.withOpacity(0.5)),
      ),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          title: Text(title, style: AppTypography.bodyMedium.copyWith(fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
          iconColor: AppColors.brandPrimary,
          collapsedIconColor: AppColors.textMuted,
          childrenPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          children: [
            Text(
              content,
              style: AppTypography.bodySmall.copyWith(height: 1.6, color: AppColors.textSecondary),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildFallbackTerms() {
    final List<Map<String, String>> fallback = [
      {"title": "1. Introduction", "content": "GigShield is a parametric micro-insurance product for delivery partners."},
      {"title": "2. Coverage", "content": "Covers loss of income due to weather triggers."},
      {"title": "3. Claims", "content": "Automatic payout, no manual claim filing needed."},
    ];
    return fallback.map((s) => _buildAccordion(s['title']!, s['content']!)).toList();
  }

  // ─── REUSABLE WIDGETS ───────────────────────────────────────────────────
  Widget _buildHeroCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [AppColors.brandGradientStart, AppColors.brandGradientEnd], begin: Alignment.topLeft, end: Alignment.bottomRight),
        borderRadius: BorderRadius.circular(AppStyles.borderRadius),
        boxShadow: AppStyles.premiumShadow,
      ),
      child: Stack(
        children: [
          Positioned(right: -20, bottom: -20, child: Icon(Icons.bolt_rounded, size: 120, color: Colors.white.withOpacity(0.1))),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(_t('hero_title'), style: AppTypography.h1.copyWith(color: Colors.white, fontSize: 32)),
              const SizedBox(height: 12),
              Text(_t('hero_sub'), style: AppTypography.bodyLarge.copyWith(color: Colors.white.withOpacity(0.9), height: 1.5)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildLabel(String dictKey) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0),
      child: TranslationFlipLabel(
        textNative: _t(dictKey),
        textEnglish: _tEn(dictKey),
        style: AppTypography.small.copyWith(color: AppColors.textSecondary, fontWeight: FontWeight.w900, letterSpacing: 0.5),
      ),
    );
  }

  Widget _buildTextField({required String hint, IconData? icon, TextEditingController? controller, TextInputType keyboardType = TextInputType.text, Function(String)? onChanged}) {
    return TextFormField(
      controller: controller, onChanged: onChanged, keyboardType: keyboardType, style: AppTypography.bodyLarge,
      decoration: InputDecoration(
        filled: true,
        fillColor: AppColors.background,
        prefixIcon: icon != null ? Icon(icon, color: AppColors.textMuted, size: 20) : null,
        hintText: hint, hintStyle: AppTypography.bodyMedium.copyWith(color: AppColors.textMuted),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.border)),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.brandPrimary, width: 2.0)),
      ),
    );
  }

  Widget _buildDropdownField({required IconData icon, required String hint, required List<String> options, required Function(String) onChanged}) {
    return Container(
      decoration: BoxDecoration(color: const Color(0xFFF9FAFB), borderRadius: BorderRadius.circular(8), border: Border.all(color: AppColors.border)),
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: options.contains(hint) ? hint : options.first,
          icon: const Icon(Icons.unfold_more_rounded, color: AppColors.textMuted, size: 20),
          isExpanded: true, style: AppTypography.bodyLarge,
          items: options.map((v) => DropdownMenuItem<String>(value: v, child: Row(children: [Icon(icon, color: AppColors.textMuted, size: 20), const SizedBox(width: 12), Text(v, style: AppTypography.bodyMedium)]))).toList(),
          onChanged: (v) { if (v != null) onChanged(v); },
        ),
      ),
    );
  }

  Widget _buildFooter() {
    return Center(
      child: Column(
        children: [
          Text('By registering, you agree to FIGGY\'s Terms and Privacy Policy.', textAlign: TextAlign.center, style: AppTypography.small),
          const SizedBox(height: 24),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.verified_user_rounded, color: AppColors.textMuted.withOpacity(0.4), size: 24), const SizedBox(width: 32),
              Icon(Icons.shield_rounded, color: AppColors.textMuted.withOpacity(0.4), size: 24), const SizedBox(width: 32),
              Icon(Icons.headset_mic_rounded, color: AppColors.textMuted.withOpacity(0.4), size: 24),
            ],
          ),
        ],
      ),
    );
  }
}

class TranslationFlipLabel extends StatefulWidget {
  final String textNative;
  final String textEnglish;
  final TextStyle style;

  const TranslationFlipLabel({super.key, required this.textNative, required this.textEnglish, required this.style});

  @override
  State<TranslationFlipLabel> createState() => _TranslationFlipLabelState();
}

class _TranslationFlipLabelState extends State<TranslationFlipLabel> {
  bool _isPressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => setState(() => _isPressed = true),
      onTapUp: (_) => setState(() => _isPressed = false),
      onTapCancel: () => setState(() => _isPressed = false),
      child: AnimatedSwitcher(
        duration: const Duration(milliseconds: 150),
        child: Text(
          _isPressed ? widget.textEnglish : widget.textNative,
          key: ValueKey(_isPressed),
          style: widget.style,
        ),
      ),
    );
  }
}

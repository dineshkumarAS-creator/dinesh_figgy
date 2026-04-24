// ignore: unused_import — retained for potential future proxy use
import 'package:flutter/material.dart';
import 'package:figgy_app/theme/app_theme.dart';
import 'package:figgy_app/screens/claim_processing_screen.dart';
import 'package:figgy_app/services/api_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ManualClaimScreen extends StatefulWidget {
  const ManualClaimScreen({super.key});

  @override
  State<ManualClaimScreen> createState() => _ManualClaimScreenState();
}

class _ManualClaimScreenState extends State<ManualClaimScreen> {
  // ── Form State ────────────────────────────────────────────────────────────
  String _selectedClaimType = 'Heavy Rain';

  DateTime? _startTime;
  DateTime? _endTime;
  int _estimatedLoss = 0;
  int _avgDailyEarnings = 800;  // loaded from SharedPreferences

  final _lossCtrl        = TextEditingController();
  final _descriptionCtrl = TextEditingController();

  bool _isSubmitting = false;
  String? _errorMessage;

  final ApiService _api = ApiService();

  @override
  void initState() {
    super.initState();
    _loadAvgEarnings();
  }

  Future<void> _loadAvgEarnings() async {
    final prefs = await SharedPreferences.getInstance();
    final now = DateTime.now();
    setState(() {
      _avgDailyEarnings = prefs.getInt('avg_daily_earnings') ?? 800;
      // 🕒 Smart Defaults: Ravi likely wants to report the current day's morning shift
      _startTime = DateTime(now.year, now.month, now.day, 9, 0);
      _endTime   = DateTime(now.year, now.month, now.day, now.hour, now.minute);
    });
    _autoCalcLoss();
  }

  @override
  void dispose() {
    _lossCtrl.dispose();
    _descriptionCtrl.dispose();
    super.dispose();
  }

  // ── Auto-calc loss whenever end time changes ───────────────────────────────
  void _autoCalcLoss() {
    if (_startTime == null || _endTime == null) return;
    final hours = _endTime!.difference(_startTime!).inMinutes / 60.0;
    if (hours <= 0) return;
    final avgHourly = _avgDailyEarnings / 8.0;
    setState(() {
      _estimatedLoss = (avgHourly * hours).round();
      _lossCtrl.text = _estimatedLoss.toString();
    });
  }

  // ── Time Picker helpers ────────────────────────────────────────────────────
  Future<void> _pickStartTime() async {
    final now = DateTime.now();
    final picked = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_startTime ?? now),
      builder: (ctx, child) => _timePickerTheme(ctx, child),
    );
    if (picked == null) return;
    setState(() {
      _startTime = DateTime(now.year, now.month, now.day, picked.hour, picked.minute);
    });
    _autoCalcLoss();
  }

  Future<void> _pickEndTime() async {
    final now = DateTime.now();
    final picked = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_endTime ?? now),
      builder: (ctx, child) => _timePickerTheme(ctx, child),
    );
    if (picked == null) return;
    setState(() {
      _endTime = DateTime(now.year, now.month, now.day, picked.hour, picked.minute);
    });
    _autoCalcLoss();
  }

  Widget _timePickerTheme(BuildContext ctx, Widget? child) {
    return Theme(
      data: ThemeData.dark().copyWith(
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFFFF6B35),
          surface: Color(0xFF1E293B),
          onSurface: Colors.white,
        ),
      ),
      child: child!,
    );
  }

  String _formatTime(DateTime? dt) {
    if (dt == null) return '';
    final h = dt.hour.toString().padLeft(2, '0');
    final m = dt.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }

  // ── Validation ────────────────────────────────────────────────────────────
  String? _validateForm() {
    if (_selectedClaimType.isEmpty) return 'Please select a claim type.';
    if (_startTime == null)         return 'Please set a start time.';
    if (_endTime == null)           return 'Please set an end time.';
    if (!_endTime!.isAfter(_startTime!)) {
      return 'End time must be after start time.';
    }
    final loss = int.tryParse(_lossCtrl.text.trim()) ?? 0;
    if (loss <= 0)    return 'Estimated loss must be greater than ₹0.';
    if (loss >= 5000) return 'Estimated loss must be less than ₹5,000.';
    return null; // all valid
  }

  // ── Submit ────────────────────────────────────────────────────────────────
  Future<void> _submitClaim() async {
    // Validate first
    final validationError = _validateForm();
    if (validationError != null) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(validationError),
          backgroundColor: const Color(0xFFEF4444),
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      );
      return;
    }

    setState(() { _errorMessage = null; _isSubmitting = true; });

    try {
      final prefs = await SharedPreferences.getInstance();
      final workerId = prefs.getString('worker_id') ?? '';

      if (workerId.isEmpty) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Worker ID not found. Please register first.'),
            backgroundColor: Color(0xFFEF4444),
            behavior: SnackBarBehavior.floating,
          ),
        );
        return;
      }

      final loss = int.tryParse(_lossCtrl.text.trim()) ?? _estimatedLoss;

      final result = await _api.submitManualClaim({
        'worker_id':      workerId,
        'claim_type':     _selectedClaimType,
        'start_time':     _startTime!.toUtc().toIso8601String(),
        'end_time':       _endTime!.toUtc().toIso8601String(),
        'estimated_loss': loss,
        'description':    _descriptionCtrl.text.trim(),
        'proof_urls':     <String>[],
      });

      final claimId = result['claim_id'] as String? ?? '';
      if (!mounted) return;

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => ClaimProcessingScreen(claimId: claimId),
        ),
      );
    } on ApiException catch (e) {
      setState(() { _errorMessage = e.message; });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.message),
          backgroundColor: const Color(0xFFEF4444),
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      );
    } catch (e) {
      setState(() { _errorMessage = 'Something went wrong. Please try again.'; });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Something went wrong. Please try again.'),
          backgroundColor: Color(0xFFEF4444),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } finally {
      if (mounted) setState(() { _isSubmitting = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: AppColors.textPrimary),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.standard),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Submit Manual Claim',
              style: AppTypography.h1.copyWith(
                fontWeight: FontWeight.w800,
                fontSize: 24,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: AppSpacing.micro),
            Text(
              'Request compensation for uncontrollable work interruptions.',
              style: AppTypography.bodyMedium.copyWith(
                color: AppColors.textSecondary,
                fontSize: 14,
              ),
            ),
            const SizedBox(height: AppSpacing.section),

            _buildLabel('Claim Type'),
            _buildDropdown(),
            const SizedBox(height: AppSpacing.standard),

            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildLabel('Start Time'),
                      _buildTimeTile(
                        value: _formatTime(_startTime),
                        hint: '09:00',
                        onTap: _pickStartTime,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: AppSpacing.standard),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildLabel('End Time'),
                      _buildTimeTile(
                        value: _formatTime(_endTime),
                        hint: '13:00',
                        onTap: _pickEndTime,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.standard),

            _buildLabel('Estimated Income Loss'),
            _buildTextField(
              hint: _estimatedLoss > 0 ? _estimatedLoss.toString() : '600',
              prefixText: '₹ ',
              controller: _lossCtrl,
              keyboardType: TextInputType.number,
              helperText: 'Based on your ₹${(_avgDailyEarnings / 8).round()}/hr average — adjust if needed',
            ),
            const SizedBox(height: AppSpacing.standard),

            _buildLabel('Proof Upload (optional — speeds up review)'),
            _buildProofUploads(),
            const SizedBox(height: AppSpacing.standard),

            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildLabel('Description (optional)'),
                Text('${_descriptionCtrl.text.length}/200', style: AppTypography.small.copyWith(fontSize: 10, color: AppColors.textMuted)),
              ],
            ),
            _buildTextArea(),
            const SizedBox(height: AppSpacing.section),

            _buildSubmitButton(),
            const SizedBox(height: AppSpacing.section),

            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Recent Claims',
                  style: AppTypography.h3.copyWith(
                    fontWeight: FontWeight.w700,
                    fontSize: 16,
                  ),
                ),
                Text(
                  'View History',
                  style: AppTypography.small.copyWith(
                    color: AppColors.brandPrimary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.standard),

            _buildRecentClaimCard(),
            const SizedBox(height: AppSpacing.section),
          ],
        ),
      ),
    );
  }

  Widget _buildLabel(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0),
      child: Text(
        text,
        style: AppTypography.bodySmall.copyWith(
          color: AppColors.textPrimary,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  Widget _buildDropdown() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: _selectedClaimType,
          isExpanded: true,
          icon: const Icon(Icons.keyboard_arrow_down_rounded, color: AppColors.textSecondary),
          style: AppTypography.bodyMedium.copyWith(color: AppColors.textPrimary),
          onChanged: (String? newValue) {
            setState(() { _selectedClaimType = newValue!; });
          },
          items: <String>[
            'Heavy Rain', 'Flood', 'Extreme Heat', 'Strike', 'Traffic', 'Other',
          ].map<DropdownMenuItem<String>>((String value) {
            return DropdownMenuItem<String>(value: value, child: Text(value));
          }).toList(),
        ),
      ),
    );
  }

  Widget _buildTextField({
    String? hint,
    String? prefixText,
    IconData? suffixIcon,
    TextEditingController? controller,
    TextInputType? keyboardType,
    String? helperText,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.border),
          ),
          child: TextField(
            controller: controller,
            keyboardType: keyboardType,
            decoration: InputDecoration(
              hintText: hint,
              prefixText: prefixText,
              prefixStyle: AppTypography.bodyLarge.copyWith(
                fontWeight: FontWeight.w600,
                color: AppColors.textSecondary,
              ),
              suffixIcon: suffixIcon != null
                  ? Icon(suffixIcon, color: AppColors.textPrimary, size: 20)
                  : null,
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              border: InputBorder.none,
              hintStyle: AppTypography.bodyMedium.copyWith(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w600,
              ),
            ),
            style: AppTypography.bodyLarge.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        if (helperText != null) ...[const SizedBox(height: 6),
          Text(
            helperText,
            style: AppTypography.small.copyWith(
              color: AppColors.textSecondary,
              fontSize: 11,
              fontStyle: FontStyle.italic,
            ),
          )],
      ],
    );
  }

  /// Tappable tile that shows a native time picker and displays selected time.
  Widget _buildTimeTile({
    required String value,
    required String hint,
    required VoidCallback onTap,
  }) {
    final hasValue = value.isNotEmpty;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: hasValue
                ? const Color(0xFFFF6B35).withOpacity(0.6)
                : AppColors.border,
          ),
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                hasValue ? value : hint,
                style: AppTypography.bodyLarge.copyWith(
                  color: hasValue ? AppColors.textPrimary : AppColors.textSecondary,
                  fontWeight: hasValue ? FontWeight.w700 : FontWeight.w500,
                ),
              ),
            ),
            Icon(
              Icons.access_time_rounded,
              color: hasValue ? const Color(0xFFFF6B35) : AppColors.textSecondary,
              size: 20,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProofUploads() {
    return Row(
      children: [
        _buildUploadBox(
          icon: Icons.camera_alt_outlined,
          label: 'PHOTO',
          color: AppColors.brandPrimary,
          isDashed: true,
        ),
        const SizedBox(width: AppSpacing.standard),
        _buildUploadBox(
          icon: Icons.smartphone_rounded,
          label: 'SCREENSHOT',
          color: AppColors.info,
          isDashed: true,
        ),
        const SizedBox(width: AppSpacing.standard),
        _buildPlaceholderBox(),
      ],
    );
  }

  Widget _buildUploadBox({required IconData icon, required String label, required Color color, required bool isDashed}) {
    return Container(
      width: 100,
      height: 100,
      decoration: BoxDecoration(
        color: color.withOpacity(0.05),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: color.withOpacity(0.3),
          style: BorderStyle.solid, // Using solid as flutter dashed border requires a package
          width: 1.5,
        ),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, color: color, size: 28),
          const SizedBox(height: 8),
          Text(
            label,
            style: AppTypography.small.copyWith(
              color: color,
              fontWeight: FontWeight.w700,
              fontSize: 10,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPlaceholderBox() {
    return Container(
      width: 100,
      height: 100,
      decoration: BoxDecoration(
        color: AppColors.border.withOpacity(0.5),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Stack(
        children: [
          // Simulated image area
          Positioned(
            top: 6,
            right: 6,
            child: Container(
              padding: const EdgeInsets.all(2),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.5),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.close, color: Colors.white, size: 12),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTextArea() {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: TextField(
        controller: _descriptionCtrl,
        maxLines: 4,
        maxLength: 200,
        onChanged: (v) => setState(() {}),
        decoration: InputDecoration(
          counterText: '',
          hintText: 'e.g. Heavy rainfall stopped deliveries in North zone from 9am-12pm.',
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          border: InputBorder.none,
          hintStyle: AppTypography.bodySmall.copyWith(
            color: AppColors.textSecondary,
            fontSize: 13,
            height: 1.4,
          ),
        ),
        style: AppTypography.bodyMedium.copyWith(
          color: AppColors.textPrimary,
        ),
      ),
    );
  }

  Widget _buildSubmitButton() {
    return Column(
      children: [
        // Error banner
        if (_errorMessage != null) ...
          [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(
                color: AppColors.error.withOpacity(0.1),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppColors.error.withOpacity(0.3)),
              ),
              child: Text(
                _errorMessage!,
                style: AppTypography.bodySmall.copyWith(color: AppColors.error),
              ),
            ),
          ],
        SizedBox(
          width: double.infinity,
          height: 50,
          child: ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.brandPrimary,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              elevation: 0,
            ),
            onPressed: _isSubmitting ? null : _submitClaim,
            child: _isSubmitting
                ? const SizedBox(
                    width: 22, height: 22,
                    child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5),
                  )
                : Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.send_rounded, color: Colors.white, size: 20),
                      const SizedBox(width: 8),
                      Text(
                        'Submit Claim Request',
                        style: AppTypography.bodyMedium.copyWith(
                          color: Colors.white, fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
          ),
        ),
      ],
    );
  }

  Widget _buildRecentClaimCard() {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.standard),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: AppColors.info.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.cloudy_snowing, color: AppColors.info, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Heavy Rain',
                      style: AppTypography.bodyLarge.copyWith(
                        fontWeight: FontWeight.w700,
                        fontSize: 15,
                      ),
                    ),
                    Text(
                      'Aug 14, 2023 • 09:00 - 13:00',
                      style: AppTypography.small.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: AppColors.warning.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  'BEING REVIEWED (24 HRS)',
                  style: AppTypography.small.copyWith(
                    color: AppColors.warning,
                    fontWeight: FontWeight.w900,
                    fontSize: 8,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.standard),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Estimated Loss',
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              Text(
                '₹600',
                style: AppTypography.bodyLarge.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.standard),
          SizedBox(
            width: double.infinity,
            height: 44,
            child: TextButton(
              onPressed: () {},
              style: TextButton.styleFrom(
                backgroundColor: Colors.transparent,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                  side: BorderSide(color: AppColors.brandPrimary.withOpacity(0.1)),
                ),
              ),
              child: Text(
                'View Claim Details',
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.brandPrimary,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:figgy_app/theme/app_theme.dart';

class WalletScreen extends StatefulWidget {
  const WalletScreen({super.key});

  @override
  State<WalletScreen> createState() => _WalletScreenState();
}

class _WalletScreenState extends State<WalletScreen> with SingleTickerProviderStateMixin {
  int _selectedTabIndex = 2; // 0 = Received, 1 = Paid, 2 = Waiting
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(vsync: this, duration: const Duration(seconds: 2))..repeat(reverse: true);
    _pulseAnimation = Tween<double>(begin: 0.3, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
        iconTheme: const IconThemeData(color: AppColors.textPrimary),
        title: Text(
          'MY WALLET',
          style: AppTypography.small.copyWith(
            letterSpacing: 2.0,
            fontWeight: FontWeight.w900,
            color: AppColors.textPrimary,
          ),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.standard, vertical: AppSpacing.standard),
        child: Column(
          children: [
            _buildPremiumCard(),
            const SizedBox(height: AppSpacing.section),
            _buildFilters(),
            const SizedBox(height: AppSpacing.section),
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 300),
              child: _buildTabContent(),
            ),
            const SizedBox(height: AppSpacing.section),
            _buildSummaryCard(),
          ],
        ),
      ),
    );
  }

  Widget _buildTabContent() {
    switch (_selectedTabIndex) {
      case 0:
        return _buildReceivedTransactions();
      case 1:
        return _buildPaidTransactions();
      case 2:
        return _buildPremiumWaitingCard();
      default:
        return const SizedBox();
    }
  }

  Widget _buildPremiumCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.section),
      decoration: BoxDecoration(
        color: AppColors.brandPrimary,
        borderRadius: BorderRadius.circular(AppStyles.cardRadius),
        boxShadow: AppStyles.premiumShadow,
        gradient: const LinearGradient(
          colors: [AppColors.brandPrimary, AppColors.brandGradientEnd, AppColors.brandGradientStart],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          stops: [0.0, 0.5, 1.0],
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'READY TO WITHDRAW',
            style: AppTypography.small.copyWith(color: Colors.white.withOpacity(0.8), letterSpacing: 1.5, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 8),
          const Text(
            '₹198',
            style: TextStyle(color: Colors.white, fontSize: 56, fontWeight: FontWeight.w900, height: 1.0, letterSpacing: -1),
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              Icon(Icons.check_circle_rounded, color: Colors.white.withOpacity(0.9), size: 16),
              const SizedBox(width: 6),
              Text(
                'Sent to worker@upi last time',
                style: AppTypography.bodySmall.copyWith(color: Colors.white.withOpacity(0.9), fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Row(
            children: [
              Expanded(
                child: Material(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(AppStyles.borderRadius),
                  child: InkWell(
                    onTap: () {},
                    borderRadius: BorderRadius.circular(AppStyles.borderRadius),
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      alignment: Alignment.center,
                      child: Text(
                        'Withdraw Funds',
                        style: AppTypography.bodyMedium.copyWith(color: AppColors.brandGradientStart, fontWeight: FontWeight.w900),
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Material(
                  color: Colors.white.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(AppStyles.borderRadius),
                  child: InkWell(
                    onTap: () {},
                    borderRadius: BorderRadius.circular(AppStyles.borderRadius),
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        border: Border.all(color: Colors.white.withOpacity(0.4)),
                        borderRadius: BorderRadius.circular(AppStyles.borderRadius),
                      ),
                      child: Text(
                        'Change UPI',
                        style: AppTypography.bodyMedium.copyWith(color: Colors.white, fontWeight: FontWeight.w800),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildFilters() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      physics: const BouncingScrollPhysics(),
      child: Row(
        children: [
          _buildFilterChip('Money received', 0),
          const SizedBox(width: 8),
          _buildFilterChip('Money paid', 1),
          const SizedBox(width: 8),
          _buildFilterChip('Waiting', 2),
        ],
      ),
    );
  }

  Widget _buildFilterChip(String text, int index) {
    final isSelected = _selectedTabIndex == index;
    return GestureDetector(
      onTap: () => setState(() => _selectedTabIndex = index),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.brandDeepBlue : AppColors.surface,
          borderRadius: BorderRadius.circular(30),
          border: Border.all(color: isSelected ? AppColors.brandDeepBlue : AppColors.border, width: 1.5),
          boxShadow: isSelected ? [
            BoxShadow(color: AppColors.brandDeepBlue.withOpacity(0.3), blurRadius: 8, offset: const Offset(0, 4))
          ] : [],
        ),
        child: Text(
          text,
          style: AppTypography.bodyMedium.copyWith(
            color: isSelected ? Colors.white : AppColors.textPrimary,
            fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
          ),
        ),
      ),
    );
  }

  Widget _buildPremiumWaitingCard() {
    return AnimatedBuilder(
      animation: _pulseAnimation,
      builder: (context, child) {
        return Container(
          key: const ValueKey('waitingTab'),
          padding: const EdgeInsets.all(AppSpacing.section),
          decoration: BoxDecoration(
            color: AppColors.warningLight,
            borderRadius: BorderRadius.circular(AppStyles.cardRadius),
            border: Border.all(color: AppColors.warning.withOpacity(0.3), width: 1.5),
            boxShadow: [
              BoxShadow(
                color: AppColors.warning.withOpacity(0.15 * _pulseAnimation.value),
                blurRadius: 16 * _pulseAnimation.value,
                spreadRadius: 4 * _pulseAnimation.value,
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 12,
                    height: 12,
                    decoration: BoxDecoration(
                      color: AppColors.warning,
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: AppColors.warning.withOpacity(0.5),
                          blurRadius: 8 * _pulseAnimation.value,
                          spreadRadius: 2 * _pulseAnimation.value,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  Text('Being checked right now', style: AppTypography.h3.copyWith(color: AppColors.warning)),
                ],
              ),
              const SizedBox(height: 16),
              Text(
                'Claim #FGY-2510',
                style: AppTypography.small.copyWith(color: AppColors.textPrimary),
              ),
              const SizedBox(height: 4),
              RichText(
                text: TextSpan(
                  text: '₹150 ',
                  style: AppTypography.h2.copyWith(color: AppColors.textPrimary, fontWeight: FontWeight.w900),
                  children: [
                    TextSpan(
                      text: 'should arrive in about ',
                      style: AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary),
                    ),
                    TextSpan(
                      text: '2 hours',
                      style: AppTypography.bodyMedium.copyWith(color: AppColors.textPrimary, fontWeight: FontWeight.w800),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildReceivedTransactions() {
    return Column(
      key: const ValueKey('receivedTab'),
      children: [
        _buildTransactionItem(
          icon: Icons.add_rounded,
          iconColor: AppColors.success,
          iconBgColor: AppColors.success.withOpacity(0.1),
          title: 'Rain payout #FGY-2483',
          subtitle: 'Apr 2 · Sent to your UPI in 12 seconds',
          amount: '+ ₹198',
          amountColor: AppColors.success,
        ),
        const Divider(color: AppColors.border, thickness: 1, height: 32),
        _buildTransactionItem(
          icon: Icons.add_rounded,
          iconColor: AppColors.success,
          iconBgColor: AppColors.success.withOpacity(0.1),
          title: 'Flood payout #FGY-2101',
          subtitle: 'Mar 18 · Sent to your UPI',
          amount: '+ ₹240',
          amountColor: AppColors.success,
        ),
      ],
    );
  }

  Widget _buildPaidTransactions() {
    return Column(
      key: const ValueKey('paidTab'),
      children: [
        _buildTransactionItem(
          icon: Icons.remove_rounded,
          iconColor: AppColors.dangerText,
          iconBgColor: AppColors.dangerSoft,
          title: 'Weekly plan fee',
          subtitle: 'Apr 1 · Taken out automatically',
          amount: '- ₹20',
          amountColor: AppColors.textPrimary,
        ),
        const Divider(color: AppColors.border, thickness: 1, height: 32),
        _buildTransactionItem(
          icon: Icons.remove_rounded,
          iconColor: AppColors.dangerText,
          iconBgColor: AppColors.dangerSoft,
          title: 'Weekly plan fee',
          subtitle: 'Mar 25 · Taken out automatically',
          amount: '- ₹20',
          amountColor: AppColors.textPrimary,
        ),
      ],
    );
  }

  Widget _buildTransactionItem({
    required IconData icon,
    required Color iconColor,
    required Color iconBgColor,
    required String title,
    required String subtitle,
    required String amount,
    required Color amountColor,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: iconBgColor, shape: BoxShape.circle),
          child: Icon(icon, color: iconColor, size: 20),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: AppTypography.bodyLarge.copyWith(fontWeight: FontWeight.w800)),
              const SizedBox(height: 2),
              Text(subtitle, style: AppTypography.bodySmall),
            ],
          ),
        ),
        Text(amount, style: AppTypography.h3.copyWith(color: amountColor, fontWeight: FontWeight.w900)),
      ],
    );
  }

  Widget _buildSummaryCard() {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.section),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppStyles.cardRadius),
        border: Border.all(color: AppColors.border),
        boxShadow: AppStyles.softShadow,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.insights_rounded, color: AppColors.textSecondary, size: 18),
              const SizedBox(width: 8),
              Text('THIS MONTH AT A GLANCE', style: AppTypography.small),
            ],
          ),
          const SizedBox(height: AppSpacing.section),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildSummaryStat('₹438', 'Total received', AppColors.success),
              Container(width: 1, height: 40, color: AppColors.border),
              _buildSummaryStat('2', 'Times paid', AppColors.textPrimary),
              Container(width: 1, height: 40, color: AppColors.border),
              _buildSummaryStat('15s', 'Speed avg', AppColors.textPrimary),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryStat(String value, String label, Color valueColor) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(value, style: AppTypography.h2.copyWith(color: valueColor, fontWeight: FontWeight.w900)),
        const SizedBox(height: 4),
        Text(label, style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w600)),
      ],
    );
  }
}

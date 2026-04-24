import 'package:flutter/material.dart';
import 'package:figgy_app/theme/app_theme.dart';
import 'package:figgy_app/models/ride.dart';

class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded, color: AppColors.textPrimary),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(
          'All Delivery History',
          style: AppTypography.bodyLarge.copyWith(fontWeight: FontWeight.w900),
        ),
        centerTitle: true,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(color: AppColors.border, height: 1),
        ),
      ),
      body: ValueListenableBuilder<List<Ride>>(
        valueListenable: globalCompletedRidesNotifier,
        builder: (context, rides, _) {
          if (rides.isEmpty) {
            return Center(
              child: Text(
                "No deliveries completed yet.",
                style: AppTypography.bodyMedium.copyWith(color: AppColors.textMuted),
              ),
            );
          }

          return ListView.separated(
            padding: const EdgeInsets.all(20),
            itemCount: rides.length,
            separatorBuilder: (ctx, i) => const SizedBox(height: 12),
            itemBuilder: (ctx, i) {
              final ride = rides[i];
              final h = ride.endTime!.hour;
              final m = ride.endTime!.minute.toString().padLeft(2, '0');
              final period = h >= 12 ? 'PM' : 'AM';
              final displayH = h > 12 ? h - 12 : (h == 0 ? 12 : h);
              
              final now = DateTime.now();
              final end = ride.endTime!;
              final diff = DateTime(now.year, now.month, now.day)
                  .difference(DateTime(end.year, end.month, end.day))
                  .inDays;
              
              String dateStr;
              if (diff == 0) {
                dateStr = 'Today';
              } else if (diff == 1) {
                dateStr = 'Yesterday';
              } else {
                const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
                dateStr = '${end.day} ${months[end.month - 1]}';
              }
              
              final timeStr = '$dateStr, $displayH:$m $period';

              return Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppColors.border),
                  boxShadow: AppStyles.softShadow,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(timeStr, style: AppTypography.small.copyWith(color: AppColors.textSecondary, fontWeight: FontWeight.w700)),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(color: AppColors.success.withOpacity(0.1), borderRadius: BorderRadius.circular(8)),
                          child: Text('Delivered', style: AppTypography.small.copyWith(color: AppColors.success, fontWeight: FontWeight.w800, fontSize: 10)),
                        ),
                      ],
                    ),
                    const Divider(height: 24, color: AppColors.border),
                    Row(
                      children: [
                        Column(
                          children: [
                            Container(width: 8, height: 8, decoration: const BoxDecoration(color: Colors.green, shape: BoxShape.circle)),
                            Container(width: 2, height: 18, color: AppColors.border),
                            Container(width: 8, height: 8, decoration: BoxDecoration(color: AppColors.error, borderRadius: BorderRadius.circular(2))),
                          ],
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(ride.restaurantName, style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w800)),
                              const SizedBox(height: 10),
                              Text(ride.customerAddress, style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w800, color: AppColors.textSecondary)),
                            ],
                          ),
                        ),
                        Text('₹${ride.earnings}', style: AppTypography.h3.copyWith(color: AppColors.brandPrimary, fontSize: 18)),
                      ],
                    ),
                  ],
                ),
              );
            },
          );
        },
      ),
    );
  }
}

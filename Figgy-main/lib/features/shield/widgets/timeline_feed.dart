import 'package:flutter/material.dart';

class TimelineItem extends StatelessWidget {
  final Widget icon;
  final String title;
  final String subtitle;
  final String amount;
  final String time;
  final bool isLast;
  final Color? amountColor;
  final Color? iconBg;

  const TimelineItem({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.amount,
    required this.time,
    this.isLast = false,
    this.amountColor,
    this.iconBg,
  });

  @override
  Widget build(BuildContext context) {
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: 48,
            child: Column(
              children: [
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: iconBg ?? Colors.white,
                    shape: BoxShape.circle,
                    border: Border.all(color: (iconBg != null && iconBg != Colors.white) ? Colors.transparent : const Color(0xFF16A34A).withOpacity(0.3), width: 1.2),
                  ),
                  child: Center(child: icon),
                ),
                if (!isLast)
                  Expanded(
                    child: Container(
                      width: 1.2,
                      color: Colors.grey.withOpacity(0.15),
                    ),
                  ),
              ],
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(top: 2, left: 12, bottom: 32),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14, color: Color(0xFF1A1A1A))),
                            if (subtitle.isNotEmpty) ...[
                              const SizedBox(height: 2),
                              Text(subtitle, style: const TextStyle(color: Color(0xFF6B7280), fontSize: 10, fontWeight: FontWeight.w500)),
                            ],
                          ],
                        ),
                      ),
                      const SizedBox(width: 8),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          if (amount.isNotEmpty)
                            Text(
                              amount,
                              style: TextStyle(
                                color: amountColor ?? (amount.startsWith('+') ? const Color(0xFF1A1A1A) : (amount.startsWith('-') ? const Color(0xFFEF4444) : const Color(0xFF1A1A1A))),
                                fontWeight: FontWeight.w800,
                                fontSize: 14,
                              ),
                            ),
                          if (time.isNotEmpty) ...[
                             const SizedBox(height: 2),
                             Text(
                              time,
                              style: const TextStyle(
                                color: Color(0xFF9CA3AF),
                                fontWeight: FontWeight.w500,
                                fontSize: 10,
                              ),
                            ),
                          ]
                        ],
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

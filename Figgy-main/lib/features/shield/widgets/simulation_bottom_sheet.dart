import 'package:flutter/material.dart';
import '../core/simulation_controller.dart';
import '../core/theme.dart';

class SimulationBottomSheet extends StatelessWidget {
  final SimulationController controller;

  const SimulationBottomSheet({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: controller,
      builder: (context, _) {
        return Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
            boxShadow: [BoxShadow(color: Color(0x22000000), blurRadius: 24, offset: Offset(0, -4))],
          ),
          padding: EdgeInsets.only(
            left: 24,
            right: 24,
            top: 20,
            bottom: MediaQuery.paddingOf(context).bottom + 24,
          ),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Center(
                  child: Container(
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.grey.shade300,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                const Text(
                  'Demo simulation',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, letterSpacing: -0.5),
                ),
                const SizedBox(height: 8),
                Text(
                  'All off: rides finish normally. Turn one on to simulate a disruption and blocked earnings.',
                  style: TextStyle(color: Colors.grey.shade600, fontSize: 14, height: 1.35),
                ),
                const SizedBox(height: 20),
                _simSwitch(
                  label: 'Rain',
                  subtitle: 'Heavy rain, deliveries slow, ride blocked',
                  value: controller.isOn(DemoDisruption.rain),
                  onChanged: (v) => controller.toggle(DemoDisruption.rain, v),
                ),
                _simSwitch(
                  label: 'Heat',
                  subtitle: 'Heat wave, unsafe conditions',
                  value: controller.isOn(DemoDisruption.heat),
                  onChanged: (v) => controller.toggle(DemoDisruption.heat, v),
                ),
                _simSwitch(
                  label: 'Traffic',
                  subtitle: 'Severe congestion, long delays',
                  value: controller.isOn(DemoDisruption.traffic),
                  onChanged: (v) => controller.toggle(DemoDisruption.traffic, v),
                ),
                _simSwitch(
                  label: 'Strike',
                  subtitle: 'Service disruption / bandh in zone',
                  value: controller.isOn(DemoDisruption.strike),
                  onChanged: (v) => controller.toggle(DemoDisruption.strike, v),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _simSwitch({
    required String label,
    required String subtitle,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Material(
        color: AppColors.highlightBg,
        borderRadius: BorderRadius.circular(16),
        child: SwitchListTile.adaptive(
          title: Text(label, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
          subtitle: Text(subtitle, style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
          value: value,
          activeTrackColor: AppColors.primary.withOpacity(0.45),
          activeThumbColor: AppColors.primary,
          onChanged: onChanged,
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        ),
      ),
    );
  }
}

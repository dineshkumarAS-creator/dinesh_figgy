import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:figgy_app/core/navigation/main_tab_scope.dart';
import 'package:figgy_app/theme/app_theme.dart';
import 'package:figgy_app/features/demand/demand_screen.dart';
import 'package:figgy_app/features/radar/radar_screen.dart';
import 'package:figgy_app/features/profile/profile_screen.dart';
import 'package:figgy_app/features/shield/shield_timeline_tab_screen.dart';
import 'package:figgy_app/features/shield/claims_tab_screen.dart';

class MainWrapper extends StatefulWidget {
  final int initialIndex;
  const MainWrapper({super.key, this.initialIndex = 0});

  static MainWrapperState? of(BuildContext context) =>
      context.findAncestorStateOfType<MainWrapperState>();

  void refresh(BuildContext context) {
    context.findAncestorStateOfType<MainWrapperState>()?.refreshState();
  }

  @override
  State<MainWrapper> createState() => MainWrapperState();
}

class MainWrapperState extends State<MainWrapper> {
  late int _currentIndex;
  bool _isLoading = true;
  String _tier = 'Smart';
  String _status = 'inactive';

  final List<GlobalKey<NavigatorState>> _navigatorKeys = [
    GlobalKey<NavigatorState>(),
    GlobalKey<NavigatorState>(),
    GlobalKey<NavigatorState>(),
    GlobalKey<NavigatorState>(),
    GlobalKey<NavigatorState>(),
  ];

  void refreshState() {
    _loadSavedStatus();
  }

  @override
  void initState() {
    super.initState();
    _currentIndex = widget.initialIndex;
    _loadSavedStatus();
  }

  Future<void> _loadSavedStatus() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _tier = (prefs.getString('selected_tier') ?? 'Smart').trim();
      _status = (prefs.getString('policy_status') ?? 'inactive').trim();
      _isLoading = false;
    });
    debugPrint("MainWrapper Loaded: Tier=$_tier, Status=$_status");
  }

  Future<void> _saveIndex(int index) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt('selected_nav_index', index);
  }

  void setIndex(int index) {
    if (_currentIndex == index) {
      _navigatorKeys[index].currentState?.popUntil((route) => route.isFirst);
      return;
    }
    setState(() {
      _currentIndex = index;
    });
    _saveIndex(index);
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator(color: AppColors.brandPrimary)),
      );
    }

    return WillPopScope(
      onWillPop: () async {
        final isFirstRouteInCurrentTab =
            !await _navigatorKeys[_currentIndex].currentState!.maybePop();
        if (isFirstRouteInCurrentTab) {
          if (_currentIndex != 0) {
            setIndex(0);
            return false;
          }
        }
        return isFirstRouteInCurrentTab;
      },
      child: MainTabScope(
        goToTab: setIndex,
        child: Scaffold(
          body: IndexedStack(
            index: _currentIndex,
            children: [
              const DemandScreen(),
              const ShieldTimelineTabScreen(),
              const ClaimsTabScreen(),
              const RadarScreen(),
              const ProfileScreen(),
            ],
          ),
          bottomNavigationBar: _buildBottomNav(),
        ),
      ),
    );
  }


  Widget _buildBottomNav() {
    final bool isElite = _tier.toLowerCase() == 'elite' &&
        (_status.toLowerCase() == 'active' || _status.toLowerCase() == 'scheduled_cancel');

    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: const Border(top: BorderSide(color: AppColors.border)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 10,
            offset: const Offset(0, -4),
          )
        ],
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildNavItem(Icons.home_outlined, 'Home', 0, isElite),
              _buildNavItem(Icons.shield_outlined, 'Shield', 1, isElite),
              _buildNavItem(Icons.receipt_long_outlined, 'Claims', 2, isElite),
              _buildNavItem(Icons.radar_rounded, 'Radar', 3, isElite, hasNotification: true),
              _buildNavItem(Icons.person_outline_rounded, 'Profile', 4, isElite),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildNavItem(IconData icon, String label, int index, bool isElite, {bool hasNotification = false}) {
    final bool isActive = _currentIndex == index;

    final Color brandColor = isElite ? const Color(0xFFFACC15) : AppColors.brandPrimary;
    final Color inactiveColor = AppColors.textSecondary;

    final color = isActive ? brandColor : inactiveColor;

    return Expanded(
      child: InkResponse(
        onTap: () => setIndex(index),
        radius: 35,
        splashColor: color.withOpacity(0.1),
        highlightColor: Colors.transparent,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Stack(
                alignment: Alignment.center,
                clipBehavior: Clip.none,
                children: [
                  if (isActive)
                    Container(
                      width: 44,
                      height: 28,
                      decoration: BoxDecoration(
                        color: brandColor.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(16),
                      ),
                    ),
                  Icon(icon, color: color, size: 22),
                  if (hasNotification && index == 3)
                    Positioned(
                      top: -2,
                      right: -2,
                      child: Container(
                        width: 10,
                        height: 10,
                        decoration: BoxDecoration(
                          color: AppColors.error,
                          shape: BoxShape.circle,
                          border: Border.all(color: AppColors.surface, width: 2),
                          boxShadow: [BoxShadow(color: AppColors.error.withOpacity(0.4), blurRadius: 4)],
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                label,
                style: AppTypography.small.copyWith(
                  fontSize: 10,
                  color: color,
                  fontWeight: isActive ? FontWeight.w800 : FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

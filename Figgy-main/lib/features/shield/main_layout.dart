import 'dart:ui';
import 'package:flutter/material.dart';
import 'screens/my_shield_screen.dart';
import 'screens/claims_screen.dart';
import 'core/theme.dart';
import 'core/notifications.dart';
import 'core/simulation_controller.dart';
import 'widgets/rain_background.dart';
import 'widgets/simulation_bottom_sheet.dart';

class MainLayout extends StatefulWidget {
  const MainLayout({super.key});

  @override
  State<MainLayout> createState() => _MainLayoutState();
}

class _MainLayoutState extends State<MainLayout> {
  int _selectedIndex = 0;
  final SimulationController _simulation = SimulationController();

  @override
  void dispose() {
    _simulation.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return NotificationListener<TabChangeNotification>(
      onNotification: (notification) {
        setState(() {
          _selectedIndex = notification.index;
        });
        return true;
      },
      child: ListenableBuilder(
        listenable: _simulation,
        builder: (context, _) {
          return Scaffold(
            backgroundColor: const Color(0xFFFBFBF5),
            appBar: AppBar(
              backgroundColor: const Color(0xFFFBFBF5),
              elevation: 0,
              scrolledUnderElevation: 0,
              automaticallyImplyLeading: false,
              title: Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Row(
                  children: [
                    if (_selectedIndex == 0)
                      const Text(
                        'figgy',
                        style: TextStyle(
                          color: Color(0xFFE96A10),
                          fontWeight: FontWeight.w900,
                          fontSize: 24,
                          letterSpacing: -1.0,
                        ),
                      )
                    else
                      const SizedBox(width: 48),
                    const Spacer(),
                    Text(
                      _selectedIndex == 0 ? 'My Shield' : 'Your Claims',
                      style: TextStyle(
                        color: Colors.black,
                        fontWeight: FontWeight.w800,
                        fontSize: 18,
                      ),
                    ),
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        shape: BoxShape.circle,
                        border: Border.all(color: Colors.grey.withOpacity(0.2)),
                        boxShadow: [
                          BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 4, offset: const Offset(0, 2)),
                        ],
                      ),
                      child: const Icon(Icons.notifications_none, color: Colors.black54, size: 20),
                    ),
                  ],
                ),
              ),
              centerTitle: false,
              titleSpacing: 0,
            ),
            body: SafeArea(
              child: IndexedStack(
                index: _selectedIndex,
                children: [
                  const MyShieldScreenContent(),
                  const ClaimsScreen(),
                ],
              ),
            ),
            bottomNavigationBar: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 800),
                    child: Container(
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.4),
                        border: Border(top: BorderSide(color: Colors.grey.withOpacity(0.05), width: 1)),
                      ),
                      child: ClipRRect(
                        child: BackdropFilter(
                          filter: ImageFilter.blur(sigmaX: 15, sigmaY: 15),
                          child: BottomNavigationBar(
                            currentIndex: _selectedIndex,
                            selectedItemColor: AppColors.primary,
                            unselectedItemColor: Colors.grey.shade500,
                            selectedLabelStyle: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13),
                            unselectedLabelStyle: const TextStyle(fontSize: 13),
                            type: BottomNavigationBarType.fixed,
                            elevation: 0,
                            backgroundColor: Colors.transparent,
                            onTap: (index) {
                              setState(() {
                                _selectedIndex = index;
                              });
                            },
                            items: const [
                              BottomNavigationBarItem(
                                icon: Padding(padding: EdgeInsets.only(bottom: 6), child: Icon(Icons.home_outlined, size: 26)),
                                activeIcon: Padding(padding: EdgeInsets.only(bottom: 6), child: Icon(Icons.home, size: 26)),
                                label: 'Shield',
                              ),
                              BottomNavigationBarItem(
                                icon: Padding(padding: EdgeInsets.only(bottom: 6), child: Icon(Icons.description_outlined, size: 26)),
                                activeIcon: Padding(padding: EdgeInsets.only(bottom: 6), child: Icon(Icons.description, size: 26)),
                                label: 'Claims',
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

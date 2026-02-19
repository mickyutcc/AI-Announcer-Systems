import 'package:flutter/material.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0F172A), // Dark Slate
        primaryColor: const Color(0xFFA855F7), // Purple Accent
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFFA855F7),
          secondary: Color(0xFFFFD700), // Gold Accent
          surface: Color(0xFF1E293B), // Card Background
        ),
        useMaterial3: true,
        fontFamily: 'Inter',
      ),
      home: const PricingScreen(),
    );
  }
}

class PricingScreen extends StatelessWidget {
  const PricingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header & Balance
              const SizedBox(height: 20),
              Center(
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF334155).withValues(alpha: 0.5),
                    borderRadius: BorderRadius.circular(50),
                    border: Border.all(color: Colors.white10),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: const [
                      Icon(Icons.account_balance_wallet_outlined,
                          color: Color(0xFFFFD700), size: 20),
                      SizedBox(width: 12),
                      Text(
                        'Current Balance: 2002 GG',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 40),

              const Text(
                'Choose Your Plan',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 10),
              const Text(
                'Unlock the full power of AI Music Generation',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 14,
                  color: Colors.white54,
                ),
              ),
              const SizedBox(height: 40),

              // Bento Grid Layout
              // Since Flutter doesn't have a native "Bento" widget, we simulate it with Column/Row or StaggeredGrid.
              // Here, we use a simple responsive layout for clarity.

              // 1. Easy Plan (Full Width)
              PricingCard(
                title: 'Easy Plan',
                price: 'Free',
                features: const ['Get 3 GG free upon signup'],
                buttonText: 'Top up (Min 10 GG)',
                isPrimary: false,
                onTap: () {},
              ),

              const SizedBox(height: 20),

              // 2. Standard Plan (Best Value - Highlighted)
              PricingCard(
                title: 'Standard Plan',
                price: '300 THB',
                subtitle: '2,000 GG (1,800 + 200 Bonus)',
                features: const ['Best Value', 'Mix & Master included'],
                buttonText: 'Get Started',
                isPrimary: true,
                accentColor: const Color(0xFFA855F7), // Purple
                badgeText: 'BEST VALUE',
                onTap: () {},
              ),

              const SizedBox(height: 20),

              // 3. Pro Plan (Premium)
              PricingCard(
                title: 'Pro Plan',
                price: '900 THB',
                subtitle: '6,900 GG',
                features: const [
                  'Full Studio Access',
                  'Voice Clone',
                  'Priority Support'
                ],
                buttonText: 'Go Pro',
                isPrimary: false,
                accentColor: const Color(0xFFFFD700), // Gold
                onTap: () {},
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class PricingCard extends StatefulWidget {
  final String title;
  final String price;
  final String? subtitle;
  final List<String> features;
  final String buttonText;
  final bool isPrimary;
  final Color? accentColor;
  final String? badgeText;
  final VoidCallback onTap;

  const PricingCard({
    super.key,
    required this.title,
    required this.price,
    this.subtitle,
    required this.features,
    required this.buttonText,
    required this.isPrimary,
    this.accentColor,
    this.badgeText,
    required this.onTap,
  });

  @override
  State<PricingCard> createState() => _PricingCardState();
}

class _PricingCardState extends State<PricingCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 100),
      lowerBound: 0.0,
      upperBound: 1.0,
    );
    _scaleAnimation = Tween<double>(begin: 1.0, end: 0.95).animate(_controller);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _onTapDown(TapDownDetails details) {
    _controller.forward();
  }

  void _onTapUp(TapUpDetails details) {
    _controller.reverse();
    widget.onTap();
  }

  void _onTapCancel() {
    _controller.reverse();
  }

  @override
  Widget build(BuildContext context) {
    final bool hasBadge = widget.badgeText != null;
    final Color effectiveAccent = widget.accentColor ?? Colors.white;

    return GestureDetector(
      onTapDown: _onTapDown,
      onTapUp: _onTapUp,
      onTapCancel: _onTapCancel,
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, child) {
          return Transform.scale(
            scale: _scaleAnimation.value,
            child: Stack(
              clipBehavior: Clip.none,
              children: [
                Container(
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E293B),
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(
                      color: widget.isPrimary
                          ? effectiveAccent.withValues(alpha: 0.5)
                          : Colors.white.withValues(alpha: 0.1),
                      width: widget.isPrimary ? 2 : 1,
                    ),
                    boxShadow: widget.isPrimary
                        ? [
                            BoxShadow(
                              color: effectiveAccent.withValues(alpha: 0.15),
                              blurRadius: 20,
                              offset: const Offset(0, 10),
                            )
                          ]
                        : [],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            widget.title,
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w500,
                              color: Colors.white70,
                            ),
                          ),
                          if (widget.isPrimary)
                            Icon(Icons.star_rounded,
                                color: effectiveAccent, size: 24),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Text(
                        widget.price,
                        style: TextStyle(
                          fontSize: 32,
                          fontWeight: FontWeight.bold,
                          color:
                              widget.isPrimary ? effectiveAccent : Colors.white,
                        ),
                      ),
                      if (widget.subtitle != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          widget.subtitle!,
                          style: const TextStyle(
                            fontSize: 14,
                            color: Colors.white54,
                          ),
                        ),
                      ],
                      const SizedBox(height: 24),
                      ...widget.features.map((feature) => Padding(
                            padding: const EdgeInsets.only(bottom: 8.0),
                            child: Row(
                              children: [
                                Icon(Icons.check_circle_rounded,
                                    color: widget.isPrimary
                                        ? effectiveAccent
                                        : Colors.white24,
                                    size: 18),
                                const SizedBox(width: 12),
                                Text(
                                  feature,
                                  style: const TextStyle(
                                      color: Colors.white70, fontSize: 14),
                                ),
                              ],
                            ),
                          )),
                      const SizedBox(height: 24),
                      SizedBox(
                        width: double.infinity,
                        height: 50,
                        child: ElevatedButton(
                          onPressed: () {}, // Handled by GestureDetector
                          style: ElevatedButton.styleFrom(
                            backgroundColor: widget.isPrimary
                                ? effectiveAccent
                                : Colors.white.withValues(alpha: 0.1),
                            foregroundColor:
                                widget.isPrimary ? Colors.black : Colors.white,
                            elevation: 0,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16),
                            ),
                          ),
                          child: Text(
                            widget.buttonText,
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                if (hasBadge)
                  Positioned(
                    top: -12,
                    right: 24,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [
                            effectiveAccent,
                            effectiveAccent.withValues(alpha: 0.8)
                          ],
                        ),
                        borderRadius: BorderRadius.circular(20),
                        boxShadow: [
                          BoxShadow(
                            color: effectiveAccent.withValues(alpha: 0.3),
                            blurRadius: 8,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      child: Text(
                        widget.badgeText!,
                        style: const TextStyle(
                          color: Colors.black,
                          fontWeight: FontWeight.bold,
                          fontSize: 10,
                          letterSpacing: 1,
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

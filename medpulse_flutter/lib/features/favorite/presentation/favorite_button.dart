import 'package:flutter/material.dart';
import '../../../core/auth/auth_service.dart';
import '../../profile/presentation/auth_modal.dart';
import '../data/favorite_service.dart';

/// Global event notifier broadcasting favorite status mutations across widgets.
class FavoriteNotifier {
  static final ValueNotifier<int?> favoriteChangedDrugId = ValueNotifier<int?>(null);

  static void notifyChanged(int drugId) {
    favoriteChangedDrugId.value = drugId;
  }
}

/// Interactive button toggling pharmaceutical bookmark status with
/// optimistic UI handling and automated authentication prompt routing.
class FavoriteButton extends StatefulWidget {
  final int drugId;

  const FavoriteButton({super.key, required this.drugId});

  @override
  State<FavoriteButton> createState() => _FavoriteButtonState();
}

class _FavoriteButtonState extends State<FavoriteButton> {
  bool _isFavorited = false;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    AuthService.authState.addListener(_onAuthChanged);
    FavoriteNotifier.favoriteChangedDrugId.addListener(_onFavoriteChanged);
    _checkInitialStatus();
  }

  @override
  void dispose() {
    AuthService.authState.removeListener(_onAuthChanged);
    FavoriteNotifier.favoriteChangedDrugId.removeListener(_onFavoriteChanged);
    super.dispose();
  }

  /// Sync local bookmark state when an external mutation targeting this drug occurs
  void _onFavoriteChanged() {
    if (!mounted) return;
    final changedDrugId = FavoriteNotifier.favoriteChangedDrugId.value;
    if (changedDrugId == widget.drugId) {
      _checkInitialStatus();
    }
  }

  /// Update state upon global authentication transitions (e.g., login/logout)
  void _onAuthChanged() {
    if (!mounted) return;
    if (!AuthService.authState.value) {
      setState(() {
        _isFavorited = false;
        _isLoading = false;
      });
    } else {
      _checkInitialStatus();
    }
  }

  @override
  void didUpdateWidget(covariant FavoriteButton oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.drugId != widget.drugId) {
      _checkInitialStatus();
    }
  }

  /// Query server to check bookmark status for authenticated user
  Future<void> _checkInitialStatus() async {
    if (widget.drugId == 0) {
      if (mounted) {
        setState(() {
          _isFavorited = false;
          _isLoading = false;
        });
      }
      return;
    }

    try {
      final loggedIn = await AuthService().isLoggedIn();
      if (!mounted) return;

      if (!loggedIn) {
        setState(() {
          _isFavorited = false;
          _isLoading = false;
        });
        return;
      }

      final status = await FavoriteService().isFavorited(widget.drugId);
      if (!mounted) return;

      setState(() {
        _isFavorited = status;
      });
    } catch (e) {
      debugPrint('[FavoriteButton] Check status failed: $e');
      if (!mounted) return;
      setState(() => _isFavorited = false);
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  /// Toggle drug bookmark status or prompt authentication modal if unauthenticated
  Future<void> _toggleFavorite() async {
    if (_isLoading) return;

    // 1. Verify active authentication state
    final loggedIn = await AuthService().isLoggedIn();
    if (!mounted) return;

    // 2. Prompt authentication modal if unauthenticated
    if (!loggedIn) {
      showDialog(
        context: context,
        builder: (context) => AuthModal(
          onAuthSuccess: () {
            if (!mounted) return;
            _checkInitialStatus().then((_) {
              if (mounted) {
                _toggleFavorite();
              }
            });
          },
        ),
      );
      return;
    }

    // 3. Set pending state
    setState(() => _isLoading = true);

    bool success = false;
    final bool previousState = _isFavorited;

    // 4. Dispatch bookmark toggle network request
    if (previousState) {
      success = await FavoriteService().removeFavorite(widget.drugId);
    } else {
      success = await FavoriteService().addFavorite(widget.drugId);
    }

    // 5. Update local state and broadcast event upon response
    if (!mounted) return;

    setState(() {
      _isLoading = false;
      if (success) {
        _isFavorited = !previousState;
      }
    });

    if (success) {
      FavoriteNotifier.notifyChanged(widget.drugId);

      ScaffoldMessenger.of(context).hideCurrentSnackBar();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _isFavorited
                ? 'Drug saved to favorites'
                : 'Drug removed from favorites',
          ),
          duration: const Duration(seconds: 1),
        ),
      );
    } else {
      ScaffoldMessenger.of(context).hideCurrentSnackBar();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Failed to update favorite. Please try again.'),
          backgroundColor: Colors.red,
          duration: Duration(seconds: 2),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const SizedBox(
        width: 24,
        height: 24,
        child: Padding(
          padding: EdgeInsets.all(4.0),
          child: CircularProgressIndicator(
            strokeWidth: 2,
            color: Color(0xFF00796B),
          ),
        ),
      );
    }

    return IconButton(
      icon: Icon(
        _isFavorited ? Icons.favorite : Icons.favorite_border,
        color: _isFavorited ? Colors.red : Colors.grey[600],
      ),
      onPressed: _toggleFavorite,
    );
  }
}
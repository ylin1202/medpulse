import 'package:flutter/material.dart';
import '../../../core/auth/auth_service.dart';
import '../../profile/presentation/auth_modal.dart';
import '../data/favorite_service.dart';

// 建立全域收藏變更通知器
class FavoriteNotifier {
  static final ValueNotifier<int?> favoriteChangedDrugId = ValueNotifier<int?>(null);

  static void notifyChanged(int drugId) {
    favoriteChangedDrugId.value = drugId;
  }
}

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
    // 監聽全域收藏改變事件
    FavoriteNotifier.favoriteChangedDrugId.addListener(_onFavoriteChanged);
    _checkInitialStatus();
  }

  @override
  void dispose() {
    AuthService.authState.removeListener(_onAuthChanged);
    // 銷毀時移除監聽
    FavoriteNotifier.favoriteChangedDrugId.removeListener(_onFavoriteChanged);
    super.dispose();
  }

  // 收到全域收藏改變通知，若改變的 drugId 與自己相同，就重新向後端/快取查詢狀態
  void _onFavoriteChanged() {
    if (!mounted) return;
    final changedDrugId = FavoriteNotifier.favoriteChangedDrugId.value;
    if (changedDrugId == widget.drugId) {
      _checkInitialStatus();
    }
  }

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
      if (!loggedIn) {
        if (mounted) {
          setState(() {
            _isFavorited = false;
            _isLoading = false;
          });
        }
        return;
      }

      final status = await FavoriteService().isFavorited(widget.drugId);
      if (mounted) {
        setState(() {
          _isFavorited = status;
        });
      }
    } catch (e) {
      debugPrint('[FavoriteButton] Check Status Failed: $e');
      if (mounted) {
        setState(() => _isFavorited = false);
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _toggleFavorite() async {
    if (_isLoading) return;

    final loggedIn = await AuthService().isLoggedIn();
    if (!loggedIn) {
      if (!mounted) return;
      showDialog(
        context: context,
        builder: (context) => AuthModal(
          onAuthSuccess: () {
            _checkInitialStatus().then((_) => _toggleFavorite());
          },
        ),
      );
      return;
    }

    setState(() => _isLoading = true);

    bool success = false;
    final bool previousState = _isFavorited;

    if (previousState) {
      success = await FavoriteService().removeFavorite(widget.drugId);
    } else {
      success = await FavoriteService().addFavorite(widget.drugId);
    }

    if (mounted) {
      setState(() {
        _isLoading = false;
        if (success) {
          _isFavorited = !previousState;
        }
      });

      if (success) {
        // 💡 廣播通知全站：這個 drugId 的收藏狀態更新了！
        FavoriteNotifier.notifyChanged(widget.drugId);

        ScaffoldMessenger.of(context).hideCurrentSnackBar();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(_isFavorited ? 'Drug saved to favorites' : 'Drug removed from favorites'),
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
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const SizedBox(
        width: 24,
        height: 24,
        child: Padding(
          padding: EdgeInsets.all(4.0),
          child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF00796B)),
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
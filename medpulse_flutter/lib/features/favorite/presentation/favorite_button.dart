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
      // 若已 unmount，直接中斷執行，不發送多餘請求
      if (!mounted) return;

      if (!loggedIn) {
        setState(() {
          _isFavorited = false;
          _isLoading = false;
        });
        return;
      }

      final status = await FavoriteService().isFavorited(widget.drugId);
      // 2：第二次 await 結束後再次驗證掛載狀態
      if (!mounted) return;

      setState(() {
        _isFavorited = status;
      });
    } catch (e) {
      debugPrint('[FavoriteButton] Check Status Failed: $e');
      if (!mounted) return;
      setState(() => _isFavorited = false);
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

 Future<void> _toggleFavorite() async {
    if (_isLoading) return;

    // 1. 檢查登入狀態
    final loggedIn = await AuthService().isLoggedIn();
    if (!mounted) return; 

    // 2. 未登入則彈出 Modal
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

    // 3. 設定 Loading 狀態
    setState(() => _isLoading = true);

    bool success = false;
    final bool previousState = _isFavorited;

    // 4. 發送 API 請求
    if (previousState) {
      success = await FavoriteService().removeFavorite(widget.drugId);
    } else {
      success = await FavoriteService().addFavorite(widget.drugId);
    }

    // 5. 請求完成後的防護與狀態更新
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
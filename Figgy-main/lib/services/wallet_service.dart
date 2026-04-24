import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

class WalletTransaction {
  final String id; // unique, used for de-dupe
  final int amountInr; // +credit, -debit
  final String reason; // user-visible
  final String category; // premium | payout | adjustment | other
  final DateTime createdAt;
  final String? refId; // optional: claimId/orderId/etc

  const WalletTransaction({
    required this.id,
    required this.amountInr,
    required this.reason,
    required this.category,
    required this.createdAt,
    this.refId,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'amount_inr': amountInr,
        'reason': reason,
        'category': category,
        'created_at': createdAt.toIso8601String(),
        'ref_id': refId,
      };

  factory WalletTransaction.fromJson(Map<String, dynamic> json) {
    return WalletTransaction(
      id: (json['id'] as String?) ?? '',
      amountInr: (json['amount_inr'] as num?)?.toInt() ?? 0,
      reason: (json['reason'] as String?) ?? '',
      category: (json['category'] as String?) ?? 'other',
      createdAt: DateTime.tryParse((json['created_at'] as String?) ?? '') ?? DateTime.now(),
      refId: json['ref_id'] as String?,
    );
  }
}

class WalletService {
  static const _kTxKey = 'wallet_transactions_v1';

  Future<List<WalletTransaction>> getTransactions() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_kTxKey);
    if (raw == null || raw.isEmpty) return [];
    try {
      final list = (jsonDecode(raw) as List).cast<dynamic>();
      final txs = list
          .map((e) => WalletTransaction.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList();
      txs.sort((a, b) => b.createdAt.compareTo(a.createdAt));
      return txs;
    } catch (_) {
      return [];
    }
  }

  Future<int> getBalanceInr() async {
    final txs = await getTransactions();
    return txs.fold<int>(0, (sum, t) => sum + t.amountInr);
  }

  Future<void> addTransaction(WalletTransaction tx) async {
    final prefs = await SharedPreferences.getInstance();
    final existing = await getTransactions();
    // De-dupe by id
    if (existing.any((e) => e.id == tx.id)) return;

    final updated = [tx, ...existing];
    await prefs.setString(_kTxKey, jsonEncode(updated.map((e) => e.toJson()).toList()));
  }
}


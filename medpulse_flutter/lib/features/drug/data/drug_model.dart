/// 藥品資料模型
class DrugModel {
  final String id;
  final String brandName;       // 商品名
  final String genericName;     // 通用名/學名
  final String manufacturer;    // 製造商
  final String indications;     // 適應症/用途
  final String dosage;          // 用法用量
  final String warnings;        // 警示與禁忌
  final String adverseReactions; // 副作用

  DrugModel({
    required this.id,
    required this.brandName,
    required this.genericName,
    required this.manufacturer,
    required this.indications,
    required this.dosage,
    required this.warnings,
    required this.adverseReactions,
  });

  /// 輔助函式：安全解析可能是 String 或 List<dynamic> 的 JSON 欄位
  static String _parseField(dynamic rawValue, {String defaultValue = 'No information provided.'}) {
    if (rawValue == null) return defaultValue;
    if (rawValue is String) {
      final trimmed = rawValue.trim();
      return trimmed.isNotEmpty ? trimmed : defaultValue;
    }
    if (rawValue is List && rawValue.isNotEmpty) {
      final joined = rawValue.map((e) => e.toString().trim()).where((s) => s.isNotEmpty).join('\n\n');
      return joined.isNotEmpty ? joined : defaultValue;
    }
    return defaultValue;
  }

  factory DrugModel.fromJson(Map<String, dynamic> json) {
    // 考慮 openfda 巢狀結構與展平結構
    final openfda = json['openfda'] as Map<String, dynamic>? ?? {};

    // 1. Brand Name
    String brand = _parseField(json['brand_name'], defaultValue: '');
    if (brand == 'No information provided.' || brand.isEmpty) {
      brand = _parseField(openfda['brand_name'], defaultValue: 'Unknown Brand');
    }

    // 2. Generic Name
    String generic = _parseField(json['generic_name'], defaultValue: '');
    if (generic == 'No information provided.' || generic.isEmpty) {
      generic = _parseField(openfda['generic_name'], defaultValue: 'N/A');
    }

    // 3. Manufacturer
    String mfr = _parseField(json['manufacturer_name'], defaultValue: '');
    if (mfr == 'No information provided.' || mfr.isEmpty) {
      mfr = _parseField(openfda['manufacturer_name'], defaultValue: 'Unknown Manufacturer');
    }

    return DrugModel(
      id: json['id']?.toString() ?? json['_id']?.toString() ?? '',
      brandName: brand,
      genericName: generic,
      manufacturer: mfr,
      // 試取常見的 openFDA 欄位名稱
      indications: _parseField(json['indications_and_usage'] ?? json['indications'] ?? json['purpose']),
      dosage: _parseField(json['dosage_and_administration'] ?? json['dosage'] ?? json['instructions']),
      warnings: _parseField(json['warnings'] ?? json['warnings_and_cautions'] ?? json['precautions']),
      adverseReactions: _parseField(json['adverse_reactions'] ?? json['side_effects']),
    );
  }
}
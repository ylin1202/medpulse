class DrugModel {
  final String id;
  final String brandName; // Proprietary/trade name
  final String genericName; // International Nonproprietary Name (INN) / chemical name
  final String manufacturer; // Marketing authorization holder or pharmaceutical manufacturer
  final String indications; // Approved clinical indications and therapeutic usage
  final String dosage; // Recommended dosage and administration guidelines
  final String warnings; // Boxed warnings, contraindications, and clinical precautions
  final String adverseReactions; // Documented adverse drug reactions and side effects

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

  /// Helper parsing dynamic fields that may appear as raw strings or serialized arrays.
  static String _parseField(
    dynamic rawValue, {
    String defaultValue = 'No information provided.',
  }) {
    if (rawValue == null) return defaultValue;
    if (rawValue is String) {
      final trimmed = rawValue.trim();
      return trimmed.isNotEmpty ? trimmed : defaultValue;
    }
    if (rawValue is List && rawValue.isNotEmpty) {
      final joined = rawValue
          .map((e) => e.toString().trim())
          .where((s) => s.isNotEmpty)
          .join('\n\n');
      return joined.isNotEmpty ? joined : defaultValue;
    }
    return defaultValue;
  }

  factory DrugModel.fromJson(Map<String, dynamic> json) {
    // Handle nested OpenFDA metadata structure with fallback to flat schemas
    final openfda = json['openfda'] as Map<String, dynamic>? ?? {};

    // 1. Proprietary Brand Name
    String brand = _parseField(json['brand_name'], defaultValue: '');
    if (brand == 'No information provided.' || brand.isEmpty) {
      brand = _parseField(openfda['brand_name'], defaultValue: 'Unknown Brand');
    }

    // 2. Generic / Chemical Name
    String generic = _parseField(json['generic_name'], defaultValue: '');
    if (generic == 'No information provided.' || generic.isEmpty) {
      generic = _parseField(openfda['generic_name'], defaultValue: 'N/A');
    }

    // 3. Manufacturer Name
    String mfr = _parseField(json['manufacturer_name'], defaultValue: '');
    if (mfr == 'No information provided.' || mfr.isEmpty) {
      mfr = _parseField(
        openfda['manufacturer_name'],
        defaultValue: 'Unknown Manufacturer',
      );
    }

    return DrugModel(
      id:
          json['id']?.toString() ??
          json['drug_id']?.toString() ??
          json['_id']?.toString() ??
          '',
      brandName: brand,
      genericName: generic,
      manufacturer: mfr,
      indications: _parseField(
        json['indications_and_usage'] ?? json['indications'] ?? json['purpose'],
      ),
      dosage: _parseField(
        json['dosage_and_administration'] ??
            json['dosage'] ??
            json['instructions'],
      ),
      warnings: _parseField(
        json['warnings'] ??
            json['warnings_and_cautions'] ??
            json['precautions'],
      ),
      adverseReactions: _parseField(
        json['adverse_reactions'] ?? json['side_effects'],
      ),
    );
  }
}
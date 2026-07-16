import 'package:google_maps_flutter/google_maps_flutter.dart';

/// 藥局資料模型
class PharmacyModel {
  final int id;
  final String name;
  final String status;
  final String city;
  final String district;
  final String address;
  final String phone;
  final bool isNhiContracted;
  final double latitude;
  final double longitude;

  PharmacyModel({
    required this.id,
    required this.name,
    required this.status,
    required this.city,
    required this.district,
    required this.address,
    required this.phone,
    required this.isNhiContracted,
    required this.latitude,
    required this.longitude,
  });

  LatLng get location => LatLng(latitude, longitude);

  factory PharmacyModel.fromJson(Map<String, dynamic> json) {
    return PharmacyModel(
      id: json['id'] ?? 0,
      name: json['name'] ?? '',
      status: json['status'] ?? '',
      city: json['city'] ?? '',
      district: json['district'] ?? '',
      address: json['address'] ?? '',
      phone: json['phone'] ?? '',
      isNhiContracted: json['is_nhi_contracted'] ?? true,
      latitude: (json['latitude'] as num?)?.toDouble() ?? 25.0330,
      longitude: (json['longitude'] as num?)?.toDouble() ?? 121.5654,
    );
  }
}
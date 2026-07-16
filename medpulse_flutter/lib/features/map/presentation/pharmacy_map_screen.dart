import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

import '../../../../core/network/api_client.dart';
import '../data/pharmacy_model.dart';

/// 台灣主要縣市資料模型
class CityOption {
  final String label;   // UI 顯示的中英文名稱
  final String? value;  
  final LatLng center;  // 切換該縣市時地圖鏡頭移動的中心點
  final double zoom;    // 預設適合的縮放比例

  const CityOption({
    required this.label,
    required this.value,
    required this.center,
    this.zoom = 13.0,
  });
}

// 台灣主要縣市對照清單
const List<CityOption> cityOptions = [
  CityOption(
    label: 'Taipei City (臺北市)',
    value: '臺北市',
    center: LatLng(25.0375, 121.5637),
    zoom: 13.0,
  ),
  CityOption(
    label: 'New Taipei City (新北市)',
    value: '新北市',
    center: LatLng(25.0118, 121.4658),
    zoom: 12.0,
  ),
  CityOption(
    label: 'Keelung City (基隆市)',
    value: '基隆市',
    center: LatLng(25.1283, 121.7419),
    zoom: 13.0,
  ),
  CityOption(
    label: 'Taoyuan City (桃園市)',
    value: '桃園市',
    center: LatLng(24.9936, 121.3010),
    zoom: 12.0,
  ),
  CityOption(
    label: 'Hsinchu City (新竹市)',
    value: '新竹市',
    center: LatLng(24.8138, 120.9675),
    zoom: 13.0,
  ),
  CityOption(
    label: 'Taichung City (臺中市)',
    value: '臺中市',
    center: LatLng(24.1477, 120.6736),
    zoom: 12.5,
  ),
  CityOption(
    label: 'Tainan City (臺南市)',
    value: '臺南市',
    center: LatLng(22.9997, 120.2270),
    zoom: 12.5,
  ),
  CityOption(
    label: 'Kaohsiung City (高雄市)',
    value: '高雄市',
    center: LatLng(22.6273, 120.3014),
    zoom: 12.5,
  ),
  CityOption(
    label: 'Yilan County (宜蘭縣)',
    value: '宜蘭縣',
    center: LatLng(24.7570, 121.7530),
    zoom: 12.0,
  ),
  CityOption(
    label: 'Hualien County (花蓮縣)',
    value: '花蓮縣',
    center: LatLng(23.9871, 121.6015),
    zoom: 11.5,
  ),
  CityOption(
    label: 'Taitung County (臺東縣)',
    value: '臺東縣',
    center: LatLng(22.7583, 121.1444),
    zoom: 11.5,
  ),
];

class PharmacyMapScreen extends StatefulWidget {
  const PharmacyMapScreen({super.key});

  @override
  State<PharmacyMapScreen> createState() => _PharmacyMapScreenState();
}

class _PharmacyMapScreenState extends State<PharmacyMapScreen> {
  GoogleMapController? _mapController;

  List<PharmacyModel> _pharmacies = [];
  Set<Marker> _markers = {};
  Set<ClusterManager> _clusterManagers = {};
  bool _isLoading = true;
  PharmacyModel? _selectedPharmacy;

  // 當前選中的縣市 (預設全台灣 All Taiwan)
  CityOption _selectedCity = cityOptions[0];

  // 官方 Cluster 管理器 ID
  static const ClusterManagerId _clusterManagerId = ClusterManagerId('pharmacy_cluster');

  @override
  void initState() {
    super.initState();
    _initClusterManager();
    _fetchPharmacies();
  }

  /// 初始化 Google 官方原生的 ClusterManager
  void _initClusterManager() {
    _clusterManagers = {
      ClusterManager(
        clusterManagerId: _clusterManagerId,
        onClusterTap: (Cluster cluster) {
          _mapController?.animateCamera(
            CameraUpdate.newLatLngZoom(cluster.position, 14.5),
          );
        },
      ),
    };
  }

  /// 向 Flask API 請求藥局資料 (支援帶入 ?city=xxx 參數)
  Future<void> _fetchPharmacies() async {
    setState(() => _isLoading = true);

    try {
      final Map<String, dynamic> queryParams = {};
      if (_selectedCity.value != null) {
        queryParams['city'] = _selectedCity.value;
      }

      final response = await ApiClient().dio.get(
        '/pharmacies',
        queryParameters: queryParams,
      );

      if (response.statusCode == 200) {
        final List rawData = response.data['data'] ?? [];
        final items = rawData.map((e) => PharmacyModel.fromJson(e)).toList();

        // 轉換成綁定 ClusterManagerId 的原生 Markers
        final markers = items.map((pharmacy) {
          return Marker(
            markerId: MarkerId('pharmacy_${pharmacy.id}'),
            position: pharmacy.location,
            clusterManagerId: _clusterManagerId, // 💡 自動交給官方原生的 ClusterManager 計算
            infoWindow: InfoWindow(
              title: pharmacy.name,
              snippet: pharmacy.address,
            ),
            icon: BitmapDescriptor.defaultMarkerWithHue(
              pharmacy.isNhiContracted
                  ? BitmapDescriptor.hueGreen
                  : BitmapDescriptor.hueRed,
            ),
            onTap: () {
              setState(() {
                _selectedPharmacy = pharmacy;
              });
            },
          );
        }).toSet();

        setState(() {
          _pharmacies = items;
          _markers = markers;
          _isLoading = false;
        });
      }
    } catch (e) {
      print('❌ [Map Error] Failed to load pharmacies: $e');
      setState(() => _isLoading = false);
    }
  }

  /// 移動地圖鏡頭至指定縣市
  void _moveCameraToCity(CityOption city) {
    _mapController?.animateCamera(
      CameraUpdate.newLatLngZoom(city.center, city.zoom),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Pharmacy Finder Map', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFF00796B),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _fetchPharmacies,
          )
        ],
      ),
      body: Stack(
        children: [
          // 1. 全螢幕 Google Maps
          GoogleMap(
            initialCameraPosition: CameraPosition(
              target: _selectedCity.center,
              zoom: _selectedCity.zoom,
            ),
            markers: _markers,
            clusterManagers: _clusterManagers, // 💡 使用 Google 官方原生的聚類管理器
            myLocationEnabled: true,
            myLocationButtonEnabled: true,
            onMapCreated: (controller) {
              _mapController = controller;
            },
            onTap: (_) {
              setState(() => _selectedPharmacy = null);
            },
          ),

          // 2. 頂部懸浮中英文縣市選擇器 (City Dropdown Selector)
          Positioned(
            top: 12,
            left: 16,
            right: 16,
            child: Card(
              elevation: 4,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              color: Colors.white,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                child: Row(
                  children: [
                    const Icon(Icons.location_city, color: Color(0xFF00796B)),
                    const SizedBox(width: 12),
                    Expanded(
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton<CityOption>(
                          value: _selectedCity,
                          isExpanded: true,
                          style: const TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                            color: Colors.black87,
                          ),
                          items: cityOptions.map((city) {
                            return DropdownMenuItem<CityOption>(
                              value: city,
                              child: Text(city.label),
                            );
                          }).toList(),
                          onChanged: (newCity) {
                            if (newCity != null) {
                              setState(() {
                                _selectedCity = newCity;
                                _selectedPharmacy = null;
                              });
                              _fetchPharmacies(); // 打 API 抓取該縣市資料
                              _moveCameraToCity(newCity); // 鏡頭動畫飛往該縣市
                            }
                          },
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),

          // 3. 載入中指示器
          if (_isLoading)
            const Center(
              child: CircularProgressIndicator(color: Color(0xFF00796B)),
            ),

          // 4. 點擊藥局時彈出的詳細資訊卡片
          if (_selectedPharmacy != null)
            Positioned(
              bottom: 20,
              left: 16,
              right: 16,
              child: Card(
                elevation: 6,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(
                            child: Text(
                              _selectedPharmacy!.name,
                              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          Chip(
                            label: Text(
                              _selectedPharmacy!.isNhiContracted ? 'NHI Contracted' : 'Non-NHI',
                              style: const TextStyle(color: Colors.white, fontSize: 12),
                            ),
                            backgroundColor: _selectedPharmacy!.isNhiContracted
                                ? const Color(0xFF00796B)
                                : Colors.grey,
                          )
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          const Icon(Icons.location_on_outlined, size: 18, color: Colors.grey),
                          const SizedBox(width: 4),
                          Expanded(
                            child: Text(
                              _selectedPharmacy!.address,
                              style: const TextStyle(color: Colors.black87),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          const Icon(Icons.phone_outlined, size: 18, color: Colors.grey),
                          const SizedBox(width: 4),
                          Text(_selectedPharmacy!.phone, style: const TextStyle(color: Colors.black87)),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
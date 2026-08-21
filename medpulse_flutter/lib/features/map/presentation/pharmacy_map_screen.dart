import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

import '../../../../core/network/api_client.dart';
import '../data/pharmacy_model.dart';

/// Administrative division and geospatial viewport model for Taiwanese municipalities.
class CityOption {
  final String label; // UI display label
  final String? value; // API query parameter
  final LatLng center; // Geospatial camera anchor coordinates
  final double zoom; // Optimal map viewport zoom level

  const CityOption({
    required this.label,
    required this.value,
    required this.center,
    this.zoom = 13.0,
  });
}

/// Normalized geographic coordinates and administrative boundaries for Taiwan municipalities.
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

/// Screen presenting an interactive geospatial locator for community pharmacies,
/// featuring native point clustering, NHI contract status filtering, and modal detail views.
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

  // Active selected administrative region
  CityOption _selectedCity = cityOptions[0];

  // Native map clustering manager identifier
  static const ClusterManagerId _clusterManagerId = ClusterManagerId(
    'pharmacy_cluster',
  );

  @override
  void initState() {
    super.initState();
    _initClusterManager();
    _fetchPharmacies();
  }

  /// Initialize Google Maps native marker clustering manager.
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

  /// Query backend for geospatial pharmacy coordinates by administrative region (GET /api/v1/pharmacies).
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

        final markers = items.map((pharmacy) {
          return Marker(
            markerId: MarkerId('pharmacy_${pharmacy.id}'),
            position: pharmacy.location,
            clusterManagerId: _clusterManagerId,
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
      debugPrint('[Pharmacy Map Error] Failed to load pharmacies: $e');
      setState(() => _isLoading = false);
    }
  }

  /// Animate camera viewport to target administrative coordinates.
  void _moveCameraToCity(CityOption city) {
    _mapController?.animateCamera(
      CameraUpdate.newLatLngZoom(city.center, city.zoom),
    );
  }

  @override
  Widget build(BuildContext context) {
    final double topSafeArea = MediaQuery.of(context).padding.top;

    return Scaffold(
      resizeToAvoidBottomInset: false,
      body: Stack(
        children: [
          // 1. Fullscreen Google Maps Canvas
          GoogleMap(
            initialCameraPosition: CameraPosition(
              target: _selectedCity.center,
              zoom: _selectedCity.zoom,
            ),
            markers: _markers,
            clusterManagers: _clusterManagers,
            myLocationEnabled: true,
            myLocationButtonEnabled: true,
            padding: const EdgeInsets.only(top: 90, bottom: 20),
            onMapCreated: (controller) {
              _mapController = controller;
            },
            onTap: (_) {
              setState(() => _selectedPharmacy = null);
            },
          ),

          // 2. Floating Location Selection & Action Header Bar
          Positioned(
            top: topSafeArea + 12,
            left: 16,
            right: 16,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.12),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.local_pharmacy,
                    color: Color(0xFF00796B),
                    size: 24,
                  ),
                  const SizedBox(width: 10),

                  // Municipality Dropdown Selector
                  Expanded(
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<CityOption>(
                        value: _selectedCity,
                        isExpanded: true,
                        icon: const Icon(
                          Icons.arrow_drop_down,
                          color: Color(0xFF00796B),
                        ),
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                          color: Colors.black87,
                        ),
                        items: cityOptions.map((city) {
                          return DropdownMenuItem<CityOption>(
                            value: city,
                            child: Text(
                              city.label,
                              overflow: TextOverflow.ellipsis,
                            ),
                          );
                        }).toList(),
                        onChanged: (newCity) {
                          if (newCity != null) {
                            setState(() {
                              _selectedCity = newCity;
                              _selectedPharmacy = null;
                            });
                            _fetchPharmacies();
                            _moveCameraToCity(newCity);
                          }
                        },
                      ),
                    ),
                  ),

                  const SizedBox(width: 4),
                  const VerticalDivider(
                    width: 1,
                    indent: 8,
                    endIndent: 8,
                    color: Colors.grey,
                  ),
                  const SizedBox(width: 4),

                  // Refresh Indicator / Action Button
                  IconButton(
                    icon: _isLoading
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                              color: Color(0xFF00796B),
                              strokeWidth: 2,
                            ),
                          )
                        : const Icon(
                            Icons.refresh,
                            color: Color(0xFF00796B),
                            size: 22,
                          ),
                    tooltip: 'Refresh Pharmacies',
                    onPressed: _isLoading ? null : _fetchPharmacies,
                  ),
                ],
              ),
            ),
          ),

          // 3. Selected Pharmacy Metadata Bottom Sheet
          if (_selectedPharmacy != null)
            Positioned(
              bottom: 24,
              left: 16,
              right: 16,
              child: Card(
                elevation: 8,
                shadowColor: Colors.black26,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
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
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          Chip(
                            padding: EdgeInsets.zero,
                            label: Text(
                              _selectedPharmacy!.isNhiContracted
                                  ? 'NHI Contracted'
                                  : 'Non-NHI',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            backgroundColor: _selectedPharmacy!.isNhiContracted
                                ? const Color(0xFF00796B)
                                : Colors.grey,
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          const Icon(
                            Icons.location_on_outlined,
                            size: 18,
                            color: Colors.grey,
                          ),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              _selectedPharmacy!.address,
                              style: const TextStyle(color: Colors.black87),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Row(
                        children: [
                          const Icon(
                            Icons.phone_outlined,
                            size: 18,
                            color: Colors.grey,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            _selectedPharmacy!.phone,
                            style: const TextStyle(color: Colors.black87),
                          ),
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
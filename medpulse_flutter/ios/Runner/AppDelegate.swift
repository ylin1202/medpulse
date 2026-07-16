import UIKit
import Flutter
import GoogleMaps

@main
@objc class AppDelegate: FlutterAppDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    
    let controller : FlutterViewController = window?.rootViewController as! FlutterViewController
    let channel = FlutterMethodChannel(name: "com.medpulse.app/config",
                                              binaryMessenger: controller.binaryMessenger)
    
    // 接收 Flutter 端傳過來的 API Key 並提供給 Google Maps SDK
    channel.setMethodCallHandler({
      (call: FlutterMethodCall, result: @escaping FlutterResult) -> Void in
      if call.method == "setGoogleMapsKey" {
        if let args = call.arguments as? [String: Any],
           let apiKey = args["key"] as? String {
          GMSServices.provideAPIKey(apiKey)
          result(true)
        } else {
          result(FlutterError(code: "INVALID_KEY", message: "API Key is missing", details: nil))
        }
      } else {
        result(FlutterMethodNotImplemented)
      }
    })

    GeneratedPluginRegistrant.register(with: self)
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }
}
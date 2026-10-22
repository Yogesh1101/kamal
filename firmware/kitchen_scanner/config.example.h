// Copy this file to config.h (same folder) and fill in your values.
// config.h is git-ignored because it holds the Wi-Fi password.

#pragma once

// Wi-Fi the laptop is also on (the ESP32 only supports 2.4 GHz).
#define WIFI_SSID     "your-wifi-name"
#define WIFI_PASSWORD "your-wifi-password"

// Laptop running the backend: `uvicorn` must listen on 0.0.0.0, not just 127.0.0.1.
// Find the laptop's IP with `hostname -I`. It changes between networks.
// Write it as http://<ip>:8000 with no trailing slash.
#define SERVER_URL "http://192.168.0.135:8000"

// Serial link to the scanner module. GM65 and GM861 both default to 9600 8N1,
// but the GM861 default is unconfirmed, so check it with SCANNER_DEBUG first.
#define SCANNER_BAUD   9600
#define SCANNER_RX_PIN 16   // ESP32 pin that receives, wired to the module's TXD
#define SCANNER_TX_PIN 17   // ESP32 pin that transmits, wired to the module's RXD

// Scan feedback. Set BUZZER_PIN to -1 if there is no buzzer.
#define STATUS_LED_PIN 2    // on-board LED on most ESP32 DevKit boards
#define BUZZER_PIN     -1

// 1 = print every frame from the module (text and hex) on the USB serial monitor.
#define SCANNER_DEBUG 1

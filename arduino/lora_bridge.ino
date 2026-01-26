#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <SPI.h>
#include <LoRa.h>
#include <ArduinoJson.h>

// ======================
// LoRa Pin Configuration (ESP8266)
// ======================
// Adjust according to your wiring
#define SS    D8   // GPIO15 (CS/NSS)
#define RST   D0   // GPIO16 (RESET)
#define DIO0  D2   // GPIO4  (DIO0)

#define LORA_FREQ 433E6  // SX1278 frequency

// ======================
// Wi-Fi AP Configuration
// ======================
const char* AP_SSID = "ESP8266_LoRa_AP";
const char* AP_PASSWORD = "12345678";

// Pi server to forward LoRa data
const char* SERVER_IP = "192.168.4.2";
const int SERVER_PORT = 5000;

// Status LED (NodeMCU / ESP-12)
#define STATUS_LED LED_BUILTIN

// ======================
// Statistics
// ======================
unsigned long packetsReceived = 0;
unsigned long packetsForwarded = 0;
unsigned long packetsFailed = 0;
unsigned long lastStatsReport = 0;
const unsigned long STATS_REPORT_INTERVAL = 300000; // 5 min

// ======================
// Setup
// ======================
void setup() {
  Serial.begin(115200);
  pinMode(STATUS_LED, OUTPUT);
  digitalWrite(STATUS_LED, HIGH); // LED off (active LOW)

  Serial.println("\n=== LoRa + AP Bridge (ESP8266) Starting ===");

  // Initialize LoRa
  Serial.println("Initializing LoRa...");
  LoRa.setPins(SS, RST, DIO0);
  if (!LoRa.begin(LORA_FREQ)) {
    Serial.println("ERROR: LoRa init failed! AP will not start.");
    while (1) {
      digitalWrite(STATUS_LED, LOW);
      delay(200);
      digitalWrite(STATUS_LED, HIGH);
      delay(200);
    }
  }
  Serial.println("✓ LoRa initialized");

  // Configure LoRa parameters
  LoRa.setSpreadingFactor(12);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);

  // Start Wi-Fi AP
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASSWORD);

  Serial.println("AP started: " + String(AP_SSID));
  Serial.print("AP IP address: ");
  Serial.println(WiFi.softAPIP());

  Serial.println("=== Setup complete ===");
}

// ======================
// Main loop
// ======================
void loop() {
  unsigned long currentTime = millis();

  if (currentTime - lastStatsReport >= STATS_REPORT_INTERVAL) {
    lastStatsReport = currentTime;
    printStatistics();
  }

  // Handle incoming LoRa packets
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    packetsReceived++;
    digitalWrite(STATUS_LED, LOW);  // LED ON

    String receivedData = "";
    while (LoRa.available()) {
      receivedData += (char)LoRa.read();
    }

    int rssi = LoRa.packetRssi();
    float snr = LoRa.packetSnr();

    Serial.println("\n--- LoRa Packet Received ---");
    Serial.println("Packet #" + String(packetsReceived));
    Serial.println("Size: " + String(packetSize));
    Serial.println("Data: " + receivedData);
    Serial.println("RSSI: " + String(rssi) + " dBm");
    Serial.println("SNR: " + String(snr) + " dB");
    Serial.println("---------------------------\n");

    if (isValidJSON(receivedData)) {
      bool success = forwardToServer(receivedData, rssi, snr);
      if (success) packetsForwarded++;
      else packetsFailed++;
    } else {
      Serial.println("ERROR: Invalid JSON received");
      packetsFailed++;
    }

    digitalWrite(STATUS_LED, HIGH);  // LED OFF
  }

  delay(10);
}

// ======================
// JSON validation
// ======================
bool isValidJSON(String jsonString) {
  StaticJsonDocument<300> doc;
  DeserializationError error = deserializeJson(doc, jsonString);
  if (error) return false;
  if (!doc.containsKey("id")) return false;
  return true;
}

// ======================
// Forward LoRa data to Pi
// ======================
bool forwardToServer(String jsonData, int rssi, float snr) {
  WiFiClient client;
  HTTPClient http;

  String url = "http://" + String(SERVER_IP) + ":" + String(SERVER_PORT) + "/api/sensor-data";
  http.begin(client, url);
  http.addHeader("Content-Type", "application/json");

  // Enrich JSON
  StaticJsonDocument<350> doc;
  deserializeJson(doc, jsonData);
  doc["rssi"] = rssi;
  doc["snr"] = snr;
  doc["bridge_time"] = millis();

  String enrichedJson;
  serializeJson(doc, enrichedJson);

  int httpCode = http.POST(enrichedJson);
  bool success = (httpCode > 0 && httpCode < 300);

  if (success) {
    Serial.println("✓ Data forwarded, HTTP code: " + String(httpCode));
  } else {
    Serial.println("✗ Failed to forward data, HTTP code: " + String(httpCode));
  }

  http.end();
  return success;
}

// ======================
// Print statistics
// ======================
void printStatistics() {
  Serial.println("\n========== STATISTICS ==========");
  Serial.println("Uptime: " + String(millis() / 1000) + " sec");
  Serial.println("Packets Received: " + String(packetsReceived));
  Serial.println("Packets Forwarded: " + String(packetsForwarded));
  Serial.println("Packets Failed: " + String(packetsFailed));
  Serial.println("AP IP: " + WiFi.softAPIP().toString());
  Serial.println("================================\n");
}

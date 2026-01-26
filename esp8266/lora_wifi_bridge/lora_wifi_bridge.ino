#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <SPI.h>
#include <LoRa.h>
#include <ArduinoJson.h>

// WiFi Configuration
const char* WIFI_SSID = "Wapday";     // Replace with your WiFi network name
const char* WIFI_PASSWORD = "B1ueL0nd@n1412!"; // Replace with your WiFi password

// Server Configuration
const char* SERVER_URL = "http://192.168.1.100:5000/api/sensor-data";  // Update with your server IP

// LoRa Pin Configuration for ESP8266
#define SS    15   // D8
#define RST   16   // D0
#define DIO0  4    // D2

// Status LED
#define STATUS_LED LED_BUILTIN  // Built-in LED

// WiFi reconnection settings
unsigned long lastWiFiCheck = 0;
const unsigned long WIFI_CHECK_INTERVAL = 30000; // Check WiFi every 30 seconds

unsigned long packetsReceived = 0;
unsigned long packetsForwarded = 0;
unsigned long packetsFailed = 0;
unsigned long lastStatsReport = 0;
const unsigned long STATS_REPORT_INTERVAL = 300000; // Report stats every 5 minutes

void setup() {
  Serial.begin(9600);
  while (!Serial);
  
  pinMode(STATUS_LED, OUTPUT);
  digitalWrite(STATUS_LED, HIGH); // LED off initially (inverted on ESP8266)
  
  Serial.println("\n\n=================================");
  Serial.println("LoRa WiFi Bridge Starting...");
  Serial.println("=================================\n");
  
  // Initialize LoRa
  Serial.println("Initializing LoRa...");
  LoRa.setPins(SS, RST, DIO0);
  
  if (!LoRa.begin(433E6)) {  // 433 MHz frequency
    Serial.println("ERROR: Starting LoRa failed!");
    while (1) {
      digitalWrite(STATUS_LED, LOW);
      delay(200);
      digitalWrite(STATUS_LED, HIGH);
      delay(200);
    }
  }
  
  // Configure LoRa parameters (must match transmitter)
  LoRa.setSpreadingFactor(12);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);
  
  Serial.println("✓ LoRa initialized successfully");
  
  // Connect to WiFi
  connectToWiFi();
  
  Serial.println("\n=================================");
  Serial.println("LoRa WiFi Bridge Ready!");
  Serial.println("Listening for sensor data...");
  Serial.println("=================================\n");
}

void loop() {
  unsigned long currentTime = millis();
  
  // Check WiFi connection periodically
  if (currentTime - lastWiFiCheck >= WIFI_CHECK_INTERVAL) {
    lastWiFiCheck = currentTime;
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("WiFi disconnected! Reconnecting...");
      connectToWiFi();
    }
  }
  
  if (currentTime - lastStatsReport >= STATS_REPORT_INTERVAL) {
    lastStatsReport = currentTime;
    printStatistics();
  }
  
  // Check for incoming LoRa packets
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    packetsReceived++;
    
    // Blink LED to indicate packet received
    digitalWrite(STATUS_LED, LOW);  // LED on
    
    // Read the packet
    String receivedData = "";
    while (LoRa.available()) {
      receivedData += (char)LoRa.read();
    }
    
    // Get RSSI (signal strength)
    int rssi = LoRa.packetRssi();
    float snr = LoRa.packetSnr();
    
    Serial.println("\n--- LoRa Packet Received ---");
    Serial.println("Packet #" + String(packetsReceived));
    Serial.println("Size: " + String(packetSize) + " bytes");
    Serial.println("Data: " + receivedData);
    Serial.println("RSSI: " + String(rssi) + " dBm");
    Serial.println("SNR: " + String(snr) + " dB");
    
    String signalQuality = "Unknown";
    if (rssi > -50) signalQuality = "Excellent";
    else if (rssi > -70) signalQuality = "Good";
    else if (rssi > -90) signalQuality = "Fair";
    else if (rssi > -110) signalQuality = "Poor";
    else signalQuality = "Very Poor";
    
    Serial.println("Signal Quality: " + signalQuality);
    Serial.println("---------------------------\n");
    
    // Validate JSON
    if (isValidJSON(receivedData)) {
      // Forward to server
      if (WiFi.status() == WL_CONNECTED) {
        bool success = forwardToServer(receivedData, rssi, snr);
        if (success) {
          packetsForwarded++;
        } else {
          packetsFailed++;
        }
      } else {
        Serial.println("ERROR: WiFi not connected, cannot forward data");
        packetsFailed++;
      }
    } else {
      Serial.println("ERROR: Invalid JSON received, skipping");
      packetsFailed++;
    }
    
    digitalWrite(STATUS_LED, HIGH);  // LED off
  }
  
  yield();
  delay(10);
}

void connectToWiFi() {
  Serial.println("Connecting to WiFi: " + String(WIFI_SSID));
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
    
    yield();
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ WiFi connected!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.print("Signal Strength: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    Serial.println("\n✗ WiFi connection failed!");
    Serial.println("Will retry in 30 seconds...");
  }
}

bool isValidJSON(String jsonString) {
  StaticJsonDocument<300> doc;
  DeserializationError error = deserializeJson(doc, jsonString);
  
  if (error) {
    Serial.println("JSON Parse Error: " + String(error.c_str()));
    return false;
  }
  
  // Check for required fields
  if (!doc.containsKey("id")) {
    Serial.println("JSON missing 'id' field");
    return false;
  }
  
  return true;
}

bool forwardToServer(String jsonData, int rssi, int snr) {
  WiFiClient client;
  HTTPClient http;
  
  Serial.println("Forwarding to server: " + String(SERVER_URL));
  
  http.begin(client, SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  
  http.setTimeout(5000); // 5 second timeout
  
  // Add LoRa metadata to the JSON
  StaticJsonDocument<350> doc;
  DeserializationError error = deserializeJson(doc, jsonData);
  
  bool success = false;
  
  if (!error) {
    doc["rssi"] = rssi;
    doc["snr"] = snr;
    doc["bridge_time"] = millis();
    doc["wifi_rssi"] = WiFi.RSSI();
    
    String enrichedJson;
    serializeJson(doc, enrichedJson);
    
    int httpResponseCode = http.POST(enrichedJson);
    
    if (httpResponseCode > 0) {
      Serial.println("✓ Server Response Code: " + String(httpResponseCode));
      String response = http.getString();
      Serial.println("Response: " + response);
      success = (httpResponseCode >= 200 && httpResponseCode < 300);
    } else {
      Serial.println("✗ HTTP Error: " + String(httpResponseCode));
      Serial.println("Error: " + http.errorToString(httpResponseCode));
    }
  } else {
    Serial.println("✗ Failed to parse JSON for enrichment");
  }
  
  http.end();
  return success;
}

void printStatistics() {
  Serial.println("\n========== STATISTICS ==========");
  Serial.println("Uptime: " + String(millis() / 1000) + " seconds");
  Serial.println("Packets Received: " + String(packetsReceived));
  Serial.println("Packets Forwarded: " + String(packetsForwarded));
  Serial.println("Packets Failed: " + String(packetsFailed));
  
  if (packetsReceived > 0) {
    float successRate = (float)packetsForwarded / packetsReceived * 100;
    Serial.println("Success Rate: " + String(successRate, 1) + "%");
  }
  
  Serial.println("WiFi Status: " + String(WiFi.status() == WL_CONNECTED ? "Connected" : "Disconnected"));
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi RSSI: " + String(WiFi.RSSI()) + " dBm");
  }
  Serial.println("================================\n");
}

#include <SPI.h>
#include <LoRa.h>
#include <DHT.h>
#include <ArduinoJson.h>

// LoRa Pin Configuration for ESP8266
#define SS    15   // D8
#define RST   16   // D0
#define DIO0  4    // D2

// Sensor Configuration
const String SENSOR_ID = "Sensor_1";  // Change to Sensor_2, Sensor_3, etc.

// Pin definitions
#define DHT_PIN 5          // D1 (GPIO5) on NodeMCU
#define DHT_TYPE DHT22
#define SOIL_MOISTURE_PIN A0  // ESP8266 has only 1 ADC pin
#define STATUS_LED LED_BUILTIN

// Sensor objects
DHT dht(DHT_PIN, DHT_TYPE);

// Calibration values - adjust based on your sensors
const int SOIL_DRY_VALUE = 1023;   // Dry soil reading
const int SOIL_WET_VALUE = 300;    // Wet soil reading

// Transmission interval (milliseconds)
// 5 minutes = 5 × 60 × 1000 = 300000 ms
const unsigned long TRANSMISSION_INTERVAL = 3000;

unsigned long lastTransmissionTime = 0;

int transmissionCount = 0;
int failedReadings = 0;
const int MAX_RETRY_ATTEMPTS = 3;

void setup() {
  Serial.begin(9600);
  while (!Serial);
  
  pinMode(STATUS_LED, OUTPUT);
  digitalWrite(STATUS_LED, HIGH); // LED off initially
  
  Serial.println("\n=================================");
  Serial.println("LoRa Sensor Transmitter Starting...");
  Serial.println("=================================");
  Serial.println("Sensor ID: " + SENSOR_ID);
  
  // Initialize DHT sensor
  dht.begin();
  
  Serial.println("Warming up sensors...");
  delay(2000);
  
  // Initialize LoRa
  Serial.println("Initializing LoRa...");
  LoRa.setPins(SS, RST, DIO0);
  
  if (!LoRa.begin(433E6)) {  // 433 MHz frequency
    Serial.println("ERROR: Starting LoRa failed!");
    while (1) {
      digitalWrite(STATUS_LED, LOW);
      delay(100);
      digitalWrite(STATUS_LED, HIGH);
      delay(100);
    }
  }
  
  // Configure LoRa parameters for better range
  LoRa.setSpreadingFactor(12);  // SF7-12, higher = longer range but slower
  LoRa.setSignalBandwidth(125E3);  // 125 kHz
  LoRa.setCodingRate4(5);  // 4/5 coding rate
  LoRa.setTxPower(20);  // Max power: 20 dBm
  
  Serial.println("✓ LoRa initialized successfully");
  Serial.println("\n=================================");
  Serial.println("Transmitter Ready!");
  Serial.println("=================================\n");
}

void loop() {
  unsigned long currentTime = millis();
  
  // Check if it's time to transmit
  if (currentTime - lastTransmissionTime >= TRANSMISSION_INTERVAL) {
    lastTransmissionTime = currentTime;
    
    digitalWrite(STATUS_LED, LOW);  // LED on
    
    float temperature = -999;
    float humidity = -999;
    int soilMoistureRaw = 0;
    
    bool sensorReadSuccess = false;
    for (int attempt = 0; attempt < MAX_RETRY_ATTEMPTS; attempt++) {
      temperature = dht.readTemperature();
      humidity = dht.readHumidity();
      soilMoistureRaw = analogRead(SOIL_MOISTURE_PIN);
      
      // Check if readings are valid
      if (!isnan(temperature) && !isnan(humidity)) {
        sensorReadSuccess = true;
        break;
      }
      
      Serial.println("Sensor read attempt " + String(attempt + 1) + " failed, retrying...");
      delay(500);
    }
    
    if (!sensorReadSuccess) {
      failedReadings++;
      Serial.println("WARNING: Failed to read DHT sensor after " + String(MAX_RETRY_ATTEMPTS) + " attempts");
    }
    
    // Calibrate soil moisture (0-100%)
    int soilMoisture = map(soilMoistureRaw, SOIL_DRY_VALUE, SOIL_WET_VALUE, 0, 100);
    soilMoisture = constrain(soilMoisture, 0, 100);
    
    StaticJsonDocument<256> doc;
    doc["id"] = SENSOR_ID;
    doc["soil_moisture"] = soilMoisture;
    doc["temperature"] = sensorReadSuccess ? round(temperature * 10) / 10.0 : -999;
    doc["humidity"] = sensorReadSuccess ? round(humidity * 10) / 10.0 : -999;
    doc["transmission_count"] = transmissionCount;
    doc["failed_readings"] = failedReadings;
    doc["uptime_ms"] = millis();
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    // Transmit via LoRa
    Serial.println("\n--- Transmission #" + String(transmissionCount) + " ---");
    Serial.println("Data: " + jsonString);
    Serial.print("Sending via LoRa... ");
    
    LoRa.beginPacket();
    LoRa.print(jsonString);
    int packetSent = LoRa.endPacket();
    
    if (packetSent) {
      Serial.println("✓ Success!");
      transmissionCount++;
      
      for (int i = 0; i < 2; i++) {
        digitalWrite(STATUS_LED, HIGH);
        delay(50);
        digitalWrite(STATUS_LED, LOW);
        delay(50);
      }
    } else {
      Serial.println("✗ Failed!");
    }
    
    Serial.println("---------------------------\n");
    
    digitalWrite(STATUS_LED, HIGH); // LED off
  }
  
  yield();
  delay(100);
}

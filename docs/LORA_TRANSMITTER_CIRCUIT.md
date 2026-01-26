# LoRa Transmitter Circuit Diagram

## Components Required

### Main Components
- **ESP8266 NodeMCU** (or any ESP8266 board)
- **LoRa Module**: SX1278 / Ra-02 (433MHz or 868MHz/915MHz depending on your region)
- **DHT22 Sensor** (Temperature & Humidity)
- **Soil Moisture Sensor** (Capacitive or Resistive)
- **Power Supply**: 5V USB or 3.7V LiPo battery with voltage regulator

### Additional Components
- **10kΩ Pull-up Resistor** (for DHT22 data line)
- **Jumper Wires** (Male-to-Female and Male-to-Male)
- **Breadboard** (for prototyping)
- **Antenna** for LoRa module (433MHz or 868/915MHz matching your module)

---

## Pin Connection Table

### ESP8266 to LoRa Module (SX1278/Ra-02)

| LoRa Module Pin | ESP8266 Pin | Pin Number | Description |
|-----------------|-------------|------------|-------------|
| VCC             | 3.3V        | 3V3        | Power supply (3.3V) |
| GND             | GND         | GND        | Ground |
| MISO            | D6          | GPIO12     | SPI Master In Slave Out |
| MOSI            | D7          | GPIO13     | SPI Master Out Slave In |
| SCK             | D5          | GPIO14     | SPI Clock |
| NSS (CS)        | D8          | GPIO15     | SPI Chip Select |
| RST             | D0          | GPIO16     | Reset pin |
| DIO0            | D1          | GPIO5      | Digital I/O 0 (interrupt) |
| ANT             | -           | -          | Connect antenna |

### ESP8266 to DHT22 Sensor

| DHT22 Pin | ESP8266 Pin | Pin Number | Description |
|-----------|-------------|------------|-------------|
| VCC       | 3.3V        | 3V3        | Power supply (3.3V) |
| GND       | GND         | GND        | Ground |
| DATA      | D4          | GPIO2      | Data pin (with 10kΩ pull-up to 3.3V) |

### ESP8266 to Soil Moisture Sensor

| Moisture Sensor Pin | ESP8266 Pin | Pin Number | Description |
|---------------------|-------------|------------|-------------|
| VCC                 | 3.3V        | 3V3        | Power supply (3.3V) |
| GND                 | GND         | GND        | Ground |
| AOUT (Analog)       | A0          | A0         | Analog output |

---

## Circuit Diagram (ASCII Art)

\`\`\`
                                    ESP8266 NodeMCU
                                   ┌─────────────────┐
                                   │                 │
                    ┌──────────────┤ 3V3             │
                    │              │                 │
                    │     ┌────────┤ GND             │
                    │     │        │                 │
                    │     │   ┌────┤ D0 (GPIO16)     │
                    │     │   │    │                 │
                    │     │   │ ┌──┤ D1 (GPIO5)      │
                    │     │   │ │  │                 │
                    │     │   │ │  │ D2 (GPIO4)      │
                    │     │   │ │  │                 │
                    │     │   │ │  │ D3 (GPIO0)      │
                    │     │   │ │  │                 │
                    │     │   │ │  │ D4 (GPIO2)  ────┼──┐ DHT22 DATA
                    │     │   │ │  │                 │  │
                    │     │   │ │  │ D5 (GPIO14) ────┼──┼──┐ LoRa SCK
                    │     │   │ │  │                 │  │  │
                    │     │   │ │  │ D6 (GPIO12) ────┼──┼──┼──┐ LoRa MISO
                    │     │   │ │  │                 │  │  │  │
                    │     │   │ │  │ D7 (GPIO13) ────┼──┼──┼──┼──┐ LoRa MOSI
                    │     │   │ │  │                 │  │  │  │  │
                    │     │   │ │  │ D8 (GPIO15) ────┼──┼──┼──┼──┼──┐ LoRa NSS
                    │     │   │ │  │                 │  │  │  │  │  │
                    │     │   │ │  │ A0          ────┼──┼──┼──┼──┼──┼──┐ Moisture
                    │     │   │ │  │                 │  │  │  │  │  │  │
                    │     │   │ │  └─────────────────┘  │  │  │  │  │  │
                    │     │   │ │                       │  │  │  │  │  │
                    │     │   │ └───────────────────────┘  │  │  │  │  │
                    │     │   │                            │  │  │  │  │
                    │     │   └────────────────────────────┘  │  │  │  │
                    │     │                                   │  │  │  │
                    │     │                                   │  │  │  │
                    ▼     ▼                                   ▼  ▼  ▼  ▼
              ┌─────────────────┐                    ┌──────────────────┐
              │   DHT22 Sensor  │                    │  LoRa SX1278/Ra-02│
              ├─────────────────┤                    ├──────────────────┤
              │ VCC ──── 3.3V   │                    │ VCC ──── 3.3V    │
              │ GND ──── GND    │                    │ GND ──── GND     │
              │ DATA ─── D4     │                    │ MISO ─── D6      │
              │         (GPIO2) │                    │ MOSI ─── D7      │
              │                 │                    │ SCK ──── D5      │
              │  [10kΩ Pull-up] │                    │ NSS ──── D8      │
              │   to 3.3V       │                    │ RST ──── D0      │
              └─────────────────┘                    │ DIO0 ─── D1      │
                                                     │ ANT ──── Antenna │
              ┌─────────────────┐                    └──────────────────┘
              │ Soil Moisture   │
              │    Sensor       │
              ├─────────────────┤
              │ VCC ──── 3.3V   │
              │ GND ──── GND    │
              │ AOUT ─── A0     │
              └─────────────────┘
\`\`\`

---

## Detailed Connection Instructions

### 1. LoRa Module Connections (SPI Interface)

The LoRa module uses SPI communication with the ESP8266:

1. **Power Connections:**
   - Connect LoRa VCC to ESP8266 3.3V (NOT 5V - this will damage the module!)
   - Connect LoRa GND to ESP8266 GND

2. **SPI Data Lines:**
   - **MISO** (Master In Slave Out): LoRa → ESP8266 D6 (GPIO12)
   - **MOSI** (Master Out Slave In): ESP8266 D7 (GPIO13) → LoRa
   - **SCK** (Clock): ESP8266 D5 (GPIO14) → LoRa
   - **NSS/CS** (Chip Select): ESP8266 D8 (GPIO15) → LoRa

3. **Control Lines:**
   - **RST** (Reset): ESP8266 D0 (GPIO16) → LoRa
   - **DIO0** (Digital I/O): LoRa → ESP8266 D1 (GPIO5)

4. **Antenna:**
   - Connect a proper antenna to the ANT pin (impedance matched to your frequency)
   - For 433MHz: ~17.3cm wire antenna
   - For 868/915MHz: ~8.2cm wire antenna

### 2. DHT22 Sensor Connections

1. **Power:**
   - VCC → ESP8266 3.3V
   - GND → ESP8266 GND

2. **Data:**
   - DATA → ESP8266 D4 (GPIO2)
   - Add a 10kΩ pull-up resistor between DATA and 3.3V

### 3. Soil Moisture Sensor Connections

1. **Power:**
   - VCC → ESP8266 3.3V
   - GND → ESP8266 GND

2. **Data:**
   - AOUT (Analog Output) → ESP8266 A0
   - Note: ESP8266 A0 accepts 0-1V, so if your sensor outputs 0-3.3V, you may need a voltage divider

---

## Power Supply Options

### Option 1: USB Power (Development/Testing)
- Connect USB cable to NodeMCU
- Provides stable 5V, regulated to 3.3V by onboard regulator
- Best for testing and development

### Option 2: Battery Power (Field Deployment)
- **3.7V LiPo Battery** with voltage regulator (3.3V output)
- Connect battery positive to VIN (if using 5V) or 3.3V pin
- Connect battery negative to GND
- Add a power switch for easy on/off control

### Option 3: Solar Power (Long-term Deployment)
- Solar panel (5V-6V) → Charge controller → LiPo battery → ESP8266
- Recommended for remote tobacco field monitoring

---

## Important Notes

### ⚠️ Critical Warnings

1. **Voltage Levels:**
   - LoRa module operates at 3.3V ONLY
   - Never connect 5V to LoRa module - it will be damaged
   - ESP8266 GPIO pins are 3.3V tolerant

2. **Antenna:**
   - Always connect an antenna before powering on the LoRa module
   - Operating without antenna can damage the RF amplifier
   - Use proper impedance-matched antenna (50Ω)

3. **Power Consumption:**
   - LoRa transmission draws significant current (up to 120mA)
   - Use adequate power supply (minimum 500mA capacity)
   - Consider deep sleep mode for battery operation

4. **Soil Moisture Sensor:**
   - Capacitive sensors are better than resistive (no corrosion)
   - Calibrate sensor for your soil type
   - ESP8266 A0 pin: 0-1V range (use voltage divider if needed)

### 📝 Pin Configuration in Code

The pin definitions in `lora_transmitter.ino` match this circuit:

\`\`\`cpp
// LoRa pins
#define LORA_SCK 14   // D5
#define LORA_MISO 12  // D6
#define LORA_MOSI 13  // D7
#define LORA_SS 15    // D8
#define LORA_RST 16   // D0
#define LORA_DIO0 5   // D1

// Sensor pins
#define DHTPIN 2      // D4
#define MOISTURE_PIN A0
\`\`\`

---

## Testing the Circuit

### Step 1: Visual Inspection
1. Check all connections match the diagram
2. Verify no short circuits between VCC and GND
3. Ensure antenna is connected to LoRa module

### Step 2: Power Test
1. Connect USB power (without uploading code yet)
2. Check LED on NodeMCU lights up
3. Measure voltage at LoRa VCC pin (should be 3.3V)

### Step 3: Upload and Monitor
1. Upload the `lora_transmitter.ino` code
2. Open Serial Monitor (115200 baud)
3. Check for initialization messages
4. Verify sensor readings appear

### Step 4: LoRa Transmission Test
1. Check for "Sending packet" messages
2. Verify packet counter increments
3. Use LoRa receiver to confirm reception

---

## Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| LoRa init failed | Wrong wiring | Check SPI connections |
| DHT22 read error | No pull-up resistor | Add 10kΩ resistor |
| Moisture always 0 | Wrong pin | Verify A0 connection |
| ESP8266 resets | Insufficient power | Use better power supply |
| No LoRa reception | No antenna | Connect proper antenna |

---

## Next Steps

After building the transmitter circuit:
1. Build the receiver circuit (see `LORA_RECEIVER_CIRCUIT.md`)
2. Upload firmware to both devices
3. Test communication range
4. Deploy in tobacco field
5. Monitor data on dashboard

---

## Photos and Diagrams

For visual learners, here's a simplified block diagram:

\`\`\`
┌─────────────┐
│   Power     │
│  Supply     │
│  (USB/Batt) │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│         ESP8266 NodeMCU             │
│  ┌──────────────────────────────┐  │
│  │   Microcontroller (3.3V)     │  │
│  │   - Reads sensors            │  │
│  │   - Formats data             │  │
│  │   - Controls LoRa            │  │
│  └──────────────────────────────┘  │
└───┬────────┬────────┬──────────┬───┘
    │        │        │          │
    ▼        ▼        ▼          ▼
┌────────┐ ┌────┐ ┌────────┐ ┌──────┐
│ DHT22  │ │Soil│ │  LoRa  │ │ LED  │
│Temp/Hum│ │Mois│ │ Module │ │Status│
└────────┘ └────┘ └────┬───┘ └──────┘
                       │
                       ▼
                   ┌────────┐
                   │Antenna │
                   │ (RF)   │
                   └────────┘
\`\`\`

---

## Bill of Materials (BOM)

| Item | Quantity | Approx. Cost (USD) |
|------|----------|-------------------|
| ESP8266 NodeMCU | 1 | $3-5 |
| LoRa SX1278/Ra-02 | 1 | $3-8 |
| DHT22 Sensor | 1 | $3-5 |
| Soil Moisture Sensor | 1 | $2-4 |
| 10kΩ Resistor | 1 | $0.10 |
| Jumper Wires | 20 | $2 |
| Breadboard | 1 | $2 |
| Antenna | 1 | $1-3 |
| **Total** | | **$16-30** |

---

## Safety Considerations

1. **Electrical Safety:**
   - Use proper insulation for outdoor deployment
   - Protect from moisture and rain
   - Use weatherproof enclosure

2. **RF Safety:**
   - LoRa operates at low power (typically 20dBm/100mW)
   - Safe for human exposure at normal distances
   - Follow local RF regulations

3. **Environmental:**
   - Soil moisture sensor may corrode over time
   - Use stainless steel or capacitive sensors
   - Regular maintenance recommended

---

For the receiver circuit diagram, see `LORA_RECEIVER_CIRCUIT.md`

/*
 * NeuroShift ESP32 — MQTT relay hub (Phase-1 hardware)
 *
 * Topics:
 *   neuroshift/actuate  {"device_id":"lamp","command":"ON"}
 *   neuroshift/status   boot / ACK / wifi
 *
 * Wiring (optocoupled 5V relay module, often active-LOW):
 *   GPIO 17 / TX2 -> IN1 / K1 Lamp
 *   GPIO 16 / RX2 unused
 *   GPIO 18       -> IN3 Plug
 *
 * Libraries: PubSubClient, ArduinoJson
 * Board: ESP32 Dev Module
 *
 * Copy secrets.h.example -> secrets.h before flashing.
 * SAFETY: Prefer USB lamps / 5V loads until mains wiring is checked.
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#if __has_include("secrets.h")
#include "secrets.h"
#else
#define WIFI_SSID "YOUR_WIFI"
#define WIFI_PASS "YOUR_PASSWORD"
#define MQTT_HOST "192.168.1.10"
#define MQTT_PORT 1883
#endif

#ifndef RELAY_ACTIVE_LOW
#define RELAY_ACTIVE_LOW 1
#endif

// USB cable from this laptop is the live control path. MQTT/Wi-Fi can block
// Serial for 15s at a time and the relay never sees on/off.
#ifndef HUB_USB_ONLY
#define HUB_USB_ONLY 1
#endif

const char* TOPIC_ACTUATE = "neuroshift/actuate";
const char* TOPIC_STATUS  = "neuroshift/status";

const int PIN_LAMP = 17;  // TX2 -> IN1 / K1
const int PIN_FAN  = 16;  // RX2
const int PIN_PLUG = 18;

WiFiClient wifi;
PubSubClient mqtt(wifi);
unsigned long lastWifiAttempt = 0;
unsigned long lastMqttAttempt = 0;
unsigned long lastStatusPrint = 0;

int pinForDevice(const String& id) {
  if (id == "lamp") return PIN_LAMP;
  if (id == "fan")  return PIN_FAN;
  if (id == "plug") return PIN_PLUG;
  return -1;
}

void writeRelay(int pin, bool on) {
  if (RELAY_ACTIVE_LOW) {
    digitalWrite(pin, on ? LOW : HIGH);
  } else {
    digitalWrite(pin, on ? HIGH : LOW);
  }
}

void setDevice(const String& id, bool on) {
  int pin = pinForDevice(id);
  if (pin < 0) return;
  writeRelay(pin, on);
}

void publishStatus(const char* json) {
  mqtt.publish(TOPIC_STATUS, json, false);
}

void applyCommand(const char* device, const char* command) {
  if (device == nullptr || command == nullptr) return;
  if (strlen(device) == 0 || strlen(command) == 0) return;
  String cmd = String(command);
  bool on = (cmd == "ON" || cmd == "on" || cmd == "1" || cmd == "true");
  setDevice(String(device), on);
  Serial.print("[hub] ");
  Serial.print(device);
  Serial.print(" ");
  Serial.println(on ? "ON" : "OFF");
}

void onMessage(char* topic, byte* payload, unsigned int len) {
  StaticJsonDocument<256> doc;
  if (deserializeJson(doc, payload, len)) return;
  const char* device = doc["device_id"] | doc["device"] | "";
  const char* command = doc["command"] | "";
  applyCommand(device, command);

  StaticJsonDocument<160> ack;
  ack["device_id"] = device;
  ack["command"] = command;
  ack["ok"] = true;
  char buf[160];
  serializeJson(ack, buf);
  publishStatus(buf);
}

void handleSerialLine(String line) {
  line.trim();
  if (line.length() == 0) return;
  if (line.startsWith("{")) {
    StaticJsonDocument<256> doc;
    if (deserializeJson(doc, line)) return;
    applyCommand(doc["device_id"] | doc["device"] | "", doc["command"] | "");
    return;
  }
  line.toLowerCase();
  if (line == "on" || line == "lamp on") applyCommand("lamp", "ON");
  if (line == "off" || line == "lamp off") applyCommand("lamp", "OFF");
}

void pollSerial() {
  static String line;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      handleSerialLine(line);
      line = "";
    } else if (line.length() < 220) {
      line += c;
    }
  }
}

void ensureWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  unsigned long now = millis();
  if (now - lastWifiAttempt < 4000) return;
  lastWifiAttempt = now;
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASS);
}

void ensureMqtt() {
  if (mqtt.connected()) return;
  if (WiFi.status() != WL_CONNECTED) return;
  unsigned long now = millis();
  if (now - lastMqttAttempt < 3000) return;
  lastMqttAttempt = now;
  Serial.print("[hub] mqtt connecting ");
  Serial.println(MQTT_HOST);
  if (mqtt.connect("neuroshift-esp32")) {
    mqtt.subscribe(TOPIC_ACTUATE);
    publishStatus("{\"boot\":true,\"wifi\":\"ok\"}");
    Serial.println("[hub] mqtt ok");
  } else {
    Serial.print("[hub] mqtt fail rc=");
    Serial.println(mqtt.state());
  }
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("[hub] boot");
  digitalWrite(PIN_LAMP, HIGH);
  digitalWrite(PIN_FAN, HIGH);
  digitalWrite(PIN_PLUG, HIGH);
  pinMode(PIN_LAMP, OUTPUT);
  pinMode(PIN_FAN, OUTPUT);
  pinMode(PIN_PLUG, OUTPUT);
  writeRelay(PIN_LAMP, false);
  writeRelay(PIN_FAN, false);
  writeRelay(PIN_PLUG, false);
  Serial.println("[hub] usb ready");

#if !HUB_USB_ONLY
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  lastWifiAttempt = millis();
  Serial.print("[hub] wifi ");
  Serial.println(WIFI_SSID);

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMessage);
#endif
}

void loop() {
  pollSerial();
#if !HUB_USB_ONLY
  ensureWifi();
  if (!mqtt.connected()) ensureMqtt();
  mqtt.loop();
  unsigned long now = millis();
  if (now - lastStatusPrint > 5000) {
    lastStatusPrint = now;
    Serial.print("[hub] wifi=");
    Serial.print(WiFi.status());
    Serial.print(" ip=");
    Serial.print(WiFi.localIP());
    Serial.print(" mqtt=");
    Serial.println(mqtt.connected() ? "1" : "0");
  }
#endif
}

/*
 * NeuroShift ESP32 stub — MQTT relay hub (Phase-1 hardware)
 *
 * Topics:
 *   neuroshift/actuate  {"device_id":"lamp","command":"ON"}
 *   neuroshift/emg      (optional future) publish envelope 0..1
 *
 * Wiring (demo hub):
 *   GPIO 16 -> Relay IN1 (Lamp)
 *   GPIO 17 -> Relay IN2 (Fan)
 *   GPIO 18 -> Relay IN3 (Plug)
 *   VIN/GND -> relay module power (follow relay module docs; use optocoupled 5V relays)
 *
 * Install: PubSubClient + ArduinoJson
 * Board: ESP32 Dev Module
 *
 * SAFETY: Use low-voltage bulbs / smart plugs for demos until mains wiring
 * is reviewed by a qualified person.
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASS = "YOUR_PASSWORD";
const char* MQTT_HOST = "192.168.1.10";
const uint16_t MQTT_PORT = 1883;

const char* TOPIC_ACTUATE = "neuroshift/actuate";
const char* TOPIC_STATUS  = "neuroshift/status";

const int PIN_LAMP = 16;
const int PIN_FAN  = 17;
const int PIN_PLUG = 18;

WiFiClient wifi;
PubSubClient mqtt(wifi);

int pinForDevice(const String& id) {
  if (id == "lamp") return PIN_LAMP;
  if (id == "fan")  return PIN_FAN;
  if (id == "plug") return PIN_PLUG;
  return -1;
}

void setDevice(const String& id, bool on) {
  int pin = pinForDevice(id);
  if (pin < 0) return;
  digitalWrite(pin, on ? HIGH : LOW);
}

void onMessage(char* topic, byte* payload, unsigned int len) {
  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, payload, len);
  if (err) return;

  const char* device = doc["device_id"] | doc["device"] | "";
  const char* command = doc["command"] | "";
  if (strlen(device) == 0 || strlen(command) == 0) return;

  bool on = (String(command) == "ON" || String(command) == "on" || String(command) == "1");
  setDevice(String(device), on);

  StaticJsonDocument<128> ack;
  ack["device_id"] = device;
  ack["command"] = command;
  ack["ok"] = true;
  char buf[128];
  serializeJson(ack, buf);
  mqtt.publish(TOPIC_STATUS, buf);
}

void ensureMqtt() {
  while (!mqtt.connected()) {
    if (mqtt.connect("neuroshift-esp32")) {
      mqtt.subscribe(TOPIC_ACTUATE);
      mqtt.publish(TOPIC_STATUS, "{\"boot\":true}");
    } else {
      delay(1500);
    }
  }
}

void setup() {
  pinMode(PIN_LAMP, OUTPUT);
  pinMode(PIN_FAN, OUTPUT);
  pinMode(PIN_PLUG, OUTPUT);
  digitalWrite(PIN_LAMP, LOW);
  digitalWrite(PIN_FAN, LOW);
  digitalWrite(PIN_PLUG, LOW);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) delay(400);

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMessage);
}

void loop() {
  if (!mqtt.connected()) ensureMqtt();
  mqtt.loop();
}

// Smart Kitchen scanner: ESP32 + GM65 or GM861 serial barcode/QR module.
//
// The module decodes the code itself and sends the text over serial. This sketch
// reads that text and posts it to the backend (POST /api/v1/scans/codes), the same
// endpoint the simulated scanner and the app use. Board: "ESP32 Dev Module".

#include <HTTPClient.h>
#include <WiFi.h>

#include "config.h"

static const size_t   MAX_CODE_LEN    = 512;   // kitchen QR labels carry a small JSON
static const uint32_t IDLE_FLUSH_MS   = 60;    // a frame ends after this much silence
static const uint32_t REPEAT_BLOCK_MS = 3000;  // continuous-mode modules re-read the same code
static const uint32_t WIFI_TIMEOUT_MS = 10000;
static const uint32_t HTTP_TIMEOUT_MS = 8000;

HardwareSerial ScannerSerial(2);

String   frame;
bool     frameOverflow = false;
uint32_t lastByteMs    = 0;
String   lastCode;
uint32_t lastCodeMs    = 0;

// ---- Feedback ----

void pulse(int times, int onMs, int offMs) {
  for (int i = 0; i < times; i++) {
    digitalWrite(STATUS_LED_PIN, HIGH);
    if (BUZZER_PIN >= 0) digitalWrite(BUZZER_PIN, HIGH);
    delay(onMs);
    digitalWrite(STATUS_LED_PIN, LOW);
    if (BUZZER_PIN >= 0) digitalWrite(BUZZER_PIN, LOW);
    delay(offMs);
  }
}

void signalAdded()  { pulse(1, 200, 0); }    // one long blink: item added
void signalFailed() { pulse(4, 80, 80); }    // fast blinks: rejected or not sent

// ---- Wi-Fi ----

bool ensureWifi() {
  if (WiFi.status() == WL_CONNECTED) return true;
  Serial.printf("Connecting to Wi-Fi '%s'...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_TIMEOUT_MS) {
    delay(250);
  }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi not connected");
    return false;
  }
  Serial.printf("Wi-Fi connected, ESP32 IP %s\n", WiFi.localIP().toString().c_str());
  return true;
}

// ---- Backend ----

// Labels look like SKI:{"name":"Idli batter"}, so quotes must be escaped in the JSON body.
String jsonEscape(const String &s) {
  String out;
  out.reserve(s.length() + 8);
  for (size_t i = 0; i < s.length(); i++) {
    char c = s[i];
    if (c == '"' || c == '\\') out += '\\';
    out += c;
  }
  return out;
}

// Returns the HTTP status, or -1 if the backend could not be reached at all.
int sendCode(const String &code) {
  if (!ensureWifi()) return -1;

  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);
  http.begin(String(SERVER_URL) + "/api/v1/scans/codes");
  http.addHeader("Content-Type", "application/json");
  int status = http.POST("{\"code\":\"" + jsonEscape(code) + "\"}");

  if (status <= 0) {
    Serial.printf("Could not reach the backend: %s\n", HTTPClient::errorToString(status).c_str());
    http.end();
    return -1;
  }
  Serial.printf("Backend answered %d: %s\n", status, http.getString().c_str());
  http.end();
  return status;
}

// ---- Scanner frames ----

void handleCode(const String &code) {
  uint32_t now = millis();
  if (code == lastCode && now - lastCodeMs < REPEAT_BLOCK_MS) {
    lastCodeMs = now;  // still in front of the module, keep ignoring it
    return;
  }
  Serial.printf("Scanned: %s\n", code.c_str());
  int status = sendCode(code);
  if (status == 201) signalAdded(); else signalFailed();

  // A slow request or the blink can take seconds, and a continuous-mode module keeps
  // re-reading the code meanwhile. Drop those stale reads and restart the repeat timer
  // after the work, or the same item would be added again.
  while (ScannerSerial.available()) ScannerSerial.read();
  lastCode   = code;
  lastCodeMs = millis();

  // Backend unreachable: let the next scan of this code try again straight away.
  if (status == -1) lastCode = "";
}

void flushFrame() {
  if (frameOverflow) {
    Serial.println("Ignored a code longer than the limit");
    signalFailed();
  } else if (frame.length() > 0) {
#if SCANNER_DEBUG
    Serial.print("Frame text: [");
    Serial.print(frame);
    Serial.print("]  hex:");
    for (size_t i = 0; i < frame.length(); i++) Serial.printf(" %02X", (uint8_t)frame[i]);
    Serial.println();
#endif
    String code = frame;
    frame = "";
    code.trim();
    if (code.length() > 0) handleCode(code);
  }
  frame = "";
  frameOverflow = false;
}

void setup() {
  Serial.begin(115200);
  pinMode(STATUS_LED_PIN, OUTPUT);
  if (BUZZER_PIN >= 0) pinMode(BUZZER_PIN, OUTPUT);

  ScannerSerial.begin(SCANNER_BAUD, SERIAL_8N1, SCANNER_RX_PIN, SCANNER_TX_PIN);
  frame.reserve(MAX_CODE_LEN);

  Serial.printf("\nKitchen scanner, backend %s, scanner at %d baud\n", SERVER_URL, SCANNER_BAUD);
  if (ensureWifi()) pulse(2, 100, 100); else signalFailed();
}

void loop() {
  // A frame ends at CR or LF, or after a short silence if the module sends no terminator.
  while (ScannerSerial.available()) {
    uint8_t c = ScannerSerial.read();
    lastByteMs = millis();
    if (c == '\r' || c == '\n') {
      flushFrame();
    } else if (c >= 32 && c != 127) {
      if (frame.length() < MAX_CODE_LEN) frame += (char)c; else frameOverflow = true;
    }
  }
  if ((frame.length() > 0 || frameOverflow) && millis() - lastByteMs > IDLE_FLUSH_MS) {
    flushFrame();
  }
}

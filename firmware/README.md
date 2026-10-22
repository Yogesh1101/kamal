# Scanner firmware (ESP32 + GM65 or GM861)

The scanner module decodes the barcode or QR code itself and sends the text to the ESP32 over serial. The ESP32 posts that text to `POST /api/v1/scans/codes` on the backend. The sketch is in [kitchen_scanner/](kitchen_scanner/kitchen_scanner.ino) and works with either module.

> **Status:** not compiled or tested on hardware yet. The module facts below come from reseller listings and Waveshare's pages for similar modules, not from the GM65/GM861 manufacturer manuals. Check each item marked *verify* on your module before relying on it.

## Wiring

Both modules connect the same way: three signal wires, crossed TX/RX.

| Module pin | ESP32 DevKit pin | Notes |
|---|---|---|
| TXD | GPIO16 (RX2) | Module transmits, ESP32 receives |
| RXD | GPIO17 (TX2) | ESP32 transmits, module receives |
| GND | GND | Common ground is required |
| VCC | see the next table | Differs between modules |

The module's USB pins (D+, D-) stay unconnected. Optional feedback: a buzzer from GPIO to GND (set `BUZZER_PIN` in `config.h`); the on-board LED on GPIO2 is used by default.

| | GM65 | GM861 / GM861S |
|---|---|---|
| Supply | 5 V, from the DevKit's `VIN`/`5V` pin (*verify*: one reseller lists 5 V) | 3.3 V, from the DevKit's `3V3` pin (about 70 mA) |
| Logic level | *Verify.* If the module's TXD measures above 3.3 V with a multimeter, add a divider (1 kΩ in series, then 2 kΩ to GND, tapped at the ESP32 pin) | 3.3 V TTL, direct to the ESP32 |

Check the silkscreen on your board for the pin order and supply voltage before powering it. Pin order differs between listings, and a 3.3 V module on 5 V can be damaged.

## Serial settings

| Setting | Value | Status |
|---|---|---|
| Baud rate | 9600 | GM65 listing says 9600 (adjustable); GM861 default is unconfirmed (*verify*) |
| Format | 8 data bits, no parity, 1 stop bit (8N1) | Same as above |
| End of code | CR, LF or a 60 ms gap | The sketch accepts any of the three, so the module's terminator setting doesn't matter |
| Scan mode | The module must scan on its own (continuous or sensing mode) | *Verify.* One listing says the GM65 defaults to continuous; a Waveshare module defaults to manual, where a button or trigger pin starts each scan |

Changing the module's baud rate, mode or terminator is done with the setting-code sheet in the manufacturer's manual (scan the printed setting codes). The sketch doesn't configure the module itself. If you change the baud rate, update `SCANNER_BAUD` in `config.h`.

## Setup

1. Install the Arduino IDE and add ESP32 board support (Boards Manager, "esp32 by Espressif Systems"). Choose the board "ESP32 Dev Module".
2. In `kitchen_scanner/`, copy `config.example.h` to `config.h` and fill in the Wi-Fi name, the Wi-Fi password and the laptop's IP. `config.h` is git-ignored.
3. Start the backend so other devices can reach it, from `backend/`: `.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000`. The laptop and the ESP32 must be on the same 2.4 GHz network, and the laptop firewall must allow port 8000.
4. Upload the sketch and open the Serial Monitor at 115200 baud.

## Testing in order

1. **Module output.** With `SCANNER_DEBUG 1`, scan any barcode. The monitor prints `Frame text: [...]` and the same bytes in hex. Readable text confirms the baud rate. The hex shows the terminator (`0D` is CR, `0A` is LF). If you see only garbage, the baud rate is wrong. If nothing appears, check the wiring (swap TXD/RXD) and the scan mode.
2. **Backend link.** Scan a product barcode (8–14 digits). The monitor shows `Backend answered 201`, and the item appears in the app's Kitchen tab. One long LED blink means added.
3. **Kitchen label.** Scan a printed `SKI:{"name":"Idli batter","category":"batter"}` QR code.
4. **Bad codes.** Scan a UPI or website QR code. The backend answers 400 and the LED blinks fast four times.

## LED signals

| Signal | Meaning |
|---|---|
| Two short blinks at power-up | Wi-Fi connected |
| One long blink | Item added |
| Four fast blinks | Backend rejected the code, couldn't be reached, or the code was too long |

The same code is ignored for 3 seconds after it was last seen, because continuous-mode modules keep re-reading a code that stays in front of them.

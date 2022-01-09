// WORKING IN VS CODE:
// Include Arduino.h so intellisense can find the standard Arduino packages. Produces false-negative for Arduino.h 
// #include <Arduino.h> 
// 
// Compile with this:
// acompile /home/pi/Signifier/leds/arduino/purple_volume && aupload /home/pi/Signifier/leds/arduino/purple_volume
//
// https://joachimweise.github.io/post/2020-04-07-vscode-remote/
//

// TODO
// - Add serial receive from Python/Pi
// - Control LED brightness with value
// - Move to callbacks for serial read?
// - Move to FastLED?

#include <Arduino.h>

#include <Adafruit_NeoPixel.h>

#include <SerialTransfer.h>

#ifdef __AVR__#include <avr/power.h>

#endif

#define LED_PIN 6
#define LED_COUNT 240

#define MAX_BRIGHT 255
double sig_volume;
int8_t reactive_bright = 0;

// MMW Purple hue code
int16_t HUE = 50000;

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);
SerialTransfer sig_serial;

void setup() {
  // The example code said this wasn't neccessary, but it seems to affect the colour
  #if defined(__AVR_ATtiny85__) && (F_CPU == 16000000)
  clock_prescale_set(clock_div_1);
  #endif

  // Strip setup
  strip.begin();
  startup();
  delay(100);

  // Serial transfer setup
  Serial.begin(115200);
  sig_serial.begin(Serial);
}

void loop() {
  if (sig_serial.available()) {
    sig_serial.rxObj(sig_volume);
  }
  strip.fill(strip.ColorHSV(HUE, 255, sig_volume * MAX_BRIGHT));
  //strip.setBrightness(sig_volume * 255);
  delay(1);
}

void solidColour(uint32_t color) {
  for (int i = 0; i < strip.numPixels(); i++) {
    strip.setPixelColor(i, color);
  }
  strip.show();
}

// mode (0 = brightness, 1 = hue)
void breath(uint16_t hue, int valStart, int valEnd, int duration, int mode) {
  uint32_t colour;
  int numSteps = 180;
  int valDiff = valEnd - valStart;
  int stepDelay = duration / numSteps;
  for (int i = 0; i < 180; i++) {
    float posRad = i * M_PI / 180;
    float sinResult = sin(posRad);
    int value = valStart + sinResult * valDiff;
    Serial.println(value);
    for (int j = 0; j < strip.numPixels(); j++) {
      if (mode == 0) {
        colour = strip.ColorHSV(hue, 255, value);
      } else {
        colour = strip.ColorHSV(hue, value, 255);
      }
      strip.setPixelColor(j, colour);
    }
    strip.show();
    delay(stepDelay);
  }
}


void startup() {
  int bright = 255 / 2;
  int saturation = 255;
  strip.clear();
  strip.setBrightness(bright);
  strip.show();
  delay(100);

  // Run through pixels for testing and dramatic effect
  for (int i = 0; i < strip.numPixels(); i++) {
    strip.setPixelColor(i, strip.ColorHSV(HUE, 255, bright));
    strip.show();
    delay(1);
  }

  // Now pulse bright white once...
  for (int i = 0; bright < 255; i++) {
    bright = constrain(bright + 2, 0, 255);
    saturation = constrain(saturation - 3, 0, 255);
    strip.fill(strip.ColorHSV(HUE, saturation, bright));
    strip.show();
    delay(1);
  }

  // Now fade out to show LEDs are ready...
  for (int i = 0; bright > 0; i++) {
    bright = constrain(bright - 1, 0, 255);
    saturation = constrain(saturation + 2, 0, 255);
    strip.fill(strip.ColorHSV(HUE, saturation, bright));
    strip.show();
    delay(1);
  }
}
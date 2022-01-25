// WORKING IN VS CODE:
// Include Arduino.h so intellisense can find the standard Arduino packages. Produces false-negative for Arduino.h 
// #include <Arduino.h> 
// 
// Compile with this:
// acompile /home/pi/Signifier/leds/arduino/purple_volume && aupload /home/pi/Signifier/leds/arduino/purple_volume
//
// https://joachimweise.github.io/post/2020-04-07-vscode-remote/
//
//
// HUE INFO: https://learn.adafruit.com/adafruit-neopixel-uberguide/arduino-library-use#hsv-hue-saturation-value-colors-dot-dot-dot-3024464-41


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

#define LOOP_DELAY 1

const unsigned int INIT_BRIGHTNESS = 127U * 256U;
const unsigned int INIT_SATURATION = 255U * 256U;
const unsigned int INIT_HUE = 50000U;

uint8_t maxBrightness = 255;

struct HSV_PROP {
  unsigned int current;
  unsigned int target;
  unsigned int duration;
  unsigned int max;
  long step;
  bool looping;
};

HSV_PROP brightness = {INIT_BRIGHTNESS, INIT_BRIGHTNESS, 0, 65535U, 0, false};
HSV_PROP saturation = {INIT_SATURATION, INIT_SATURATION, 0, 65535U, 0, false};
HSV_PROP hue = {INIT_HUE, INIT_HUE, 0, 65535U, 0, true};

struct COMMAND {
  char command;
  double value;
  double duration;
};

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);
SerialTransfer sigSerial;

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
  Serial.begin(9600);
  //sigSerial.begin(Serial);
}


void loop() {
  // processInput();
  // // brightness = fadeToTarget(brightness);
  // // saturation = fadeToTarget(saturation);
  // // hue = fadeToTarget(hue);
  // brightness.current = brightness.target;
  // saturation.current = saturation.target;
  // hue.current = hue.target;

  // strip.fill(strip.ColorHSV(hue.current, saturation.current>>8, brightness.current>>8));

  delay(LOOP_DELAY);
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



void processInput() {
  if(sigSerial.available())
  {
    COMMAND inputCommand;

    uint16_t recSize = 0;
    recSize = sigSerial.rxObj(inputCommand, recSize);

    uint32_t value = inputCommand.value;

    switch (inputCommand.command) {
      case 'b':
        value = value << 8;
        brightness.target = constrain(value, 0, brightness.max);
        brightness.duration = inputCommand.duration;
        break;
      case 's':
        value = value << 8;
        saturation.target = constrain(value, 0, saturation.max);
        saturation.duration = inputCommand.duration;
        break;
      case 'h':
        hue.target = constrain(value, 0, hue.max);
        hue.duration = inputCommand.duration;
        break;
      default:
        return;
    }
  }
}

HSV_PROP fadeToTarget(HSV_PROP inputProperty) {
  long diff = (long)inputProperty.current - inputProperty.target;
  // Return intact property struct if it's value is at the target and duration has ended
  if (inputProperty.duration == 0U && diff == 0L) {
    return inputProperty;
  }
  // Reset duration and/or current value to target if stuck
  if (inputProperty.duration < 1U || (diff < -10L && diff > 10L)) {
    inputProperty.current = inputProperty.target;
    inputProperty.duration = 0;
    return inputProperty;
  }
  // Otherwise, start moving value towards target. Maybe add shaping/smoothing later?
  long step = diff / (long)inputProperty.duration / LOOP_DELAY;
  inputProperty.current -= step;

  

  if (inputProperty.current < 0U) {
    inputProperty.current = 0U;
  } else if (inputProperty.current > inputProperty.max) {
    inputProperty.current = inputProperty.max;
  }
  #inputProperty.current = constrain(inputProperty.current, 0U, inputProperty.max);
  inputProperty.duration -= LOOP_DELAY; 
  return inputProperty;
}


void startup() {
  strip.clear();
  strip.setBrightness(255);
  strip.show();
  delay(100);

  // Run through pixels for testing and dramatic effect
  for (int i = 0; i < strip.numPixels(); i++) {
    strip.setPixelColor(i, strip.ColorHSV(hue.current, saturation.current >> 8, brightness.current >> 8));
    strip.show();
    delay(LOOP_DELAY);
  }

  strip.clear();
  strip.show();
  // Now pulse bright white once...
  brightness.current = 0 * 256;
  brightness.target = 100 * 256;
  brightness.duration = 1000;
  
  Serial.println('Fading to: ' + brightness.target);
  while (brightness.current != brightness.target) {
    brightness = fadeToTarget(brightness);
    strip.fill(strip.ColorHSV(hue.current, saturation.current >> 8, 255));
    strip.setBrightness(brightness.current >> 8);
    strip.show();
    Serial.println(brightness.current);
    delay(LOOP_DELAY);
  }
  brightness.target = 0 * 256;
  brightness.duration = 1000;
  while (brightness.current != brightness.target) {
    brightness = fadeToTarget(brightness);
    strip.fill(strip.ColorHSV(hue.current, saturation.current >> 8, brightness.current >> 8));
    strip.show();
    Serial.println(brightness.current);
    delay(LOOP_DELAY);
  }

  brightness.current = 0;
  brightness.target = 255 * 256;
  brightness.duration = 0;
  brightness = fadeToTarget(brightness);
  strip.fill(strip.ColorHSV(hue.current, saturation.current >> 8, brightness.current >> 8));
  strip.show();
  delay(1000);
  strip.clear();
  strip.show();
  Serial.println('Finished startup.');
  //saturation = fadeToTarget(saturation);
  //hue = fadeToTarget(hue);

  // for (int i = 0; brightness.current < 255; i++) {
  //   brightness.current = constrain(brightness.current + 2, 0, 255);
  //   saturation.current = constrain(saturation.current - 3, 0, 255);
  //   strip.fill(strip.ColorHSV(hue.current, saturation.current, brightness.current));
  //   strip.show();
  //   delay(LOOP_DELAY);
  // }

  // // Now fade out to show LEDs are ready...
  // for (int i = 0; brightness.current > 0; i++) {
  //   brightness.current = constrain(brightness.current - 1, 0, 255);
  //   saturation.current = constrain(saturation.current + 0.8, 0, 255);
  //   strip.fill(strip.ColorHSV(hue.current, saturation.current, brightness.current));
  //   strip.show();
  //   delay(LOOP_DELAY);
  // }
}
// acompile /home/pi/Signifier/leds/arduino/2animations && aupload /home/pi/Signifier/leds/arduino/2animations




#include "FastLED.h"

#define NUM_LEDS 240
#define DATA_PIN 6

// have 3 independent CRGBs - 2 for the sources and one for the output
CRGB leds[NUM_LEDS];
CRGB leds2[NUM_LEDS];
CRGB leds3[NUM_LEDS];

void setup() {
  FastLED.addLeds<NEOPIXEL, DATA_PIN>(leds, NUM_LEDS);
  LEDS.setBrightness(128);
}

void loop() {
  
  // render the first animation into leds2 
  animationA();
  
  // render the second animation into leds3
  animationB();

  // set the blend ratio for the video cross fade
  // (set ratio to 127 for a constant 50% / 50% blend)

  uint8_t ratio = 255;
  
  //beatsin8(127);

  // mix the 2 arrays together
  for (int i = 0; i < NUM_LEDS; i++) {
    leds[i] = blend( leds2[i], leds3[i], ratio );
  }
    millis();
  FastLED.show();
}

void animationA() {
  // running red stripes 
  for (uint16_t i = 0; i < NUM_LEDS; i++) {
    uint8_t red = (millis() / 3) + (i * 5);
    if (red > 128) red = 0;
    leds2[i] = CRGB(red, 0, 0);
  }
}

void animationB() {
  // the moving rainbow
  for (uint16_t i = 0; i < NUM_LEDS; i++) {
    leds3[i] = CHSV((millis() / 4) - (i * 3), 255, 255);
  }
}
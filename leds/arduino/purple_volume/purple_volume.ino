#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#ifdef __AVR__
 #include <avr/power.h>
#endif

#define LED_PIN 6
#define LED_COUNT 240

#define BRIGHTNESS 0.1

int HUE = 50000;

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

// https://joachimweise.github.io/post/2020-04-07-vscode-remote/
// acompile /home/pi/Signifier/leds/arduino/purple_volume && aupload /home/pi/Signifier/leds/arduino/purple_volume

void setup() {
  // The example code said this wasn't neccessary, but it seems to affect the colour
  #if defined(__AVR_ATtiny85__) && (F_CPU == 16000000)
    clock_prescale_set(clock_div_1);
  #endif
 
  Serial.begin(9600);
  strip.begin();
  strip.setBrightness(255 * BRIGHTNESS);

  // Initial LED strip population (for testing)
  for(int i = 0; i < strip.numPixels(); i ++)
  {
    strip.setPixelColor(i, strip.ColorHSV(HUE, 255, 255));
    delay(1);
    strip.show();
  }
  strip.show();
}

void loop() {
  solidColour(strip.ColorHSV(HUE, 255, 255));
  delay(10);
}

void solidColour(uint32_t color){
  for(int i=0; i < strip.numPixels(); i++) {
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
  for(int i = 0; i < 180; i++){
    float posRad = i * M_PI / 180;
    float sinResult = sin(posRad);
    int value = valStart + sinResult * valDiff;
    Serial.println(value);
     for(int j = 0; j < strip.numPixels(); j++){
     if (mode == 0){
        colour = strip.ColorHSV(hue, 255, value);        
      }
     else {
        colour = strip.ColorHSV(hue, value, 255);        
     }
     strip.setPixelColor(j, colour);
    }
    strip.show();
    delay(stepDelay);
  }
}

#include <Adafruit_NeoPixel.h>
#ifdef __AVR__
 #include <avr/power.h>
#endif

#define LED_PIN 6
#define LED_COUNT 240

#define BRIGHTNESS 0.1
#define COLOUR ColorHSV(50000, 255, 255)

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

// https://joachimweise.github.io/post/2020-04-07-vscode-remote/

// acompile /home/pi/Signifier/arduino_test/arduino/mmw_led_breath_purple && aupload /home/pi/Signifier/arduino_test/arduino/mmw_led_breath_purple

void setup() {
  // The example code said this wasn't neccessary, but it seems to affect the colour
  #if defined(__AVR_ATtiny85__) && (F_CPU == 16000000)
    clock_prescale_set(clock_div_1);
  #endif
 
  
  Serial.begin(9600);
  strip.begin();
  strip.show();
  strip.setBrightness(255 * BRIGHTNESS);

  randomSeed(analogRead(0));
  int delayOffet = random(0, 3000);
  delay(delayOffet);

  for(int i = 0; i < strip.numPixels(); i ++)
  {
    strip.setPixelColor(i, COLOUR);
    strip.show();
    delay(50);
  }
}

void loop() {
  solidColour(strip.ColorHSV(50000, 255, 255));

  // breath(50000, 255, 220, 2000, 1);
  // breath(50000, 255, 150, 500, 0);
  // breath(50000, 255, 100, 1000, 0);
  // breath(50000, 255, 150, 500, 0);
  delay(100);
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

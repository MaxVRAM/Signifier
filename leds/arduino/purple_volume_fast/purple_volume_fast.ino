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
// - Move to callbacks for serial read?

#define FASTLED_ALLOW_INTERRUPTS 0

#include <Arduino.h>
#include <SerialTransfer.h>
#include <FastLED.h>
#define NUM_LEDS 240
#define DATA_PIN 6
#define LOOP_DELAY 10

const uint8_t INIT_BRIGHTNESS = 255U;
const uint8_t INIT_SATURATION = 255U;
const uint16_t INIT_HUE = 195U;

struct HSV_PROP {
  unsigned short current;
  unsigned short target;
  unsigned short max;
  unsigned int duration;
};

struct COMMAND {
  byte command;
  int value;
  int duration;
} inputCommand;

struct SEND_STRUCT {
  char command;
  long value;
} sendStruct;

struct SIG_MESSAGE {
  char command;
  double value;
} sigMessage;

unsigned short hardBright = 0;
unsigned long ms = 0;
unsigned long start_ms = 0;
unsigned long end_ms = 0;
bool new_message = false;

CRGB initialLed = CHSV(INIT_HUE, INIT_SATURATION, INIT_BRIGHTNESS);
CRGB leds[NUM_LEDS];
CRGB noise[NUM_LEDS];
//fill_noise8(noise, NUM_LEDS, 4, 0, 1, 4, 0, 1, 0);

HSV_PROP main_brightness = {INIT_BRIGHTNESS, INIT_BRIGHTNESS, 255, 0};
HSV_PROP brightness = {INIT_BRIGHTNESS, INIT_BRIGHTNESS, 255, 0};
HSV_PROP saturation = {INIT_SATURATION, INIT_SATURATION, 255, 0};
HSV_PROP hue = {INIT_HUE, INIT_HUE, 255, 0};

SerialTransfer sigSerial;



void setup() {
  FastLED.addLeds<NEOPIXEL, DATA_PIN>(leds, NUM_LEDS);
  startup_sequence();
  
  // Serial transfer setup
  Serial.begin(38400);
  sigSerial.begin(Serial);
  delay(100);
}

void loop() {
  //processInput();
  // blend (leds[], target[], fract8 (ratio 0-255))
  // rainbow(leds, NUM_LEDS);
  // millisCheck(leds, NUM_LEDS);
  // FastLED.setBrightness(map(milliPong(4000), 0, 1000, 0, 255));
  
  //double y = 4.5;
  start_ms = millis();
  main_brightness = fadeToTarget(main_brightness);
  FastLED.setBrightness(main_brightness.current);
  FastLED.show();  ////// TAKES ~16ms to complete show() command
  //sendCommand('a', (int) millis() - start_ms);

  sendCommand('r', 1);
  
  end_ms = millis() + LOOP_DELAY;
  while (ms < end_ms && new_message == false) {
    ms = millis();
    if( sigSerial.available() ) {
      sigSerial.rxObj(inputCommand, 0U);
      processInput(inputCommand);
      break;
    }
    // new_message = processInput();
    // ms = millis();
  }
  //sendCommand('b', ms - start_ms);

  //sendCommand('m', ms);

  //FastLED.delay(LOOP_DELAY);


  // for (unsigned short i=0; i < LOOP_DELAY; i++) {
  //   bool message = processInput();
  //   if (message) i = LOOP_DELAY;
  //   else FastLED.delay(1);
  // }

  // uint16_t sendSize = 0;
  // sendSize = sigSerial.txObj(sigMessage, sendSize);
  // sigSerial.sendData(sendSize);
}

// void loop() {
//   // processInput();
//   // // brightness = fadeToTarget(brightness);
//   // // saturation = fadeToTarget(saturation);
//   // // hue = fadeToTarget(hue);
//   // brightness.current = brightness.target;
//   // saturation.current = saturation.target;
//   // hue.current = hue.target;

//   // strip.fill(strip.ColorHSV(hue.current, saturation.current>>8, brightness.current>>8));

//   delay(LOOP_DELAY);
// }

void sendCommand(char command, long value) {
  uint16_t sendSize = 0;
  sendStruct = {command, value};
  sendSize = sigSerial.txObj(sendStruct, sendSize);
  sigSerial.sendData(sendSize);
}

void sendValue(double value) {
  sigSerial.sendDatum(value);
}


// Mirror/pingpong values the reach the provided ms time
unsigned short milliPong(unsigned int time) {
  unsigned short outVal;
  unsigned int half = time / 2;
  unsigned short odd = ms / (half / 2) % 2;
  if (odd == 1) outVal = half - ms % half;
  else outVal = ms % half;
  return outVal;
}

bool processInput(COMMAND input) {
  switch (input.command) {
    case 'B':
      main_brightness.target = constrain(input.value, 0, main_brightness.max);
      if (dur == 0) main_brightness.current = main_brightness.target;
      main_brightness.duration = input.duration;
      return true;
    case 'b':
      brightness.target = constrain(input.value, 0, brightness.max);
      if (dur == 0) brightness.current = brightness.target;
      brightness.duration = input.duration;
      return true;
    case 's':
      saturation.target = constrain(input.value, 0, saturation.max);
      if (dur == 0) saturation.current = brightness.target;
      saturation.duration = input.duration;
      return true;
    case 'h':
      hue.target = constrain(input.value, 0, hue.max);
      if (dur == 0) hue.current = hue.target;
      hue.duration = input.duration;
      return true;
    default:
      return false;
  }
}

HSV_PROP fadeToTarget(HSV_PROP inputProperty) {
  long diff = (long)inputProperty.current - inputProperty.target;
  // Return intact property struct if it's value is at the target and duration has ended
  if (inputProperty.duration == 0 && diff == 0) {
    return inputProperty;
  }
  // Reset duration and/or current value to target if stuck
  if (inputProperty.duration < 1 || (diff < -1 && diff > 1)) {
    inputProperty.current = inputProperty.target;
    inputProperty.duration = 0;
    return inputProperty;
  }
  // Otherwise, start moving value towards target. Maybe add shaping/smoothing later?
  long step = diff / inputProperty.duration / LOOP_DELAY;
  inputProperty.current -= step;

  if (inputProperty.current < 0) {
    inputProperty.current = 0;
  } else if (inputProperty.current > inputProperty.max) {
    inputProperty.current = inputProperty.max;
  }
  //inputProperty.current = constrain(inputProperty.current, 0U, inputProperty.max);
  inputProperty.duration -= LOOP_DELAY; 
  return inputProperty;
}


// void rainbow(CRGB led_array[], int arraySize) {
//   for (uint16_t i = 0; i < arraySize; i++) {
//     led_array[i] = CHSV((millis() / 4) - (i * 3), 255, 255);
//   }
// }

void startup_sequence() {
  FastLED.clear(true);
  CRGB whiteTarget = CRGB::White;

  // Initial colour population
  for (uint16_t i = 0; i < NUM_LEDS; i++) {
    leds[i] = initialLed;
    FastLED.show();
    for (uint16_t j = 0; j < NUM_LEDS; j++) {
      leds[j].nscale8_video(253);
    }
  }

  // Shiney!
  for (uint16_t i = 0; i < NUM_LEDS; i++) {
    CRGB currentA = leds[i];
    CRGB currentB = leds[NUM_LEDS-i-1];
    whiteTarget.nscale8(253);
    leds[i] = whiteTarget;
    leds[NUM_LEDS-i-1] = whiteTarget;
    FastLED.show();
    leds[i] = blend(currentA, initialLed, 1);
    leds[NUM_LEDS-i-1] = blend(currentB, initialLed, 1);
    //leds[i].lerp8(targetLed, 0.9);
    //leds[NUM_LEDS-i-1].lerp8(targetLed, 0.9);
    for (uint16_t j = 0; j < NUM_LEDS; j++) {
      leds[j].nscale8(253);
    }
  }

  for (uint16_t i = 0; i < NUM_LEDS; i++) {
    leds[i] = initialLed;
  }

  main_brightness.current = 0;
  main_brightness.duration = 0;
  main_brightness.target = 0;

  FastLED.setBrightness(main_brightness.current);
  FastLED.show();
}
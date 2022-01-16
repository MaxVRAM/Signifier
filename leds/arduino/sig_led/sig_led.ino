
//    _________.__         .____     ___________________   
//   /   _____/|__| ____   |    |    \_   _____/\______ \  
//   \_____  \ |  |/ ___\  |    |     |    __)_  |    |  \ 
//   /        \|  / /_/  > |    |___  |        \ |    `   \
//  /_______  /|__\___  /  |_______ \/_______  //_______  /
//          \/   /_____/           \/        \/         \/ 

// Compile using Ardino-CLI: https://github.com/arduino/arduino-cli
// Use command:
// acompile /home/pi/Signifier/leds/arduino/sig_led && aupload /home/pi/Signifier/leds/arduino/sig_led

// TODO:
// Reporting: periodic updates to RPi with average loop length, run-time, etc.
// Systems: shutdown sequence...
// Mapping: fixed hardware mapped positions, north <-> south, in <-> out
// Functions: layer blending, blend modulation, position and HSV shaping
// Layers: solid colours, gradients, noise, trails, shapes (line blocks, etc)

#define FASTLED_ALLOW_INTERRUPTS 0

#include <Arduino.h>
#include <SerialTransfer.h>
#include <FastLED.h>
#define NUM_LEDS 240
#define DATA_PIN 6
#define LOOP_DELAY 10

const unsigned int INIT_BRIGHTNESS = 255U;
const unsigned int INIT_SATURATION = 255U;
const unsigned int INIT_HUE = 195U;
const unsigned int loopNumReadings = 10;

struct HSV_PROP
{
  unsigned short currVal;
  unsigned short startVal;
  unsigned short targetVal;
  float stepSize;
  float lerpPos;
};

struct COMMAND
{
  char command;
  long value;
  long duration;
} inputCommand;

struct AVERAGE
{
  unsigned int readings[loopNumReadings];
  long readIndex = 0;
  long total = 0;
  float average = 0;
} loopAvg;

unsigned long ms = 0;
unsigned long loopStartTime = 0;
unsigned long serialStartTime = 0;
unsigned long loopEndTime = 0;
unsigned long prevLoopTime = 0;

CRGB initRGB = CHSV(INIT_HUE, INIT_SATURATION, INIT_BRIGHTNESS);
CRGB leds[NUM_LEDS];
CRGB noise[NUM_LEDS];
//fill_noise8(noise, NUM_LEDS, 4, 0, 1, 4, 0, 1, 0);

HSV_PROP main_brightness = {INIT_BRIGHTNESS, INIT_BRIGHTNESS, INIT_BRIGHTNESS, 0UL, 0UL};
HSV_PROP brightness = {INIT_BRIGHTNESS, INIT_BRIGHTNESS, INIT_BRIGHTNESS, 0UL, 0UL};
HSV_PROP saturation = {INIT_SATURATION, INIT_SATURATION, INIT_SATURATION, 0UL, 0UL};
HSV_PROP hue = {INIT_HUE, INIT_HUE, INIT_HUE, 0UL, 0UL};

SerialTransfer sigSerial;


void setup()
{
  FastLED.addLeds<NEOPIXEL, DATA_PIN>(leds, NUM_LEDS);
  startup_sequence();

  // Serial transfer setup
  Serial.begin(38400);
  sigSerial.begin(Serial);
  delay(100);
}

void loop()
{
  prevLoopTime = millis() - loopStartTime;
  loopStartTime = millis();
  smooth(loopAvg, prevLoopTime);
  sendCommand(COMMAND{'L', loopStartTime, loopAvg.average});

  fadeToTarget(main_brightness);

  FastLED.setBrightness(main_brightness.currVal);
  FastLED.show();

  // Let the RPi know the Arduino is ready to receive serial commands for number of ms
  sendCommand(COMMAND{'r', 1, LOOP_DELAY});

  serialStartTime = millis();
  loopEndTime = serialStartTime + LOOP_DELAY;
  while (ms < loopEndTime)
  {
    ms = millis();
    if (sigSerial.available())
    {
      uint16_t recSize = 0;
      sigSerial.rxObj(inputCommand, recSize);
      processInput(inputCommand);
      break; // TODO: Test without to see if multiple commands can be received per loop
    }
  }
}

// Output the supplied COMMAND stcrut to the RPi via serial. Currently used only for debugging.
void sendCommand(COMMAND output)
{
  unsigned int sendSize = 0;
  sendSize = sigSerial.txObj(output, sendSize);
  sigSerial.sendData(sendSize);
}

// Uses received serial command to update matching parameters and control system flow. 
void processInput(COMMAND input)
{
  switch (input.command)
  {
  case 'B':
    assignInput(input, main_brightness);
    break;
  case 'b':
    assignInput(input, brightness);
    break;
  case 's':
    assignInput(input, saturation);
    break;
  case 'h':
    assignInput(input, hue);
    break;
  default:
    return;
  }
}

void assignInput(COMMAND input, HSV_PROP &property)
{
  //sendCommand(COMMAND{'A', property.currVal, input.value});
  
  // Reset property, assign start/end values, and calculate step size based on the average loop time
  resetFade(property);
  property.targetVal = input.value;
  property.startVal = property.currVal;
  property.stepSize = loopAvg.average / input.duration;
  property.lerpPos = 0.0f;

  //sendCommand(COMMAND{'R', property.currVal, property.targetVal});
}

// Linearly fade an LED property towards its target value.
void fadeToTarget(HSV_PROP &property)
{
  if (property.stepSize == 0.0f)
  {
    return;
  }
  // Maintain the current value and zero out the fade properties
  if (property.currVal == property.targetVal || property.lerpPos == 1.0f)
  {
    resetFade(property);
    return;
  }
  // Increment the lerp position and update the property's current value accordingly.
  property.lerpPos += property.stepSize;
  if (property.lerpPos > 1.0f)
  {
    property.currVal = property.targetVal;
    resetFade(property);
    return;
  }

  property.currVal = lerp8by8(property.startVal, property.targetVal, fract8(property.lerpPos*256));
}

void resetFade(HSV_PROP &property)
{
  property.targetVal = property.currVal;
  property.lerpPos = 1.0f;
  property.stepSize = 0.0f;
}

void startup_sequence()
{
  FastLED.clear(true);
  FastLED.setBrightness(main_brightness.currVal);

  // Initial colour population
  for (unsigned int i = 0; i < NUM_LEDS; i++)
  {
    leds[i] = initRGB;
    FastLED.show();
    for (unsigned int j = 0; j < NUM_LEDS; j++)
    {
      leds[j].nscale8_video(253);
    }
  }

  // Shiney demo bit
  CRGB whiteTarget = CRGB::White;
  for (unsigned int i = 0; i < NUM_LEDS; i++)
  {
    CRGB currentA = leds[i];
    CRGB currentB = leds[NUM_LEDS - i - 1];
    whiteTarget.nscale8(253);
    leds[i] = CRGB::White;
    leds[NUM_LEDS - i - 1] = CRGB::White;
    FastLED.show();
    leds[i] = blend(currentA, initRGB, 1);
    leds[NUM_LEDS - i - 1] = blend(currentB, initRGB, 1);
    for (unsigned int j = 0; j < NUM_LEDS; j++)
    {
      leds[j].nscale8(253);
    }
  }
  for (unsigned int i = 0; i < NUM_LEDS; i++)
  {
    leds[i] = initRGB;
  }

  main_brightness.currVal = 0;
  resetFade(main_brightness);
  FastLED.setBrightness(main_brightness.currVal);
  FastLED.show();
}

float smooth(AVERAGE &avgStruct, long newValue) {
  // https://www.aranacorp.com/en/implementation-of-the-moving-average-in-arduino/
  avgStruct.total = avgStruct.total - avgStruct.readings[avgStruct.readIndex];
  avgStruct.readings[avgStruct.readIndex] = newValue;
  avgStruct.total = avgStruct.total + avgStruct.readings[avgStruct.readIndex];

  avgStruct.readIndex = avgStruct.readIndex + 1;
  if (avgStruct.readIndex >= loopNumReadings) {
    avgStruct.readIndex = 0;
  }
  avgStruct.average = (float)avgStruct.total / (float)loopNumReadings;
  return avgStruct.average;
}

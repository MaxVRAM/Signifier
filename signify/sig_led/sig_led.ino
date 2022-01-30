
//    _________.__         .____     ___________________   
//   /   _____/|__| ____   |    |    \_   _____/\______ \  
//   \_____  \ |  |/ ___\  |    |     |    __)_  |    |  \ 
//   /        \|  / /_/  > |    |___  |        \ |    `   \
//  /_______  /|__\___  /  |_______ \/_______  //_______  /
//          \/   /_____/           \/        \/         \/ 

// Compile using Ardino-CLI: https://github.com/arduino/arduino-cli
// Use command:
// acompile ~/Signifier/signify/sig_led && aupload ~/Signifier/signify/sig_led -v

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
#define BAUD 38400
#define NUM_LEDS 240
#define HALF_LEDS 120
#define QRT_LEDS 60
#define DATA_PIN 6

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

unsigned long TARGET_LOOP_DUR = 30;

unsigned long ms = 0;
unsigned long loopStartTime = 0;
unsigned long serialStartTime = 0;
unsigned long loopEndTime = 0;
unsigned long prevLoopTime = 0;


CRGB initRGB = CHSV(INIT_HUE, INIT_SATURATION, INIT_BRIGHTNESS);
CRGB leds[NUM_LEDS];
CRGB noise[NUM_LEDS];
//fill_noise8(noise, NUM_LEDS, 4, 0, 1, 4, 0, 1, 0);

HSV_PROP brightness = {INIT_BRIGHTNESS, INIT_BRIGHTNESS, INIT_BRIGHTNESS, 0UL, 0UL};
HSV_PROP saturation = {INIT_SATURATION, INIT_SATURATION, INIT_SATURATION, 0UL, 0UL};
HSV_PROP hue = {INIT_HUE, INIT_HUE, INIT_HUE, 0UL, 0UL};

SerialTransfer sigSerial;


unsigned int loopValue(unsigned int min, unsigned int max, unsigned int val)
{
  if (val < min) val = max - 1;
  return val % max;
}

// Provides remapped pixel assignment. Index should be within 1/4 of total LED count
void mirrorPixel(CRGB (& in_leds)[NUM_LEDS], CRGB colour, unsigned int i)
{
  unsigned int UA = loopValue(0, NUM_LEDS, i);
  unsigned int UB = loopValue(0, NUM_LEDS, HALF_LEDS - 1 - i);
  unsigned int DA = loopValue(0, NUM_LEDS, NUM_LEDS - 1 - i);
  unsigned int DB = loopValue(0, NUM_LEDS, HALF_LEDS + i);

  in_leds[UA] = colour;   // Up, Side A
//  in_leds[UB] = colour;   // Up, Side B
//  in_leds[DA] = colour;   // Down, Side A
//  in_leds[DB] = colour;   // Down, Side B
}  

// Provides remapped pixel assignment. Index should be within 1/2 of total LED count
void endToEnd(CRGB (& in_leds)[NUM_LEDS], CRGB colour, unsigned int i)
{
  unsigned int SA = loopValue(0, NUM_LEDS, QRT_LEDS + i);
  unsigned int SB = loopValue(0, NUM_LEDS, QRT_LEDS - 1 - i);

  in_leds[SA] = colour;   // Side A
  in_leds[SB] = colour;   // Side B
}


void setup()
{
  FastLED.addLeds<NEOPIXEL, DATA_PIN>(leds, NUM_LEDS);
  startup_sequence();

  // Serial transfer setup
  Serial.begin(BAUD);
  sigSerial.begin(Serial);
  loopStartTime = millis();
  delay(TARGET_LOOP_DUR);
  ms = millis();
}

void loop()
{
  prevLoopTime = millis() - loopStartTime;
  loopStartTime = millis();
  smooth(loopAvg, prevLoopTime);
  //sendCommand(COMMAND{'L', loopStartTime, loopAvg.average});

  fadeToTarget(brightness);

  FastLED.setBrightness(brightness.currVal);
  FastLED.show();

  // Calculates the remaining time to wait for a response based on the target loop time
  loopEndTime = loopStartTime + TARGET_LOOP_DUR;

  // Let the RPi know the Arduino is ready to receive serial commands for number of ms
  sendCommand(COMMAND{'r', 1, loopEndTime - millis()});

  while (ms < loopEndTime)
  {
    ms = millis();
    if (sigSerial.available())
    {
      uint16_t recSize = 0;
      sigSerial.rxObj(inputCommand, recSize);
      processInput(inputCommand);
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
    assignInput(input, brightness);
    break;
  case 'S':
    assignInput(input, saturation);
    break;
  case 'H':
    assignInput(input, hue);
    break;
  case 'l':
    TARGET_LOOP_DUR = input.value;
    sendCommand(COMMAND{'l', TARGET_LOOP_DUR, 0});
  default:
    return;
  }
}

void assignInput(COMMAND input, HSV_PROP &property)
{
  sendCommand(COMMAND{'A', property.currVal, input.value});
  
  // Reset property, assign start/end values, and calculate step size based on the average loop time
  resetFade(property);
  property.targetVal = input.value;
  property.startVal = property.currVal;
  property.stepSize = loopAvg.average / input.duration;
  property.lerpPos = 0.0f;
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
  brightness.currVal = 0;
  resetFade(brightness);
  FastLED.setBrightness(255);

  for (unsigned int i = 0; i < NUM_LEDS; i++)
  {
    leds[i] = initRGB;
  }

  FastLED.show();
  
  for (int i = 255; i > 0; i--)
  {
    FastLED.setBrightness(i);
    FastLED.show();
  }

  // FastLED.clear(true);
  // leds[0] = CRGB::White;
  // leds[QRT_LEDS - 1] = CRGB::White;
  // leds[QRT_LEDS] = CRGB::White;
  // leds[HALF_LEDS - 1] = CRGB::White;
  // leds[NUM_LEDS - 1] = CRGB::White;
  // leds[HALF_LEDS + QRT_LEDS - 1] = CRGB::White;
  // leds[HALF_LEDS + QRT_LEDS] = CRGB::White;

  // FastLED.show();
  // delay(100000);

  // for (int j = 0; j < 100; j++)
  // {
  //   // Demo for mirror
  //   for (unsigned int i = 0; i < QRT_LEDS; i++)
  //   {
  //     mirrorPixel(leds, initRGB, i);
  //     FastLED.show();
  //     mirrorPixel(leds, CRGB::Black, i - 1);
  //     delay(10);
  //   }
  // }

  // // Demo for end to end
  // for (unsigned int i = 0; i < HALF_LEDS; i++)
  // {
  //   endToEnd(leds, initRGB, i);
  //   for (unsigned int j = 0; j < NUM_LEDS; j++)
  //   {
  //     leds[j].nscale8_video(253);
  //   }
  //   FastLED.show();
  //   delay(1);
  // }


  // for (unsigned int i = 0; i < )



  // // // Shiney demo bit
  // CRGB whiteTarget = CRGB::White;
  // for (unsigned int i = 0; i < NUM_LEDS; i++)
  // {
  //   CRGB currentA = leds[i];
  //   CRGB currentB = leds[NUM_LEDS - i - 1];
  //   whiteTarget.nscale8(253);
  //   leds[i] = CRGB::White;
  //   leds[NUM_LEDS - i - 1] = CRGB::White;
  //   FastLED.show();
  //   leds[i] = blend(currentA, initRGB, 1);
  //   leds[NUM_LEDS - i - 1] = blend(currentB, initRGB, 1);
  //   for (unsigned int j = 0; j < NUM_LEDS; j++)
  //   {
  //     leds[j].nscale8(253);
  //   }
  // }
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


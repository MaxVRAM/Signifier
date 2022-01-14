// WORKING IN VS CODE:
// Include Arduino.h so intellisense can find the standard Arduino packages. Produces false-negative for Arduino.h
// #include <Arduino.h>
//
// Compile with this:
// acompile /home/pi/Signifier/leds/arduino/purple_volume_fast && aupload /home/pi/Signifier/leds/arduino/purple_volume_fast
//
// https://joachimweise.github.io/post/2020-04-07-vscode-remote/
//
//
// USING FASTLED LIBRARY
// https://github.com/FastLED/FastLED/wiki/Overview

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

// Covert to its own class?
struct HSV_PROP
{
  unsigned short currVal;
  unsigned short startVal;
  unsigned short targetVal;
  float stepSize;
  float lerpPos;
  //unsigned long startTime;
  //unsigned long endTime;
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
  //sendCommand(COMMAND{'L', loopStartTime, loopAvg.average});

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

// Output the supplied COMMAND scrut to the RPi via serial. Currently used only for debugging.
void sendCommand(COMMAND output)
{
  unsigned int sendSize = 0;
  sendSize = sigSerial.txObj(output, sendSize);
  sigSerial.sendData(sendSize);
}

// Uses received serial command to update matching parameters and control system flow. 
void processInput(COMMAND input)
{
  // For debugging, send detected command back to the RPi
  // sendCommand(input);
  // // Assinged to a property based on char sent in serial command.
  // HSV_PROP property;
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
  sendCommand(COMMAND{'A', property.currVal, input.value});
  // Reset property, assign start/end values, and calculate step size based on the average loop time
  resetFade(property);
  property.targetVal = input.value;
  property.startVal = property.currVal;
  //float stepFactor = loopAvg.average / input.duration;
  //float valueDiff = (float)property.targetVal - (float)property.startVal;
  //property.stepSize = valueDiff * stepFactor;
  property.stepSize = loopAvg.average / input.duration;
  property.lerpPos = 0.0f;

  sendCommand(COMMAND{'R', property.currVal, property.targetVal});
  //sendCommand(COMMAND{'D', valueDiff, long(stepFactor*1000)});
}

  // // If I knew I'd probably use pointers instead
  // switch (input.command)
  // {
  // case 'B':
  //   main_brightness = property;
  //   break;
  // case 'b':
  //   brightness = property;
  //   break;
  // case 's':
  //   saturation = property;
  //   break;
  // case 'h':
  //   hue = property;
  //   break;
  // default:
  //   return;
  // }
// }



  // switch (input.command)
  // {
  // case 'B':
  //   main_brightness.targetVal = constrain(input.value, 0, 255);
  //   main_brightness.startTime = currMs;
  //   if (input.duration == 0)
  //   {
  //     main_brightness.currVal = main_brightness.targetVal;
  //     main_brightness.endTime = currMs;
  //   }
  //   else {
  //     main_brightness.endTime = currMs + input.duration;
  //     sendCommand(COMMAND{'M', main_brightness.startTime, main_brightness.endTime});
  //     sendCommand(COMMAND{'T', main_brightness.currVal, main_brightness.targetVal});
  //   }
  //   break;
  // case 'b':
  //   brightness.targetVal = constrain(input.value, 0, 255);
  //   brightness.startTime = currMs;
  //   if (input.duration == 0)
  //   {
  //     brightness.currVal = brightness.targetVal;
  //     brightness.endTime = currMs;
  //   }
  //   else
  //   {
  //     brightness.endTime = currMs + input.duration;
  //   }
  //   break;
  // case 's':
  //   saturation.targetVal = constrain(input.value, 0, 255);
  //   saturation.startTime = currMs;
  //   if (input.duration == 0)
  //   {
  //     saturation.currVal = saturation.targetVal;
  //     saturation.endTime = currMs;
  //   }
  //   else {
  //     saturation.endTime = currMs + input.duration;
  //   }
  //   break;
  // case 'h':
  //   hue.targetVal = constrain(input.value, 0, 255);
  //   hue.startTime = currMs;
  //   if (input.duration == 0)
  //   {
  //     hue.currVal = hue.targetVal;
  //     hue.endTime = currMs;
  //   }
  //   else {
  //     hue.endTime = currMs + input.duration;
  //   }
  //   break;
  // default:
  //   break;
  // }

//   property.targetVal = constrain(input.value, 0, 255);
//   property.startTime = currMs;
//   if (input.duration == 0)
//   {
//     property.currVal = property.targetVal;
//     property.endTime = currMs;
//   }
//   else {
//     property.endTime = currMs + input.duration;
//   }
// }

// Linearly fade an LED property towards its target value.
void fadeToTarget(HSV_PROP &property)
{
  if (property.stepSize == 0.0f)
  {
    //sendCommand(COMMAND{'S', long(property.stepSize*1000), property.currVal});
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
  //sendCommand(COMMAND{'N', property.currVal, property.targetVal});
}

void resetFade(HSV_PROP &property)
{
  property.targetVal = property.currVal;
  property.lerpPos = 1.0f;
  property.stepSize = 0.0f;
}


  // long valueDiff = (long)input.currVal - input.targetVal;
  // float timeDiff = input.endTime - input.startTime;
  // long estLoopLen = currMs - prevMs;
  // float estNumStepsLeft = estLoopLen / (input.endTime - currMs);
  // // Return intact property struct if it's value is at the target and duration has ended
  // if (input.endTime <= currMs || valueDiff <= 1)
  // {
  //   input.currVal = input.targetVal;
  //   input.startTime = 0;
  //   input.endTime = 0;
  //   return input;
  // }
  // // Reset propery details if we think the event should ended
  // // if (inputProperty.endTime >= currMs + estLoopLen || (diff < -1 && diff > 1))
  // // {
  // //   inputProperty.current = inputProperty.target;
  // //   inputProperty.startTime = 0;
  // //   inputProperty.endTime = 0;
  // //   return inputProperty;
  // // }
  // // Otherwise, start moving value towards target. Maybe add shaping/smoothing later?
  // long step = round(valueDiff / estLoopLen);
  // input.currVal -= step;

  // sendCommand(COMMAND{'P', step, estLoopLen});

  // // Limit value within range. TODO: Add value wrapping for hue?
  // if (input.currVal < 0) input.currVal = 0;
  // else if (input.currVal > 255) input.currVal = 255;
// }

// void rainbow(CRGB led_array[], int arraySize) {
//   for (uint16_t i = 0; i < arraySize; i++) {
//     led_array[i] = CHSV((millis() / 4) - (i * 3), 255, 255);
//   }
// }

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

  // // Shiney!
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
  //   //leds[i].lerp8(targetLed, 0.9);
  //   //leds[NUM_LEDS-i-1].lerp8(targetLed, 0.9);
  //   for (unsigned int j = 0; j < NUM_LEDS; j++)
  //   {
  //     leds[j].nscale8(253);
  //   }
  // }

  // for (unsigned int i = 0; i < NUM_LEDS; i++)
  // {
  //   leds[i] = initRGB;
  // }

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





// Mirror/pingpong values the reach the provided ms time TODO: Remove
unsigned short milliPong(unsigned int time)
{
  unsigned short outVal;
  unsigned int half = time / 2;
  unsigned short odd = ms / (half / 2) % 2;
  if (odd == 1)
    outVal = half - ms % half;
  else
    outVal = ms % half;
  return outVal;
}



// void loop() {
//   // processInput();
//   // // brightness = fadeToTarget(brightness);
//   // // saturation = fadeToTarget(saturation);
//   // // hue = fadeToTarget(hue);
//   // brightness.current = brightness.target;
//   // saturation.current = saturation.target;
//   // hue.current = hue.target;

  //processInput();
  // blend (leds[], target[], fract8 (ratio 0-255))
  // rainbow(leds, NUM_LEDS);
  // millisCheck(leds, NUM_LEDS);
  // FastLED.setBrightness(map(milliPong(4000), 0, 1000, 0, 255));

//   // strip.fill(strip.ColorHSV(hue.current, saturation.current>>8, brightness.current>>8));

//   delay(LOOP_DELAY);
// }



// Likely redundent... will remove.
// void sendValue(double value)
// {
//   sigSerial.sendDatum(value);
// }

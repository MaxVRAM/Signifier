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

const unsigned int INIT_BRIGHTNESS = 255U;
const unsigned int INIT_SATURATION = 255U;
const unsigned int INIT_HUE = 195U;

struct HSV_PROP
{
  unsigned short current;
  unsigned short target;
  unsigned short max;
  unsigned long startTime;
  unsigned long endTime;
};

struct COMMAND
{
  char command;
  long value;
  long duration;
} inputCommand;

unsigned short hardBright = 0;
unsigned long ms = 0;
unsigned long loop_start_ms = 0;
unsigned long serial_start_ms = 0;
unsigned long end_ms = 0;
bool new_message = false;

CRGB initialLed = CHSV(INIT_HUE, INIT_SATURATION, INIT_BRIGHTNESS);
CRGB leds[NUM_LEDS];
CRGB noise[NUM_LEDS];
//fill_noise8(noise, NUM_LEDS, 4, 0, 1, 4, 0, 1, 0);

HSV_PROP main_brightness = {INIT_BRIGHTNESS, INIT_BRIGHTNESS, 255, 0UL, 0UL};
HSV_PROP brightness = {INIT_BRIGHTNESS, INIT_BRIGHTNESS, 255, 0UL, 0UL};
HSV_PROP saturation = {INIT_SATURATION, INIT_SATURATION, 255, 0UL, 0UL};
HSV_PROP hue = {INIT_HUE, INIT_HUE, 255, 0UL, 0UL};

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
  loop_start_ms = millis();
  //processInput();
  // blend (leds[], target[], fract8 (ratio 0-255))
  // rainbow(leds, NUM_LEDS);
  // millisCheck(leds, NUM_LEDS);
  // FastLED.setBrightness(map(milliPong(4000), 0, 1000, 0, 255));

  //double y = 4.5;
  main_brightness = fadeToTarget(main_brightness, loop_start_ms, serial_start_ms);

  FastLED.setBrightness(main_brightness.current);
  FastLED.show(); ////// TAKES ~16ms to complete show() command
  //sendCommand('a', (int) millis() - loop_start_ms);

  //sendCommand(COMMAND{'Z', 40, 50});
  sendCommand(COMMAND{'r', 1, 0});

  serial_start_ms = millis();
  end_ms = serial_start_ms + LOOP_DELAY;
  while (ms < end_ms && new_message == false)
  {
    ms = millis();
    if (sigSerial.available())
    {
      uint16_t recSize = 0;
      sigSerial.rxObj(inputCommand, recSize);
      processInput(inputCommand);
      break; // TODO: Test without break
    }
  }
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

void sendCommand(COMMAND output)
{
  unsigned int sendSize = 0;
  sendSize = sigSerial.txObj(output, sendSize);
  sigSerial.sendData(sendSize);
}

void sendValue(double value)
{
  sigSerial.sendDatum(value);
}

// Mirror/pingpong values the reach the provided ms time
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

bool processInput(COMMAND input)
{
  sendCommand(input);
  switch (input.command)
  {
  case 'B':
    main_brightness.target = constrain(input.value, 0, main_brightness.max);
    main_brightness.startTime = ms;
    if (input.duration == 0)
    {
      main_brightness.current = main_brightness.target;
      main_brightness.endTime = ms;
    }
    else {
      main_brightness.endTime = ms + input.duration;
      sendCommand(COMMAND{'M', main_brightness.startTime, main_brightness.endTime});
      sendCommand(COMMAND{'T', main_brightness.current, main_brightness.target});
    }
    break;
  case 'b':
    brightness.target = constrain(input.value, 0, brightness.max);
    brightness.startTime = ms;
    if (input.duration == 0)
    {
      brightness.current = brightness.target;
      brightness.endTime = ms;
    }
    else
    {
      brightness.endTime = ms + input.duration;
    }
    break;
  case 's':
    saturation.target = constrain(input.value, 0, saturation.max);
    saturation.startTime = ms;
    if (input.duration == 0)
    {
      saturation.current = saturation.target;
      saturation.endTime = ms;
    }
    else {
      saturation.endTime = ms + input.duration;
    }
    break;
  case 'h':
    hue.target = constrain(input.value, 0, hue.max);
    hue.startTime = ms;
    if (input.duration == 0)
    {
      hue.current = hue.target;
      hue.endTime = ms;
    }
    else {
      hue.endTime = ms + input.duration;
    }
    break;
  default:
    break;
  }
}

HSV_PROP fadeToTarget(HSV_PROP inputProperty, unsigned long currMs, unsigned long prevMs)
{
  long valueDiff = (long)inputProperty.current - inputProperty.target;
  float timeDiff = inputProperty.endTime - inputProperty.startTime;
  long estLoopLen = currMs - prevMs;
  // Return intact property struct if it's value is at the target and duration has ended
  if (inputProperty.endTime <= currMs || valueDiff == 0)
  {
    inputProperty.current = inputProperty.target;
    inputProperty.startTime = 0;
    inputProperty.endTime = 0;
    return inputProperty;
  }
  // Reset propery details if we think the event should ended
  // if (inputProperty.endTime >= currMs + estLoopLen || (diff < -1 && diff > 1))
  // {
  //   inputProperty.current = inputProperty.target;
  //   inputProperty.startTime = 0;
  //   inputProperty.endTime = 0;
  //   return inputProperty;
  // }
  // Otherwise, start moving value towards target. Maybe add shaping/smoothing later?
  float estNumStepsLeft = estLoopLen / (inputProperty.endTime - currMs);
  long step = round(valueDiff / estLoopLen);
  inputProperty.current -= step;

  sendCommand(COMMAND{'P', step, estLoopLen});
  //sendCommand(COMMAND{'P', 0, estLoopLen});

  // Limit value within range. TODO: Add value looping for hue
  if (inputProperty.current < 0)
  {
    inputProperty.current = 0;
  }
  else if (inputProperty.current > inputProperty.max)
  {
    inputProperty.current = inputProperty.max;
  }
  //inputProperty.current = constrain(inputProperty.current, 0U, inputProperty.max);
  return inputProperty;
}

// void rainbow(CRGB led_array[], int arraySize) {
//   for (uint16_t i = 0; i < arraySize; i++) {
//     led_array[i] = CHSV((millis() / 4) - (i * 3), 255, 255);
//   }
// }

void startup_sequence()
{
  FastLED.clear(true);
  CRGB whiteTarget = CRGB::White;

  // Initial colour population
  for (unsigned int i = 0; i < NUM_LEDS; i++)
  {
    leds[i] = initialLed;
    FastLED.show();
    for (unsigned int j = 0; j < NUM_LEDS; j++)
    {
      leds[j].nscale8_video(253);
    }
  }

  // Shiney!
  for (unsigned int i = 0; i < NUM_LEDS; i++)
  {
    CRGB currentA = leds[i];
    CRGB currentB = leds[NUM_LEDS - i - 1];
    whiteTarget.nscale8(253);
    leds[i] = whiteTarget;
    leds[NUM_LEDS - i - 1] = whiteTarget;
    FastLED.show();
    leds[i] = blend(currentA, initialLed, 1);
    leds[NUM_LEDS - i - 1] = blend(currentB, initialLed, 1);
    //leds[i].lerp8(targetLed, 0.9);
    //leds[NUM_LEDS-i-1].lerp8(targetLed, 0.9);
    for (unsigned int j = 0; j < NUM_LEDS; j++)
    {
      leds[j].nscale8(253);
    }
  }

  for (unsigned int i = 0; i < NUM_LEDS; i++)
  {
    leds[i] = initialLed;
  }

  main_brightness.current = 0;
  main_brightness.startTime = 0;
  main_brightness.endTime = 0;
  main_brightness.target = 0;

  FastLED.setBrightness(main_brightness.current);
  FastLED.show();
}
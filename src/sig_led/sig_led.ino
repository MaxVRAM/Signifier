
/***
 *      _________.__         .____     ___________________   
 *     /   _____/|__| ____   |    |    \_   _____/\______ \  
 *     \_____  \ |  |/ ___\  |    |     |    __)_  |    |  \ 
 *     /        \|  / /_/  > |    |___  |        \ |    `   \
 *    /_______  /|__\___  /  |_______ \/_______  //_______  /
 *            \/   /_____/           \/        \/         \/ 
 */

// Compile using Ardino-CLI: https://github.com/arduino/arduino-cli
// Use command:
// acompile ~/Signifier/src/sig_led && aupload ~/Signifier/src/sig_led -v


#define FASTLED_ALLOW_INTERRUPTS 0

#include <Arduino.h>
#include <SerialTransfer.h>
#include <FastLED.h>
#define BAUD 38400
#define NUM_LEDS 240
#define HALF_LEDS 120
#define QRT_LEDS 60
#define DATA_PIN 6

SerialTransfer sigSerial;

const unsigned int loopNumReadings = 10;

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

struct LED_PROPERTY
{
  byte currVal;
  byte startVal;
  byte targetVal;
  float stepSize;
  float lerpPos;
};

const byte INIT_BRIGHTNESS = 255;
const byte INIT_SATURATION = 255;
const byte INIT_HUE = 195;

const byte INIT_NOISE_SPEED = 200;
const byte INIT_NOISE_AMT = 0;
const byte INIT_NOISE_SAT = 0;
const byte INIT_NOISE_HUE = 0;

const byte INIT_MIRROR_BAR = 0;
const byte INIT_MIRROR_SAT = 0;
const byte INIT_MIRROR_HUE = 0;

LED_PROPERTY brightness = {INIT_BRIGHTNESS, INIT_BRIGHTNESS, INIT_BRIGHTNESS, 0UL, 0UL};
LED_PROPERTY saturation = {INIT_SATURATION, INIT_SATURATION, INIT_SATURATION, 0UL, 0UL};
LED_PROPERTY hue = {INIT_HUE, INIT_HUE, INIT_HUE, 0UL, 0UL};
LED_PROPERTY noiseAmt = {INIT_NOISE_AMT, INIT_NOISE_AMT, INIT_NOISE_AMT, 0UL, 0UL};
LED_PROPERTY noiseSpeed = {INIT_NOISE_SPEED, INIT_NOISE_SPEED, INIT_NOISE_SPEED, 0UL, 0UL};
LED_PROPERTY noiseSat = {INIT_NOISE_SAT, INIT_NOISE_SAT, INIT_NOISE_SAT, 0UL, 0UL};
LED_PROPERTY noiseHue = {INIT_NOISE_HUE, INIT_NOISE_HUE, INIT_NOISE_HUE, 0UL, 0UL};
LED_PROPERTY mirrorBar = {INIT_MIRROR_BAR, INIT_MIRROR_BAR, INIT_MIRROR_BAR, 0UL, 0UL};
LED_PROPERTY mirrorSat = {INIT_MIRROR_SAT, INIT_MIRROR_SAT, INIT_MIRROR_SAT, 0UL, 0UL};
LED_PROPERTY mirrorHue = {INIT_MIRROR_HUE, INIT_MIRROR_HUE, INIT_MIRROR_HUE, 0UL, 0UL};

CHSV initHSV = CHSV(INIT_HUE, INIT_SATURATION, INIT_BRIGHTNESS);

CRGB led_pixels[NUM_LEDS];

uint8_t noise_pixels[NUM_LEDS];
unsigned long noiseTime = 0;
uint8_t mirror_bar_pixels[QRT_LEDS];


unsigned long TARGET_LOOP_DUR = 60;
unsigned long ms = 0;
unsigned long loopStartTime = 0;
unsigned long serialStartTime = 0;
unsigned long loopEndTime = 0;
unsigned long prevLoopTime = 0;


unsigned int loopValue(unsigned int min, unsigned int max, unsigned int val)
{
  if (val < min) val = max - 1;
  return val % max;
}


/***
 *      _________       __                
 *     /   _____/ _____/  |_ __ ________  
 *     \_____  \_/ __ \   __\  |  \____ \ 
 *     /        \  ___/|  | |  |  /  |_> >
 *    /_______  /\___  >__| |____/|   __/ 
 *            \/     \/           |__|    
 */

void setup()
{
  for (uint8_t i = 0; i < NUM_LEDS; i++)
  {
    noise_pixels[i] = 0;
  }

  FastLED.addLeds<NEOPIXEL, DATA_PIN>(led_pixels, NUM_LEDS);
  startup_sequence();

  // Serial transfer setup
  Serial.begin(BAUD);
  sigSerial.begin(Serial);
  loopStartTime = millis();
  delay(TARGET_LOOP_DUR);
  ms = millis();
}


/***
 *    .____                         
 *    |    |    ____   ____ ______  
 *    |    |   /  _ \ /  _ \\____ \ 
 *    |    |__(  <_> |  <_> )  |_> >
 *    |_______ \____/ \____/|   __/ 
 *            \/            |__|    
 */

void loop()
{
  prevLoopTime = millis() - loopStartTime;
  loopStartTime = millis();
  smooth(loopAvg, prevLoopTime);

  // Update moving values
  fadeToTarget(brightness);
  fadeToTarget(saturation);
  fadeToTarget(hue);
  fadeToTarget(noiseAmt);
  fadeToTarget(noiseSpeed);
  fadeToTarget(noiseSat);
  fadeToTarget(noiseHue);
  fadeToTarget(mirrorBar);
  fadeToTarget(mirrorSat);
  fadeToTarget(mirrorHue);
  
  // Write to pixel arrays
  fill_solid(led_pixels, NUM_LEDS, CHSV(hue.currVal, saturation.currVal, brightness.currVal));
  add_noise(led_pixels, NUM_LEDS);
  add_mirror_bar(led_pixels, NUM_LEDS);

  // Push pixel arrays to LEDs
  //FastLED.setBrightness(brightness.currVal);
  FastLED.setBrightness(255);
  FastLED.show();

  // Calculates the remaining time to wait for a response based on the target loop time
  loopEndTime = loopStartTime + TARGET_LOOP_DUR;

  // Send ready command to RPi with previous loop duration, number of ms it will listen until next loop
  sendCommand(COMMAND{'r', prevLoopTime, loopEndTime - millis()});

  while (ms < loopEndTime)
  {
    // Gather and process incoming serial commands until target loop time is reached.
    ms = millis();
    if (sigSerial.available())
    {
      uint16_t recSize = 0;
      sigSerial.rxObj(inputCommand, recSize);
      processInput(inputCommand);
    }
  }
}


/***
 *      _________            .__       .__   
 *     /   _____/ ___________|__|____  |  |  
 *     \_____  \_/ __ \_  __ \  \__  \ |  |  
 *     /        \  ___/|  | \/  |/ __ \|  |__
 *    /_______  /\___  >__|  |__(____  /____/
 *            \/     \/              \/      
 */

// Push serial command to RPi.
void sendCommand(COMMAND output)
{
  unsigned int sendSize = 0;
  sendSize = sigSerial.txObj(output, sendSize);
  sigSerial.sendData(sendSize);
}

// Update matching LED and system parameters based on received serial commands. 
void processInput(COMMAND input)
{
  switch (input.command)
  {
  case 'l': // Updates the Arduino's target loop duration
    TARGET_LOOP_DUR = input.value;
    sendCommand(COMMAND{'l', TARGET_LOOP_DUR, 0});
  case 'B': // Sets the solid fill colour's brightness
    assignInput(input, brightness);
    break;
  case 'S': // Set solid fill colour saturation
    assignInput(input, saturation);
    break;
  case 'H': // Set solid fill colour hue
    assignInput(input, hue);
    break;
  case 'N': // Set amount of overlaid noise effect
    assignInput(input, noiseAmt);
    break;
  case 'O': // Set speed of noise effect
    assignInput(input, noiseSpeed);
    break;
  case 'P': // Set saturation of noise effect
    assignInput(input, noiseSat);
    break;
  case 'Q': // Set hue of noise effect
    assignInput(input, noiseHue);
    break;
  case 'M': // Set size of mirror bar layer
    assignInput(input, mirrorBar);
    break;
  case 'K': // Set saturation of mirror bar layer
    assignInput(input, mirrorSat);
    break;
  case 'L': // Set hue of mirror bar layer
    assignInput(input, mirrorHue);
    break;
  default:
    return;
  }
}


/***
 *    __________                                          .__                
 *    \______   \_______  ____   ____  ____   ______ _____|__| ____    ____  
 *     |     ___/\_  __ \/  _ \_/ ___\/ __ \ /  ___//  ___/  |/    \  / ___\ 
 *     |    |     |  | \(  <_> )  \__\  ___/ \___ \ \___ \|  |   |  \/ /_/  >
 *     |____|     |__|   \____/ \___  >___  >____  >____  >__|___|  /\___  / 
 *                                  \/    \/     \/     \/        \//_____/  
 */

// Apply new target value for LED property
void assignInput(COMMAND input, LED_PROPERTY &property)
{
  // Reset property, assign start/end values, and calculate step size based on the average loop time
  resetFade(property);
  property.targetVal = input.value;
  property.startVal = property.currVal;
  property.stepSize = loopAvg.average / input.duration;
  property.lerpPos = 0.0f;
}

// Linearly fade an LED property towards its target value.
void fadeToTarget(LED_PROPERTY &property)
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
  // Apply interpolated value to LED property 
  property.currVal = lerp8by8(property.startVal, property.targetVal, fract8(property.lerpPos*256));
}

// Zero out the current fade values and stop LED property where it is
void resetFade(LED_PROPERTY &property)
{
  property.targetVal = property.currVal;
  property.lerpPos = 1.0f;
  property.stepSize = 0.0f;
}


/***
 *    __________         __    __                              
 *    \______   \_____ _/  |__/  |_  ___________  ____   ______
 *     |     ___/\__  \\   __\   __\/ __ \_  __ \/    \ /  ___/
 *     |    |     / __ \|  |  |  | \  ___/|  | \/   |  \\___ \ 
 *     |____|    (____  /__|  |__|  \___  >__|  |___|  /____  >
 *                    \/                \/           \/     \/ 
 */

// Generates simplex noise pattern over LED strip and adds the effect to the solid colour
void add_noise(struct CRGB * targetArray, int numToFill)
{
  // Only process the effect's values if it's amount is above 0.
  // Otherwise we assume the effect layer is off and skip it.
  if (noiseAmt.currVal > 0)
  {
    // Update the offset of the noise function based on speed parameter and loop time.
    noiseTime += prevLoopTime * noiseSpeed.currVal / 10;
    long width = map(noiseAmt.currVal, 0, 255, 2, 60);
    long thresh = map(noiseAmt.currVal, 0, 255, 215, 185);
    long amount = map(noiseAmt.currVal, 0, 255, 40, 255);

    for (unsigned int i = 0; i < NUM_LEDS; i++)
    {
      uint8_t noiseBrightness = inoise8(i * width, noiseTime) > thresh ? amount : 0;
      noise_pixels[i] = blend8(noise_pixels[i], noiseBrightness, noiseSpeed.currVal);
      CRGB new_noise;
      hsv2rgb_rainbow(CHSV(noiseHue.currVal, noiseSat.currVal, noise_pixels[i]), new_noise);
      targetArray[i] += new_noise; // addToRGB(noise_pixels[i]);
    }
  }
}


// Applies the mirror bar effect pattern over the solid colour
void add_mirror_bar(struct CRGB * targetArray, int numToFill)
{
  for (unsigned int i = 0; i < QRT_LEDS; i++)
  {
    uint8_t barBrightness = i * 4 < mirrorBar.currVal ? 255 : 0;
    mirror_bar_pixels[i] = blend8(mirror_bar_pixels[i], barBrightness, 10);
    CRGB new_bar;
    hsv2rgb_rainbow(CHSV(mirrorHue.currVal, mirrorSat.currVal, mirror_bar_pixels[i]), new_bar);
    mirrorPixel(targetArray, i, new_bar);
    //targetArray[i].addToRGB(mirror_bar_pixels[i]);
  }
}


/***
 *      _________ __                 __                
 *     /   _____//  |______ ________/  |_ __ ________  
 *     \_____  \\   __\__  \\_  __ \   __\  |  \____ \ 
 *     /        \|  |  / __ \|  | \/|  | |  |  /  |_> >
 *    /_______  /|__| (____  /__|   |__| |____/|   __/ 
 *            \/           \/                  |__|    
 */

void startup_sequence()
{
  // Ensure blackout pixels
  FastLED.clear(true);
  brightness.currVal = 0;
  resetFade(brightness);
  FastLED.setBrightness(0);
  FastLED.show();

  // Write default colour to pixels
  fill_solid(led_pixels, NUM_LEDS, initHSV);

  int counter = 0;
  // Quickly fade in
  while (counter < 255)
  {
    counter += 3;
    if (counter > 255) counter = 255;
    FastLED.setBrightness(counter);
    FastLED.show();
  }
  // Quickerly fade out
  while (counter > 0)
  {
    counter -= 4;
    if (counter < 0) counter = 0;
    FastLED.setBrightness(counter);
    FastLED.show();
  }
}


/***
 *     ____ ___   __  .__.__  .__  __  .__               
 *    |    |   \_/  |_|__|  | |__|/  |_|__| ____   ______
 *    |    |   /\   __\  |  | |  \   __\  |/ __ \ /  ___/
 *    |    |  /  |  | |  |  |_|  ||  | |  \  ___/ \___ \ 
 *    |______/   |__| |__|____/__||__| |__|\___  >____  >
 *                                             \/     \/ 
 */

float smooth(AVERAGE &avgStruct, long newValue)
{
  // https://www.aranacorp.com/en/implementation-of-the-moving-average-in-arduino/
  avgStruct.total = avgStruct.total - avgStruct.readings[avgStruct.readIndex];
  avgStruct.readings[avgStruct.readIndex] = newValue;
  avgStruct.total = avgStruct.total + avgStruct.readings[avgStruct.readIndex];

  avgStruct.readIndex = avgStruct.readIndex + 1;
  if (avgStruct.readIndex >= loopNumReadings)
  {
    avgStruct.readIndex = 0;
  }
  avgStruct.average = (float)avgStruct.total / (float)loopNumReadings;
  return avgStruct.average;
}

uint8_t lerp(uint8_t a, uint8_t b, uint8_t x)
{ 
  return a + (long)x / 255 * (b - a);
}


// Provides remapped pixel assignment. Index should be within 1/2 of total LED count
void endToEnd(struct CRGB * targetArray, int index, CRGB colour)
{
  unsigned int SA = loopValue(0, NUM_LEDS, QRT_LEDS + index);
  unsigned int SB = loopValue(0, NUM_LEDS, QRT_LEDS - 1 - index);

  targetArray[SA] = colour;   // Side A
  targetArray[SB] = colour;   // Side B
}


// Provides remapped pixel assignment. Index should be within 1/4 of total LED count
//void mirrorPixel(CRGB (& in_leds)[NUM_LEDS], CRGB colour, unsigned int i)
void mirrorPixel(struct CRGB * targetArray, int index, CRGB colour)
{
  unsigned int UA = loopValue(0, NUM_LEDS, index);
  unsigned int UB = loopValue(0, NUM_LEDS, HALF_LEDS - 1 - index);
  unsigned int DA = loopValue(0, NUM_LEDS, NUM_LEDS - 1 - index);
  unsigned int DB = loopValue(0, NUM_LEDS, HALF_LEDS + index);

  targetArray[UA] += colour;   // Up, Side A
  targetArray[UB] += colour;   // Up, Side B
  targetArray[DA] += colour;   // Down, Side A
  targetArray[DB] += colour;   // Down, Side B
}


/***
 *    ________  .__       .___   _________ __          _____  _____ 
 *    \_____  \ |  |    __| _/  /   _____//  |_ __ ___/ ____\/ ____\
 *     /   |   \|  |   / __ |   \_____  \\   __\  |  \   __\\   __\ 
 *    /    |    \  |__/ /_/ |   /        \|  | |  |  /|  |   |  |   
 *    \_______  /____/\____ |  /_______  /|__| |____/ |__|   |__|   
 *            \/           \/          \/                           
 */

  // FastLED.clear(true);
  // led_pixels[0] = CRGB::White;
  // led_pixels[QRT_LEDS - 1] = CRGB::White;
  // led_pixels[QRT_LEDS] = CRGB::White;
  // led_pixels[HALF_LEDS - 1] = CRGB::White;
  // led_pixels[NUM_LEDS - 1] = CRGB::White;
  // led_pixels[HALF_LEDS + QRT_LEDS - 1] = CRGB::White;
  // led_pixels[HALF_LEDS + QRT_LEDS] = CRGB::White;

  // FastLED.show();
  // delay(100000);

  // for (int j = 0; j < 100; j++)
  // {
  //   // Demo for mirror
  //   for (unsigned int i = 0; i < QRT_LEDS; i++)
  //   {
  //     mirrorPixel(led_pixels, initHSV, i);
  //     FastLED.show();
  //     mirrorPixel(led_pixels, CRGB::Black, i - 1);
  //     delay(10);
  //   }
  // }

  // // Demo for end to end
  // for (unsigned int i = 0; i < HALF_LEDS; i++)
  // {
  //   endToEnd(led_pixels, initHSV, i);
  //   for (unsigned int j = 0; j < NUM_LEDS; j++)
  //   {
  //     led_pixels[j].nscale8_video(253);
  //   }
  //   FastLED.show();
  //   delay(1);
  // }

  // for (unsigned int i = 0; i < )

  // // // Shiny demo bit
  // CRGB whiteTarget = CRGB::White;
  // for (unsigned int i = 0; i < NUM_LEDS; i++)
  // {
  //   CRGB currentA = led_pixels[i];
  //   CRGB currentB = led_pixels[NUM_LEDS - i - 1];
  //   whiteTarget.nscale8(253);
  //   led_pixels[i] = CRGB::White;
  //   led_pixels[NUM_LEDS - i - 1] = CRGB::White;
  //   FastLED.show();
  //   led_pixels[i] = blend(currentA, initHSV, 1);
  //   led_pixels[NUM_LEDS - i - 1] = blend(currentB, initHSV, 1);
  //   for (unsigned int j = 0; j < NUM_LEDS; j++)
  //   {
  //     led_pixels[j].nscale8(253);
  //   }
  // }




// NOTE: This may not be feasible with the varied physical alignment of LED strips across each Signifiers
// // Provides remapped pixel assignment. Index should be within 1/4 of total LED count
// void mirrorPixel(CRGB (& in_leds)[NUM_LEDS], CRGB colour, unsigned int i)
// {
//   unsigned int UA = loopValue(0, NUM_LEDS, i);
//   unsigned int UB = loopValue(0, NUM_LEDS, HALF_LEDS - 1 - i);
//   unsigned int DA = loopValue(0, NUM_LEDS, NUM_LEDS - 1 - i);
//   unsigned int DB = loopValue(0, NUM_LEDS, HALF_LEDS + i);

//   in_leds[UA] = colour;   // Up, Side A
// //  in_leds[UB] = colour;   // Up, Side B
// //  in_leds[DA] = colour;   // Down, Side A
// //  in_leds[DB] = colour;   // Down, Side B
// }  

// // Provides remapped pixel assignment. Index should be within 1/2 of total LED count
// void endToEnd(CRGB (& in_leds)[NUM_LEDS], CRGB colour, unsigned int i)
// {
//   unsigned int SA = loopValue(0, NUM_LEDS, QRT_LEDS + i);
//   unsigned int SB = loopValue(0, NUM_LEDS, QRT_LEDS - 1 - i);

//   in_leds[SA] = colour;   // Side A
//   in_leds[SB] = colour;   // Side B
// }
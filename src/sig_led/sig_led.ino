
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

const byte INIT_MAIN_BRIGHT = 255;

const byte INIT_SOLID_BRIGHT = 0;
const byte INIT_SOLID_SAT = 255;
const byte INIT_SOLID_HUE = 195;

const byte INIT_NOISE_SPD = 200;
const byte INIT_NOISE_AMT = 0;
const byte INIT_NOISE_THRESH = 120;
const byte INIT_NOISE_WIDTH = 120;
const byte INIT_NOISE_SAT = 0;
const byte INIT_NOISE_HUE = 0;

const byte INIT_MIRROR_BAR = 0;
const byte INIT_MIRROR_MIX = 125;
const byte INIT_MIRROR_SAT = 0;
const byte INIT_MIRROR_HUE = 0;

LED_PROPERTY mainBright = {INIT_MAIN_BRIGHT, INIT_MAIN_BRIGHT, INIT_MAIN_BRIGHT, 0UL, 0UL};
LED_PROPERTY solidBright = {INIT_SOLID_BRIGHT, INIT_SOLID_BRIGHT, INIT_SOLID_BRIGHT, 0UL, 0UL};
LED_PROPERTY solidSat = {INIT_SOLID_SAT, INIT_SOLID_SAT, INIT_SOLID_SAT, 0UL, 0UL};
LED_PROPERTY solidHue = {INIT_SOLID_HUE, INIT_SOLID_HUE, INIT_SOLID_HUE, 0UL, 0UL};
LED_PROPERTY noiseAmt = {INIT_NOISE_AMT, INIT_NOISE_AMT, INIT_NOISE_AMT, 0UL, 0UL};
LED_PROPERTY noiseThresh = {INIT_NOISE_THRESH, INIT_NOISE_THRESH, INIT_NOISE_THRESH, 0UL, 0UL};
LED_PROPERTY noiseWidth = {INIT_NOISE_WIDTH, INIT_NOISE_WIDTH, INIT_NOISE_WIDTH, 0UL, 0UL};
LED_PROPERTY noiseSpeed = {INIT_NOISE_SPD, INIT_NOISE_SPD, INIT_NOISE_SPD, 0UL, 0UL};
LED_PROPERTY noiseSat = {INIT_NOISE_SAT, INIT_NOISE_SAT, INIT_NOISE_SAT, 0UL, 0UL};
LED_PROPERTY noiseHue = {INIT_NOISE_HUE, INIT_NOISE_HUE, INIT_NOISE_HUE, 0UL, 0UL};
LED_PROPERTY mirrorBar = {INIT_MIRROR_BAR, INIT_MIRROR_BAR, INIT_MIRROR_BAR, 0UL, 0UL};
LED_PROPERTY mirrorMix = {INIT_MIRROR_MIX, INIT_MIRROR_MIX, INIT_MIRROR_MIX, 0UL, 0UL};
LED_PROPERTY mirrorSat = {INIT_MIRROR_SAT, INIT_MIRROR_SAT, INIT_MIRROR_SAT, 0UL, 0UL};
LED_PROPERTY mirrorHue = {INIT_MIRROR_HUE, INIT_MIRROR_HUE, INIT_MIRROR_HUE, 0UL, 0UL};

CHSV initHSV = CHSV(INIT_SOLID_HUE, INIT_SOLID_SAT, INIT_SOLID_BRIGHT);

CRGB ledPixels[NUM_LEDS];

uint8_t noisePixels[NUM_LEDS];
unsigned long noiseTime = 0;

uint8_t mirrorBarPixels[QRT_LEDS];

CRGB noiseLeds[NUM_LEDS];
CRGB mirrorLeds[QRT_LEDS];



unsigned long TARGET_LOOP_DUR = 30;
unsigned long ms = 0;
unsigned long loopStartTime = 0;
unsigned long serialStartTime = 0;
unsigned long loopEndTime = 0;
unsigned long prevLoopTime = 0;
bool disconnected = false;

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
    noisePixels[i] = 0;
  }

  FastLED.addLeds<NEOPIXEL, DATA_PIN>(ledPixels, NUM_LEDS);
  startup_sequence();
  FastLED.setBrightness(0);

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
  fadeToTarget(mainBright);
  fadeToTarget(solidBright);
  fadeToTarget(solidSat);
  fadeToTarget(solidHue);
  fadeToTarget(noiseAmt);
  fadeToTarget(noiseThresh);
  fadeToTarget(noiseWidth);
  fadeToTarget(noiseSpeed);
  fadeToTarget(noiseSat);
  fadeToTarget(noiseHue);
  fadeToTarget(mirrorBar);
  fadeToTarget(mirrorMix);
  fadeToTarget(mirrorSat);
  fadeToTarget(mirrorHue);
  
  CHSV solidColour = CHSV(solidHue.currVal, solidSat.currVal, solidBright.currVal);
  // Write to pixel arrays
  fill_solid(ledPixels, NUM_LEDS, solidColour);
  //add_mirror_bar(ledPixels, NUM_LEDS);
  add_noise(ledPixels, NUM_LEDS);

  // Push pixel arrays to LEDs
  FastLED.setBrightness(mainBright.currVal);
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
  sendCommand(input);
  if (disconnected == true && mainBright.currVal == 0) {
    mainBright.currVal = INIT_MAIN_BRIGHT;
    resetFade(mainBright);
  }
  switch (input.command)
  {
  case 'l': // Updates the Arduino's target loop duration
    TARGET_LOOP_DUR = input.value;
    //sendCommand(COMMAND{'l', TARGET_LOOP_DUR, 0});
  case 'B': // Sets the solid fill colour's brightness
    assignInput(input, solidBright);
    break;
  case 'S': // Set solid fill colour saturation
    assignInput(input, solidSat);
    break;
  case 'H': // Set solid fill colour hue
    assignInput(input, solidHue);
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
  case 'R': // Set threshold of noise effect
    assignInput(input, noiseThresh);
    break;
  case 'W': // Set width of noise effect
    assignInput(input, noiseWidth);
    break;
  case 'M': // Set size of mirror bar layer
    assignInput(input, mirrorBar);
    break;
  case 'J': // Set mix level of mirror bar layer
    assignInput(input, mirrorMix);
    break;
  case 'K': // Set saturation of mirror bar layer
    assignInput(input, mirrorSat);
    break;
  case 'L': // Set hue of mirror bar layer
    assignInput(input, mirrorHue);
    break;
  case 'Z': // Main LED strip brightness amount
    assignInput(input, mainBright);
    if (input.value == 0) {
      disconnected = true;
    }
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


// Applies the mirror bar effect pattern over the solid colour
void add_mirror_bar(struct CRGB * targetArray, int numToFill)
{
  // Fade out existing mirror array pixel amount
  fadeToBlackBy(mirrorLeds, QRT_LEDS, 200);
  blur1d(mirrorLeds, QRT_LEDS, 180);
  for (unsigned int i = 0; i < QRT_LEDS; i++) {
    // Calculate the 4 strip pixel positions for this mirror pixel
    unsigned int mirrorPos[4] = {
      loopValue(0, NUM_LEDS, i),
      loopValue(0, NUM_LEDS, HALF_LEDS - 1 - i),
      loopValue(0, NUM_LEDS, NUM_LEDS - 1 - i),
      loopValue(0, NUM_LEDS, HALF_LEDS + i)
    };
    // Add new pixel to mirror array if within value threshold
    if ( i * 4 < mirrorBar.currVal ) {
      mirrorLeds[i] = CRGB(CHSV(mirrorHue.currVal, mirrorSat.currVal, 255));
    }
    // Add mirror pixel to all 4 sections
    for (uint8_t j = 0; j < 4; j++) {
      nblend(targetArray[mirrorPos[j]], mirrorLeds[i], mirrorMix.currVal);
    }
  }
}


// // Generates simplex noise pattern over LED strip and adds the effect to the solid colour
// void add_noise(struct CRGB * targetArray, int numToFill)
// {
//   // Prepare new noise pixel colour
//   //CRGB new_pixel;
//   //hsv2rgb_rainbow(CHSV(noiseHue.currVal, noiseSat.currVal, 255), new_pixel);
//   // Update the offset of the noise function based on speed parameter and loop time.
//   noiseTime += prevLoopTime * noiseSpeed.currVal / 10;
//   long width = map(noiseAmt.currVal, 0, 128, 10, 80);
//   long thresh = map(noiseAmt.currVal, 0, 255, 230, 190);
//   long amount = map(noiseAmt.currVal, 0, 255, 0, 160);

//   for (unsigned int i = 0; i < NUM_LEDS; i++)
//   {
//     // Blend existing noise pixel towards current LED strip array pixel
//     nblend(noisePixels[i], targetArray[i], 120);
//     // Add new noise pixel to noise array
//     uint8_t noiseBrightness = inoise8(i * width, 0, noiseTime) > thresh ? noiseSpeed.currVal : 0;
//     noisePixels[i] += CRGB(CHSV(noiseHue.currVal, noiseSat.currVal, noiseBright));
//     // Blend noise pixel into LED strip array
//     nblend(targetArray[i], noisePixels[i], noiseAmt.currVal);
    
//     //noisePixels[i] = blend8(noisePixels[i], noiseBrightness, noiseSpeed.currVal);
//     //CRGB new_noise;
//     //hsv2rgb_rainbow(CHSV(noiseHue.currVal, noiseSat.currVal, noisePixels[i]), new_noise);
//     //targetArray[i] += new_noise;
//   }
// }

// Generates perlin noise pattern over LED strip and adds the effect to the solid colour
void add_noise(struct CRGB * targetArray, int numToFill)
{
  long width = map(noiseAmt.currVal, 0, 255, 50, 1);
  long thresh = map(noiseThresh.currVal, 0, 255, 140, 230);
  long amount = map(noiseAmt.currVal, 0, 255, 40, 255);

  // Update the offset of the noise function based on speed parameter and loop time.
  noiseTime += prevLoopTime * noiseSpeed.currVal / 30;

  for (unsigned int i = 0; i < NUM_LEDS; i++) {
    // Fade out existing noise array pixel amount
    noisePixels[i] = scale8(noisePixels[i], 124);
    // Calculate noise pixel
    uint8_t newNoisePixel = inoise8(i * width, noiseTime) > thresh ? noiseAmt.currVal : 0;

    // Add new pixel amount to noise array if within current effect value
    // newNoisePixel = map8(
    //   newNoisePixel,
    //   124 - noiseAmt.currVal / 4,
    //   124 + noiseAmt.currVal / 4,
    //   0, 255);

//    if ( newNoisePixel > thresh ) {
    //newNoisePixel = map(newNoisePixel, 0, noiseAmt.currVal, 0, 255);

    // Add noise pixel to noise array
    if (noisePixels[i] + newNoisePixel > 255) {
      noisePixels[i] = newNoisePixel;
    }
    else {
      noisePixels[i] += newNoisePixel;
    }
    // Add noise pixel to LED strip
    targetArray[i] += CRGB(CHSV(
      noiseHue.currVal,
      noiseSat.currVal,
      noisePixels[i]));
//      .fadeToBlackBy(255 - noiseAmt.currVal);
  }
}


//   // Only process the effect's values if it's amount is above 0.
//   // Otherwise we assume the effect layer is off and skip it.
//   if (noiseAmt.currVal > 0)
//   {

//     long width = map(noiseAmt.currVal, 0, 255, 2, 60);
//     long thresh = map(noiseAmt.currVal, 0, 255, 215, 185);
//     long amount = map(noiseAmt.currVal, 0, 255, 40, 255);

//     for (unsigned int i = 0; i < NUM_LEDS; i++)
//     {
//       uint8_t noiseBrightness = inoise8(i * width, noiseTime) > thresh ? amount : 0;
//       noisePixels[i] = blend8(noisePixels[i], noiseBrightness, noiseSpeed.currVal);
//       CRGB new_noise = CRGB(CHSV(noiseHue.currVal, noiseSat.currVal, noisePixels[i]));
//       targetArray[i] += new_noise;
//     }
//   }
// }


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
void mirrorPixel(struct CRGB * targetArray, int index, CRGB colour, uint8_t bright)
{
  unsigned int UA = loopValue(0, NUM_LEDS, index);
  unsigned int UB = loopValue(0, NUM_LEDS, HALF_LEDS - 1 - index);
  unsigned int DA = loopValue(0, NUM_LEDS, NUM_LEDS - 1 - index);
  unsigned int DB = loopValue(0, NUM_LEDS, HALF_LEDS + index);

  // targetArray[UA] += colour;   // Up, Side A
  // targetArray[UB] += colour;   // Up, Side B
  // targetArray[DA] += colour;   // Down, Side A
  // targetArray[DB] += colour;   // Down, Side B

  nblend(targetArray[UA], colour, bright);   // Up, Side A
  nblend(targetArray[UB], colour, bright);   // Up, Side B
  nblend(targetArray[DA], colour, bright);   // Down, Side A
  nblend(targetArray[DB], colour, bright);   // Down, Side B
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
  FastLED.setBrightness(0);
  FastLED.show();

  // Write default colour to pixels
  fill_solid(ledPixels, NUM_LEDS, initHSV);

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
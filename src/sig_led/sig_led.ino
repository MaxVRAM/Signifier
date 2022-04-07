
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

const byte NOISE_SPEED = 200;
const byte NOISE_AMT = 0;

LED_PROPERTY brightness = {INIT_BRIGHTNESS, INIT_BRIGHTNESS, INIT_BRIGHTNESS, 0UL, 0UL};
LED_PROPERTY saturation = {INIT_SATURATION, INIT_SATURATION, INIT_SATURATION, 0UL, 0UL};
LED_PROPERTY hue = {INIT_HUE, INIT_HUE, INIT_HUE, 0UL, 0UL};
LED_PROPERTY noiseAmt = {NOISE_AMT, NOISE_AMT, NOISE_AMT, 0UL, 0UL};
LED_PROPERTY noiseSpeed = {NOISE_SPEED, NOISE_SPEED, NOISE_SPEED, 0UL, 0UL};

CHSV initHSV = CHSV(INIT_HUE, INIT_SATURATION, INIT_BRIGHTNESS);
CHSV solidHSV = initHSV;

CRGB led_pixels[NUM_LEDS];
CRGB temp_pixels[NUM_LEDS];
CRGB solid_pixels[NUM_LEDS];
CRGB noise_pixels[NUM_LEDS];
unsigned long noiseTime = 0;


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
  fadeToTarget(noiseAmt);
  fadeToTarget(noiseSpeed);
  fadeToTarget(brightness);
  fadeToTarget(saturation);
  fadeToTarget(hue);
  solidHSV = CHSV(hue.currVal, saturation.currVal, brightness.currVal);
  
  // Write to pixel arrays
  fill_solid(solid_pixels, NUM_LEDS, solidHSV);
  update_noise();

  if (noiseAmt.currVal > 0)
    for (unsigned int i = 0; i < NUM_LEDS; i++)
    {
      led_pixels[i] = solid_pixels[i] + noise_pixels[i];
    }
  else
    for (unsigned int i = 0; i < NUM_LEDS; i++)
    {
      led_pixels[i] = solid_pixels[i];
    }


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
  case 'l':
    TARGET_LOOP_DUR = input.value;
    sendCommand(COMMAND{'l', TARGET_LOOP_DUR, 0});
  case 'B':
    assignInput(input, brightness);
    break;
  case 'S':
    assignInput(input, saturation);
    break;
  case 'H':
    assignInput(input, hue);
    break;
  case 'N':
    assignInput(input, noiseAmt);
    break;
  case 'O':
    assignInput(input, noiseSpeed);
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


void update_noise()
{
  // Update the offset of the noise function based on speed parameter and loop time.
  noiseTime += prevLoopTime * noiseSpeed.currVal / 10;
  CRGB old_noise[NUM_LEDS];
  CRGB temp_noise[NUM_LEDS];

  // Only process noise pixels if the noise master value is above 0. Otherwise we
  // assume the noise layer is off and skip it.
  if (noiseAmt.currVal > 0)
  {
    long width = map(noiseAmt.currVal, 0, 255, 2, 60);
    long thresh = map(noiseAmt.currVal, 0, 255, 215, 185);

    for (unsigned int i = 0; i < NUM_LEDS; i++)
    {
      old_noise[i] = noise_pixels[i];
      uint8_t noiseBrightness = inoise8(i * width, noiseTime) > thresh ? 255 : 0;
      temp_noise[i] = CRGB(noiseBrightness, noiseBrightness, noiseBrightness);
      noise_pixels[i] = blend(old_noise[i], temp_noise[i], noiseSpeed.currVal);
    }
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
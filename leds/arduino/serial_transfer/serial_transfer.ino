// pip install pySerialTransfer

#include "SerialTransfer.h"


SerialTransfer sig_serial;


void setup()
{
  Serial.begin(115200);
  sig_serial.begin(Serial);
}


void loop()
{
  if(sig_serial.available())
  {
    // send all received data back to Python
    for(uint16_t i=0; i < sig_serial.bytesRead; i++)
      sig_serial.packet.txBuff[i] = sig_serial.packet.rxBuff[i];
    
    sig_serial.sendData(sig_serial.bytesRead);
  }
}
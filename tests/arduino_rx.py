from time import sleep
from pySerialTransfer import pySerialTransfer as txfer


class struct(object):
    command = ''
    valA = 0.0
    valB = 0.0


if __name__ == '__main__':
    try:
        testStruct = struct
        link = txfer.SerialTransfer('/dev/ttyACM0', baud=38400)
        
        link.open()
        sleep(5)
    
        while True:
            if link.available():
                recSize = 0
                
                testStruct.command = link.rx_obj(obj_type='c', start_pos=recSize)
                recSize += txfer.STRUCT_FORMAT_LENGTHS['c']
                
                testStruct.valA = link.rx_obj(obj_type='l', start_pos=recSize)
                recSize += txfer.STRUCT_FORMAT_LENGTHS['l']

                testStruct.valB = link.rx_obj(obj_type='l', start_pos=recSize)
                recSize += txfer.STRUCT_FORMAT_LENGTHS['l']
                                
                print(f'{testStruct.command} | {testStruct.valA} {testStruct.valB}')
                
            elif link.status < 0:
                if link.status == txfer.CRC_ERROR:
                    print('ERROR: CRC_ERROR')
                elif link.status == txfer.PAYLOAD_ERROR:
                    print('ERROR: PAYLOAD_ERROR')
                elif link.status == txfer.STOP_BYTE_ERROR:
                    print('ERROR: STOP_BYTE_ERROR')
                else:
                    print('ERROR: {}'.format(link.status))
                
        
    except KeyboardInterrupt:
        link.close()
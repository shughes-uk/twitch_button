#Led Sequences!
#FLASH CIRCLE
CIRCLE_FLASH = [
    [0x12, 0x00, 0x00, 0x00, 0x06, 0x82, 0x00, 0x00],
    [0x12, 0x14, 0x00, 0x00, 0x06, 0x81, 0x00, 0x00],
    [0x12, 0x00, 0x00, 0x00, 0x06, 0x82, 0x00, 0x00],
    [0x22, 0x14, 0x00, 0x00, 0x06, 0x83, 0x00, 0x00],
    [0x22, 0x00, 0x00, 0x00, 0x06, 0x84, 0x00, 0x00],
    [0x42, 0x14, 0x00, 0x00, 0x06, 0x85, 0x00, 0x00],
    [0x42, 0x00, 0x00, 0x00, 0x06, 0x86, 0x00, 0x00], 
    [0x82, 0x14, 0x00, 0x00, 0x06, 0x87, 0x00, 0x00], 
    [0x82, 0x00, 0x00, 0x00, 0x06, 0x88, 0x00, 0x00],
]
#GLOW PULSE
CIRCLE_FLASH = [
    [0xf3, 0x00, 0x14, 0x00, 0x00, 0x41, 0x00, 0x00],
    [0xf3, 0x14, 0x64, 0x00, 0x00, 0x42, 0x00, 0x00],
    [0xf3, 0x64, 0x2d, 0x00, 0x32, 0x43, 0x00, 0x00],
    [0xf3, 0x2d, 0x14, 0x00, 0x32, 0x44, 0x00, 0x00],
]
#SOLID ON
#the first four bits of the first byte corespond to the LEDs/LED you want to turn on/off!
ALL_ ON = [[0b11110001, 0x23, 0x00, 0x00, 0x00, 0x11, 0x00, 0x00]]
#TURNS OFF
ALL_OFF = [[0b11110001, 0x00, 0x00, 0x00, 0x00, 0x11, 0x00, 0x00]]



from time import sleep
from msvcrt import kbhit

import pywinusb.hid as hid

def sample_handler(data):
    print data

def feature_test(target_usage):
    # simple test
    # browse devices...
    all_hids = hid.find_all_hid_devices()
    if all_hids:
        for device in all_hids:
            if device.vendor_id == 1994:
                try:
                    device.open()
                    # browse feature reports
                    for report in device.find_output_reports():
                        target_usage = hid.get_full_usage_id(0xffa0, 0x02)
                        if target_usage in report:
                            report[target_usage] = [0b11110001, 0b00100011, 0b0000000, 0b00000000, 0b00000000, 0b00010001, 0b00000000, 0b00000000]
                            report.send()

                            
                finally:
                    device.close()
def raw_test():
    # simple test
    # browse devices...
    all_hids = hid.find_all_hid_devices()
    if all_hids:
        while True:
            for device in all_hids:
                if device.vendor_id == 1994:
                    try:
                        device.open()

                        #set custom raw data handler
                        device.set_raw_data_handler(sample_handler)

                        print("\nWaiting for data...\nPress any (system keyboard) key to stop...")
                        while not kbhit() and device.is_plugged():
                            #just keep the device opened to receive events
                            sleep(0.5)
                        return
                    finally:
                        device.close()
    else:
        print("There's not any non system HID class device available")
#
if __name__ == '__main__':
    # first be kind with local encodings
    import sys
    if sys.version_info >= (3,):
        # as is, don't handle unicodes
        unicode = str
        raw_input = input
    else:
        # allow to show encoded strings
        import codecs
        sys.stdout = codecs.getwriter('mbcs')(sys.stdout)
    #raw_test()
     # generic vendor page, usage_id = 2
    # go for it!
    feature_test(target_usage)

from noolite import NooliteProtocolHandler

class NooliteTxDevice(object):
    def __init__(self, addr, radio_send):
        self.addr = addr
        self.addr_hex = hex(self.addr)
        #~ self.mqtt_client = mqtt_client

        self.radio_send = radio_send

        self.device_id = "noolite_tx_" + self.addr_hex

        self.device_name = "Noolite TX " + self.addr_hex
        self.device_room = 'Noolite'

        self.controls_desc = {
                'level'  :  { 'value' : 0,
                              'meta' :  { 'type' : 'range',
                                          'order' : '1',
                                        }
                            },
                'on'    : { 'value' : 0,
                            'meta': {  'type' : 'pushbutton',
                                       'order' : '2',
                                },
                          },
                'off'   : { 'value' : 0,
                            'meta': {  'type' : 'pushbutton' ,
                                       'order' : '3',
                                    },
                          },
                'switch'  : { 'value' : 0,
                            'meta': {  'type' : 'pushbutton' ,
                                       'order' : '4',
                                    },
                          },
                'bind'  : { 'value' : 0,
                            'meta': {  'type' : 'pushbutton',
                                       'order' : '5',
                                    },
                          },
                'unbind'  : { 'value' : 0,
                            'meta': {  'type' : 'pushbutton',
                                       'order' : '6',
                                    },
                          },
              }

        self.protocol_handler = NooliteProtocolHandler()
        self.flip = 0

    def get_controls(self):
        return self.controls_desc


    def update_control(self, control, value):
        self.flip = 0 if self.flip else 1


        var = {  'addr'  : self.addr_hex,
                 'flip'  : self.flip,
              }

        var['arg'] = '0'

        if control == 'bind':
            var['cmd'] = 15
        elif control == 'unbind':
            var['cmd'] = 9
        elif control == 'on':
            var['cmd'] = 2
        elif control == 'off':
            var['cmd'] = 0
        elif control == 'switch':
            var['cmd'] = 4
        elif control == 'level':
            var['cmd'] = 6
            val_int = int(value)
            if val_int > 255: val_int = 255
            if val_int < 0: val_int = 0

            var['arg'] = str(val_int)
        else:
            print "unknown control "
            return


        data = self.protocol_handler.tryEncode(var)
        self.radio_send(data)

        return None






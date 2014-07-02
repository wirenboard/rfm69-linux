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
                'state'    : { 'value' : 0,
                            'meta': {  'type' : 'switch',
                                       'order' : '2',
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
                                       'export' : '0',
                                    },
                          },
                'unbind'  : { 'value' : 0,
                            'meta': {  'type' : 'pushbutton',
                                       'order' : '6',
                                       'export' : '0',
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
        elif control == 'state':
            if int(value):
                var['cmd'] = 2
            else:
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



class OregonRxDevice(object):
    device_room = None
    def __init__(self, dev_type, code, channel, data = {}):
        self.dev_type = dev_type
        self.code = code


        try:
            self.channel = int(channel)
        except:
            self.channel = 0


        self.device_id = "oregon_rx_%s_%s_%s" % (self.dev_type, self.code, self.channel)

        # full list on http://jeelabs.net/projects/cafe/wiki/Decoding_the_Oregon_Scientific_V2_protocol
        #~ if self.dev_type in ('1a2d', 'fa28', 'ca2c', 'fab8', '1a3d',) or self.dev_type.endswith('acc'):
            #~ self.device_type_name = 'Temp-Hygro'
        #~ else:
        self.device_type_name = "[%s]" % self.dev_type

        self.device_name = "Oregon Sensor %s (%s-%d)" % ( self.device_type_name, self.code, self.channel)

        self.controls_desc = {}

        if 'temp' in data:
            self.controls_desc['temperature'] =   { 'value' : 0,
                                                    'meta' :  { 'type' : 'temperature',
                                                              },
                                                  }
        if 'humidity' in data:
            self.controls_desc['humidity'] =     { 'value' : 0,
                                                   'meta' :  { 'type' : 'rel_humidity',
                                                             },
                                                 }


    def get_controls(self):
        return self.controls_desc



    def handle_data(self, data):
        print "\n" * 15
        print "handle data!", data

        var = {}

        var['temperature'] = data['temp']
        var['humidity'] = data['humidity']
        return var


class OregonRxHandler(object):
    name = "oregon"
    def __init__(self):
        self.devices = {}

    def get_device(self, data):
        if ('code' in data) and  ('type' in data):
            channel = data.get('channel')
            key = (data['type'], data['code'], channel)
            if key not in self.devices:
                self.devices[key] = OregonRxDevice(data['type'], data['code'], channel, data)

            return self.devices[key]


rx_handler_classes = (OregonRxHandler, )

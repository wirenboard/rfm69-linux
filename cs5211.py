#coding: utf-8

import utils
import re
import operator


# (c1) http://detail.1688.com/offer/382659770.html
# (c2) http://www.aliexpress.com/item/Free-shipping-433MHz-Wireless-Water-Intrusion-Detector-Work-With-GSM-PSTN-SMS-Home-Security/1743754761.html


tristatecode = {'10001000':'0' , '11101110':'1' , '10001110':'F'}


class Cs5211ProtocolHandler():
    name = "cs5211"
    kw = {}

    def tryDecode(self, data):
        bitstream = utils.get_bits(data)
        packs = []
#        print "raw: ",bitstream
        streams = re.split('1{1}0{27}[0-1]{3}0{1}', bitstream) 

        for ar in streams:
            out = ""
            if len(ar) == 96:
                good_pack = True
                for i in range(12):
                    try:
                        out = out + tristatecode[(ar[i*8:(i+1)*8])]
                    except:
                        good_pack = False
                        break
                if good_pack:
                    packs.append(out)
        if not packs:
            return
        ppp = {}
        for p in packs:
            try:
                ppp[p] = ppp[p] + 1
            except:
                ppp[p] = 1
        if not ppp:
            return

        self.kw['raw'] = max(ppp.iteritems(), key=operator.itemgetter(1))[0]
        self.kw['addr'] = self.kw['raw']
        self.kw['state'] = "on" 
        return self.kw



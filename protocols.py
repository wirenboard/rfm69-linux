import binascii


class BaseRCProtocolHandler(object):
    name = None

class RawProtocolHandler(BaseRCProtocolHandler):
    name = "raw"

    def tryDecode(self, data):
        raw = binascii.hexlify("".join(chr(x) for x in data))
        kw = {'raw': raw}
        return kw


    def tryEncode(self, kw):
        raw = kw['raw']
        data = [ord(ch) for ch in binascii.unhexlify(raw)]
        print data
        return data


import unittest
import binascii

import noolite
import oregon
import utils


to_bytes = lambda s: [ord(x) for x in binascii.unhexlify(s)]


class ProtocolTestCase(unittest.TestCase):
    def setUp(self):
        self.handler = self.HandlerClass()
    def decode(self, raw):
        return self.handler.tryDecode(
            to_bytes(raw)
        )

    def check_decode(self, raw, expected_str):
        ans = self.decode(raw)
        #~ print ans
        self.assertFalse(ans is None)

        expected_vars = dict(kv_str.split('=', 1) for kv_str in expected_str.split())
        for k, v in expected_vars.iteritems():
            self.assertEqual(ans.get(k), v, "expected %s=%s, got %s" %(k, v, ans.get(k)))

class TestNoolite(ProtocolTestCase):
    HandlerClass = noolite.NooliteProtocolHandler



    def test_thermometer(self):
        self.check_decode('aaaaaaaaaaaaaaa86666aa666559a595a55555569a66a56aaa6960cccd54cccab34b2b4aaaaaad34cd4ad554d2c000000000007fffffffffffffffff',
                          'addr=149f    cmd=21  flip=0  fmt=7 temp=-17.2 lowbat=0 humidity=59')

        self.check_decode('aaaaaaaaaaaaaaa85666aa96a6a9a995a55555569a66a56aa66650accd552d4d53532b4aaaaaad34cd4ad54ccca00000000000000000001ffffffff0',
                          'addr=149f    cmd=21  flip=1  fmt=7 temp=28.0 lowbat=0 humidity=58')

        self.check_decode('aaaaaaaaaaaaaaa85666a65969a9aa6aa55555569a66a56aaaa590accd4cb2d35354d54aaaaaad34cd4ad5554b200000000000000001fffffc7fffe0',
                          'addr=149f    temp=62.1   lowbat=0    fmt=7   cmd=21  flip=1  humidity=4')

        self.check_decode('aaaaaaaaaaaaa1599a9a96a6a665aa9555555a699a95aaaaa542b335352d4d4ccb552aaaaab4d3352b55554a8000000000000000000ffff87fffffff',
                          'addr=149f    temp=56.1   lowbat=1    fmt=7   cmd=21  flip=1  humidity=6')




    def test_rgb(self):
        self.check_decode('aaaaaaaaaaaaaaa8596a5aa9a9aa59aaaaa6955669a5aaaaa6a0b2d4b5535354b355554d2aacd34b55554d4000000000000000000000200fffffffff',
                          'addr=25f9 cmd=6 flip=1 fmt=3')
#~
        self.check_decode('34b55532b41a5a96aa6a6a966aaaa9a5559a696aaa65680000000000000000000000000bffffffffffffffffffffffffffffffffffffffffffffffff',
                          'addr=25f9 cmd=6 flip=0 fmt=3')

    def test_sw_mode(self):
        self.check_decode('aaaaaaaaaaaaaaa859a6a5955669aa6aa56950b34d4b2aacd354d54ad2a0000000000000000000001007e3feffc87ffffffffff007c0ffffffffffff',
                          'addr=25fb cmd=18 flip=1 fmt=4')

        self.check_decode('aaaaaaaaaaaaaaa869a6a5955669aa6aaa59a0d34d4b2aacd354d554b340000000000000000000000003c07ffffffffffffffffffffffa3ff80fffff',
                          'addr=25fb cmd=18 flip=0 fmt=4')

    def test_on_ch(self):
        self.check_decode('aaaaaaaaaaaaaaa859aa555669aaaaaa6960b354aaacd3555554d2c0000000000000000000000017fffffffe3fff87f0fffffffffffffffff8ffffff',
                          'fmt=0    cmd=2   flip=1  addr=25fc')

        self.check_decode('aaaaaaaaaaaaaaa869aa555669aaaaaa9560d354aaacd35555552ac0000000000000000000000013fffffffffff3a73ffcffffffffffffffffffff0f',
                          'fmt=0    cmd=2   flip=0  addr=25fc')




    def test_set_level(self):

        self.check_decode('aaaaaaaaaaaaaaa859665696555669a6aaa95990b2ccad2caaacd34d5552b320000000000000000000000001ffffffe7f81ff80fffffc07ffffffc0f',
                          'fmt=1    cmd=6   flip=1  addr=25fd')
        self.check_decode('aaaaaaaaaaaaaaaaa869665696555669a6aaaaa690d2ccad2caaacd34d55554d20000000000000000000000087ffffffffe07fffffffffffffffffff',
                          'fmt=1    cmd=6   flip=0  addr=25fd')


    def test_noise_at_the_end(self):
        self.check_decode('aaaaaaaaaaaaaaa859aa955669aaaaa99550b3552aacd35555532aa0000000000000000000000000fe38ffff8fffffffffffffffffffffffffffffff',
                            'addr=25f8  cmd=2 flip=1 fmt=0')

    def test_shifted_start(self):
            self.check_decode('fffffd5555555555555555550d4d52aacd3555552cac1a9aa5559a6aaaaa5958000000000000000000000001ffffffbffffbf17fffffffffffffffff',
                                'addr=25f8 cmd=4 fmt=0 flip=0')

class TestOregonV2(ProtocolTestCase):
    HandlerClass = oregon.OregonV2ProtocolHandler

    def test_temp_hygro(self):
        #thgn132n
        self.check_decode('666666666666669696699969669699999999699999669699696699966996999999696966999996966666999999669600000003fff0bffffffcffffff',
                          'code=b0  temp=26.3   humidity=35 type=1a2d   channel=4')

    def test_noise_at_the_end(self):
        self.check_decode('666666666666669696699969669699999996996669966699699669696996999999669999699999666666996969996900000000000000003fbfffffdf',
                          'channel=2 code=e7 humidity=43 temp=25.6 type=1a2d')

class TestOregonV3(ProtocolTestCase):
    HandlerClass = oregon.OregonV3ProtocolHandler

    def test_thgr800(self):
		# http://contactless.ru/forums/topic/%D0%BF%D0%BE%D0%B4%D0%B4%D0%B5%D1%80%D0%B6%D0%BA%D0%B0-%D0%B4%D0%B0%D1%82%D1%87%D0%B8%D0%BA%D0%BE%D0%B2-oregon-scientific-v3-0/

		self.check_decode('aaaa66aa56655995a5a66559a9655596a556aa5969980000000000000000000bffffffffffffffffffffffffffffffffffffffffffffffffffffffff',
						  'channel=1 code=b3 humidity=39 temp=27.4 type=fa28')

		self.check_decode('aaa99aa95995665696999659a595565a955a9665995000000000000000000007ffffffffffffffffffffffffffffffffffffffffffffffffffffffff',
						  'channel=1 code=b3 humidity=39 temp=26.9 type=fa28')
		self.check_decode('aaaa66aa56655995a5a655a969655596a556aa59555400000000000000000001ffffffffffffffffffffffffffffffffffffffffffffffffffffffff',
						  'channel=1 code=b3 humidity=39 temp=26.7 type=fa28')

		self.check_decode('aaaa66aa56655995a5a6556969655596a5566a59699400000000000000000001ffffffffffffffffffffffffffffffffffffffffffffffffffffffff',
						  'channel=1 code=b3 humidity=39 temp=26.6 type=fa28')

		self.check_decode('aaa99aa95995665696995565a595565a955969659a900000000000000000000fffffffffffffffffffffffffffffffffffffffffffffffffffffffff',
						  'channel=1 code=b3 humidity=39 temp=26.4 type=fa28')
		self.check_decode('aaaa66aa56655995a5a655a5696555555956a55965a600000000000000000001ffffffffffffffffffffffffffffffffffffffffffffffffffffffff',
						  'channel=1 code=b3 humidity=40 temp=26.3 type=fa28')
		self.check_decode('aaaa66aa56655995a5a655a5696555555956a55965a600000000000000000001ffffffffffffffffffffffffffffffffffffffffffffffffffffffff',
						  'channel=1 code=b3 humidity=40 temp=26.3 type=fa28')


if __name__ == '__main__':
    unittest.main()

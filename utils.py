import re

def batch_gen(data, batch_size):
	for i in range(0, len(data), batch_size):
		yield data[i:i+batch_size]


def get_bits(data):
	return "".join([bin(x)[2:].zfill(8) for x in data])

def get_bytes(bitstream):
	data = []
	for chunk in batch_gen(bitstream, 8):
		data.append( int(chunk, 2))
	return data


def invert(s):
    return "".join('1' if x=='0' else '0' for x in s)


def manchester_decode_ext(pulseStream):
    i = 1
    #while pulseStream[i] != pulseStream[i-1]:
    #    i = i + 1
    #    print str(i) + " => " + str(pulseStream[i])

    bits = []
    slips = []

    # here pulseStream[i] is "guaranteed" to be the beginning of a bit
    while i < len(pulseStream):
        if pulseStream[i] == pulseStream[i-1]:
            # if so, sync has slipped
            # try to resync
            slips.append(i)
            #~ print "<slip: " + str(i) + ">"
            i = i - 1
        bits.append(pulseStream[i])
        i = i + 2

    return slips, "".join(bits)

import sys
def manchester_decode(pulseStream):
	slips, data = manchester_decode_ext(pulseStream)
	if slips:
		pass
		#~ print >>sys.stderr, ">>slips: ", ",".join(str(x) for x in slips)
	return data



def manchester_encode(bitstream, inverted=False):
	res = []
	for ch in bitstream:
		if (ch == '1')  == inverted:
			res.append('10')
		else:
			res.append('01')
	return "".join(res)



def find_longest_match(pattern, s):
	matches = list(re.finditer(pattern, s))
	if matches:
		match = max(matches, key=lambda m: (m.end() - m.start()))
		return match
	else:
		return None


def strip_tail(bitstream, zero_bits=10, one_bits=10, ignore_bits=0):
	match = find_longest_match('0+.{0,%d}1+' % ignore_bits , bitstream)
	if match:
		return bitstream[:match.start()]
	return bitstream

def strip_preamble(bitstream, ignore_bits=5):
	match = re.match('^.{0,%d}((?:10)+)|((?:01)+)' % ignore_bits, bitstream)
	if match:
		return bitstream[match.end():]

	return bitstream



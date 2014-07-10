import re

def batch_gen(data, batch_size, align_right = False):
	if align_right:
		if len(data) <= batch_size:
			yield data
		else:
			seq = list(reversed(range(len(data) - batch_size ,0, -batch_size)))

			yield data[:seq[0]]
			for i in seq:
				yield data[i:i+batch_size]

	else:
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



def find_longest_match(pattern, s, align_left=False):
	""" return longest match, aligned right by default"""
	def _max_key(m):
		length = m.end() - m.start()

		if align_left:
			align_key = -m.start()
		else:
			align_key = m.start()

		return (length, align_key)

	matches = list(re.finditer(pattern, s))
	if matches:
		match = max(matches, key=_max_key)
		return match
	else:
		return None


def strip_tail(bitstream, zero_bits=10, one_bits=10, ignore_bits=0):
	#~ print "strip_tail", bitstream
	match = find_longest_match('0{%d,}.{0,%d}1{%d,}' % (zero_bits, ignore_bits, one_bits) , bitstream)
	if match:
		return bitstream[:match.start()]
	return bitstream

def strip_to_pause(bitstream, zero_bits=20):
	""" Strip to first sequence of N zeroes"""
	index = bitstream.find('0' * zero_bits)
	if index > -1:
		return bitstream[:index]
	else:
		return bitstream


def strip_preamble(bitstream, ignore_bits=5, min_length =1):
	""" min_length - preamble length in 01 transitions"""

	#~ print "strip_preamble:", bitstream
	#~ match = find_longest_match('^.{0,%d}((?:10){%d,})|((?:01){%d,})' % (ignore_bits, min_length, min_length), bitstream)
	match = re.match('^.{0,%d}((?:10){%d,})|((?:01){%d,})' % (ignore_bits, min_length, min_length), bitstream)
	if match:
		#~ print "stripped: ", bitstream[:match.end()]
		return bitstream[match.end():]

	return bitstream



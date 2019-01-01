#!/usr/bin/env python
"""
Requirements:
  - libsigrok (includes Python bindings)

Installation of library:
    $ sudo apt-get install git-core gcc g++ make autoconf autoconf-archive automake libtool pkg-config libglib2.0-dev libglibmm-2.4-dev libzip-dev libusb-1.0-0-dev libftdi1-dev check doxygen python-numpy   python-dev python-gi-dev python-setuptools swig default-jdk
    $ git clone git://sigrok.org/libsigrok
    $ cd libsigrok
    $ ./autogen.sh
    $ ./configure
    $ make
    $ sudo make install
    $ sudo ldconfig
"""

import sigrok.core as sr
import collections
import itertools

"""
Find matches for RC commands

Format:
  - 50 edge transitions repeated altogther ~8 times
  - timing between them is either:
      - ~ 900 us (denoted as '1')
      - ~ 230 us (denoted as '0')
  - last one is ~ 8700 us or more (denoted as 'e')

Example:
    920 200 890 240 340 790 900 230 320 790 910 230 320 800 910 220 880 260 870 250
    320 800 870 270 320 810 880 230 360 790 310 800 300 840 310 810 310 820 320 810
    900 210 880 250 340 800 300 840 290 8710
"""
# circular buffer of 50 samples
last_samples = collections.deque(maxlen=50)

# circular buffer of last 3 matches
last_matches = collections.deque(maxlen=3)


def items_equal(l):
    """Check if all items in list are equal."""
    for x,y in itertools.combinations(l, 2):
        if x != y:
            return False

    return True


def find_matches(time_diff):
    last_samples.append(time_diff)

    if time_diff > 7000:
        out = []
        while True:
            try:
                i = last_samples.popleft()

                if i > 8000:
                    out.append('e')
                elif i > 500:
                    out.append('1')
                else:
                    out.append('0')
            except IndexError:
                break

        last_matches.append(''.join(out))

        if len(last_matches) == 3 and items_equal(last_matches):
            print(''.join(out))


"""
Callback for each data chunk
"""
cur = 0         # position of current sample
prev = 0        # state of previous sample with change
prev_pos = 0    # position of previous sample with change

def _datafeed_callback(device, packet):
    global cur, prev, prev_pos

    # we only care about data packages for logic analyzers
    if packet.type != sr.PacketType.LOGIC:
        return

    # packet.payload.data =
    #   - samples in ~10 ms (depens on how much we get in 512 * n chunks)
    #   - type: uint8[] - each sample contains state of all 8 channels

    if packet.payload.data_length() != 1024:
        raise Exception('wrong length: %d' % packet.payload.data_length())

    for i in packet.payload.data:
        # we only want channel #3
        state = i >> 3 & 0b1

        # state was changed
        if state != prev:
            time_diff = (cur-prev_pos) * 10 # 100kHz, one sample each 10 us

            find_matches(time_diff)
            # print(state[0], time_diff)

            prev = state
            prev_pos = cur

        cur = cur + 1


if __name__ == '__main__':
    context = sr.Context_create()

    # hardcoded driver for saleae 8 channel logic analyzer
    driver = context.drivers['fx2lafw']
    devs = driver.scan()
    if not devs:
        raise Exception('No devices found.')

    device = devs[0]

    # set sample rate
    ck = sr.ConfigKey.get_by_identifier('samplerate')
    val = ck.parse_string('100kHz')

    device.open()
    device.config_set(ck, val)

    def _stopped_callback(**kwargs):
        print("stopped")

    # create session
    session = context.create_session()
    session.add_datafeed_callback(_datafeed_callback)
    session.set_stopped_callback(_stopped_callback)

    session.add_device(device)
    session.start()

    # wait until session is running
    session.run()

    session.stop()

# RC switch
How to remotely control 433MHz RC sockets or (more appropriate) how to spend TOO much time debugging random issues.

# Issue
* Want to turn on/off christmas lights on schedule?
* Dont want to spend 10 EUR per Sonoff WiFi smart plug (or at least waiting few weeks for them)?
* Have unused cheap 433 MHz RC sockets?

# Approach #1
There seems to be an open source project [pilight](https://www.pilight.org/) for controlling 433 MHz devices, with support for many many devices.

However, it doesn't have any support (that I could find) for really cheap RC socket sets (maybe because there are too many of them, and they are more or less incompatible between each other?)

Thankfully it has `pilight-raw` and `pilight-debug` commands which can help you find out what coding patterns are sent by a remote control.

You can then sent received codes back by `pilight-send -p raw -c '<code here'>`, to check if everything works.

The only issue is if code sequences you observed via `pilight-debug` multiple times, don't really work (they might work sporadically) when sending them back.

You might want to blame the hardware and/or software, but when testing multiple combinations, you find out that it doesn't really matter much, and there is no combination that works 100% of the time (same configuration (mostly) worked one day, and stopped working the other, go figure).

Even when running `pilight-debug`, and sending the codes via remote control and via `pilight-send` (on a different computer), it shows that they are the same, but RC socket only switches when sending it via remote control.

Tested configurations:
* Receiver via Arduino Nano connected via USB (on computer and on RPi).
* Transmitter via Arduino Nano connected via USB (on computer and on RPi).
* Transmitter via RPi GPIO.
* Using receiver/transmitter with and without the antenna (17 cm long straight wire, nothing fancy).

Arduino Nano filters received signals so that we don't wake up RPi SoC all the time (looking at transmitter's output via logic analyzer it seems that there is a lot of traffic and noise on 433 MHz, and we might want to also use RPi for some other tasks except decoding this), and when using `pilight` on laptop we don't have GPIO anyways.

I've also noticed a few issues with `pilight` during the debugging:
* Receiver/transmitter via Arduino Nano doesn't seem to be the most stable solution. I've noticed chrashes of `pilight-daemon` (after sending a few requests either via API or by using `pilight-send` it would just crash). USB device would occasionally just reset, and it would change the port (e.g. going from `/dev/ttyUSB0` to `/dev/ttyUSB1`). However, those issues might be completely related to hardware issues (bad connection, bad serial-to-USB converter chip).
* Default `systemd` configuration doesn't seem to use auto restart for the daemon.
* `pilight-daemon` default configuration doesn't have SSDP discovery enabled (it's running in standalone mode), which is needed by `pilight-send/receive/...` (you can manually specify host and port on CLI tools, but port is by default choosen randomly on every start).
* Socket API is not easy to use (especially with the SSDP discovery), but thankfully there is also less documented REST API.
* Configuring RPi GPIO is a bit cumbersome, since you need to manually specify RPi board you have in `gpio-platform` in [config file](./pilight-config.json). There is little to no mention regarding this in official documentation.

# Approach #1 1/2
So if we get the successful response only occasionally, regardless of the configuration, there must be an issue either with software (`pilight`) or hardware. Let's try by replacing the software. There were some hints that it might be related to timing issues, since remote control used the same timings for all edge transitions, and `pilight` via Arduino Nano board had some deviations between them.

Since the final solution would be on RPi, let's try by using it's GPIO directly. I know that timing on RPi is problematic for some tasks, but RC transmission for this purpose doesn't have such hard requirements.

Googling for fastest GPIO library (not that I need it) pointed me to `pigpio`. Experimenting with `gpioWrite`/`gpioSleep` resulted with terrible timings, much worse that what can be observed by `pilight` and Nano. For example, transitioning to high, waiting for 900 us, and transitioning back to low, resulted in line being held high for ~900 us to ~1500 us.

Documentation pointed me to waveform feature, which enables you to construct output waveform which can then be sent with microsecond precision.

`pigpio` API is straightforward, and it didn't took me long to make a [working solution](./toggle.c). Resulting timing was close to perfect, but the R/C socket wouldn't budge. Ok, so I guess transmitting is not the problem (at least not the most problematic one, anyways).

# Approach #2
Instead of relying on the `pilight-debug` output, it would seem better to observe output of 433 MHz receiver chip directly.

I didn't really know what to expect, but I assumed that there would be a lot of noise on that frequency, so manually deciphering the data wouldn't be easy.

Connecting the logic analyzer between the receiver and Arduino, and recording the signal immediatelly showed that what is transmitted by the remote control is different to what is transmitted by `pilight-send`. It also shows that what we transmit matches what we receive on the other end, so the transmitting part is not the issue.

Manually exporting data from Saleae Logic software, parsing the CSV, and converting it to a format for the `pigpio` code, resulted in RC socket switching 100% of the time. Sucess!

Using the same code sequence for `pilight-send` also worked without any issue, so it means that the transmission part is not really problematic, and I can just use `pilight`, instead of making my own app for that (but since `pigpio` also has Python bindings, it shouldn't be that much work to add a REST API server).

I've also tried a [simple Python solution](./toggle.py) with `RPi.GPIO` library and just using `time.sleep` for waiting between transitions. It worked without any issues. Very nice.

Ok, so we can replicate the signal from remote control, and toggle the socket without any issues. However, this RC set has 3 sockets, and each of them has different ON/OFF code. I didn't really want to manually catch signal for each combination, export it, and decode it. Seems like we should automate this...

When searching for API / Python library for Saleae Logic I found some projects on GitHub, and it seems there is actually an API I can use. However it doesn't seem to be able to get samples directly, you need to record them to a file, and they parse the file.

That didn't sound so great, so I remembered that there exists an open source tool [sigrok](http://sigrok.org/) for recording/parsing/decoding logic analyzer data. It supports my analyzer out of the box, and also has an library (with Python bindings).

macOS package doesn't include the C library (much less the Python one), and I didn't really want to build it myself. Installing sigrok on Ubuntu VM sounds a lot easier, but attaching the USB device to the VM proofed to be harder than I expected (never had issues with various serial-to-USB converters before).

Running the GUI and CLI program worked flawlessly, and I could see the expected signal. I was afraid of issues relating to USB passthrough performance, since I had experienced them when running Logic directly on macOS, and adding another layer to the mix sounds less than ideal.

Installing `libsigrok-dev` (and `libsigrok2` as a dependency) didn't seem to install the Python bindings, and the version was quite old (`0.3.0` vs `0.5.1`). Building it manually took just a few steps, and I could successfully import it to Python.

Ok, so now that I have a working Python library, and know what pattern to look for in the samples, it should take me a few minutes to get the results I want, right? No, nope, nein, nyet.

There is no documentation apart from [Python binding reference](https://sigrok.org/api/libsigrok/unstable/bindings/python/index.html) (and coresponding C++ reference), and there is only one example [sigrok-meter](https://sigrok.org/wiki/Sigrok-meter) that I could find using the Python bindings, and it only interfaces with analog sources (which has quite different payload format than the digital sources).

With the help of this library, and source code of both the sigrok library, and sigrok program itself, I was able to get the idea of how to use the API, and correctly parse the received data. The result is in [sniffer.py](./sniffer.py), with enough comments to qualify as the best documentation for Python bindings of `libsigrok`. 😃

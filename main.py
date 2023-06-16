import time
import gc
import inky_helper as ih

CONFIG_FILENAME = '/sd/gallery-config.json'
STATE_FILENAME = '/gallery-state.json'


def load_config():
    import json
    import os
    import sdcard
    from machine import Pin, SPI

    # set up the SD card
    sd_spi = SPI(0, sck=Pin(18, Pin.OUT), mosi=Pin(19, Pin.OUT), miso=Pin(16, Pin.OUT))
    sd = sdcard.SDCard(sd_spi, Pin(22))
    os.mount(sd, "/sd")

    config = {}
    try:
        with open(CONFIG_FILENAME, 'r') as config_file:
            data = json.loads(config_file.read())
            print(data)
            if type(data) is dict:
                config = data

    except Exception as e:
        print("error reading config file", e)
        return None

    return config


def load_state():
    state = {"etag": None}
    try:
        with open(STATE_FILENAME, "r") as state_file:
            import json
            data = json.loads(state_file.read())
            print(data)
            if type(data) is dict:
                state = data

    except OSError as e:
        print("failed to load state", e)

    return state


def save_state(state):
    try:
        with open(STATE_FILENAME, "w") as state_file:
            import json
            state_file.write(json.dumps(state))
            state_file.flush()

    except OSError as e:
        print("failed to save state", e)


def display_image(filename):
    import jpegdec
    from picographics import PicoGraphics, DISPLAY_INKY_FRAME as DISPLAY

    graphics = PicoGraphics(DISPLAY)

    j = jpegdec.JPEG(graphics)
    gc.collect()

    # Open the JPEG file
    j.open_file(filename)

    dither = True
    if "dithered" in filename:
        dither = False

    # Decode the JPEG
    j.decode(0, 0, jpegdec.JPEG_SCALE_FULL, dither=dither)

    ih.led_warn.on()
    graphics.update()
    ih.led_warn.off()


def display_bin(filename):
    from picographics import PicoGraphics, DISPLAY_INKY_FRAME as DISPLAY

    graphics = PicoGraphics(DISPLAY)
    WIDTH, HEIGHT = graphics.get_bounds()


    with open(filename, "rb") as f:
        # skip header
        _ = f.read(64)

        for y in range(HEIGHT):
            row = f.read(int(WIDTH/2))
            for x in range(len(row)):
                graphics.set_pen(row[x] & 0xf)
                graphics.pixel(x*2, y)

                graphics.set_pen(row[x] >> 4)
                graphics.pixel(x*2 + 1, y)

    ih.led_warn.on()
    graphics.update()
    ih.led_warn.off()


def fetch(config, state):
    import urequests as requests

    if not 'host' in config:
        print('missing host in config')
        return None

    if not 'path' in config:
        print('missing path in config')
        return None

    if not 'authorization' in config:
        print('missing authorization in config')
        return None

    headers = {
        'Authorization': config['authorization'],
    }


    # use previous etag if there is one
    etag = state.get('etag')
    if etag:
        headers['If-None-Match'] = etag


    url = "https://%s%s" % (config['host'], config['path'])
    print("fetching '%s'... " % url)
    try:
        res = requests.get(url, headers=headers)
        print("status code: %d" % res.status_code)


        # in case of 304 Not Modified we return None so there there will be no refresh
        # this is the same as any other error
        if res.status_code != 200:
            return None

        print('headers: ', res.headers)
        state['etag'] = res.headers.get('etag')
        content_disposition = res.headers.get('Content-Disposition')

        image_filename = None
        for ext in ['.dithered.jpg', '.jpg', '.bin']:
            if content_disposition.endswith(ext):
                image_filename = "/sd/latest%s" % ext
                break

        if not image_filename:
            print("unsupported content: %s" % content_disposition)
            return None

        print("image filename: %s" % image_filename)


        temp_filename = '/sd/latest.tmp'
        with open(temp_filename, 'wb') as image_file:
            buf_size = 1024

            while True:
                buf = res.raw.read(buf_size)
                print("read %d bytes" % len(buf))
                image_file.write(buf)
                if len(buf) < buf_size:
                    break

            image_file.flush()
            res.close()

            import os
            os.rename(temp_filename, image_filename)
            gc.collect()
            return image_filename

    except OSError as e:
        print("failed to fetch url", e)
        return None


def loop():
    # A short delay to give USB chance to initialise
    time.sleep(0.5)

    gc.collect()
    print("Hello, %d bytes free" % gc.mem_free())

    try:
        from secrets import WIFI_SSID, WIFI_PASSWORD
        ih.network_connect(WIFI_SSID, WIFI_PASSWORD)
    except ImportError:
        print("Create secrets.py with your WiFi credentials")
        return

    config = load_config()
    if not config:
        return

    state = load_state()
    filename = fetch(config, state)
    if filename:
        if filename.endswith(".bin"):
            display_bin(filename)
        else:
            display_image(filename)

        save_state(state)

    import os
    os.umount('/sd')
    return


def entrypoint():
    while True:
        loop()
        ih.sleep(240)

entrypoint()

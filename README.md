This repository contains a micropython script intended to run on an [Inky Frame](https://shop.pimoroni.com/products/inky-frame-5-7?variant=40048398958675).
The script downloads an image from a preconfigured URL and displays it, then it goes to sleep and the process repeats at a later time.

Depending on the implementation of the server providing the image, this can be used to implement a remote controlled picture frame. 
For example, [frameserve](https://github.com/asssaf/frameserve) is an appengine based server that serves an image from a Google Cloud Storage Bucket on every request.

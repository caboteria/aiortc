Webcam server
=============

This example illustrates how to read frames from a webcam and send them
to one or more browsers.

Running
-------

First install the required packages:

.. code-block:: console

    $ pip install aiohttp aiortc

When you start the example, it will create an HTTP server which you
can connect to from your browser:

.. code-block:: console

    $ python examples/persistentwebcam/webcam.py

You can then browse to http://127.0.0.1:8080 to see the video.

Once you click `Start` the server will send video from its webcam to
the browser.  You can connect additional browsers and the server will
stream to them, too.

Credits
-------

The original idea and code for this example was from the "webcam"
example.

import asyncio
import logging
import threading

import av
from av import VideoFrame

from aiortc.mediastreams import MediaStreamError, MediaStreamTrack

logger = logging.getLogger("media")


def worker(loop, container, streams, video_tracks, quit_event):
    video_first_pts = None

    while not quit_event.is_set():
        try:
            frame = next(container.decode(*streams))
        except (av.AVError, StopIteration):
            for track in video_tracks:
                asyncio.run_coroutine_threadsafe(track._queue.put(None), loop)
            break

        if isinstance(frame, VideoFrame):
            if frame.pts is None:  # pragma: no cover
                logger.warning("Skipping video frame with no pts")
                continue

            # video from a webcam doesn't start at pts 0, cancel out offset
            if video_first_pts is None:
                video_first_pts = frame.pts
            frame.pts -= video_first_pts

            for track in video_tracks:
                asyncio.run_coroutine_threadsafe(track._queue.put(frame), loop)


class WebcamStreamTrack(MediaStreamTrack):
    def __init__(self, player, kind):
        super().__init__()
        self.kind = kind
        self._player = player
        self._queue = asyncio.Queue()
        self._player._start(self)

    async def recv(self):
        if self.readyState != "live":
            raise MediaStreamError

        frame = await self._queue.get()
        if frame is None:
            self.stop()
            raise MediaStreamError
        return frame

    def stop(self):
        super().stop()
        self._player.stop(self)


class WebcamSource:
    """
    A media source that reads video from a webcam.

    Examples:

    .. code-block:: python

        # Open webcam on Linux.
        player = MediaPlayer('/dev/video0', format='v4l2', options={
            'video_size': '640x480'
        })

        # Open webcam on OS X.
        player = MediaPlayer('default:none', format='avfoundation', options={
            'video_size': '640x480'
        })

    :param file: The path to a file, or a file-like object.
    :param format: The format to use, defaults to autodect.
    :param options: Additional options to pass to FFmpeg.
    """

    def __init__(self, file, format=None, options={}):
        self.__container = av.open(file=file, format=format, mode="r", options=options)
        self.__thread = None
        self.__thread_quit = threading.Event()

        self.__started = set()
        self.__streams = []
        self.__video = None

        logger.info("Starting worker thread")
        self.__thread = threading.Thread(
            name="media-player",
            target=worker,
            args=(
                asyncio.get_event_loop(),
                self.__container,
                self.__streams,
                self.__started,
                self.__thread_quit,
            ),
        )
        self.__thread.start()

    def addPC(self, pc, kind):
        pc.addTrack(WebcamStreamTrack(self, kind=kind))

    def _start(self, track):
        self.__started.add(track)

    def _stop(self, track):
        self.__started.discard(track)

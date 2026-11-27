"""Dispatch the latest camera frames to independent Vision receipt endpoints."""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPException
from threading import Condition, Thread
from time import monotonic

from amo_ai_interface.frame import Frame
from amo_ai_interface.latest_frames import DroppedFrame, LatestFrames

ReceiptPort = Callable[[Frame], None]


def _log_drop(dropped: DroppedFrame) -> None:
    logging.info(
        'camera_frame_dropped robot=%s frame=%s reason=%s',
        dropped.frame.robot_id,
        dropped.frame.frame_id,
        dropped.reason,
    )


class FrameDelivery:
    """Own one scheduling thread and one concurrent request per Vision target.

    Each selected frame completes its fan-out before another starts. On exit
    stop accepting frames, discard pending work and finish in-flight requests.
    """

    def __init__(
        self,
        robot_ids: frozenset[str],
        receipts: dict[str, ReceiptPort],
    ) -> None:
        self._queue = LatestFrames(robot_ids)
        if not receipts:
            raise ValueError('Configure at least one Vision receipt endpoint')
        self._receipts = dict(receipts)
        self._ready = Condition()
        self._closed = False
        self._worker = Thread(target=self._run, name='vision-frame-delivery')

    def __enter__(self) -> 'FrameDelivery':
        """Start the worker before the ROS adapter begins accepting input."""
        self._worker.start()
        return self

    def __exit__(self, *_error: object) -> None:
        """Wake an idle worker and wait for active HTTP operations to finish."""
        with self._ready:
            self._closed = True
            self._ready.notify()
        self._worker.join()

    def offer(self, frame: Frame) -> None:
        """Accept valid ingress from the ROS callback without waiting for HTTP."""
        with self._ready:
            if self._closed:
                return
            dropped = self._queue.offer(frame, monotonic())
            self._ready.notify()
        if dropped is not None:
            _log_drop(dropped)

    def _run(self) -> None:
        with ThreadPoolExecutor(max_workers=len(self._receipts)) as pool:
            while True:
                with self._ready:
                    if self._closed:
                        return
                    frame, expired = self._queue.take(monotonic())
                    if frame is None and not expired:
                        self._ready.wait()
                        continue
                for dropped in expired:
                    _log_drop(dropped)
                if frame is not None:
                    self._deliver(pool, frame)

    def _deliver(self, pool: ThreadPoolExecutor, frame: Frame) -> None:
        jobs = {
            service: pool.submit(receipt, frame)
            for service, receipt in self._receipts.items()
        }
        confirmed = []
        for service, job in jobs.items():
            try:
                job.result()
            except (OSError, ValueError, HTTPException) as error:
                logging.warning(
                    'vision_receipt_failed robot=%s frame=%s service=%s error_type=%s',
                    frame.robot_id,
                    frame.frame_id,
                    service,
                    type(error).__name__,
                )
            else:
                confirmed.append(service)
        logging.info(
            'vision_receipts robot=%s frame=%s confirmed=%d/%d services=%s',
            frame.robot_id,
            frame.frame_id,
            len(confirmed),
            len(jobs),
            ','.join(confirmed) or '-',
        )

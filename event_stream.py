"""flapi/event_stream.py

Server-Sent Events (SSE) manager for real-time data streaming.
Supports both Flask and FastAPI backends.
"""

from __future__ import annotations

import json
import queue
import threading
import time
from enum import IntEnum
from typing import TYPE_CHECKING, Any, Callable, Generator, Iterable

from ionbus_utils.logging_utils import logger

if TYPE_CHECKING:
    from ionbus_flapi.app import FlapiApp


class EventStreamTypes(IntEnum):
    """Types of EventStreams for different update targets."""

    GRID = 1
    DIV = 2
    LINE_PLOT = 4
    OHLC_PLOT = 8

    def str(self) -> str:
        """Return lowercase name for JavaScript."""
        return self.name.lower()

    @classmethod
    def message_type_lines(cls, value: int) -> str:
        """Generate JavaScript if-else blocks for message types."""
        ret_str = ""
        for est in EventStreamTypes:
            if est.value & value:
                ret_str += (
                    f'            else if (msg.MessageType == "{est.str()}") {{\n'
                    f"                update_{est.str()}(msg);\n"
                    f"            }}\n"
                )
        return ret_str

    @classmethod
    def update_functions(cls, value: int) -> str:
        """Generate JavaScript update functions for enabled types."""
        ret_str = ""
        for est in EventStreamTypes:
            if est.value & value:
                ret_str += _UPDATE_FUNCTIONS[est] + "\n"
        return ret_str


_UPDATE_FUNCTIONS = {
    EventStreamTypes.GRID: """        function update_grid(msg) {
            let { GridName, UpdateId, Rows } = msg;
            let dataArr = window["data" + GridName];
            for (let i = 0; i < Rows.length; i++) {
                let row = Rows[i];
                let doDelete = row.IsEmpty === 'DELETE';
                let found = dataArr.findIndex(d => d[UpdateId] == row[UpdateId]);
                if (doDelete) {
                    if (found >= 0) {
                        dataArr.splice(found, 1);
                    }
                }
                else {
                    if (found == -1) {
                        dataArr.push(row);
                    }
                    else {
                        dataArr[found] = row;
                    }
                }
            }
            $("#grid"+GridName).jqxGrid('updatebounddata', 'cells');
        }
""",
    EventStreamTypes.DIV: """        function update_div(msg) {
            document.getElementById(msg.DivId).innerHTML = msg.Html;
        }
""",
    EventStreamTypes.LINE_PLOT: """        function update_line_plot(msg) {
            let graphDiv = document.getElementById(msg.PlotName);
            let graph = graphDiv.data;
            let points = msg.Points;
            let xVals = [];
            let yVals = [];
            let traceList = [];
            for (let l = 0; l < points.length; l++) {
                let point = points[l];
                let trace = graph.findIndex(e => e.name == point.name);
                if (trace > -1) {
                    let valIndex = traceList.findIndex(e => e == trace);
                    if (valIndex == -1) {
                        traceList.push(trace);
                        xVals.push([point.x]);
                        yVals.push([point.y]);
                    }
                    else {
                        xVals[valIndex].push(point.x);
                        yVals[valIndex].push(point.y);
                    }
                }
            }
            Plotly.extendTraces(graphDiv,{ x:xVals, y:yVals }, traceList);
            let maxWidth = msg.MaxWidth || 500;
            let currleft = -1;
            let currright = -1;
            for (let t = 0; t < graph.length; t++) {
                if (graph[t].x.length >= maxWidth) {
                    currleft = Math.max(currleft, new Date(graph[t].x[graph[t].x.length-maxWidth]));
                }
                currright = Math.max(currright, new Date(graph[t].x[graph[t].x.length-1]));
            }
            if (currleft != -1) {
                Plotly.relayout(graphDiv,{ xaxis: { range: [currleft, currright] } });
            }
        }
""",
    EventStreamTypes.OHLC_PLOT: """        function update_ohlc_plot(msg) {
            let graphDiv = document.getElementById(msg.PlotName);
            let graph = graphDiv.data;
            let points = msg.Points;
            let xVals = [], openVals = [], highVals = [], lowVals = [], closeVals = [];
            let traceList = [];
            for (let l = 0; l < points.length; l++) {
                let point = points[l];
                let trace = graph.findIndex(e => e.name == point.name);
                if (trace > -1) {
                    let valIndex = traceList.findIndex(e => e == trace);
                    if (valIndex == -1) {
                        traceList.push(trace);
                        xVals.push([point.x]);
                        openVals.push([point.open]);
                        highVals.push([point.high]);
                        lowVals.push([point.low]);
                        closeVals.push([point.close]);
                    }
                    else {
                        xVals[valIndex].push(point.x);
                        openVals[valIndex].push(point.open);
                        highVals[valIndex].push(point.high);
                        lowVals[valIndex].push(point.low);
                        closeVals[valIndex].push(point.close);
                    }
                }
            }
            Plotly.extendTraces(graphDiv,{
                x:xVals, open:openVals, high:highVals, low:lowVals, close:closeVals
            }, traceList);
            let maxWidth = msg.MaxWidth || 500;
            let currleft = -1;
            let currright = -1;
            for (let t = 0; t < graph.length; t++) {
                if (graph[t].x.length >= maxWidth) {
                    currleft = Math.max(currleft, new Date(graph[t].x[graph[t].x.length-maxWidth]));
                }
                currright = Math.max(currright, new Date(graph[t].x[graph[t].x.length-1]));
            }
            if (currleft != -1) {
                Plotly.relayout(graphDiv,{ xaxis: { range: [currleft, currright] } });
            }
        }
""",
}


class EventStream:
    """Manages a queue of events for a single client connection."""

    unique_id: str
    max_size: int
    event_queue: queue.Queue
    subscriptions: list[str]
    is_dead: bool = False
    _lock: threading.Lock
    _esm: EventStreamManager

    def __init__(
        self,
        esm: EventStreamManager,
        unique_id: str,
        subscriptions: list[str] | str | None = None,
        max_size: int = 50,
    ):
        if isinstance(subscriptions, str):
            subscriptions = [subscriptions]
        self._esm = esm
        self.subscriptions = subscriptions if subscriptions else []
        self.unique_id = unique_id
        self.max_size = max_size
        self.event_queue: queue.Queue = queue.Queue()
        self._waiting = 0
        self._lock = threading.Lock()

    def add_event(
        self,
        event: dict[str, Any],
        idx: int,
        always_alive: bool = False,
    ) -> bool:
        """Add an event to the queue. Returns False if stream is dead."""
        with self._lock:
            if self.is_dead:
                return False
            if not idx:
                self._waiting += 1
            if self._waiting >= self.max_size and not always_alive:
                self.is_dead = True
                return False
            self.event_queue.put(event)
            return True

    def stream(self) -> Generator[str, None, None]:
        """Generator that yields events from the queue."""
        while not self.is_dead:
            try:
                event = self.event_queue.get(timeout=1.0)
                self._waiting = 0
                yield f"data: {json.dumps(event)}\n\n"
                self.event_queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                break

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EventStream):
            return False
        return self.unique_id == other.unique_id

    def __hash__(self) -> int:
        return hash(self.unique_id)


class EventStreamManager:
    """Manages multiple EventStreams and subscriptions for SSE.

    Example usage:
        esm = EventStreamManager(
            "MyStream",
            EventStreamTypes.GRID | EventStreamTypes.DIV,
            subscribe_func=on_subscribe,
            unsubscribe_func=on_unsubscribe,
            include_pause=True,
        )

        # In your endpoint:
        stream_address = esm.get_stream_address("ticker1")
        js = esm.javascript(stream_address)
        html = esm.html()

        # From a data thread:
        esm.broadcast_event("ticker1", {"MessageType": "div", ...})
    """

    name: str
    subscribe_func: Callable[[Iterable[str]], None] | None
    unsubscribe_func: Callable[[Iterable[str]], None] | None
    stream_types: int
    streams: dict[str, EventStream]
    subscriptions: dict[str, set[EventStream]]
    modes: int
    include_pause: bool
    _lock: threading.Lock
    _sub_lock: threading.Lock
    _registered: bool = False

    def __init__(
        self,
        name: str,
        modes: int = EventStreamTypes.DIV,
        subscribe_func: Callable[[Iterable[str]], None] | None = None,
        unsubscribe_func: Callable[[Iterable[str]], None] | None = None,
        include_pause: bool = True,
    ):
        """Create an EventStreamManager.

        Args:
            name: Unique name for this stream manager.
            modes: Bitmask of EventStreamTypes to support.
            subscribe_func: Called when new tickers are subscribed.
            unsubscribe_func: Called when tickers are unsubscribed.
            include_pause: Include pause/resume button in HTML.
        """
        self.name = name
        self.subscribe_func = subscribe_func
        self.unsubscribe_func = unsubscribe_func
        self.modes = modes
        self.include_pause = include_pause
        self.streams = {}
        self.subscriptions = {}
        self._lock = threading.Lock()
        self._sub_lock = threading.Lock()
        self._registered = False

    def register(self, flapi_app: FlapiApp) -> None:
        """Register the streaming endpoint with the FlapiApp.

        Must be called after ionbus_flapi.initialize() and before serve().
        """
        from ionbus_flapi.routing import prepare_url

        if self._registered:
            return

        endpoint_path = prepare_url(f"/_{self.name}_streaming")

        # Check if Flask or FastAPI
        if hasattr(flapi_app.app, "add_url_rule"):
            # Flask
            flapi_app.app.add_url_rule(
                endpoint_path,
                f"{self.name}_stream",
                self._flask_stream_func,
            )
        else:
            # FastAPI - use explicit query parameters
            esm_ref = self  # Capture reference for closure

            @flapi_app.app.get(endpoint_path)
            def stream_endpoint(
                id: str | None = None,
                tickers: str | None = None,
            ):
                return esm_ref._get_streaming_response(
                    id, tickers, use_fastapi=True
                )

        self._registered = True
        logger.info(f"Registered EventStreamManager '{self.name}' at {endpoint_path}")

    def _flask_stream_func(self):
        """Flask view function to stream events."""
        from flask import request

        unique_id = request.args.get("id")
        tickers_param = request.args.get("tickers")
        return self._get_streaming_response(
            unique_id, tickers_param, use_fastapi=False
        )

    def _get_streaming_response(
        self,
        unique_id: str | None,
        tickers_param: str | None,
        use_fastapi: bool = False,
    ):
        """Get streaming response for Flask or FastAPI."""
        logger.debug(f"Streaming request for id={unique_id}")

        if unique_id and unique_id in self.streams:
            event_stream = self.streams[unique_id]
        elif tickers_param:
            tickers = tickers_param.split(",")
            logger.info(f"Creating new stream for tickers: {tickers}")
            new_id = self.create_stream(tickers)
            event_stream = self.streams[new_id]
        else:
            logger.warning(f"Stream not found: {unique_id}")
            if use_fastapi:
                from fastapi.responses import PlainTextResponse

                return PlainTextResponse("Stream not found", status_code=404)
            else:
                from flask import Response

                return Response("Stream not found", status=404)

        if use_fastapi:
            from fastapi.responses import StreamingResponse

            headers = {
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
            return StreamingResponse(
                event_stream.stream(),
                media_type="text/event-stream",
                headers=headers,
            )
        else:
            from flask import Response

            # Note: Connection header is hop-by-hop, forbidden by WSGI/PEP 3333
            headers = {
                "Cache-Control": "no-cache",
                "Access-Control-Allow-Origin": "*",
            }
            return Response(
                event_stream.stream(),
                mimetype="text/event-stream",
                headers=headers,
            )

    def get_stream_address(self, tickers: str | list[str]) -> str:
        """Create a stream for given tickers and return the stream address."""
        from ionbus_flapi.routing import prepare_url

        if isinstance(tickers, str):
            tickers = [tickers]
        unique_id = self.create_stream(tickers)
        ticker_param = ",".join(tickers)
        return prepare_url(
            f"/_{self.name}_streaming?id={unique_id}&tickers={ticker_param}"
        )

    def create_stream(self, tickers: str | list[str]) -> str:
        """Create a new EventStream and return its unique ID."""
        unique_id = f"{int(time.time() * 1000000):x}"
        if isinstance(tickers, str):
            tickers = [tickers]
        with self._lock:
            event_stream = EventStream(self, unique_id, tickers)
            self.streams[unique_id] = event_stream
            for ticker in tickers:
                self.subscriptions.setdefault(ticker, set()).add(event_stream)
        self._call_subscribe_func_if_needed(tickers)
        return unique_id

    def broadcast_event(
        self,
        ticker: str | None,
        events: dict[str, Any] | list[dict[str, Any]],
    ) -> None:
        """Broadcast events to all streams subscribed to the ticker.

        Args:
            ticker: The ticker/channel to broadcast to, or None for all.
            events: Single event dict or list of event dicts.
        """
        if not isinstance(events, list):
            events = [events]
        dead_streams: set[EventStream] = set()
        with self._lock:
            if ticker:
                stream_collection = self.subscriptions.get(ticker)
                if stream_collection is None:
                    return
            else:
                stream_collection = set(self.streams.values())
            for es in stream_collection:
                for idx, event in enumerate(events):
                    if not es.add_event(event, idx):
                        dead_streams.add(es)

        if dead_streams:
            self._cleanup_dead_streams(dead_streams)

    def _cleanup_dead_streams(self, dead_streams: set[EventStream]) -> None:
        """Clean up dead streams and their subscriptions."""
        no_longer_wanted: set[str] = set()
        with self._sub_lock:
            with self._lock:
                for ds in dead_streams:
                    if ds.unique_id in self.streams:
                        del self.streams[ds.unique_id]
                    for ticker in ds.subscriptions:
                        ticker_set = self.subscriptions.get(ticker)
                        if not ticker_set or ds not in ticker_set:
                            continue
                        ticker_set.remove(ds)
                        if not ticker_set:
                            no_longer_wanted.add(ticker)
                            del self.subscriptions[ticker]

            if self.unsubscribe_func and no_longer_wanted:
                self.unsubscribe_func(no_longer_wanted)

    def has_subscriptions(self) -> bool:
        """Check if there are any active subscriptions."""
        with self._lock:
            return bool(self.subscriptions)

    def get_subscribed_tickers(self) -> list[str]:
        """Get list of currently subscribed tickers."""
        with self._lock:
            return list(self.subscriptions.keys())

    def javascript(self, stream_address: str) -> str:
        """Get JavaScript code for receiving and processing events.

        Args:
            stream_address: The stream URL from get_stream_address().

        Returns:
            JavaScript code to include in your page.
        """
        ret_str = f"""            let eventSource = new EventSource('{stream_address}');
            eventSource.onmessage = function (e) {{
                let msg = JSON.parse(e.data);\n"""
        if self.include_pause:
            ret_str += """                if (document.getElementById('pauseStream').innerHTML == 'Stream') {{
                    return;
                }}\n"""
        ret_str += EventStreamTypes.message_type_lines(self.modes)
        ret_str += """                else {
                    console.log("Unknown MessageType: "+msg.MessageType);
                }
            };\n"""
        ret_str += EventStreamTypes.update_functions(self.modes)
        if self.include_pause:
            ret_str += """            var pausedStream = false;
            window.toggleStream = function() {
                pausedStream = !pausedStream;
                document.getElementById('pauseStream').innerHTML =
                    pausedStream ? 'Stream' : 'Pause';
            };\n"""
        return ret_str

    def html(self) -> str:
        """Get HTML for pause/resume button if enabled."""
        if self.include_pause:
            return (
                '<span><button id="pauseStream" onclick="toggleStream()" '
                'style="width:140px">Pause</button></span><p>'
            )
        return ""

    def _call_subscribe_func_if_needed(self, tickers: Iterable[str]) -> None:
        """Call subscribe_func for new tickers."""
        if isinstance(tickers, str):
            tickers = [tickers]
        with self._sub_lock:
            with self._lock:
                current = set(self.subscriptions.keys())
                new_tickers = [t for t in tickers if t and t not in current]
            if new_tickers and self.subscribe_func:
                for ticker in new_tickers:
                    self.subscribe_func(ticker)

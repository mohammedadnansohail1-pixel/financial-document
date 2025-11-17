"""
Streaming Data Processor
Real-time data stream processing for market data, news, and filings
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass
from collections import deque
from enum import Enum
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StreamType(Enum):
    """Stream types"""
    MARKET_DATA = "market_data"
    NEWS_FEED = "news_feed"
    SEC_FILINGS = "sec_filings"
    EARNINGS_CALLS = "earnings_calls"
    SOCIAL_SENTIMENT = "social_sentiment"


@dataclass
class StreamEvent:
    """Individual stream event"""
    event_id: str
    stream_type: StreamType
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Dict[str, Any]


class StreamBuffer:
    """
    Buffered stream with windowing support
    """

    def __init__(self, max_size: int = 1000, window_seconds: int = 60):
        self.max_size = max_size
        self.window_seconds = window_seconds
        self.buffer: deque = deque(maxlen=max_size)

    def add(self, event: StreamEvent):
        """Add event to buffer"""
        self.buffer.append(event)

    def get_window(
        self,
        window_seconds: Optional[int] = None
    ) -> List[StreamEvent]:
        """
        Get events within time window

        Args:
            window_seconds: Time window in seconds (None for all)
        """
        if window_seconds is None:
            window_seconds = self.window_seconds

        cutoff = datetime.now().timestamp() - window_seconds

        return [
            event for event in self.buffer
            if event.timestamp.timestamp() >= cutoff
        ]

    def get_last_n(self, n: int) -> List[StreamEvent]:
        """Get last N events"""
        return list(self.buffer)[-n:]

    def clear(self):
        """Clear buffer"""
        self.buffer.clear()


class StreamProcessor:
    """
    Process individual stream events
    """

    def __init__(self):
        self.processors: Dict[StreamType, Callable] = {}

    def register_processor(
        self,
        stream_type: StreamType,
        processor_func: Callable
    ):
        """
        Register processor function for stream type

        Args:
            stream_type: Type of stream
            processor_func: Processing function
        """
        self.processors[stream_type] = processor_func
        logger.info(f"Registered processor for {stream_type.value}")

    async def process_event(self, event: StreamEvent) -> Dict[str, Any]:
        """
        Process individual event

        Args:
            event: Stream event
        """
        processor = self.processors.get(event.stream_type)

        if processor:
            try:
                result = await processor(event) if asyncio.iscoroutinefunction(processor) else processor(event)
                return {
                    'status': 'success',
                    'event_id': event.event_id,
                    'result': result
                }
            except Exception as e:
                logger.error(f"Error processing event {event.event_id}: {e}")
                return {
                    'status': 'error',
                    'event_id': event.event_id,
                    'error': str(e)
                }
        else:
            return {
                'status': 'no_processor',
                'event_id': event.event_id
            }


class StreamAggregator:
    """
    Aggregate streaming data over windows
    """

    def __init__(self, window_size: int = 60):
        self.window_size = window_size
        self.aggregators: Dict[str, Callable] = {}

    def register_aggregator(
        self,
        name: str,
        aggregator_func: Callable
    ):
        """
        Register aggregation function

        Args:
            name: Aggregator name
            aggregator_func: Aggregation function (takes list of events)
        """
        self.aggregators[name] = aggregator_func

    def aggregate(
        self,
        events: List[StreamEvent],
        aggregator_name: str
    ) -> Any:
        """
        Aggregate events

        Args:
            events: List of events to aggregate
            aggregator_name: Name of aggregator to use
        """
        aggregator = self.aggregators.get(aggregator_name)

        if aggregator:
            return aggregator(events)
        else:
            raise ValueError(f"Unknown aggregator: {aggregator_name}")


class StreamConsumer:
    """
    Consume data from streams
    """

    def __init__(
        self,
        consumer_id: str,
        stream_type: StreamType
    ):
        self.consumer_id = consumer_id
        self.stream_type = stream_type
        self.is_running = False
        self.event_handlers: List[Callable] = []

    def add_handler(self, handler: Callable):
        """Add event handler"""
        self.event_handlers.append(handler)

    async def start(self, stream_source: Any):
        """
        Start consuming stream

        Args:
            stream_source: Source to consume from
        """
        self.is_running = True
        logger.info(f"Consumer {self.consumer_id} started for {self.stream_type.value}")

        # In production, connect to actual stream (Kafka, WebSocket, etc.)
        # while self.is_running:
        #     event = await stream_source.receive()
        #     await self.handle_event(event)

    async def handle_event(self, event: StreamEvent):
        """Handle incoming event"""
        for handler in self.event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in handler: {e}")

    def stop(self):
        """Stop consuming"""
        self.is_running = False
        logger.info(f"Consumer {self.consumer_id} stopped")


class RealTimeStreamProcessor:
    """
    Main real-time stream processing engine
    """

    def __init__(self):
        self.buffers: Dict[StreamType, StreamBuffer] = {}
        self.processor = StreamProcessor()
        self.aggregator = StreamAggregator()
        self.consumers: Dict[str, StreamConsumer] = {}

        # Initialize buffers for each stream type
        for stream_type in StreamType:
            self.buffers[stream_type] = StreamBuffer()

        # Register default processors
        self._register_default_processors()

        # Register default aggregators
        self._register_default_aggregators()

        logger.info("RealTimeStreamProcessor initialized")

    def _register_default_processors(self):
        """Register default processing functions"""

        async def process_market_data(event: StreamEvent):
            """Process market data event"""
            data = event.data

            # Extract price changes
            if 'price' in data and 'previous_price' in data:
                change = data['price'] - data['previous_price']
                change_pct = (change / data['previous_price']) * 100 if data['previous_price'] != 0 else 0

                return {
                    'symbol': data.get('symbol'),
                    'price': data['price'],
                    'change': change,
                    'change_pct': change_pct,
                    'volume': data.get('volume', 0)
                }

            return data

        async def process_news(event: StreamEvent):
            """Process news event"""
            data = event.data

            # Extract key information
            return {
                'title': data.get('title', ''),
                'source': data.get('source', ''),
                'sentiment': data.get('sentiment', 0.0),
                'entities': data.get('entities', []),
                'timestamp': event.timestamp
            }

        async def process_sec_filing(event: StreamEvent):
            """Process SEC filing event"""
            data = event.data

            return {
                'company': data.get('company'),
                'cik': data.get('cik'),
                'filing_type': data.get('filing_type'),
                'filing_date': data.get('filing_date'),
                'url': data.get('url')
            }

        # Register processors
        self.processor.register_processor(StreamType.MARKET_DATA, process_market_data)
        self.processor.register_processor(StreamType.NEWS_FEED, process_news)
        self.processor.register_processor(StreamType.SEC_FILINGS, process_sec_filing)

    def _register_default_aggregators(self):
        """Register default aggregation functions"""

        def avg_price(events: List[StreamEvent]) -> float:
            """Calculate average price"""
            prices = [
                e.data.get('price', 0)
                for e in events
                if 'price' in e.data
            ]
            return sum(prices) / len(prices) if prices else 0.0

        def total_volume(events: List[StreamEvent]) -> float:
            """Calculate total volume"""
            return sum(
                e.data.get('volume', 0)
                for e in events
            )

        def sentiment_score(events: List[StreamEvent]) -> float:
            """Calculate aggregate sentiment"""
            sentiments = [
                e.data.get('sentiment', 0.0)
                for e in events
                if 'sentiment' in e.data
            ]
            return sum(sentiments) / len(sentiments) if sentiments else 0.0

        # Register aggregators
        self.aggregator.register_aggregator('avg_price', avg_price)
        self.aggregator.register_aggregator('total_volume', total_volume)
        self.aggregator.register_aggregator('sentiment_score', sentiment_score)

    async def ingest_event(self, event: StreamEvent):
        """
        Ingest and process stream event

        Args:
            event: Stream event
        """
        # Add to buffer
        buffer = self.buffers.get(event.stream_type)
        if buffer:
            buffer.add(event)

        # Process event
        result = await self.processor.process_event(event)

        return result

    def get_window_events(
        self,
        stream_type: StreamType,
        window_seconds: int = 60
    ) -> List[StreamEvent]:
        """
        Get events from time window

        Args:
            stream_type: Stream type
            window_seconds: Time window
        """
        buffer = self.buffers.get(stream_type)
        if buffer:
            return buffer.get_window(window_seconds)
        return []

    def aggregate_window(
        self,
        stream_type: StreamType,
        aggregator_name: str,
        window_seconds: int = 60
    ) -> Any:
        """
        Aggregate events in time window

        Args:
            stream_type: Stream type
            aggregator_name: Aggregator to use
            window_seconds: Time window
        """
        events = self.get_window_events(stream_type, window_seconds)
        return self.aggregator.aggregate(events, aggregator_name)

    def create_consumer(
        self,
        consumer_id: str,
        stream_type: StreamType,
        handler: Callable
    ) -> StreamConsumer:
        """
        Create stream consumer

        Args:
            consumer_id: Consumer identifier
            stream_type: Stream to consume
            handler: Event handler function
        """
        consumer = StreamConsumer(consumer_id, stream_type)
        consumer.add_handler(handler)

        self.consumers[consumer_id] = consumer

        return consumer

    def get_stream_statistics(self) -> Dict[str, Any]:
        """Get streaming statistics"""
        stats = {}

        for stream_type, buffer in self.buffers.items():
            stats[stream_type.value] = {
                'buffer_size': len(buffer.buffer),
                'window_size': buffer.window_seconds,
                'last_event': buffer.buffer[-1].timestamp.isoformat() if buffer.buffer else None
            }

        return {
            'streams': stats,
            'active_consumers': len(self.consumers),
            'registered_processors': len(self.processor.processors),
            'registered_aggregators': len(self.aggregator.aggregators)
        }


# Utility functions for stream processing

def create_market_data_event(
    symbol: str,
    price: float,
    volume: int,
    previous_price: Optional[float] = None
) -> StreamEvent:
    """
    Create market data event

    Args:
        symbol: Stock symbol
        price: Current price
        volume: Trading volume
        previous_price: Previous price for change calculation
    """
    return StreamEvent(
        event_id=f"market_{symbol}_{datetime.now().timestamp()}",
        stream_type=StreamType.MARKET_DATA,
        timestamp=datetime.now(),
        data={
            'symbol': symbol,
            'price': price,
            'volume': volume,
            'previous_price': previous_price or price
        },
        metadata={}
    )


def create_news_event(
    title: str,
    content: str,
    source: str,
    sentiment: float = 0.0
) -> StreamEvent:
    """
    Create news event

    Args:
        title: News title
        content: News content
        source: News source
        sentiment: Sentiment score (-1 to 1)
    """
    return StreamEvent(
        event_id=f"news_{datetime.now().timestamp()}",
        stream_type=StreamType.NEWS_FEED,
        timestamp=datetime.now(),
        data={
            'title': title,
            'content': content,
            'source': source,
            'sentiment': sentiment
        },
        metadata={}
    )


# Example usage
async def main():
    """Example stream processing"""
    processor = RealTimeStreamProcessor()

    # Simulate market data stream
    symbols = ['AAPL', 'MSFT', 'GOOGL']

    for i in range(100):
        for symbol in symbols:
            # Create market data event
            price = 100 + i * 0.5 + (hash(symbol) % 10)
            event = create_market_data_event(
                symbol=symbol,
                price=price,
                volume=1000000 + i * 10000,
                previous_price=price - 0.5
            )

            # Ingest event
            await processor.ingest_event(event)

        await asyncio.sleep(0.1)

    # Get windowed events
    recent_events = processor.get_window_events(StreamType.MARKET_DATA, window_seconds=30)
    print(f"Recent events: {len(recent_events)}")

    # Aggregate data
    avg_price = processor.aggregate_window(StreamType.MARKET_DATA, 'avg_price', window_seconds=30)
    print(f"Average price (30s window): {avg_price:.2f}")

    total_vol = processor.aggregate_window(StreamType.MARKET_DATA, 'total_volume', window_seconds=30)
    print(f"Total volume (30s window): {total_vol:,.0f}")

    # Get statistics
    stats = processor.get_stream_statistics()
    print(f"Stream statistics: {json.dumps(stats, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())

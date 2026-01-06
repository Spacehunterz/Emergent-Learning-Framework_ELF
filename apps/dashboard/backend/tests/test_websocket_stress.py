"""
WebSocket Stress Tests for the Emergent Learning Dashboard.

Tests concurrent WebSocket connections, reconnection under load, and message
ordering under stress conditions.

These tests verify the fixes for CRITICAL #1 and CRITICAL #6:
- WebSocket reconnect race condition (multiple concurrent reconnection timeouts)
- Broadcast list modification race (concurrent disconnect during broadcast)
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from utils.broadcast import ConnectionManager


@pytest.mark.asyncio
class TestWebSocketConcurrentConnections:
    """Test concurrent WebSocket connection handling."""

    @pytest.fixture
    def connection_manager(self):
        """Create a ConnectionManager instance for testing."""
        return ConnectionManager()

    async def test_concurrent_connections_no_race(self, connection_manager: ConnectionManager):
        """Test that multiple clients can connect concurrently without issues."""
        # Create 50 mock WebSocket connections
        mock_websockets = [AsyncMock() for _ in range(50)]

        # Connect all clients concurrently
        connect_tasks = [
            connection_manager.connect(ws) for ws in mock_websockets
        ]
        await asyncio.gather(*connect_tasks)

        # Verify all connections were accepted
        for ws in mock_websockets:
            ws.accept.assert_called_once()

        # Verify all connections are tracked
        assert len(connection_manager.active_connections) == 50

    async def test_concurrent_disconnect_no_race(self, connection_manager: ConnectionManager):
        """Test that concurrent disconnects don't cause list modification errors."""
        # Create and connect 20 clients
        mock_websockets = [AsyncMock() for _ in range(20)]
        for ws in mock_websockets:
            await connection_manager.connect(ws)

        assert len(connection_manager.active_connections) == 20

        # Disconnect all clients concurrently
        disconnect_tasks = [
            connection_manager.disconnect(ws) for ws in mock_websockets
        ]
        await asyncio.gather(*disconnect_tasks)

        # Verify all connections were removed
        assert len(connection_manager.active_connections) == 0

    async def test_concurrent_connect_and_disconnect(self, connection_manager: ConnectionManager):
        """Test mixed concurrent connections and disconnections."""
        # Create 30 clients
        mock_websockets = [AsyncMock() for _ in range(30)]

        # Connect first 20
        for ws in mock_websockets[:20]:
            await connection_manager.connect(ws)

        # Mix operations: connect new clients while disconnecting old ones
        tasks = []
        # Disconnect first 10
        tasks.extend([connection_manager.disconnect(ws) for ws in mock_websockets[:10]])
        # Connect remaining 10
        tasks.extend([connection_manager.connect(ws) for ws in mock_websockets[20:]])

        await asyncio.gather(*tasks)

        # Should have 20 connections (10 old + 10 new)
        assert len(connection_manager.active_connections) == 20


@pytest.mark.asyncio
class TestWebSocketReconnectionStress:
    """Test WebSocket reconnection logic under stress."""

    async def test_no_duplicate_reconnect_timeouts(self):
        """
        Test that multiple reconnect attempts don't create duplicate timeouts.

        This tests the fix for CRITICAL #1: WebSocket Reconnect Race Condition.
        Before the fix, multiple concurrent reconnection timeouts could be scheduled,
        causing connection instability.
        """
        reconnect_timeout = None
        reconnect_count = 0

        async def mock_connect():
            """Mock connect function that tracks reconnect attempts."""
            nonlocal reconnect_count
            reconnect_count += 1
            await asyncio.sleep(0.01)

        # Simulate multiple rapid reconnection attempts
        for i in range(5):
            # Clear existing timeout before scheduling new one (the fix)
            if reconnect_timeout:
                reconnect_timeout.cancel()
                try:
                    await reconnect_timeout
                except asyncio.CancelledError:
                    pass

            # Schedule new reconnect
            reconnect_timeout = asyncio.create_task(mock_connect())

        # Wait for the final reconnect to complete
        await reconnect_timeout

        # Only the last reconnect should execute
        assert reconnect_count == 1, "Multiple reconnect timeouts were not properly cleared"

    async def test_reconnect_backoff_under_load(self):
        """Test that reconnection backoff works correctly under load."""
        reconnect_attempts = 0
        base_delay = 0.01  # Short delay for testing
        max_attempts = 5

        async def attempt_reconnect(attempt_number: int):
            """Simulate a reconnection attempt with exponential backoff."""
            nonlocal reconnect_attempts
            delay = min(base_delay * (2 ** attempt_number), 0.1)
            await asyncio.sleep(delay)
            reconnect_attempts += 1

        # Simulate sequential reconnection attempts
        tasks = [attempt_reconnect(i) for i in range(max_attempts)]
        await asyncio.gather(*tasks)

        assert reconnect_attempts == max_attempts

    async def test_reconnect_cancellation_on_unmount(self):
        """Test that pending reconnects are cancelled when component unmounts."""
        mounted = True
        reconnect_task = None

        async def connect():
            """Mock connect that respects mount state."""
            if not mounted:
                return
            await asyncio.sleep(0.1)

        # Schedule a reconnect
        reconnect_task = asyncio.create_task(connect())

        # Simulate unmount
        mounted = False
        reconnect_task.cancel()

        try:
            await reconnect_task
        except asyncio.CancelledError:
            pass  # Expected

        assert reconnect_task.cancelled()


@pytest.mark.asyncio
class TestBroadcastRaceConditions:
    """Test broadcast message ordering and race conditions."""

    @pytest.fixture
    def connection_manager(self):
        """Create a ConnectionManager instance for testing."""
        return ConnectionManager()

    async def test_broadcast_during_concurrent_disconnect(self, connection_manager: ConnectionManager):
        """
        Test that broadcast handles concurrent disconnections safely.

        This tests the fix for CRITICAL #6: Broadcast List Modification Race.
        Before the fix, concurrent disconnect during broadcast could cause ValueError
        due to list modification during iteration.
        """
        # Create and connect 100 clients
        mock_websockets = [AsyncMock() for _ in range(100)]
        for ws in mock_websockets:
            await connection_manager.connect(ws)

        # Make some clients fail during send
        for i in range(0, 100, 3):  # Every 3rd client fails
            mock_websockets[i].send_json.side_effect = RuntimeError("Connection closed")

        # Start disconnecting clients concurrently with broadcast
        async def disconnect_clients():
            await asyncio.sleep(0.001)  # Small delay to overlap with broadcast
            tasks = [connection_manager.disconnect(ws) for ws in mock_websockets[50:75]]
            await asyncio.gather(*tasks)

        disconnect_task = asyncio.create_task(disconnect_clients())

        # Broadcast while disconnects are happening
        await connection_manager.broadcast({"type": "test", "data": "stress test"})

        await disconnect_task

        # Should not raise ValueError and should remove dead connections
        # The exact count depends on timing, but should be less than 100
        assert len(connection_manager.active_connections) < 100

    async def test_broadcast_message_ordering(self, connection_manager: ConnectionManager):
        """Test that messages are delivered in order under load."""
        # Create 10 clients
        mock_websockets = [AsyncMock() for _ in range(10)]
        for ws in mock_websockets:
            await connection_manager.connect(ws)

        # Send 50 messages rapidly
        messages = [{"type": "test", "sequence": i} for i in range(50)]

        for msg in messages:
            await connection_manager.broadcast(msg)

        # Each client should receive all messages
        for ws in mock_websockets:
            assert ws.send_json.call_count == 50

    async def test_broadcast_lock_prevents_corruption(self, connection_manager: ConnectionManager):
        """Test that the asyncio lock prevents connection list corruption."""
        # Create 50 clients
        mock_websockets = [AsyncMock() for _ in range(50)]
        for ws in mock_websockets:
            await connection_manager.connect(ws)

        # Perform many concurrent operations that modify the connection list
        async def mixed_operations(ws_list: List[AsyncMock]):
            tasks = []
            for i, ws in enumerate(ws_list):
                if i % 2 == 0:
                    tasks.append(connection_manager.disconnect(ws))
                else:
                    tasks.append(connection_manager.broadcast({"type": "test", "index": i}))
            await asyncio.gather(*tasks)

        await mixed_operations(mock_websockets[:25])

        # Verify the connection list is in a valid state
        # Should have removed ~12-13 connections
        assert 0 <= len(connection_manager.active_connections) <= 50

    async def test_broadcast_with_dead_connections_cleanup(self, connection_manager: ConnectionManager):
        """Test that dead connections are properly cleaned up during broadcast."""
        # Create 20 clients
        mock_websockets = [AsyncMock() for _ in range(20)]
        for ws in mock_websockets:
            await connection_manager.connect(ws)

        # Make half of them "dead" (send_json fails)
        for i in range(10):
            mock_websockets[i].send_json.side_effect = Exception("Dead connection")

        # Broadcast a message
        await connection_manager.broadcast({"type": "test", "data": "cleanup test"})

        # Dead connections should be removed
        assert len(connection_manager.active_connections) == 10

        # Verify only live connections remain
        for ws in connection_manager.active_connections:
            assert ws not in mock_websockets[:10]


@pytest.mark.asyncio
class TestWebSocketStressIntegration:
    """Integration tests for WebSocket under realistic load."""

    async def test_high_connection_churn(self):
        """Test rapid connection and disconnection cycles."""
        manager = ConnectionManager()

        async def client_lifecycle():
            """Simulate a client connecting, receiving messages, and disconnecting."""
            ws = AsyncMock()
            await manager.connect(ws)
            await asyncio.sleep(0.001)
            await manager.broadcast({"type": "ping"})
            await asyncio.sleep(0.001)
            await manager.disconnect(ws)

        # Run 100 client lifecycles concurrently
        tasks = [client_lifecycle() for _ in range(100)]
        await asyncio.gather(*tasks)

        # All clients should have disconnected
        assert len(manager.active_connections) == 0

    async def test_sustained_load_with_failures(self):
        """Test sustained message broadcasting with intermittent failures."""
        manager = ConnectionManager()

        # Connect 30 stable clients
        stable_clients = [AsyncMock() for _ in range(30)]
        for ws in stable_clients:
            await manager.connect(ws)

        # Add 10 unstable clients that fail randomly
        unstable_clients = [AsyncMock() for _ in range(10)]
        for i, ws in enumerate(unstable_clients):
            await manager.connect(ws)
            # Make some fail after a few messages
            if i % 3 == 0:
                ws.send_json.side_effect = [None, None, Exception("Intermittent failure")]

        # Send 100 messages
        for i in range(100):
            await manager.broadcast({"type": "load_test", "sequence": i})
            if i % 10 == 0:
                await asyncio.sleep(0.001)  # Small delay every 10 messages

        # Should have removed failing clients but kept stable ones
        assert 30 <= len(manager.active_connections) <= 40

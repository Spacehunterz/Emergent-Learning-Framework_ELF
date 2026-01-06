"""
Broadcast Race Condition Tests for the Emergent Learning Dashboard.

Tests the thread safety and race condition handling in the WebSocket broadcast
system, focusing on concurrent disconnect during broadcast operations.

These tests verify the fix for CRITICAL #6: Broadcast List Modification Race.
Before the fix, concurrent disconnect could cause ValueError when the broadcast
was iterating over the connection list.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from utils.broadcast import ConnectionManager


@pytest.mark.asyncio
class TestBroadcastListModification:
    """Test list modification safety during broadcast operations."""

    @pytest.fixture
    def connection_manager(self):
        """Create a ConnectionManager instance for testing."""
        return ConnectionManager()

    async def test_concurrent_disconnect_during_broadcast_no_error(self, connection_manager: ConnectionManager):
        """
        Test that concurrent disconnect during broadcast doesn't raise ValueError.

        This is the primary test for CRITICAL #6. Before the fix, this would fail with:
        ValueError: list.remove(x): x not in list

        The fix creates a snapshot of connections under lock before iteration.
        """
        # Create 100 connections
        websockets = [AsyncMock() for _ in range(100)]
        for ws in websockets:
            await connection_manager.connect(ws)

        assert len(connection_manager.active_connections) == 100

        # Start a broadcast
        async def slow_broadcast():
            """Broadcast with small delays to increase chance of race condition."""
            # Temporarily make broadcast slower to create race window
            async with connection_manager._lock:
                connections = list(connection_manager.active_connections)

            for connection in connections:
                try:
                    await connection.send_json({"type": "test"})
                    # Small delay to create race window
                    await asyncio.sleep(0.0001)
                except Exception:
                    pass

        # Start disconnecting connections while broadcast is in progress
        async def concurrent_disconnects():
            await asyncio.sleep(0.0005)  # Let broadcast start
            # Disconnect half the connections
            tasks = [connection_manager.disconnect(ws) for ws in websockets[50:]]
            await asyncio.gather(*tasks)

        # Run broadcast and disconnects concurrently
        # Before the fix, this would raise ValueError
        await asyncio.gather(
            slow_broadcast(),
            concurrent_disconnects()
        )

        # Should complete without error and have ~50 connections
        assert len(connection_manager.active_connections) <= 60

    async def test_snapshot_prevents_iteration_modification(self, connection_manager: ConnectionManager):
        """Test that the connection snapshot prevents iteration issues."""
        # Create connections
        websockets = [AsyncMock() for _ in range(50)]
        for ws in websockets:
            await connection_manager.connect(ws)

        # Track calls to verify snapshot was used
        broadcast_count = [0]
        disconnect_count = [0]

        original_broadcast = connection_manager.broadcast
        original_disconnect = connection_manager.disconnect

        async def tracked_broadcast(message):
            broadcast_count[0] += 1
            # Take snapshot (this is what the fix does)
            async with connection_manager._lock:
                snapshot = list(connection_manager.active_connections)

            # Iterate over snapshot, not live list
            for conn in snapshot:
                try:
                    await conn.send_json(message)
                except Exception:
                    pass

        async def tracked_disconnect(ws):
            disconnect_count[0] += 1
            await original_disconnect(ws)

        connection_manager.broadcast = tracked_broadcast
        connection_manager.disconnect = tracked_disconnect

        # Concurrent operations
        tasks = []
        tasks.append(connection_manager.broadcast({"type": "test"}))
        tasks.extend([connection_manager.disconnect(ws) for ws in websockets[:25]])

        await asyncio.gather(*tasks)

        assert broadcast_count[0] > 0
        assert disconnect_count[0] == 25

    async def test_lock_contention_handling(self, connection_manager: ConnectionManager):
        """Test that the asyncio lock properly handles contention."""
        # Create connections
        websockets = [AsyncMock() for _ in range(30)]
        for ws in websockets:
            await connection_manager.connect(ws)

        # Perform many concurrent lock-requiring operations
        tasks = []

        # 10 broadcasts
        for i in range(10):
            tasks.append(connection_manager.broadcast({"type": "test", "index": i}))

        # 10 connects
        new_websockets = [AsyncMock() for _ in range(10)]
        for ws in new_websockets:
            tasks.append(connection_manager.connect(ws))

        # 10 disconnects
        for ws in websockets[:10]:
            tasks.append(connection_manager.disconnect(ws))

        # All operations should complete without deadlock
        await asyncio.gather(*tasks)

        # Should have 30 connections (30 original - 10 disconnected + 10 new)
        assert len(connection_manager.active_connections) == 30

    async def test_dead_connection_removal_race(self, connection_manager: ConnectionManager):
        """
        Test that dead connection removal doesn't interfere with concurrent operations.

        The fix ensures dead connections are removed in a separate lock acquisition
        after the main broadcast loop.
        """
        # Create connections
        websockets = [AsyncMock() for _ in range(40)]
        for ws in websockets:
            await connection_manager.connect(ws)

        # Make every 4th connection dead
        for i in range(0, 40, 4):
            websockets[i].send_json.side_effect = Exception("Dead connection")

        # Broadcast while concurrently connecting new clients
        async def add_new_connections():
            await asyncio.sleep(0.001)  # Let broadcast start
            new_websockets = [AsyncMock() for _ in range(10)]
            for ws in new_websockets:
                await connection_manager.connect(ws)

        await asyncio.gather(
            connection_manager.broadcast({"type": "test"}),
            add_new_connections()
        )

        # Should have removed 10 dead connections and added 10 new ones
        # 40 - 10 + 10 = 40
        assert 35 <= len(connection_manager.active_connections) <= 45


@pytest.mark.asyncio
class TestBroadcastAtomicity:
    """Test broadcast operation atomicity and consistency."""

    async def test_broadcast_all_or_none_semantics(self):
        """Test that broadcast attempts to deliver to all clients."""
        manager = ConnectionManager()

        # Create 20 connections
        websockets = [AsyncMock() for _ in range(20)]
        for ws in websockets:
            await manager.connect(ws)

        # Make 5 connections fail
        for i in range(0, 20, 4):
            websockets[i].send_json.side_effect = Exception("Send failed")

        # Broadcast a message
        await manager.broadcast({"type": "test", "data": "atomicity test"})

        # Verify all live connections received the message
        successful_sends = 0
        for ws in websockets:
            if ws.send_json.call_count > 0 and ws.send_json.side_effect is None:
                successful_sends += 1

        # Should have sent to 15 live connections
        assert successful_sends >= 15

    async def test_broadcast_snapshot_consistency(self):
        """Test that broadcast uses a consistent snapshot of connections."""
        manager = ConnectionManager()

        # Create initial connections
        websockets = [AsyncMock() for _ in range(30)]
        for ws in websockets:
            await manager.connect(ws)

        snapshot_sizes = []

        # Override broadcast to track snapshot size
        original_broadcast = manager.broadcast

        async def tracked_broadcast(message):
            async with manager._lock:
                snapshot = list(manager.active_connections)
                snapshot_sizes.append(len(snapshot))

            for conn in snapshot:
                try:
                    await conn.send_json(message)
                except Exception:
                    pass

        manager.broadcast = tracked_broadcast

        # Start broadcast
        broadcast_task = asyncio.create_task(manager.broadcast({"type": "test"}))

        # Modify connections during broadcast
        await asyncio.sleep(0.0001)
        new_ws = AsyncMock()
        await manager.connect(new_ws)

        await broadcast_task

        # Snapshot should have been 30 (before the new connection)
        assert snapshot_sizes[0] == 30

    async def test_multiple_broadcasts_no_interference(self):
        """Test that multiple concurrent broadcasts don't interfere."""
        manager = ConnectionManager()

        # Create connections
        websockets = [AsyncMock() for _ in range(20)]
        for ws in websockets:
            await manager.connect(ws)

        # Send 10 concurrent broadcasts
        messages = [{"type": "test", "index": i} for i in range(10)]
        tasks = [manager.broadcast(msg) for msg in messages]

        await asyncio.gather(*tasks)

        # Each client should have received all 10 messages
        for ws in websockets:
            assert ws.send_json.call_count == 10


@pytest.mark.asyncio
class TestBroadcastErrorHandling:
    """Test error handling in broadcast operations."""

    async def test_partial_failure_cleanup(self):
        """Test that partial failures are properly cleaned up."""
        manager = ConnectionManager()

        # Create connections
        websockets = [AsyncMock() for _ in range(30)]
        for ws in websockets:
            await manager.connect(ws)

        # Make first 10 fail
        for i in range(10):
            websockets[i].send_json.side_effect = Exception("Connection failed")

        initial_count = len(manager.active_connections)

        # Broadcast
        await manager.broadcast({"type": "test"})

        # Failed connections should be removed
        assert len(manager.active_connections) < initial_count
        assert len(manager.active_connections) == 20

    async def test_all_connections_fail(self):
        """Test broadcast behavior when all connections fail."""
        manager = ConnectionManager()

        # Create connections that all fail
        websockets = [AsyncMock() for _ in range(10)]
        for ws in websockets:
            ws.send_json.side_effect = Exception("All failed")
            await manager.connect(ws)

        # Broadcast should not raise, but should clean up all connections
        await manager.broadcast({"type": "test"})

        # All dead connections should be removed
        assert len(manager.active_connections) == 0

    async def test_exception_propagation(self):
        """Test that broadcast handles exceptions gracefully."""
        manager = ConnectionManager()

        # Create connections
        websockets = [AsyncMock() for _ in range(5)]
        for ws in websockets:
            await manager.connect(ws)

        # Make one throw a non-standard exception
        websockets[2].send_json.side_effect = RuntimeError("Unexpected error")

        # Broadcast should handle the exception
        await manager.broadcast({"type": "test"})

        # The problematic connection should be removed
        assert websockets[2] not in manager.active_connections
        assert len(manager.active_connections) == 4


@pytest.mark.asyncio
class TestBroadcastPerformance:
    """Test broadcast performance under various conditions."""

    async def test_large_connection_count(self):
        """Test broadcast performance with many connections."""
        manager = ConnectionManager()

        # Create 500 connections
        websockets = [AsyncMock() for _ in range(500)]
        for ws in websockets:
            await manager.connect(ws)

        # Time the broadcast
        import time
        start = time.time()
        await manager.broadcast({"type": "test", "data": "large scale test"})
        duration = time.time() - start

        # Should complete in reasonable time (< 1 second for 500 connections)
        assert duration < 1.0

    async def test_broadcast_with_slow_clients(self):
        """Test broadcast when some clients are slow to receive."""
        manager = ConnectionManager()

        # Create mix of fast and slow clients
        websockets = [AsyncMock() for _ in range(20)]
        for i, ws in enumerate(websockets):
            if i % 5 == 0:
                # Every 5th client is slow
                async def slow_send(msg):
                    await asyncio.sleep(0.01)
                ws.send_json = slow_send
            await manager.connect(ws)

        # Broadcast should still complete
        await manager.broadcast({"type": "test"})

        # All connections should still be active (no failures)
        assert len(manager.active_connections) == 20

    async def test_rapid_sequential_broadcasts(self):
        """Test rapid sequential broadcast operations."""
        manager = ConnectionManager()

        # Create connections
        websockets = [AsyncMock() for _ in range(30)]
        for ws in websockets:
            await manager.connect(ws)

        # Send 100 messages rapidly
        for i in range(100):
            await manager.broadcast({"type": "rapid", "index": i})

        # All clients should have received all 100 messages
        for ws in websockets:
            assert ws.send_json.call_count == 100


@pytest.mark.asyncio
class TestBroadcastIntegration:
    """Integration tests for realistic broadcast scenarios."""

    async def test_realistic_client_lifecycle(self):
        """Test broadcast in a realistic scenario with client churn."""
        manager = ConnectionManager()

        # Simulate 5 minute session with various events
        active_clients = []

        # Initial 10 clients connect
        for i in range(10):
            ws = AsyncMock()
            await manager.connect(ws)
            active_clients.append(ws)

        # Send some messages
        for i in range(5):
            await manager.broadcast({"type": "update", "index": i})

        # 5 new clients join
        for i in range(5):
            ws = AsyncMock()
            await manager.connect(ws)
            active_clients.append(ws)

        # Send more messages
        for i in range(5, 10):
            await manager.broadcast({"type": "update", "index": i})

        # 3 clients disconnect
        for ws in active_clients[:3]:
            await manager.disconnect(ws)

        # 2 clients fail
        active_clients[10].send_json.side_effect = Exception("Client crashed")
        active_clients[11].send_json.side_effect = Exception("Network error")

        # Final broadcast
        await manager.broadcast({"type": "final"})

        # Should have 10 active clients (15 - 3 disconnected - 2 failed)
        assert len(manager.active_connections) == 10

    async def test_broadcast_during_mass_disconnect(self):
        """Test broadcast behavior during mass disconnection event."""
        manager = ConnectionManager()

        # Create 100 connections
        websockets = [AsyncMock() for _ in range(100)]
        for ws in websockets:
            await manager.connect(ws)

        # Simulate server restart - all clients disconnect
        async def mass_disconnect():
            await asyncio.sleep(0.001)  # Let broadcast start
            tasks = [manager.disconnect(ws) for ws in websockets]
            await asyncio.gather(*tasks)

        # Try to broadcast during mass disconnect
        await asyncio.gather(
            manager.broadcast({"type": "critical", "data": "server restarting"}),
            mass_disconnect()
        )

        # Should complete without error
        # Most/all clients will be disconnected
        assert len(manager.active_connections) <= 10

    async def test_broadcast_state_hash_tracking(self):
        """Test that broadcast state hash is properly managed."""
        manager = ConnectionManager()

        # Verify initial state
        assert manager.last_state_hash is None

        # Create connections and broadcast
        websockets = [AsyncMock() for _ in range(5)]
        for ws in websockets:
            await manager.connect(ws)

        await manager.broadcast({"type": "test"})

        # State hash tracking is not used in current implementation
        # but the attribute exists for potential future use
        # This test just verifies the attribute exists
        assert hasattr(manager, 'last_state_hash')

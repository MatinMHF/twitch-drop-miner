"""Tests for SingleAccountWorker._run_wrapper automatic recovery and exponential backoff."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.engine.miner_worker import SingleAccountWorker


@pytest.mark.asyncio
async def test_run_wrapper_recovers_and_retries_on_transient_exception():
    """Verify _run_wrapper catches exceptions, sets error_message, sleeps backoff, and restarts."""
    on_change_called = 0

    async def on_change():
        nonlocal on_change_called
        on_change_called += 1

    worker = SingleAccountWorker(
        account_id="acc1",
        twitch_user_id="12345",
        twitch_username="test_user",
        on_change_cb=on_change,
    )
    worker.is_running = True

    # Configure small backoff for test speed
    worker.INITIAL_RETRY_DELAY = 0.05
    worker.MAX_RETRY_DELAY = 0.2

    mock_twitch = MagicMock()
    run_calls = 0

    async def mock_run():
        nonlocal run_calls
        run_calls += 1
        if run_calls == 1:
            raise RuntimeError("Transient network/GQL glitch")
        elif run_calls == 2:
            # Succeeded on 2nd attempt, stop running so loop terminates
            worker.is_running = False
            return

    mock_twitch.run = AsyncMock(side_effect=mock_run)
    mock_twitch._session = None
    worker.twitch = mock_twitch

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        mock_sleep.return_value = None
        await worker._run_wrapper()

        # Should have called run twice
        assert run_calls == 2
        # Error message was captured from the first crash
        assert worker.error_message == "Transient network/GQL glitch"
        # Backoff sleep was called with INITIAL_RETRY_DELAY
        mock_sleep.assert_called_with(worker.INITIAL_RETRY_DELAY)
        # on_change_cb was notified
        assert on_change_called >= 1


@pytest.mark.asyncio
async def test_run_wrapper_exponential_backoff_progression():
    """Verify retry delay doubles on repeated failures up to MAX_RETRY_DELAY."""
    worker = SingleAccountWorker(
        account_id="acc1",
        twitch_user_id="12345",
        twitch_username="test_user",
        on_change_cb=AsyncMock(),
    )
    worker.is_running = True
    worker.INITIAL_RETRY_DELAY = 1.0
    worker.MAX_RETRY_DELAY = 4.0

    mock_twitch = MagicMock()
    attempts = 0

    async def mock_run():
        nonlocal attempts
        attempts += 1
        if attempts >= 4:
            worker.is_running = False
        raise RuntimeError(f"Error {attempts}")

    mock_twitch.run = AsyncMock(side_effect=mock_run)
    mock_twitch._session = None
    worker.twitch = mock_twitch

    sleep_delays = []

    async def fake_sleep(delay):
        sleep_delays.append(delay)
        return None

    with patch("asyncio.sleep", side_effect=fake_sleep):
        await worker._run_wrapper()

    assert attempts == 4
    # Expected backoff delays: 1.0, 2.0, 4.0 (capped at MAX_RETRY_DELAY)
    assert sleep_delays == [1.0, 2.0, 4.0]


@pytest.mark.asyncio
async def test_run_wrapper_stops_cleanly_on_cancellation():
    """Verify _run_wrapper exits cleanly without uncaught exception when cancelled."""
    worker = SingleAccountWorker(
        account_id="acc1",
        twitch_user_id="12345",
        twitch_username="test_user",
        on_change_cb=AsyncMock(),
    )
    worker.is_running = True

    mock_twitch = MagicMock()
    mock_twitch.run = AsyncMock(side_effect=asyncio.CancelledError)
    mock_twitch._session = None
    worker.twitch = mock_twitch

    # Should not raise CancelledError or any other exception
    await worker._run_wrapper()


@pytest.mark.asyncio
async def test_run_wrapper_clean_exit_does_not_retry():
    """Verify clean exit of twitch.run (no exception) does not retry."""
    worker = SingleAccountWorker(
        account_id="acc1",
        twitch_user_id="12345",
        twitch_username="test_user",
        on_change_cb=AsyncMock(),
    )
    worker.is_running = True

    mock_twitch = MagicMock()
    mock_twitch.run = AsyncMock(return_value=None)
    mock_twitch._session = None
    worker.twitch = mock_twitch

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await worker._run_wrapper()
        assert mock_twitch.run.call_count == 1
        mock_sleep.assert_not_called()

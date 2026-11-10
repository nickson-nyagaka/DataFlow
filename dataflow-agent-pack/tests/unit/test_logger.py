"""Unit test for identifier-scrubbing logger (Phase 1)."""

import io
import logging

from utils.logger import IdentifierScrubbingFilter


def test_100_planted_uic_strings_never_logged():
    """Generates 100 diverse planted UIC strings and tests that zero appear in logs."""
    # Generate 100 varied UIC and identifier strings
    planted_uics = [f"FSW{1000 + i}" for i in range(25)]
    planted_uics += [f"MSM/2024/{i:03d}" for i in range(25)]
    planted_uics += [f"KSM-PWID-{i:04d}" for i in range(25)]
    planted_uics += [f"2024{100000 + i}" for i in range(25)]  # 10-digit CCC numbers

    assert len(planted_uics) == 100

    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    handler.addFilter(IdentifierScrubbingFilter())

    test_logger = logging.getLogger("test_scrubbing_logger")
    test_logger.setLevel(logging.DEBUG)
    test_logger.handlers = [handler]
    test_logger.addFilter(IdentifierScrubbingFilter())

    # Log every single planted identifier in messages, args, and exceptions
    for idx, uic in enumerate(planted_uics):
        if idx % 3 == 0:
            test_logger.info(f"Processing client with UIC: {uic}")
        elif idx % 3 == 1:
            test_logger.warning("Client exception for record", extra={"client_uic": uic})
            test_logger.error("Failed record: %s", uic)
        else:
            try:
                raise ValueError(f"Encountered error for identifier {uic}")
            except ValueError:
                test_logger.exception("Caught error during processing")

    captured_output = log_stream.getvalue()

    # Assert that none of the 100 planted identifiers exist in the output
    found_leaks = [uic for uic in planted_uics if uic in captured_output]
    assert len(found_leaks) == 0, f"Privacy leak! Found un-scrubbed identifiers: {found_leaks}"
    assert "[REDACTED_" in captured_output

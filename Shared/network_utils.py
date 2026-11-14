# -*- coding: utf-8 -*-
# Shared/network_utils.py
"""
Network Optimization Utilities & IPv4 Stack Prioritizer.

This module optimizes Python's network resolution layer on Windows systems. On certain
networks or ISPs, IPv6 DNS queries are returned even when end-to-end IPv6 routing is
non-functional, causing 2-30 second TCP timeout stalls when contacting external APIs.
This module eliminates those stalls by prioritizing IPv4 addresses.

Key Responsibilities:
    • IPv4 Socket Resolution: Intercepts `socket.getaddrinfo` calls to prioritize
      `socket.AF_INET` (IPv4) records over `socket.AF_INET6`.
    • API Speed Optimization: Ensures instantaneous network handshakes for external web
      services utilized by the application, including:
        - Yahoo Finance (`yfinance`) market quote lookups.
        - Google Gemini AI API endpoints (`StockMan.ai_analyzer`).
        - Google Drive API file synchronization (`Shared.google_drive_sync`).

Key Functions:
    • `optimize_network_resolution()`: Patches `socket.getaddrinfo` with an IPv4-first
      resolution wrapper if not already applied.
"""

import socket
import logging

logger = logging.getLogger("StockMan.Network")

_IPV4_PRIORITY_INSTALLED = False
_ORIGINAL_GETADDRINFO = socket.getaddrinfo


def enable_ipv4_priority() -> bool:
    """
    Optimizes socket.getaddrinfo to sort IPv4 ahead of IPv6.

    This eliminates 20-30s per-endpoint connection timeouts on Windows systems
    where IPv6 is enabled in adapters but not routed to internet by ISP.
    IPv6 addresses remain in the list as a seamless fallback.
    """
    global _IPV4_PRIORITY_INSTALLED

    if _IPV4_PRIORITY_INSTALLED:
        return True

    def _ipv4_first_getaddrinfo(
        host, port, family=0, type=0, proto=0, flags=0
    ):
        results = _ORIGINAL_GETADDRINFO(
            host, port, family, type, proto, flags
        )
        # When family is AF_UNSPEC (0), sort AF_INET (IPv4) ahead of AF_INET6
        if family == 0 and results:
            return sorted(
                results,
                key=lambda res: 0 if res[0] == socket.AF_INET else 1,
            )
        return results

    try:
        socket.getaddrinfo = _ipv4_first_getaddrinfo
        _IPV4_PRIORITY_INSTALLED = True
        logger.info("IPv4 priority network adapter installed successfully.")
        return True
    except Exception as e:
        logger.warning(
            f"Failed to install IPv4 priority network adapter: {e}"
        )
        return False

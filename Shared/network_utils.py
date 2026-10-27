# -*- coding: utf-8 -*-
# Shared/network_utils.py
"""
Network optimization utilities for fast DNS resolution and IPv4 prioritization.
Prevents Windows TCP timeout stalls on IPv6 when ISPs lack IPv6 routing.
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

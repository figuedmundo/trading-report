"""Channels package for notification service."""

from src.channels.base import Channel
from src.channels.factory import ChannelFactory

__all__ = ["Channel", "ChannelFactory"]

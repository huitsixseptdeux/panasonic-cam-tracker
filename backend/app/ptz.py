from __future__ import annotations

import abc


class PTZController(abc.ABC):
    """Interface for optional physical PTZ hardware control.

    Not implemented: no PTZ camera with a documented, testable protocol was
    available during this build (see START.md guardrails — hardware control
    is only added after confirming a camera's documented protocol and testing
    safely). This interface exists so an ONVIF or vendor-SDK adapter can be
    dropped in later without touching the pipeline or UI.
    """

    @abc.abstractmethod
    def pan(self, dx: float) -> None:
        ...

    @abc.abstractmethod
    def tilt(self, dy: float) -> None:
        ...

    @abc.abstractmethod
    def zoom(self, dz: float) -> None:
        ...

    @abc.abstractmethod
    def get_capabilities(self) -> dict:
        ...


class NullPTZController(PTZController):
    """No-op implementation used when no physical PTZ adapter is configured."""

    def pan(self, dx: float) -> None:
        return None

    def tilt(self, dy: float) -> None:
        return None

    def zoom(self, dz: float) -> None:
        return None

    def get_capabilities(self) -> dict:
        return {"available": False, "reason": "no PTZ adapter configured"}

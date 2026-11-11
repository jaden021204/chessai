import time


TIME_CONTROLS = {
    "5": (300, 0),
    "5+5": (300, 5),
    "10": (600, 0),
    "10+5": (600, 5),
}


class GameClock:
    def __init__(self, control):
        seconds, self.increment = TIME_CONTROLS[control]
        self.control = control
        self.remaining = {"r": float(seconds), "b": float(seconds)}
        self.active = None
        self.last = None

    def start(self, side, now=None):
        self.active = side
        self.last = time.monotonic() if now is None else now

    def tick(self, now=None):
        if self.active is None:
            return None
        now = time.monotonic() if now is None else now
        elapsed = max(0, now - self.last)
        self.last = now
        self.remaining[self.active] = max(0, self.remaining[self.active] - elapsed)
        if self.remaining[self.active] == 0:
            expired = self.active
            self.active = None
            return expired
        return None

    def complete_move(self, now=None):
        expired = self.tick(now)
        if expired:
            return expired
        side = self.active
        self.remaining[side] += self.increment
        self.active = "b" if side == "r" else "r"
        return None

    def stop(self):
        self.active = None

    def snapshot(self):
        return {"control": self.control, "remaining": self.remaining.copy(),
                "active": self.active, "increment": self.increment}

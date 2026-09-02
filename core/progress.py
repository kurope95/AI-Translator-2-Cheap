import threading


class TranslationProgress:
    """Tracks translation progress for SSE streaming."""

    def __init__(self):
        self.lock = threading.RLock()
        self.total_steps = 0
        self.completed_steps = 0
        self.current_phase = "Preparing..."
        self.is_cancelled = False

    def set_total(self, total: int):
        with self.lock:
            self.total_steps = total

    def reset(self):
        with self.lock:
            self.total_steps = 0
            self.completed_steps = 0
            self.current_phase = "Preparing..."

    def advance(self, phase: str = ""):
        with self.lock:
            self.completed_steps += 1
            if phase:
                self.current_phase = phase

    def set_phase(self, phase: str):
        with self.lock:
            self.current_phase = phase

    @property
    def percent(self) -> int:
        with self.lock:
            if self.total_steps == 0:
                return 0
            return min(100, int(self.completed_steps / self.total_steps * 100))

    def to_dict(self) -> dict:
        with self.lock:
            return {
                "percent": self.percent,
                "completed": self.completed_steps,
                "total": self.total_steps,
                "phase": self.current_phase,
            }

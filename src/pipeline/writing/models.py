from dataclasses import dataclass

@dataclass(frozen=True)
class HookCandidate:
    text: str
    score: float

@dataclass(frozen=True)
class ScriptCandidate:
    text: str
    score: float
    hook: str

"""Signal fusion: join app + Garmin + engine into a daily readiness read.

The package is split so the *brain* stays explainable and unit-testable:

* :mod:`app.fusion.baselines` — pure rolling statistics (mean/std, z-score).
* :mod:`app.fusion.rules` — pure rules over already-fetched data; each returns a
  :class:`~app.fusion.signals.Signal`. No IO, so every rule is trivially testable.
* :mod:`app.fusion.readiness` — pure composite score, top signals and the
  recommendation.
* :mod:`app.fusion.service` — the only async/IO layer: it fetches everything
  (DB + :class:`~app.engines.port.EnginePort`), runs the rules and assembles the
  :class:`~app.fusion.readiness.DailyRead`.

The anchor product signal is the *divergence subjective↔objective*: how the
athlete feels versus what the engine's form says. Injury output is always a
nudge to *consult a physio*, never a diagnosis.
"""

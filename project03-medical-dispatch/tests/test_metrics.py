import json
from pathlib import Path
from dispatch.metrics import summarize


def test_hand_derived_queue_and_objective():
    root=Path(__file__).parents[1]/'fixtures'
    s=json.loads((root/'hand_four.json').read_text())
    a=json.loads((root/'hand_four_schedule.json').read_text())
    m=summarize(s,a)
    assert m['objective']==2
    assert m['charging_wait_minutes']==2
    assert m['max_charging_wait_minutes']==2
    assert m['charging_queue_peak']==1
    assert m['unrecharged_returns']==2
    assert m['censored_dirty_minutes']==2
    assert m['vehicle_utilization']==.5
    assert m['charger_utilization']==.5
    assert m['technician_utilization']==.5

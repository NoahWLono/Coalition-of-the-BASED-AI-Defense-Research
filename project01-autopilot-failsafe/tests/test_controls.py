import unittest
try:
 from failsafelab.controls import control_accepted
except ImportError:control_accepted=None

def case(gap='PASS',mode='FAIL',disarmed='FAIL',mode_values=(4,),armed=True):
 return {'outcome':'FAIL','checks':[{'outcome':'PASS'}],'assertions':[{'type':'heartbeat_gap','outcome':gap},{'type':'text','outcome':'INDETERMINATE'},{'type':'mode','outcome':mode,'observations':[{'mode':m,'armed':armed} for m in mode_values]},{'type':'disarmed','outcome':disarmed,'observations':[{'mode':4,'armed':armed}]}]}
class Controls(unittest.TestCase):
 def test_missing_injection_does_not_count_as_detection(self):
  self.assertIsNotNone(control_accepted)
  self.assertFalse(control_accepted(case(gap='FAIL',mode='PASS',disarmed='PASS',mode_values=(9,),armed=False),'disabled'))
 def test_disabled_requires_guided_armed_and_verified_silence(self):
  self.assertIsNotNone(control_accepted)
  self.assertTrue(control_accepted(case(),'disabled'))
  self.assertFalse(control_accepted(case(mode_values=(2,)),'disabled'))
  self.assertFalse(control_accepted(case(gap='INDETERMINATE'),'disabled'))
 def test_replay_requires_only_targeted_mode_mismatch(self):
  self.assertIsNotNone(control_accepted)
  r=case(disarmed='PASS',mode_values=(4,9));r['assertions'][1]['outcome']='PASS'
  self.assertTrue(control_accepted(r,'wrong-mode'))
  r['assertions'][0]['outcome']='FAIL'
  self.assertFalse(control_accepted(r,'wrong-mode'))
if __name__=='__main__':unittest.main()

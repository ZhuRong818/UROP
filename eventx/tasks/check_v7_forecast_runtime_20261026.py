"""Synthetic runtime integrity tests; never reads prospective labels."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import joblib
from eventx.v7.forecast_runtime_20261026 import *
from eventx.tasks.evaluate_v7_frozen_classifier_20261026 import validate_emissions

class RuntimeChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples=[json.loads(l) for l in (OLDREL/'live_cohort.jsonl').read_text().splitlines()]
        cls.cid=cls.samples[0]['market_id'];cls.bundle=joblib.load(MODEL)
        original=read_chain(OLD/'readiness/journal.jsonl')[0]
        cls.probe=next(r for r in original if r['kind']=='clock_probe' and packet_clock_health([r],r['available_epoch'])[0])
        cls.t=1793005200  # synthetic grid; no live target
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);(self.root/'objects').mkdir();self.j=Journal(self.root/'journal.jsonl')
    def tearDown(self): self.temp.cleanup()
    def add(self,kind,at,**v): return self.j.append({'kind':kind,'at':iso(at),**v})
    def payload(self,p):
        b=json.dumps(p).encode();h=hashlib.sha256(b).hexdigest();(self.root/'objects'/h).write_bytes(b);return h
    def quote(self,at,bid='.40',ask='.42',available=None):
        available=at+.01 if available is None else available
        p={'event_type':'price_change','market':self.cid,'timestamp':str(int(at*1000)),'price_changes':[{'asset_id':self.samples[0]['yes_asset_id'],'best_bid':bid,'best_ask':ask}]}
        return self.add('ws_frame',available,response_received_at=iso(available-.001),available_at=iso(available),payload_sha256=self.payload(p))
    def metadata(self,at,ok=True):
        s=self.samples[0]
        p=[{'conditionId':self.cid,'clobTokenIds':[s['yes_asset_id'],s['no_asset_id']],'outcomes':['Yes','No'],'description':s['rules'],'acceptingOrders':ok,'closed':False,'active':True,'endDate':iso(self.t+10000)}]
        self.add('rest',at,market_id=self.cid,endpoint_kind='market_metadata',source='venue',status='observed',available_at=iso(at),payload_sha256=self.payload(p))
        p={'data':[{'condition_id':self.cid,'status':'posed','resolved_at':None,'was_disputed':False}]}
        self.add('rest',at,market_id=self.cid,endpoint_kind='resolution_state',source='venue',status='observed',available_at=iso(at),payload_sha256=self.payload(p))
    def setup_valid(self):
        t=self.t;self.add('ws_connected',t-1900)
        for x in range(t-1890,t+1801,10): self.add('ws_pong',x)
        for x in range(t-300,t+1801,300):
            p=copy.deepcopy(self.probe);p.pop('record_sha256');p.pop('previous_sha256');p.update(at=iso(x),available_epoch=x)
            self.j.append(p);self.metadata(x)
        self.quote(t-1);self.quote(t+1799,'.41','.43')
        return Inputs(self.root,self.samples)
    def test_valid_current(self):
        inp=self.setup_valid();f,r=inp.current(self.cid,self.t);self.assertFalse(r);self.assertEqual(len(f),14);self.assertAlmostEqual(f[0],.41)
    def test_endpoint_changed(self):
        inp=self.setup_valid();v,r=inp.endpoint(self.cid,self.t);self.assertFalse(r);self.assertAlmostEqual(v,.42)
    def test_endpoint_late_quote_cannot_repair(self):
        inp=self.setup_valid();self.quote(self.t+1800,'.49','.51',self.t+1801);inp.refresh();self.assertAlmostEqual(inp.endpoint(self.cid,self.t)[0],.42)
    def test_future_observations_do_not_change_inputs(self):
        inp=self.setup_valid();before=inp.current(self.cid,self.t);self.quote(self.t+10,'.60','.62');inp.refresh();self.assertEqual(inp.current(self.cid,self.t),before)
    def test_missing_endpoint_is_unknown(self):
        inp=self.setup_valid();inp.tapes[self.cid]=SourceTimeQuoteTape([r for r in inp.by[self.cid] if r['timestamp'].timestamp()<self.t]);self.assertIsNone(inp.endpoint(self.cid,self.t)[0])
    def test_status_invalid_mid_horizon(self):
        inp=self.setup_valid();self.metadata(self.t+650,False);inp.refresh();self.assertIsNone(inp.endpoint(self.cid,self.t)[0])
    def test_status_gap(self):
        inp=self.setup_valid();k=(self.cid,'resolution_state');keep=[r for r in inp.status.series[k] if not self.t+1<r['at']<self.t+1000];inp.status.series[k]=keep;inp.status.times[k]=[r['at'] for r in keep];self.assertIsNone(inp.endpoint(self.cid,self.t)[0])
    def test_disconnect_endpoint(self):
        inp=self.setup_valid();self.add('ws_disconnected',self.t+1799);inp.refresh();self.assertIsNone(inp.endpoint(self.cid,self.t)[0])
    def test_clockstep_resets_warmup(self):
        inp=self.setup_valid();self.add('operational_cycle_gap',self.t-5,reason='clock_step_over20ms');inp.refresh();self.assertIsNone(inp.current(self.cid,self.t)[0])
    def test_invalid_packet_excluded(self):
        p=copy.deepcopy(self.probe)
        for m in p['measurements']: m['raw']='selected: invalid'
        self.assertFalse(packet_clock_health([p],p['available_epoch'])[0])
    def test_latest_bad_probe_no_fallback(self):
        p=copy.deepcopy(self.probe);p['available_epoch']+=1;p['measurements']=[]
        self.assertFalse(packet_clock_health([self.probe,p],p['available_epoch'])[0])
    def test_expired_probe(self): self.assertFalse(packet_clock_health([self.probe],self.probe['available_epoch']+361)[0])
    def test_future_probe(self): self.assertFalse(packet_clock_health([self.probe],self.probe['available_epoch']-1)[0])
    def test_decision_deadline(self):
        inp=self.setup_valid();r=decision(inp,self.bundle,self.cid,self.t,self.t+30.001);self.assertEqual(r['status'],'missed');self.assertFalse(r['predictions'])
    def test_decision_future(self):
        inp=self.setup_valid()
        with self.assertRaises(ValueError): decision(inp,self.bundle,self.cid,self.t,self.t-1)
    def test_ready_prediction_parity(self):
        inp=self.setup_valid();r=decision(inp,self.bundle,self.cid,self.t,self.t+1);self.assertEqual(r['status'],'ready');self.assertEqual(set(r['predictions']),set(NAMES))
        expected=predict(self.bundle,[{'market_id':self.cid,'features':r['features']}]);self.assertEqual(r['predictions'],{n:float(v[0]) for n,v in expected.items()})
    def test_chain_tampering(self):
        self.add('test',self.t);p=self.j.path;p.write_text(p.read_text().replace('test','bad'))
        with self.assertRaises(RuntimeError): read_chain(p)
    def test_partial_journal_live_only(self):
        self.add('test',self.t);n=self.j.path.stat().st_size
        with self.j.path.open('ab') as f:f.write(b'{')
        self.assertEqual(read_chain(self.j.path,partial=True)[2],n)
        with self.assertRaises(RuntimeError): read_chain(self.j.path)
    def test_prefix_boundaries(self):
        self.add('test',self.t)
        with self.assertRaises(RuntimeError): read_chain(self.j.path,3)
    def test_duplicate_decisions_fail(self):
        r={'kind':'decision','market_id':self.cid,'t':self.t}
        with self.assertRaises(RuntimeError): validate_emissions([r,r],[self.t],[self.cid])
    def test_false_timely_commit_fails(self):
        d={'kind':'decision','market_id':self.cid,'t':self.t,'record_sha256':'x','recorded_at':self.t,'status':'ready'}
        c={'kind':'emission_commit','market_id':self.cid,'t':self.t,'decision_sha256':'x','decision_durable_at':self.t+31,'timely':True}
        with self.assertRaises(RuntimeError): validate_emissions([d,c],[self.t],[self.cid])
    def test_window_exact(self):
        w=window(self.t);gg=grids(w['first_grid'],w['last_grid']);self.assertEqual(len(gg),276*7);self.assertEqual(w['first_grid']%86400,1800);self.assertEqual(w['last_grid']%86400,84300)
    def test_empty_evaluation(self):
        r=evaluate_rows([]);self.assertEqual(r['known'],0);self.assertFalse(r['descriptive_improvement'])
    def test_unknown_bounds_and_matched_scores(self):
        rr=[{'market_id':'x','t':self.t,'target':None,'predictions':{n:.2 if n=='hgb7' else .5 for n in NAMES}}]
        r=evaluate_rows(rr);self.assertEqual(r['known'],0);self.assertEqual(r['unknown'],1);self.assertLess(r['contrasts']['full_logit']['all_issued_gain_bounds'][0],0);self.assertGreater(r['contrasts']['full_logit']['all_issued_gain_bounds'][1],0)
    def test_no_activation(self):
        from eventx.tasks.run_v7_frozen_classifier_20261026 import main
        with patch('eventx.tasks.run_v7_frozen_classifier_20261026.verify_release'),patch('eventx.tasks.run_v7_frozen_classifier_20261026.BASE',self.root):
            with self.assertRaises(FileNotFoundError): main()
        self.assertFalse((self.root/'prospective').exists())

if __name__=='__main__':unittest.main()

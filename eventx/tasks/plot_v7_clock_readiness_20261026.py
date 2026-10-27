"""Standalone research figure from completed clock/input artifacts only."""
import json
from datetime import datetime,timezone
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from eventx.tasks.run_v7_source_time_study_20261026_v03 import BASE

def main():
 report=json.loads((BASE/'clock_repeat_diagnosis.json').read_text());audit=json.loads((BASE/'readiness_audit/report.json').read_text())
 fig,ax=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
 start=datetime.fromisoformat(audit['capture_started_at']).timestamp()
 colors={'time.google.com':'#2463a6','time.cloudflare.com':'#b76617','time.apple.com':'#25856a'}
 for host,color in colors.items():
  xs=[];ys=[];errs=[]
  for r in report['clock_rounds']:
   for m in r['measurements']:
    if m['host']==host and m['offset_seconds'] is not None:
     xs.append((datetime.fromisoformat(r['at']).timestamp()-start)/60);ys.append(1000*m['offset_seconds']);errs.append(1000*m['reported_uncertainty_seconds'])
  ax[0].errorbar(xs,ys,yerr=errs,fmt='o-',markersize=4,lw=1,capsize=2,label=host,color=color,alpha=.85)
 ax[0].axhline(100,color='#a32929',ls='--',lw=1,label='Host offset budget ±100 ms');ax[0].axhline(-100,color='#a32929',ls='--',lw=1)
 ax[0].set(xlabel='Minutes from capture start',ylabel='Server minus local time (ms)',title='Independent clock measurements')
 ax[0].legend(fontsize=8,loc='best');ax[0].grid(alpha=.15)
 labels=['Strict V02','Bounded V03'];counts=[audit['strict_fully_ready_decisions'],audit['fully_ready_decisions']]
 bars=ax[1].bar(labels,counts,color=['#778899','#2463a6'],width=.55)
 total=sum(m['scheduled'] for m in audit['markets']);post=sum(m['transport_ready'] for m in audit['markets'])
 ax[1].bar_label(bars,padding=3);ax[1].set_ylim(0,max(4,max(counts)+1));ax[1].set(ylabel='Fully ready market-decisions',title='Same messages, same operational gates')
 ax[1].text(.5,.95,f'{total} total decisions; {post} transport-ready after warmup',transform=ax[1].transAxes,ha='center',va='top',fontsize=9)
 ax[1].grid(axis='y',alpha=.15);ax[1].set_axisbelow(True)
 fig.suptitle('EventX clock correction: input readiness only',fontsize=14)
 fig.savefig(BASE/'clock_readiness.png',dpi=180);fig.savefig(BASE/'clock_readiness.pdf');plt.close(fig)
 print('Clock readiness figure saved')
if __name__=='__main__':main()

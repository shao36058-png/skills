"""Run the saved HFSS half model with RAM/commit monitoring in the existing desktop.
Does not close AEDT or modify system paging settings. Requires Windows, psutil, and PyAEDT.
"""
import os,sys,json,time,csv,threading,ctypes,math
from ctypes import wintypes
from pathlib import Path
import psutil
from collections import Counter
from ansys.aedt.core import Hfss
ROOT=Path(__file__).resolve().parent
DESIGN=os.environ['HFSS_DESIGN']
PROJECT=os.environ['HFSS_PROJECT']
VERSION=os.environ.get('HFSS_AEDT_VERSION','2025.2')
SETUP=os.environ.get('HFSS_SETUP','Setup1')
BAND_SWEEP=os.environ.get('HFSS_BAND_SWEEP','Band_27p5_28p5')
TE01_EXPRESSION=os.environ.get('HFSS_TE01_EXPRESSION','S(2:4,1:4)')
AEDT_PID=int(os.environ['HFSS_AEDT_PID'])
AEDT_PORT=int(os.environ['HFSS_AEDT_PORT'])
OUT=Path(os.environ['HFSS_RUN_DIR']).resolve()
if OUT.exists() and any(OUT.iterdir()):
    raise RuntimeError('Use an empty output directory; preserve previous run evidence')
OUT.mkdir(parents=True,exist_ok=True)
GIB=1024**3
class Perf(ctypes.Structure):
    _fields_=[('cb',wintypes.DWORD)]+[(k,ctypes.c_size_t) for k in ('CommitTotal','CommitLimit','CommitPeak','PhysicalTotal','PhysicalAvailable','SystemCache','KernelTotal','KernelPaged','KernelNonpaged','PageSize')]+[(k,wintypes.DWORD) for k in ('HandleCount','ProcessCount','ThreadCount')]
def memory():
    p=Perf();p.cb=ctypes.sizeof(p)
    if not ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(p),p.cb): raise ctypes.WinError()
    return dict(available_gib=p.PhysicalAvailable*p.PageSize/GIB,used_gib=(p.PhysicalTotal-p.PhysicalAvailable)*p.PageSize/GIB,commit_gib=p.CommitTotal*p.PageSize/GIB,commit_limit_gib=p.CommitLimit*p.PageSize/GIB,commit_free_gib=(p.CommitLimit-p.CommitTotal)*p.PageSize/GIB)
assert psutil.Process(AEDT_PID).name().lower()=='ansysedt.exe'
assert any(c.status==psutil.CONN_LISTEN and c.laddr.port==AEDT_PORT for c in psutil.Process(AEDT_PID).net_connections(kind='tcp')), 'AEDT gRPC port is not listening; do not launch another session'
h=Hfss(project=PROJECT,design=DESIGN,version=VERSION,port=AEDT_PORT,aedt_process_id=AEDT_PID,new_desktop=False,close_on_exit=False)
assert h.project_name==PROJECT and h.design_name==DESIGN
assert not h.are_there_simulations_running
initial_memory=memory()
if initial_memory['available_gib']<4 or initial_memory['commit_free_gib']<3:
    h.desktop_class.release_desktop(close_projects=False,close_on_exit=False)
    raise RuntimeError('Insufficient initial memory headroom; no simulation submitted')
stop_event=threading.Event();reason=[];started=time.time();solver_seen={}
def request_stop():
    try: h.stop_simulations(clean_stop=False)
    except Exception as e: print('STOP API ERROR',str(e),flush=True)
def guard():
    with (OUT/'memory_log.csv').open('w',newline='',encoding='utf-8') as f:
        writer=None
        while not stop_event.is_set():
            m=memory();solvers=[]
            for p in psutil.Process(AEDT_PID).children(recursive=True):
                try:
                    if p.create_time()>=started-2 and any(x in p.name().lower() for x in ('hf3d','mesher','hfs','ansysmesh')):
                        solver_seen[p.pid]=p.create_time();solvers.append(p)
                except psutil.Error: pass
            rss=0
            for p in solvers:
                try:rss+=p.memory_info().rss
                except psutil.Error:pass
            m.update(elapsed_s=round(time.time()-started,1),solver_rss_gib=rss/GIB,solver_pids=';'.join(str(p.pid) for p in solvers))
            if writer is None: writer=csv.DictWriter(f,fieldnames=list(m));writer.writeheader()
            writer.writerow(m);f.flush()
            (OUT/'memory_status.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
            if not reason and (m['available_gib']<4 or m['commit_free_gib']<3 or (OUT/'STOP_REQUEST').exists()):
                reason.append({'time':time.time(),'message':'memory_guard_or_stop_request','memory':m})
                print('GUARD STOP',json.dumps(reason),flush=True)
                threading.Thread(target=request_stop,daemon=True).start()
            if reason and (m['available_gib']<2 or m['commit_free_gib']<1.5 or time.time()-reason[0]['time']>20):
                for pid,ctime in solver_seen.items():
                    try:
                        p=psutil.Process(pid)
                        if p.create_time()==ctime:
                            p.terminate();print('GUARD terminated solver only',pid,flush=True)
                    except psutil.Error: pass
            stop_event.wait(2)
guard_thread=threading.Thread(target=guard,daemon=True);guard_thread.start()
band_floor=float(os.environ.get('HFSS_STOP_BAND_BELOW','0'))
last_band_read=0
try:
    print('START_MEMORY',json.dumps(memory()),flush=True)
    previous_messages=Counter(h.odesktop.GetMessages(h.project_name,h.design_name,0))
    cores=int(os.environ.get('HFSS_CORES','4'));tasks=int(os.environ.get('HFSS_TASKS','1'))
    print('SOLVER_RESOURCES',json.dumps({'cores':cores,'tasks':tasks}),flush=True)
    ok=h.analyze_setup(SETUP,cores=cores,tasks=tasks,use_auto_settings=False,blocking=False)
    print('SUBMITTED',ok,flush=True)
    if not ok: raise RuntimeError('HFSS failed to submit')
    time.sleep(5)
    while h.are_there_simulations_running:
        print('RUNNING',round(time.time()-started),json.dumps(memory()),flush=True)
        if band_floor and not reason and time.time()-last_band_read>60:
            last_band_read=time.time()
            try:
                # Explicit category avoids querying AnalysisSetup.GetSetups during a running solve.
                d=h.post.get_solution_data_per_variation(solution_type='Modal Solution Data',expressions=[TE01_EXPRESSION],setup_sweep_name=f'{SETUP} : {BAND_SWEEP}',sweeps={'Freq':['All']})
                if d:
                    rows=[{'frequency_GHz':float(f),'TE01_power':float(a*a+b*b)} for f,a,b in zip(d.primary_sweep_values,d.get_expression_data(TE01_EXPRESSION,'real')[1],d.get_expression_data(TE01_EXPRESSION,'imag')[1]) if math.isfinite(float(a*a+b*b))]
                    if rows:
                        worst=min(rows,key=lambda x:x['TE01_power'])
                        (OUT/'live_band_progress.json').write_text(json.dumps({'completed_samples':len(rows),'worst':worst,'points':rows},indent=2),encoding='utf-8')
                        print('BAND_PROGRESS',len(rows),'worst',json.dumps(worst),flush=True)
                        if worst['TE01_power']<band_floor:
                            reason.append({'time':time.time(),'message':'TE01_band_efficiency_failure','threshold':band_floor,'measurement':worst})
                            print('EFFICIENCY STOP',json.dumps(reason),flush=True)
                            threading.Thread(target=request_stop,daemon=True).start()
            except Exception as e:print('LIVE_BAND_READ',str(e),flush=True)
        time.sleep(15)
    time.sleep(5)
    try: h.save_project()
    except Exception:
        h=Hfss(project=PROJECT,design=DESIGN,version=VERSION,port=AEDT_PORT,aedt_process_id=AEDT_PID,new_desktop=False,close_on_exit=False)
        h.save_project()
    msgs=list(h.odesktop.GetMessages(h.project_name,h.design_name,0))
    remaining=previous_messages.copy();new_msgs=[]
    for message in msgs:
        if remaining[message]>0:remaining[message]-=1
        else:new_msgs.append(message)
    errors=[message for message in new_msgs if '[error]' in message.lower()]
    (OUT/'solver_messages.json').write_text(json.dumps(msgs,ensure_ascii=False,indent=2),encoding='utf-8')
    for name,fn in [('convergence',h.export_convergence),('profile',h.export_profile)]:
        try: print('EXPORT',name,fn(SETUP,output_file=str(OUT/(name+'.txt'))),flush=True)
        except Exception as e: print('EXPORT ERROR',name,str(e),flush=True)
    (OUT/'run_status.json').write_text(json.dumps({'finished':True,'successful':not reason and not errors,'elapsed_s':time.time()-started,'guard':reason,'execution_errors':errors,'new_messages':new_msgs,'messages':msgs},ensure_ascii=False,indent=2),encoding='utf-8')
    print('FINISHED',msgs,flush=True)
    if errors and not reason:raise RuntimeError('HFSS execution error; no valid simulation acceptance: '+str(errors))
finally:
    stop_event.set();guard_thread.join(5)
    h.desktop_class.release_desktop(close_projects=False,close_on_exit=False)

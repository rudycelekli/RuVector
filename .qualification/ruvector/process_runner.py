import ctypes,errno,os,signal,subprocess,time
# Linux child subreaper: adopted grandchildren can be reaped after their parent exits.
def enable_subreaper():
 if ctypes.CDLL(None,use_errno=True).prctl(36,1,0,0,0):raise OSError(ctypes.get_errno(),'PR_SET_CHILD_SUBREAPER')
def bounded(args,cwd,seconds):
 p=subprocess.Popen(args,cwd=cwd,start_new_session=True)
 timed_out=False
 try:code=p.wait(timeout=seconds)
 except subprocess.TimeoutExpired:timed_out=True;code=124
 finally:
  # Every child owns this isolated session, including any orphaned compiler/test subprocesses.
  for sig in [signal.SIGTERM,signal.SIGKILL]:
   try:os.killpg(p.pid,sig)
   except ProcessLookupError:pass
   if sig==signal.SIGTERM:
    deadline=time.monotonic()+2
    while time.monotonic()<deadline:
     try:os.killpg(p.pid,0)
     except (ProcessLookupError,PermissionError):break
     time.sleep(.05)
  p.wait()
  deadline=time.monotonic()+5
  while True:
   try:pid,_=os.waitpid(-1,os.WNOHANG)
   except ChildProcessError:break
   if pid==0:
    if time.monotonic()>deadline:raise RuntimeError('Owned descendants remain unreaped; refusing next gate')
    time.sleep(.05)
 return code,timed_out

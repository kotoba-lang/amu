#!/usr/bin/env python3
"""Observe fixed-fixture native driver ownership in a fresh delegated scope.

This is not authenticated release admission or a general container test. Only
cgroups and children created by this observer are modified or removed.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'seed/fune/fixed-fixture-driver.kotoba'
FRAME = b'K\x07\x00\x00\x00\x0bfune-smoke\n'


class Filter(ctypes.Structure):
    _fields_ = [('code',ctypes.c_ushort),('jt',ctypes.c_ubyte),('jf',ctypes.c_ubyte),('k',ctypes.c_uint)]


class Program(ctypes.Structure):
    _fields_ = [('len',ctypes.c_ushort),('filter',ctypes.POINTER(Filter))]


def install(code):
    program=Program(len(code),code);libc=ctypes.CDLL(None,use_errno=True)
    if libc.prctl(38,1,0,0,0) or libc.prctl(22,2,ctypes.byref(program),0,0): os._exit(125)


def deny_seals():
    install((Filter*6)(Filter(0x20,0,0,0),Filter(0x15,0,3,25),Filter(0x20,0,0,24),
                       Filter(0x15,0,1,1033),Filter(0x06,0,0,0x00050001),Filter(0x06,0,0,0x7fff0000)))


def deny_clock():
    install((Filter*4)(Filter(0x20,0,0,0),Filter(0x15,0,1,113),
                       Filter(0x06,0,0,0x00050001),Filter(0x06,0,0,0x7fff0000)))


def deny_execveat():
    install((Filter*4)(Filter(0x20,0,0,0),Filter(0x15,0,1,281),
                       Filter(0x06,0,0,0x00050001),Filter(0x06,0,0,0x7fff0000)))


def deny_close_range():
    install((Filter*4)(Filter(0x20,0,0,0),Filter(0x15,0,1,436),
                       Filter(0x06,0,0,0x00050001),Filter(0x06,0,0,0x7fff0000)))


def build(compiler,out):
    binary=out/'driver.elf';env={'PATH':'/nonexistent','KEXE_ALLOW':'35,37,38,39','KEXE_STACK_BYTES':'8388608',
                                 'KEXE_CAP_RESOURCES_35':f'{ROOT}:{out}'}
    p=subprocess.run([str(compiler),'fune-driver-build','aarch64-linux',str(SOURCE),str(binary)],cwd=out,env=env,capture_output=True,timeout=900)
    assert p.returncode==0 and binary.is_file(),(p.returncode,p.stderr[-1000:]);binary.chmod(0o700)
    changed=out/'altered.kotoba';changed.write_bytes(SOURCE.read_bytes()+b'\n;; changed source\n');wrong=out/'altered.elf'
    p=subprocess.run([str(compiler),'fune-driver-build','aarch64-linux',str(changed),str(wrong)],cwd=out,env=env,capture_output=True,timeout=900)
    assert p.returncode!=0 and not wrong.exists() and b'E6015' in p.stderr
    return binary


def main(binary, supervisor, worker, producer, layout, manifest, max_layout, max_manifest, out, factory_verified):
    assert platform.system()=='Linux' and platform.machine() in ('aarch64','arm64') and os.geteuid()!=0
    cgpath=Path('/proc/self/cgroup').read_text().strip().split('::',1)[1];root=Path('/sys/fs/cgroup')/cgpath.lstrip('/')
    assert len((root/'cgroup.procs').read_text().split())==1
    assert all(x in (root/'cgroup.controllers').read_text().split() for x in ('cpu','memory','pids'))
    observer=root/'fune-native-observer';parent=root/'fune-native-parent';observer.mkdir();parent.mkdir();observations={}
    try:
        (observer/'cgroup.procs').write_text(str(os.getpid()))
        (root/'cgroup.subtree_control').write_text('+cpu +memory +pids')
        (parent/'cgroup.subtree_control').write_text('+cpu +memory +pids')
        fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY);assert fd==3,fd
        try:
            def args(sup=supervisor,work=worker,prod=producer,image=layout,digest=manifest):
                return [str(binary),str(sup),str(work),str(prod),str(image),digest]
            def dirs():return [p for p in parent.iterdir() if p.is_dir()]
            def run(name,argv=None,preexec=None):
                p=subprocess.run(argv or args(),stdin=subprocess.DEVNULL,capture_output=True,pass_fds=(fd,),
                                 env={'PATH':'/nonexistent'},preexec_fn=preexec,timeout=100)
                assert not dirs(),(name,dirs(),p.stderr)
                return p
            p=run('success');assert p.returncode==0 and p.stdout==FRAME and not p.stderr,(p.returncode,p.stdout,p.stderr)
            observations['fixed_oci_stdout_status_and_cleanup']='pass'
            p=run('wrong_manifest',args(digest='sha256:'+'0'*64));assert p.returncode!=0 and not p.stdout
            observations['wrong_manifest']='refused_and_cleaned'
            for name,path in (('supervisor',supervisor),('worker',worker),('producer',producer)):
                bad=out/(name+'-bad.elf');data=bytearray(path.read_bytes());data[-1]^=1;bad.write_bytes(data)
                kw={'sup':supervisor,'work':worker,'prod':producer};kw[{'supervisor':'sup','worker':'work','producer':'prod'}[name]]=bad
                p=run('bad_'+name,args(**kw));assert p.returncode!=0 and not p.stdout
                observations['bad_'+name]='refused_before_cgroup'
            link=out/'supervisor-link';link.symlink_to(supervisor)
            p=run('symlink',args(sup=link));assert p.returncode!=0 and not p.stdout;observations['symlink']='refused'
            fifo=out/'not-a-file';os.mkfifo(fifo)
            p=run('fifo',args(sup=fifo));assert p.returncode!=0 and not p.stdout;observations['fifo']='refused_without_blocking'
            for name,filter_fn in (('seal',deny_seals),('close_range',deny_close_range),('clock',deny_clock),('execveat',deny_execveat)):
                p=run(name,preexec=filter_fn);assert p.returncode!=0 and not p.stdout
                observations['denied_'+name]='refused'
            for descriptor in (0,1,2):
                p=run('closed_stdio',preexec=lambda n=descriptor:os.close(n))
                assert p.returncode!=0 and not p.stdout
                observations[f'closed_fd_{descriptor}']='refused_before_cgroup'
            for label, path in (('ordinary_fd', '/tmp'), ('foreign_cgroup', '/sys/fs/cgroup')):
                os.close(fd); fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY);assert fd==3,fd
                if label=='foreign_cgroup': assert os.fstat(fd).st_uid != os.geteuid()
                try:
                    p=subprocess.run(args(),stdin=subprocess.DEVNULL,capture_output=True,pass_fds=(fd,),env={'PATH':'/nonexistent'},timeout=100)
                    assert p.returncode!=0 and not p.stdout and not dirs(),(label,p.returncode,p.stdout,p.stderr)
                    observations[label]='refused'
                finally:
                    os.close(fd);fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY);assert fd==3,fd
            # Force an exact PID-name collision before exec. The driver must
            # refuse without removing or changing the pre-existing child.
            stdout_r,stdout_w=os.pipe();stderr_r,stderr_w=os.pipe();pid=os.fork()
            if pid==0:
                try:
                    os.close(stdout_r);os.close(stderr_r);os.dup2(stdout_w,1);os.dup2(stderr_w,2)
                    os.set_inheritable(fd,True);os.kill(os.getpid(),signal.SIGSTOP)
                    os.execve(str(binary),args(),{'PATH':'/nonexistent'})
                finally:os._exit(127)
            os.close(stdout_w);os.close(stderr_w);collision=parent/f'fune-{pid}';created=False;reaped=False;identity=None
            try:
                waited,status=os.waitpid(pid,os.WUNTRACED);assert waited==pid and os.WIFSTOPPED(status)
                collision.mkdir();created=True;identity=collision.stat().st_ino;os.kill(pid,signal.SIGCONT)
                waited,status=os.waitpid(pid,0);reaped=True;stdout=os.read(stdout_r,4096);stderr=os.read(stderr_r,4096)
                assert os.WIFEXITED(status) and os.WEXITSTATUS(status)!=0 and not stdout,(status,stdout,stderr)
                assert collision.is_dir() and collision.stat().st_ino==identity
                collision.rmdir();created=False;observations['existing_name']='refused_without_removal'
            finally:
                if not reaped:
                    try:os.kill(pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    os.waitpid(pid,0)
                os.close(stdout_r);os.close(stderr_r)
                if created and collision.exists() and collision.stat().st_ino==identity and 'populated 0' in (collision/'cgroup.events').read_text() and not [x for x in collision.iterdir() if x.is_dir()]:collision.rmdir()
            # An unrelated, test-owned occupant must remain alive and untouched.
            other=parent/'occupied-by-observer';other.mkdir();occupant=subprocess.Popen(['/usr/bin/sleep','60'])
            try:
                (other/'cgroup.procs').write_text(str(occupant.pid))
                p=subprocess.run(args(),stdin=subprocess.DEVNULL,capture_output=True,pass_fds=(fd,),env={'PATH':'/nonexistent'},timeout=100)
                assert p.returncode!=0 and not p.stdout and occupant.poll() is None and other.is_dir()
                assert dirs()==[other];observations['populated_parent']='refused_without_killing_occupant'
            finally:
                if occupant.poll() is None:occupant.terminate()
                occupant.wait(timeout=10);other.rmdir()
            # Deliberately leave one empty test-owned child in the driver's
            # cgroup: safe cleanup must refuse rather than delete it.
            p=subprocess.Popen(args(image=max_layout,digest=max_manifest),stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE,pass_fds=(fd,),env={'PATH':'/nonexistent'})
            target=parent/f'fune-{p.pid}';deadline=time.monotonic()+15
            try:
                while not target.is_dir() and p.poll() is None and time.monotonic()<deadline:time.sleep(.005)
                assert target.is_dir(),(p.poll(),p.communicate(timeout=5) if p.poll() is not None else 'timeout')
                identity=target.stat().st_ino;blocker=target/'observer-owned-blocker';blocker.mkdir()
                stdout,stderr=p.communicate(timeout=100)
                assert p.returncode!=0 and not stdout and b'fune_driver_pending' in stderr,(p.returncode,stdout,stderr)
                assert target.stat().st_ino==identity and blocker.is_dir() and 'populated 0' in (target/'cgroup.events').read_text()
                blocker.rmdir();target.rmdir();observations['cleanup_blocked']='refused_preserved_then_observer_removed'
            finally:
                if p.poll() is None:p.kill();p.communicate(timeout=20)
            assert not dirs()
            # SIGKILL cannot invoke cleanup. Verify the test's descendants die,
            # preserve the stale cgroup until empty, then remove our own one.
            p=subprocess.Popen(args(image=max_layout,digest=max_manifest),stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE,pass_fds=(fd,),env={'PATH':'/nonexistent'})
            target=parent/f'fune-{p.pid}';deadline=time.monotonic()+15
            try:
                while time.monotonic()<deadline and p.poll() is None:
                    if target.is_dir() and 'populated 1' in (target/'cgroup.events').read_text():break
                    time.sleep(.01)
                assert target.is_dir() and 'populated 1' in (target/'cgroup.events').read_text()
                children=Path(f'/proc/{p.pid}/task/{p.pid}/children').read_text().split()
                assert len(children)==1,children
                outer_input=os.readlink(f'/proc/{p.pid}/fd/0')
                supervisor_input=os.readlink(f'/proc/{children[0]}/fd/0')
                assert outer_input.startswith('pipe:') and supervisor_input.startswith('pipe:') and outer_input!=supervisor_input
                observations['supervisor_stdin']='separate_pipe_observed'
                identity=target.stat().st_ino;p.send_signal(signal.SIGKILL);stdout,stderr=p.communicate(timeout=30)
                assert not stdout and p.returncode == -signal.SIGKILL
                deadline=time.monotonic()+20
                while time.monotonic()<deadline and 'populated 0' not in (target/'cgroup.events').read_text():time.sleep(.05)
                assert target.stat().st_ino==identity and 'populated 0' in (target/'cgroup.events').read_text()
                target.rmdir();observations['sigkill']='stale_empty_group_observer_removed'
            finally:
                if p.poll() is None:p.kill();p.communicate(timeout=20)
            assert not dirs()
        finally:os.close(fd)
        (parent/'cgroup.subtree_control').write_text('-cpu -memory -pids');parent.rmdir()
        noctrl=root/'fune-native-no-controllers';noctrl.mkdir();fd=os.open(noctrl,os.O_RDONLY|os.O_DIRECTORY);assert fd==3,fd
        try:
            p=subprocess.run(args(),stdin=subprocess.DEVNULL,capture_output=True,pass_fds=(fd,),env={'PATH':'/nonexistent'},timeout=100)
            assert p.returncode!=0 and not p.stdout and not [x for x in noctrl.iterdir() if x.is_dir()],(p.returncode,p.stdout,p.stderr)
            observations['missing_controllers']='refused_and_cleaned'
        finally:os.close(fd);noctrl.rmdir()
    finally:
        if parent.exists() and not [x for x in parent.iterdir() if x.is_dir()] and 'populated 0' in (parent/'cgroup.events').read_text():
            (parent/'cgroup.subtree_control').write_text('-cpu -memory -pids');parent.rmdir()
        if parent.exists():
            raise AssertionError('test-owned parent still contains work; preserved for inspection')
        (root/'cgroup.subtree_control').write_text('-cpu -memory -pids')
        (root/'cgroup.procs').write_text(str(os.getpid()));observer.rmdir()
    def digest(path): return 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()
    result={'status':'PASS_FUNE_NATIVE_FIXED_DRIVER','driver':digest(binary),'supervisor':digest(supervisor),
            'worker':digest(worker),'producer':digest(producer),'manifest':manifest,'maxManifest':max_manifest,
            'factorySourceMutationRefused':factory_verified,'observations':observations,
            'generalExecutionQualified':False,'securityBoundaryQualified':False}
    (out/'native-driver.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS_FUNE_NATIVE_FIXED_DRIVER',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--compiler',type=Path);p.add_argument('--driver',type=Path)
    for n in ('supervisor','worker','producer','layout','max-layout','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--manifest',required=True);p.add_argument('--max-manifest',required=True)
    a=p.parse_args();assert bool(a.compiler)!=bool(a.driver);out=a.output.resolve();out.mkdir(mode=0o700,parents=True,exist_ok=False)
    binary=build(a.compiler.resolve(),out) if a.compiler else a.driver.resolve()
    main(binary,a.supervisor.resolve(),a.worker.resolve(),a.producer.resolve(),a.layout.resolve(),a.manifest,
         a.max_layout.resolve(),a.max_manifest,out,bool(a.compiler))

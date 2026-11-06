package dev.kotoba.jun902;
import android.app.Activity; import android.os.Build; import android.os.Bundle; import android.system.Os;
import java.io.*; import java.nio.file.Files; import java.security.MessageDigest; import java.util.*; import java.util.concurrent.TimeUnit;
public class Probe extends Activity {
  PrintWriter log; File files; String lib;
  @Override protected void onCreate(Bundle b) { super.onCreate(b); new Thread(new Runnable(){ public void run(){ try { go(); } catch (Throwable t) { if (log!=null) { t.printStackTrace(log); log.flush(); } } finally { if (log!=null) log.close(); try { new File(getExternalFilesDir(null),"done").createNewFile(); } catch (IOException e) {} } } }).start(); }
  void say(String s){ log.println(s); log.flush(); }
  String one(String s){ s=s.replace('\n','|'); return s.length()>200?s.substring(0,200):s; }
  String read(File f) throws IOException { return new String(Files.readAllBytes(f.toPath()),"UTF-8"); }
  String sha(File f) throws Exception { MessageDigest m=MessageDigest.getInstance("SHA-256"); byte[] d=m.digest(Files.readAllBytes(f.toPath())); StringBuilder s=new StringBuilder(); for(byte x:d) s.append(String.format("%02x",x)); return s.toString(); }
  int t(String name,int want,String stdin,Map<String,String> env,String... argv) throws Exception {
    long st=System.currentTimeMillis(); String out; int c;
    try { ProcessBuilder pb=new ProcessBuilder(argv); pb.environment().clear(); pb.environment().putAll(env); pb.directory(files); pb.redirectErrorStream(true);
      final Process p=pb.start(); OutputStream o=p.getOutputStream(); if(stdin!=null) o.write(stdin.getBytes("UTF-8")); o.close();
      Thread w=new Thread(new Runnable(){ public void run(){ try { if(!p.waitFor(300,TimeUnit.SECONDS)) p.destroyForcibly(); } catch(Exception e){} } }); w.start();
      ByteArrayOutputStream bo=new ByteArrayOutputStream(); InputStream in=p.getInputStream(); byte[] b=new byte[8192]; int n; while((n=in.read(b))>0) bo.write(b,0,n); c=p.waitFor(); out=bo.toString("UTF-8");
    } catch(IOException e){ c=-1; out="IOException: "+e.getMessage(); }
    say((c==want?"PASS ":"DIFF ")+name+" exit="+c+" want="+want+" ms="+(System.currentTimeMillis()-st)+" :: "+one(out)); return c; }
  Map<String,String> e(String... kv){ Map<String,String> m=new HashMap<>(); for(int i=0;i<kv.length;i+=2) m.put(kv[i],kv[i+1]); return m; }
  void asset(String n) throws Exception { try(InputStream i=getAssets().open(n); OutputStream o=new FileOutputStream(new File(files,n))){ byte[] b=new byte[65536]; int k; while((k=i.read(b))>0) o.write(b,0,k);} }
  String so(String n){ return lib+"/lib"+n+".so"; }
  void wire(String name,String so,String allow,int want,String stdin,String... extra) throws Exception { Map<String,String> m=e("KEXE_FUEL","100000000","KEXE_ALLOW",allow); for(int i=0;i<extra.length;i+=2) m.put(extra[i],extra[i+1]); t(name,want,stdin,m,so(so)); t(name+"-deny",120,null,e("KEXE_FUEL","100000000","KEXE_ALLOW",name.equals("w37")?"3":"37"),so(so)); }
  void go() throws Exception {
    log=new PrintWriter(new FileWriter(new File(getExternalFilesDir(null),"results.txt"))); files=getFilesDir(); lib=getApplicationInfo().nativeLibraryDir;
    say("device "+Build.MODEL+" sdk="+Build.VERSION.SDK_INT+" targetSdk="+getApplicationInfo().targetSdkVersion+" pageSize="+Os.sysconf(android.system.OsConstants._SC_PAGESIZE));
    say("context "+read(new File("/proc/self/attr/current")).trim()); for(String l:read(new File("/proc/self/status")).split("\n")) if(l.startsWith("Seccomp")||l.startsWith("NoNewPrivs")) say(l.replace('\t',' '));
    say("nativeLibraryDir="+lib+" extractNativeLibs="+((getApplicationInfo().flags&android.content.pm.ApplicationInfo.FLAG_EXTRACT_NATIVE_LIBS)!=0)); File[] ls=new File(lib).listFiles(); say("libs="+(ls==null?"none":ls.length)); say("filesDir="+files);
    if(checkSelfPermission("android.permission.INTERNET")!=android.content.pm.PackageManager.PERMISSION_GRANTED){ say("no INTERNET permission"); t("w43-47-noperm",7,null,e("KEXE_FUEL","100000000","KEXE_ALLOW","37,43,44,45,46,47","KEXE_CAP_RESOURCES_43","127.0.0.1:39021","KEXE_CAP_RESOURCES_45","127.0.0.1:39021"),so("wnet")); return; }
    t("hello-exit",42,null,e(),so("hello"));
    if(!new File(so("hello")).exists()) { say("lib dir has no hello, stopping"); return; }
    t("hello-report",0,null,e("KEXE_STRUCTURED_REPORT","1"),so("hello"));
    t("seccomp-default",0,null,e("KEXE_STRUCTURED_REPORT","1"),so("hello"));
    t("sandbox-probe",120,null,e("KEXE_STRUCTURED_REPORT","1","KEXE_SANDBOX_PROBE","1"),so("hello"));
    t("cpu1",120,null,e("KEXE_STRUCTURED_REPORT","1","KEXE_CPU_SECONDS","1"),so("spin"));
    t("wall3",120,null,e("KEXE_STRUCTURED_REPORT","1","KEXE_WALL_SECONDS","3"),so("spin"));
    t("stack",120,null,e("KEXE_STRUCTURED_REPORT","1"),so("deep"));
    File copy=new File(files,"hello-copy"); Files.copy(new File(so("hello")).toPath(),copy.toPath()); Os.chmod(copy.getPath(),0755); t("exec-filesDir",42,null,e(),copy.getPath());
    File ecopy=new File(getExternalFilesDir(null),"hello-copy"); Files.copy(new File(so("hello")).toPath(),ecopy.toPath()); ecopy.setExecutable(true); t("exec-externalFilesDir",42,null,e(),ecopy.getPath());
    t("exec-data-local-tmp",42,null,e(),"/data/local/tmp/jun902/hello.elf");
    t("sh-filesDir",42,null,e(),"/system/bin/sh","-c",copy.getPath());
    wire("w3","w3hash","3",7,null); wire("w7","w7clock","7",7,null); wire("w23","w23entropy","23",7,null); wire("w37","w37write","37",7,null); wire("w38","w38args","37,38",7,null); wire("w39","w39err","39",7,null); wire("w40","w40cwd","37,40",7,null); wire("w41","w41read","37,41",7,"hello-41\n");
    wire("w20","w20spawn","20,37",7,null,"KEXE_CAP_RESOURCES_20","/system/bin/toybox");
    wire("w43-47","wnet","37,43,44,45,46,47",7,null,"KEXE_CAP_RESOURCES_43","127.0.0.1:39021","KEXE_CAP_RESOURCES_45","127.0.0.1:39021");
    File fsr=new File(files,"fsr"); fsr.mkdir();
    for(String c:new String[]{"original-forms","raw","managed","no-replace","large","managed-return","managed-publish","managed-publish-exclusive"}){ File s=new File(fsr,c); s.mkdir(); String p=(c.equals("raw")||c.equals("large"))?new File(s,"data").getPath():s.getPath(); t(c,0,null,g(s),so("w35fs"),c,p); String[] l=s.list(); int left=0; if(l!=null) for(String x:l) if(x.startsWith("kotoba-output-")) left++; say("  stageLeft="+left); }
    File s=new File(fsr,"full-mode"); s.mkdir(); String[][] fm={{"regular","420"},{"special","2468"},{"group","1444"},{"sticky","932"}}; for(String[] f:fm){ File x=new File(s,f[0]); try(FileOutputStream o=new FileOutputStream(x)){o.write('x');} try{ Os.chmod(x.getPath(),Integer.parseInt(f[1])); }catch(Exception ex){ say("  chmod "+f[0]+" "+f[1]+" refused: "+ex.getMessage()); } } Os.symlink(new File(s,"regular").getPath(),new File(s,"link").getPath()); new File(s,"directory").mkdir(); t("full-mode",0,null,g(s),so("w35fs"),"full-mode",s.getPath());
    s=new File(fsr,"exists"); s.mkdir(); File outside=new File(fsr,"outside"); try(FileOutputStream o=new FileOutputStream(outside)){o.write('x');} File r=new File(s,"readable"); try(FileOutputStream o=new FileOutputStream(r)){o.write('x');} File den=new File(s,"denied"); try(FileOutputStream o=new FileOutputStream(den)){o.write('x');} Os.chmod(den.getPath(),0); File par=new File(s,"parent"); par.mkdir(); try(FileOutputStream o=new FileOutputStream(new File(par,"inside"))){o.write('x');} Os.chmod(par.getPath(),0); Os.symlink(r.getPath(),new File(s,"link").getPath()); Os.symlink(outside.getPath(),new File(s,"escape").getPath()); t("exists-errors",0,null,g(s),so("w35fs"),"exists-errors",s.getPath(),outside.getPath()); Os.chmod(par.getPath(),0700);
    for(String[] c:new String[][]{{"fault","managed-fault",""},{"cpu","managed-signal","KEXE_CPU_SECONDS"},{"wall","managed-signal","KEXE_WALL_SECONDS"}}){ s=new File(fsr,c[0]); s.mkdir(); Map<String,String> m=g(s); if(!c[2].isEmpty()) m.put(c[2],c[0].equals("cpu")?"1":"2"); t(c[0],120,null,m,so("w35fs"),c[1],s.getPath()); }
    for(String n:new String[]{"hello.kotoba","full-unity.kotoba","runner.kotoba"}) asset(n);
    String F=files.getPath(); Map<String,String> ce=e("KEXE_CAP_RESOURCES_35",F,"KEXE_STACK_BYTES","8388608");
    t("compile-hello",0,null,ce,so("root"),"compile",F+"/hello.kotoba","--target","aarch64-linux","--output",F+"/hello2.elf","--format","static"); say("hello2 sha="+sha(new File(F,"hello2.elf"))+" bundled="+sha(new File(so("hello")))); new File(F,"hello2.elf").setExecutable(true); t("exec-compiled-output",42,null,e(),F+"/hello2.elf");
    t("F1-compile",0,null,ce,so("root"),"compile",F+"/full-unity.kotoba","--target","aarch64-macos","--output",F+"/F1.kseed"); t("F1-pack",0,null,ce,so("root"),"compile",F+"/runner.kotoba","--target","aarch64-linux","--output",F+"/F1.elf","--format","packed","--payload",F+"/F1.kseed");
    say("F1.kseed sha="+sha(new File(F,"F1.kseed"))); say("F1.elf sha="+sha(new File(F,"F1.elf"))); say("root sha="+sha(new File(so("root")))); say("ROOT_REPRODUCES="+sha(new File(F,"F1.elf")).equals(sha(new File(so("root")))));
  }
  Map<String,String> g(File s){ return e("PATH","/nonexistent","KEXE_ALLOW","35,37,38,39","KEXE_CAP_RESOURCES_35",s.getPath(),"KEXE_STACK_BYTES","8388608"); }
}

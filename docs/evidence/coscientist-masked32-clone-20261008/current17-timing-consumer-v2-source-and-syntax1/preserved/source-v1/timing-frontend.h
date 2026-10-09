/* Only fixed packet-relative images, never caller-selected paths or symbols. */
static int timing_exact_file(const char *p,const unsigned char*b,size_t n) {
  FILE*f=fopen(p,"rb");if(!f)return 0;unsigned char buf[4096];size_t at=0;int ok=1;
  while(at<n){size_t z=n-at;if(z>sizeof(buf))z=sizeof(buf);if(fread(buf,1,z,f)!=z||memcmp(buf,b+at,z)){ok=0;break;}at+=z;}
  if(ok&&(fgetc(f)!=EOF||ferror(f)))ok=0;if(fclose(f))ok=0;return ok;
}
static int timing_load_c(void) {
  if(!timing_exact_file(TIMING_C_PATH,timing_c_bytes,sizeof(timing_c_bytes)))return 0;
  char dir[]="/private/tmp/amu-current17-C-XXXXXX",file[256];if(!mkdtemp(dir))return 0;
  if(snprintf(file,sizeof(file),"%s/known.dylib",dir)>=(int)sizeof(file)){rmdir(dir);return 0;}
  int fd=open(file,O_WRONLY|O_CREAT|O_EXCL,0600);if(fd<0){rmdir(dir);return 0;}
  size_t at=0;int ok=1;while(at<sizeof(timing_c_bytes)){ssize_t z=write(fd,timing_c_bytes+at,sizeof(timing_c_bytes)-at);if(z<0&&errno==EINTR)continue;if(z<=0){ok=0;break;}at+=(size_t)z;}
  if(ok&&fchmod(fd,0400))ok=0;if(close(fd))ok=0;
  if(ok)timing_c_handle=dlopen(file,RTLD_NOW|RTLD_LOCAL);
  if(unlink(file)||rmdir(dir))ok=0;
  if(!ok||!timing_c_handle)return 0;
  dlerror();timing_c_fn=(kexe_fn8)dlsym(timing_c_handle,TIMING_C_SYMBOL);
  return timing_c_fn && !dlerror();
}
int main(int argc,char **argv) {
  /* Caller supplies arm, n, calls, warmup only. Fuel/caps/helpers remain fixed current loader environment. */
  if(argc!=5)return 2;
  if(!strcmp(argv[1],"OFF"))timing_arm=0;else if(!strcmp(argv[1],"ON"))timing_arm=1;else if(!strcmp(argv[1],"C"))timing_arm=2;else return 2;
  uint64_t n=timing_decimal(argv[2],TIMING_MAX_N);timing_calls=timing_decimal(argv[3],100000000);timing_warmup=timing_decimal(argv[4],1);
  if(!timing_calls||timing_warmup!=1||!getenv("KEXE_ARENA_USE")||!getenv("KEXE_STRUCTURED_REPORT"))return 2;
  unsigned image=timing_arm==1?1:0;
  if(!timing_exact_file(timing_paths[image],timing_images[image],timing_sizes[image]))return 2;
  if(timing_arm==2&&!timing_load_c())return 2;
  timing_receipt=mmap(NULL,sizeof(*timing_receipt),PROT_READ|PROT_WRITE,MAP_ANONYMOUS|MAP_SHARED,-1,0);
  if(timing_receipt==MAP_FAILED)return 2;
  char offset[32],arg[32];snprintf(offset,sizeof(offset),"%llu",(unsigned long long)timing_offsets[image]);snprintf(arg,sizeof(arg),"%llu",(unsigned long long)n);
  char *args[]={argv[0],(char*)timing_paths[image],offset,"1","aarch64","-",arg,NULL};
  int rc=timing_loader_main(7,args);
  if(munmap(timing_receipt,sizeof(*timing_receipt)))return 2;
  if(timing_c_handle&&dlclose(timing_c_handle))return 2;return rc;
}

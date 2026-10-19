static int timing_exact_file(const char*p,const unsigned char*b,size_t n){FILE*f=fopen(p,"rb");if(!f)return 0;unsigned char buf[4096];size_t at=0;int ok=1;while(at<n){size_t z=n-at;if(z>sizeof(buf))z=sizeof(buf);if(fread(buf,1,z,f)!=z||memcmp(buf,b+at,z)){ok=0;break;}at+=z;}if(ok&&(fgetc(f)!=EOF||ferror(f)))ok=0;if(fclose(f))ok=0;return ok;}
int main(int argc,char**argv){
 if(argc!=2)return 2;uint64_t n=timing_decimal(argv[1],2147483647);if(!n)return 2;
 if(!timing_exact_file(TIMING_NATIVE_PATH,timing_native,sizeof(timing_native)))return 2;
 timing_receipt=mmap(NULL,sizeof(*timing_receipt),PROT_READ|PROT_WRITE,MAP_ANONYMOUS|MAP_SHARED,-1,0);if(timing_receipt==MAP_FAILED)return 2;
 char offset[32],arg[32];snprintf(offset,sizeof(offset),"%llu",(unsigned long long)TIMING_BENCH_OFFSET);snprintf(arg,sizeof(arg),"%llu",(unsigned long long)n);
 char arity[8];snprintf(arity,sizeof(arity),"%d",TIMING_BENCH_ARITY);char*args[]={argv[0],TIMING_NATIVE_PATH,offset,arity,"aarch64","-",arg,TIMING_BENCH_ARITY==2?"0":NULL,NULL};int rc=timing_loader_main(TIMING_BENCH_ARITY==2?8:7,args);
 if(munmap(timing_receipt,sizeof(*timing_receipt)))return 2;return rc;
}

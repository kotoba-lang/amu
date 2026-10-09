/* BOOTSTRAP-TOOL: unchanged C benchmark plus initialized ctx snapshots. */
#define GLOBAL_SCALE_FACTOR 1
#include <stdint.h>
#include <limits.h>
#include "../upstream/src/nettle-sha256/nettle-sha256.c"
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
static uint64_t snapshot[294];static int compress_index;
static void snapctx(struct sha256_ctx *ctx,int base,int bytes){for(int i=0;i<8;i++)snapshot[base+i]=ctx->state[i];snapshot[base+8]=ctx->count;snapshot[base+9]=ctx->index;for(int i=0;i<bytes;i++)snapshot[base+10+i]=ctx->block[i];}
static void observed_compress(struct sha256_ctx *ctx,const uint8_t *input){_nettle_sha256_compress(ctx->state,input,K);int base=76+72*compress_index++;for(int i=0;i<64;i++)snapshot[base+i]=input[i];for(int i=0;i<8;i++)snapshot[base+64+i]=ctx->state[i];}
#undef COMPRESS
#define COMPRESS(ctx,data) observed_compress(ctx,data)
static void
observed_write_digest (struct sha256_ctx *ctx, size_t length, uint8_t * digest)
{
  uint64_t bit_count;

  assert_beebs (length <= SHA256_DIGEST_SIZE);

  MD_PAD (ctx, 8, COMPRESS);

  /* There are 512 = 2^9 bits in one block */
  bit_count = (ctx->count << 9) | (ctx->index << 3);

  /* This is slightly inefficient, as the numbers are converted to
     big-endian format, and will be converted back by the compression
     function. It's probably not worth the effort to fix this. */
  WRITE_UINT64 (ctx->block + (SHA256_BLOCK_SIZE - 8), bit_count);
  COMPRESS (ctx, ctx->block);

  _nettle_write_be32 (length, digest, ctx->state);
}

static void observed_digest(struct sha256_ctx *ctx,size_t length,uint8_t *out){observed_write_digest(ctx,length,out);sha256_init(ctx);snapctx(ctx,220,64);}
static int
observed_body(unsigned int lsf, unsigned int gsf)
{
  int i;

  for (unsigned int lsf_cnt = 0; lsf_cnt < lsf; lsf_cnt++)
    for (unsigned int gsf_cnt = 0; gsf_cnt < gsf; gsf_cnt++)
    {
      memset (buffer, 0, sizeof (buffer));
      struct sha256_ctx ctx;
      nettle_sha256.init (&ctx);snapctx(&ctx,0,0);
      nettle_sha256.update (&ctx, sizeof (msg), msg);snapctx(&ctx,10,56);
      observed_digest (&ctx, nettle_sha256.digest_size, buffer);
    }

  return 0;
}
int64_t bench(int64_t n,EXTRA){if(!n)return 0;initialise_benchmark();return verify_benchmark(benchmark_body(1,n));}
int64_t observe(int64_t encoded,EXTRA){int n=encoded/512,f=encoded%512;memset(buffer,0,sizeof(buffer));memset(snapshot,0,sizeof(snapshot));compress_index=0;if(n){for(int i=0;i<n;i++){compress_index=0;observed_body(1,1);}}if(f<8){int64_t acc=0;for(int i=0;i<4;i++)acc=acc*256+buffer[f*4+i];return acc;}if(f<302)return snapshot[f-8];return INT64_MIN;}
int64_t oracle_selfcheck(int64_t n,EXTRA){for(int i=0;i<n;i++){compress_index=0;observed_body(1,1);}uint8_t saved[32];memcpy(saved,buffer,32);int a=verify_benchmark(0);int b=benchmark_body(1,n);return a&&verify_benchmark(b)&&memcmp(saved,buffer,32)==0;}

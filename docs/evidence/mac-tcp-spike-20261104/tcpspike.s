// Spike: Darwin arm64 direct-syscall TCP listener on 127.0.0.1:18766.
// Qualifies the constants recalled in ADR 0408 D2 (not part of amu).
// step 1 socket 2 setsockopt 3 bind 4 listen 5 fcntl 6 poll 7 accept 8 read 9 write
.globl _main
.p2align 2
_main:
  sub sp, sp, #256
  mov x20, #1
  mov x0, #2                    // AF_INET
  mov x1, #1                    // SOCK_STREAM
  mov x2, #0
  mov x16, #97                  // socket
  svc #0x80
  b.cs fail
  mov x19, x0                   // listener fd
  // setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, 4)
  mov x20, #2
  mov w9, #1
  str w9, [sp, #32]
  mov x0, x19
  mov x1, #0xffff               // SOL_SOCKET
  mov x2, #4                    // SO_REUSEADDR
  add x3, sp, #32
  mov x4, #4
  mov x16, #105
  svc #0x80
  b.cs fail
  // sockaddr_in at [sp]: len 16, family 2, port 18766 (0x494e) big endian, 127.0.0.1
  mov x20, #3
  stp xzr, xzr, [sp]
  mov w9, #16
  strb w9, [sp, #0]
  mov w9, #2
  strb w9, [sp, #1]
  mov w9, #0x49
  strb w9, [sp, #2]
  mov w9, #0x4e
  strb w9, [sp, #3]
  mov w9, #127
  strb w9, [sp, #4]
  mov w9, #1
  strb w9, [sp, #7]
  mov x0, x19
  mov x1, sp
  mov x2, #16
  mov x16, #104                 // bind
  svc #0x80
  b.cs fail
  mov x20, #4
  mov x0, x19
  mov x1, #4
  mov x16, #106                 // listen
  svc #0x80
  b.cs fail
  // fcntl(fd, F_SETFL=4, O_NONBLOCK=4)
  mov x20, #5
  mov x0, x19
  mov x1, #4
  mov x2, #4
  mov x16, #92
  svc #0x80
  b.cs fail
  // announce readiness
  mov x0, #1
  adr x1, ready
  mov x2, #6
  mov x16, #4
  svc #0x80
  // poll({fd, POLLIN}, 1, 8000)
  mov x20, #6
  str w19, [sp, #48]
  mov w9, #1
  strh w9, [sp, #52]
  strh wzr, [sp, #54]
  add x0, sp, #48
  mov x1, #1
  mov x2, #8000
  mov x16, #230
  svc #0x80
  b.cs fail
  cbz x0, timedout
  // accept(fd, 0, 0) -> conn
  mov x20, #7
  mov x0, x19
  mov x1, #0
  mov x2, #0
  mov x16, #30
  svc #0x80
  b.cs fail
  mov x21, x0
  // the accepted socket inherits O_NONBLOCK on Darwin: wait for data first
  mov x20, #10
  str w21, [sp, #48]
  mov w9, #1
  strh w9, [sp, #52]
  strh wzr, [sp, #54]
  add x0, sp, #48
  mov x1, #1
  mov x2, #3000
  mov x16, #230
  svc #0x80
  b.cs fail
  cbz x0, timedout
  // read(conn, buf, 64)
  mov x20, #8
  mov x0, x21
  add x1, sp, #64
  mov x2, #64
  mov x16, #3
  svc #0x80
  b.cs fail
  mov x22, x0
  // write(conn, buf, n)
  mov x20, #9
  mov x0, x21
  add x1, sp, #64
  mov x2, x22
  mov x16, #4
  svc #0x80
  b.cs fail
  mov x0, x21
  mov x16, #6
  svc #0x80
  mov x0, x19
  mov x16, #6
  svc #0x80
  mov x0, #1
  adr x1, okmsg
  mov x2, #3
  mov x16, #4
  svc #0x80
  mov x0, #0
  mov x16, #1
  svc #0x80
timedout:
  mov x0, #1
  adr x1, tmsg
  mov x2, #8
  mov x16, #4
  svc #0x80
  mov x0, #99
  mov x16, #1
  svc #0x80
fail:
  mov x21, x0                   // errno
  mov x0, x20                   // exit code = failing step
  mov x1, x21
  mov x16, #1
  svc #0x80
ready: .ascii "ready\n"
okmsg: .ascii "OK\n"
tmsg:  .ascii "timeout\n"

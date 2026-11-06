# usage: wires.sh DIR SPAWN_PROG SPAWN_ARG0
D=$1; PROG=$2; PRE=$3; cd $D/wires || exit 9
sed "s#SPAWNPROG#$PROG$PRE#" w20spawn.kotoba > w20.tmp && mv w20.tmp w20spawn.kotoba
cp net.tmpl wnet.kotoba
for s in *.kotoba; do b=${s%.kotoba}; env KEXE_CAP_RESOURCES_35=$D KEXE_STACK_BYTES=8388608 $D/root.elf compile $D/wires/$s --target aarch64-linux --output $D/wires/$b.elf --format static >/dev/null 2>$b.cerr; c=$?; chmod 755 $b.elf 2>/dev/null; echo "compile $b exit=$c $(head -c 160 $b.cerr)"; done
t(){ n=$1; want=$2; shift 2; o=$("$@" 2>&1 </dev/null); c=$?; [ "$c" = "$want" ] && r=PASS || r=DIFF; echo "$r $n exit=$c want=$want :: $(echo "$o" | tr '\n' '|' | cut -c1-170)"; }
R="env KEXE_FUEL=100000000"
t w3 7 $R KEXE_ALLOW=3 ./w3hash.elf
t w3-deny 120 $R KEXE_ALLOW=37 ./w3hash.elf
t w7 7 $R KEXE_ALLOW=7 ./w7clock.elf
t w7-deny 120 $R KEXE_ALLOW=37 ./w7clock.elf
t w23 7 $R KEXE_ALLOW=23 ./w23entropy.elf
t w23-deny 120 $R KEXE_ALLOW=37 ./w23entropy.elf
t w37 7 $R KEXE_ALLOW=37 ./w37write.elf
t w37-deny 120 $R KEXE_ALLOW=3 ./w37write.elf
t w38 7 $R KEXE_ALLOW=37,38 ./w38args.elf
t w38-deny 120 $R KEXE_ALLOW=37 ./w38args.elf
t w39 7 $R KEXE_ALLOW=39 ./w39err.elf
t w39-deny 120 $R KEXE_ALLOW=37 ./w39err.elf
t w40 7 $R KEXE_ALLOW=37,40 ./w40cwd.elf
t w40-deny 120 $R KEXE_ALLOW=37 ./w40cwd.elf
o=$(echo hello-41 | $R KEXE_ALLOW=37,41 ./w41read.elf 2>&1); echo "stdin w41 exit=$? want=7 :: $o"
t w41-deny 120 $R KEXE_ALLOW=37 ./w41read.elf
t w20 7 $R KEXE_ALLOW=20,37 KEXE_CAP_RESOURCES_20=$PROG ./w20spawn.elf
t w20-deny 120 $R KEXE_ALLOW=37 ./w20spawn.elf
t w43-47 7 $R KEXE_ALLOW=37,43,44,45,46,47 KEXE_CAP_RESOURCES_43=127.0.0.1:39021 KEXE_CAP_RESOURCES_45=127.0.0.1:39021 ./wnet.elf
t w43-deny 120 $R KEXE_ALLOW=37 ./wnet.elf
mkdir -p $D/fs; F="env KEXE_ALLOW=35,37,38,39 KEXE_CAP_RESOURCES_35=$D/fs KEXE_STACK_BYTES=8388608"
for m in full-mode raw original-forms managed no-replace large; do t w35-$m 0 $F ./w35fs.elf $m $D/fs/$m; done
t w35-deny 120 env KEXE_ALLOW=37,38 ./w35fs.elf raw $D/fs/deny

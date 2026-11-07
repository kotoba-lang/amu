# usage: fs.sh DIR  (same scope set-up as scripts/seed/check-native-fs2.py)
D=$1; cd $D/wires || exit 9
env KEXE_CAP_RESOURCES_35=$D KEXE_STACK_BYTES=8388608 $D/root.elf compile $D/wires/w39err.kotoba --target aarch64-linux --output $D/wires/w39err.elf --format static; chmod 755 w39err.elf
o=$(env KEXE_FUEL=100000000 KEXE_ALLOW=39 ./w39err.elf 2>&1); echo "w39 exit=$? want=7 :: $o"
o=$(env KEXE_FUEL=100000000 KEXE_ALLOW=37 ./w39err.elf 2>&1); echo "w39-deny exit=$? want=120 :: $o" | tr '\n' '|'; echo
rm -rf $D/fsr; mkdir -p $D/fsr
t(){ n=$1; want=$2; shift 2; o=$("$@" 2>&1 </dev/null); c=$?; [ "$c" = "$want" ] && r=PASS || r=DIFF; echo "$r $n exit=$c want=$want :: $(echo "$o" | tr '\n' '|' | cut -c1-170)"; }
g(){ echo "env PATH=/nonexistent KEXE_ALLOW=35,37,38,39 KEXE_CAP_RESOURCES_35=$1 KEXE_STACK_BYTES=8388608"; }
for c in original-forms raw managed no-replace large managed-return managed-publish managed-publish-exclusive; do s=$D/fsr/$c; mkdir $s; case $c in raw|large) p=$s/data;; *) p=$s;; esac; t $c 0 $(g $s) ./w35fs.elf $c $p; n=$(ls $s | grep -c '^kotoba-output-'); echo "  stageLeft=$n"; done
s=$D/fsr/full-mode; mkdir $s; for f in "regular 644" "special 4644" "group 2644" "sticky 1644"; do set -- $f; echo x > $s/$1; chmod $2 $s/$1 || echo "chmod $1 $2 refused"; done; ln -s $s/regular $s/link; mkdir $s/directory; t full-mode 0 $(g $s) ./w35fs.elf full-mode $s
s=$D/fsr/exists; mkdir $s; echo x > $D/fsr/outside; echo x > $s/readable; echo x > $s/denied; chmod 0 $s/denied; mkdir $s/parent; echo x > $s/parent/inside; chmod 0 $s/parent; ln -s $s/readable $s/link; ln -s $D/fsr/outside $s/escape; t exists-errors 0 $(g $s) ./w35fs.elf exists-errors $s $D/fsr/outside; chmod 700 $s/parent; chmod 600 $s/denied
for c in "fault managed-fault 120" "cpu managed-signal 120 KEXE_CPU_SECONDS=1" "wall managed-signal 120 KEXE_WALL_SECONDS=2"; do set -- $c; s=$D/fsr/$1; mkdir $s; t $1 $3 $(g $s) $4 ./w35fs.elf $2 $s; echo "  stageLeft=$(ls $s | grep -c '^kotoba-output-')"; done

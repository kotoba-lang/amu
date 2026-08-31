(ns kotoba.compiler.nbb.native-package
  "Artifact packaging for the JDK-free native driver.

  `kotoba.compiler.nbb.cli` sealed a `:kotoba.kexe/v1` artifact and wrote it
  out as EDN, full stop. The JVM CLI does one more thing for the aiueos target
  profiles: it hands that same sealed artifact to an ELF64 or PE32+ packager
  and writes THOSE bytes to `--output`. Nothing about that step needs a JVM --
  `kotoba.native.elf64` and `kotoba.compiler.packaging.pe32plus` are portable
  `.cljc` that load unchanged under nbb -- it simply had no caller on this
  route. That absence is the whole reason `os/aiueos` built every one of its
  67 kernel objects through `clojure`.

  Kept out of `cli.cljs` deliberately: that namespace is shared with the Wasm
  driver, which must not pay to load two native packagers it will never call.
  The ISA entrypoint supplies `package` the same way it supplies
  `emit-program`."
  (:require [kotoba.compiler.packaging.pe32plus :as pe32plus]
            [kotoba.kir.target :as target-profile]
            [kotoba.native.elf64 :as elf64]))

(def ^:private kits
  "Exactly the `cond->` arms of `kotoba.compiler.core/compile-source*`. A target
  absent here has no packaged form, which is not an error: it means `--output`
  receives the artifact EDN, same as on the JVM."
  {:x86_64-aiueos-kernel-v1  {:object elf64/package-kernel-object
                              :image  elf64/package-kernel}
   :aarch64-aiueos-kernel-v1 {:image  elf64/package-kernel-aarch64}
   :x86_64-aiueos-user-v1    {:image  elf64/package-user}
   :x86_64-aiueos-uefi-v1    {:image  pe32plus/package-efi}})

(defn package
  "Select and run the packager exactly as `kotoba.compiler.cli`'s `:kexe/v1`
  branch does, and return a Buffer, or nil when the artifact EDN is what
  `--output` should hold.

  The defaulting rule is copied rather than simplified: with no `--artifact`,
  an object is preferred when one exists, and an image is used only for a
  `:process` profile. That is why `--target x86_64-aiueos-kernel-v1` alone
  yields a `.o` (what `bisect-object-migration.sh` hashes) while the UEFI
  image requires `--artifact image` (what `build-kotoba-native-kernel.sh`
  passes)."
  [target artifact artifact-kind]
  (let [kit (get kits target)
        packager (case artifact-kind
                   "image" (:image kit)
                   "object" (:object kit)
                   (or (:object kit)
                       (when (= :process (:execution (target-profile/profile target)))
                         (:image kit))))]
    (when packager
      (let [packaged (packager artifact)]
        (js/Buffer.from (clj->js (mapv #(bit-and (int %) 0xff) (:bytes packaged))))))))

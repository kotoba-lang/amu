(ns kotoba.compiler.ipld-adl-source
  "Fail-closed Kotoba-source compiler for the ipld-adl-wasm-v1 guest ABI.

  The first profile is deliberately small: two byte identities and two total
  validators.  It is still a real source compiler--the admitted Kotoba HIR is
  the authority--and unsupported bodies are rejected instead of being silently
  replaced by an identity transform."
  (:require [kotoba.sema :as sema]
            [kotoba.kir.compatibility :as compatibility]))

(def target :wasm32-ipld-adl-v1)
(def target-profile
  {:format :kotoba.target-profile/v1 :execution :wasm :isa :wasm32
   :os :unspecified :abi :ipld-adl-wasm-v1
   :runtime :kotoba.ipld-adl-wasmtime/v1 :ambient-authority false})

(def ^:private required-exports
  '[validate-representation decode encode validate-logical])

(defn- uleb [n]
  (loop [n (long n) out []]
    (let [b (bit-and n 0x7f) n' (unsigned-bit-shift-right n 7)]
      (if (zero? n') (conj out b) (recur n' (conj out (bit-or b 0x80)))))))

(defn- sleb [n]
  (loop [n (long n) out []]
    (let [b (bit-and n 0x7f) n' (bit-shift-right n 7)
          done? (or (and (zero? n') (zero? (bit-and b 0x40)))
                    (and (= -1 n') (not (zero? (bit-and b 0x40)))))]
      (if done? (conj out b) (recur n' (conj out (bit-or b 0x80)))))))

(defn- utf8 [s]
  (mapv #(bit-and (int %) 0xff) (.getBytes ^String s "UTF-8")))

(defn- name-bytes [s]
  (let [bytes (utf8 s)] (into (uleb (count bytes)) bytes)))

(defn- section [id payload]
  (concat [id] (uleb (count payload)) payload))

(defn- export-entry [name kind index]
  (concat (name-bytes name) [kind] (uleb index)))

(defn- function-body [instructions]
  (let [body (concat [0] instructions [0x0b])]
    (concat (uleb (count body)) body)))

(defn- identity-module
  [memory-pages]
  (let [capacity (- (* memory-pages 65536) 1024)
        types (concat [2]
                      [0x60 1 0x7f 1 0x7f]
                      [0x60 3 0x7f 0x7f 0x7f 1 0x7e])
        functions [2 0 1]
        memory [1 1 memory-pages memory-pages]
        exports (concat [3]
                        (export-entry "memory" 2 0)
                        (export-entry "adl_alloc" 0 0)
                        (export-entry "adl_transform" 0 1))
        alloc (concat
               [0x20 0x00 0x41] (sleb capacity) [0x4b 0x04 0x40 0x00 0x0b]
               [0x41] (sleb 1024))
        transform
        (concat
         ;; validators return canonical DAG-CBOR true (0xf5) at memory[0].
         [0x20 0x00 0x41 0x00 0x46
          0x20 0x00 0x41 0x03 0x46 0x72
          0x04 0x7e 0x42 0x01 0x05
          ;; Only decode=1 and encode=2 reach the byte identity branch.
          0x20 0x00 0x41 0x01 0x46
          0x20 0x00 0x41 0x02 0x46 0x72 0x45
          0x04 0x40 0x00 0x0b
          ;; pack (pointer << 32) | length.
          0x20 0x01 0xad 0x42 0x20 0x86
          0x20 0x02 0xad 0x84 0x0b])
        code (concat [2] (function-body alloc) (function-body transform))
        data [1 0 0x41 0 0x0b 1 0xf5]
        custom (concat (name-bytes "kotoba.ipld-adl")
                       (utf8 "ipld-adl-wasm-v1;profile=pure-identity-v1"))
        bytes (concat [0 0x61 0x73 0x6d 1 0 0 0]
                      (section 0 custom)
                      (section 1 types) (section 3 functions)
                      (section 5 memory) (section 7 exports)
                      (section 10 code) (section 11 data))]
    (byte-array (map unchecked-byte bytes))))

(defn- reject! [message data]
  (throw (ex-info message (merge {:phase :ipld-adl-source} data))))

(defn- exact-function? [function result body]
  (and (= ['value] (:params function))
       (= [:bytes] (:param-types function))
       (= result (:result function))
       (empty? (:effects function))
       (= body (:body function))))

(defn compile-source
  "Compile the closed pure identity ADL Kotoba profile to ipld-adl-wasm-v1.

  Required source exports/signatures are:
  validate-representation(bytes)->bool = true, decode(bytes)->bytes = input,
  encode(bytes)->bytes = input, and validate-logical(bytes)->bool = true.
  MEMORY-PAGES is fixed in the emitted module (1..64; default 2)."
  ([source] (compile-source source {}))
  ([source {:keys [memory-pages] :or {memory-pages 2} :as options}]
   (when-not (= (set (keys options)) (if (contains? options :memory-pages)
                                      #{:memory-pages} #{}))
     (reject! "unsupported IPLD ADL compiler option" {:options (set (keys options))}))
   (when-not (and (integer? memory-pages) (<= 1 memory-pages 64))
     (reject! "invalid IPLD ADL memory pages" {:memory-pages memory-pages}))
   (let [hir (sema/analyze source)
         by-name (into {} (map (juxt :name identity)) (:functions hir))]
     (when-not (= required-exports (:exports hir))
       (reject! "IPLD ADL source must export the exact operation set in ABI order"
                {:expected required-exports :actual (:exports hir)}))
     (when-not (= (set required-exports) (set (keys by-name)))
       (reject! "IPLD ADL source must contain only the four ABI operations"
                {:expected (set required-exports) :actual (set (keys by-name))}))
     (doseq [[name result body]
             [['validate-representation :bool true]
              ['decode :bytes 'value]
              ['encode :bytes 'value]
              ['validate-logical :bool true]]]
       (when-not (exact-function? (get by-name name) result body)
         (reject! "unsupported IPLD ADL operation body"
                  {:operation name :profile :pure-identity-v1})))
     (let [kir {:format :kotoba.ipld-adl-kir/v1
                :profile :pure-identity-v1
                :operations required-exports}
           compatible (assoc
                       (compatibility/descriptor
                        {:hir-format (:format hir) :kir-format (:format kir)
                         :target target :target-profile target-profile
                         :value-abi :ipld.canonical-dag-cbor/bytes-v1})
                       :tender-contract :ipld-adl-wasm-v1)]
       {:format :wasm/v1 :target target :target-profile target-profile
      :hir hir :kir kir :compatibility compatible
      :bytes (identity-module memory-pages)
      :adl {:abi "ipld-adl-wasm-v1" :profile :pure-identity-v1
            :operations #{:validate-representation :decode :encode :validate-logical}}
      :limits {:memory-pages memory-pages :ambient-authority false
               :imports 0 :max-input-bytes (- (* memory-pages 65536) 1024)}}))))

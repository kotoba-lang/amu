(ns kotoba.compiler.ipld-adl-source
  "Fail-closed Kotoba-source compiler for the ipld-adl-wasm-v1 guest ABI.

  The profile is deliberately closed: byte transforms may return their input
  or the canonical empty bytes value, and validators may return literals, a
  bounded comparison of the actual input byte count, or a bounded comparison
  of one byte read out of the input at a literal index. It is still a real
  source compiler--the admitted Kotoba HIR is the
  authority--and unsupported bodies are rejected instead of being silently
  replaced by another transform."
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

(defn- packed [pointer length]
  (bit-or (bit-shift-left (long pointer) 32) (long length)))

(defn- emit-bool [condition]
  ;; CONDITION leaves one i32 on the stack; select the canonical DAG-CBOR
  ;; true/false node already present in the data segment.
  (concat condition [0x04 0x7e]
          [0x42] (sleb (packed 0 1)) [0x05]
          [0x42] (sleb (packed 1 1)) [0x0b]))

(defn- emit-result [result]
  (cond
    (and (vector? result) (= :input-byte-count-eq (first result)))
    ;; The ABI supplies input length as local 2. Return canonical DAG-CBOR true
    ;; or false without reading guest memory or importing a host function.
    (emit-bool (concat [0x20 0x02 0x41] (sleb (second result)) [0x46]))

    (and (vector? result) (= :input-byte-at-eq (first result)))
    (let [[_ index expected] result]
      (concat
       ;; The bound that matters is the operand's length, not the memory's
       ;; size. Linear memory is two pages and the input is copied in at 1024,
       ;; so an index past the input still lands inside memory and would read
       ;; whatever follows it. `length <= index` therefore has to trap here,
       ;; before the load, rather than being left to Wasm's own bounds check.
       [0x20 0x02 0x41] (sleb index) [0x4d 0x04 0x40 0x00 0x0b]
       ;; i32.load8_u align=0 offset=index, folded onto the ABI pointer. The
       ;; unsigned load is what makes 0xFF read as 255 instead of -1.
       (emit-bool (concat [0x20 0x01 0x2d 0x00] (uleb index)
                          [0x41] (sleb expected) [0x46]))))

    :else
    (case result
      :true (concat [0x42] (sleb (packed 0 1)))
      :false (concat [0x42] (sleb (packed 1 1)))
      :empty-bytes (concat [0x42] (sleb (packed 2 1)))
      :identity [0x20 0x01 0xad 0x42 0x20 0x86
                 0x20 0x02 0xad 0x84])))

(defn- emit-dispatch [entries]
  (if-let [[operation result] (first entries)]
    (concat [0x20 0x00 0x41] (sleb operation) [0x46 0x04 0x7e]
            (emit-result result) [0x05]
            (emit-dispatch (next entries)) [0x0b])
    ;; Invalid operation: trap. The unreachable instruction is polymorphic;
    ;; the dead i64.const keeps the block's result shape explicit to validators.
    [0x00 0x42 0x00]))

(defn- closed-module
  [memory-pages plan profile]
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
        transform (emit-dispatch
                   [[0 (:validate-representation plan)]
                    [1 (:decode plan)] [2 (:encode plan)]
                    [3 (:validate-logical plan)]])
        code (concat [2] (function-body alloc) (function-body transform))
        ;; canonical DAG-CBOR true, false, and empty byte string.
        data [1 0 0x41 0 0x0b 3 0xf5 0xf4 0x40]
        custom (concat (name-bytes "kotoba.ipld-adl")
                       (utf8 (str "ipld-adl-wasm-v1;profile=" (name profile))))
        bytes (concat [0 0x61 0x73 0x6d 1 0 0 0]
                      (section 0 custom)
                      (section 1 types) (section 3 functions)
                      (section 5 memory) (section 7 exports)
                      (section 10 code) (section 11 data))]
    (byte-array (map unchecked-byte bytes))))

(defn- reject! [message data]
  (throw (ex-info message (merge {:phase :ipld-adl-source} data))))

(defn- exact-function-shape? [function result]
  (and (= ['value] (:params function))
       (= [:bytes] (:param-types function))
       (= result (:result function))
       (empty? (:effects function))))

(defn- operation-plan [function name result allowed]
  (when-not (exact-function-shape? function result)
    (reject! "unsupported IPLD ADL operation signature"
             {:operation name :profile :pure-closed-v1}))
  (or (get allowed (:body function))
      (reject! "unsupported IPLD ADL operation body"
               {:operation name :profile :pure-closed-v1 :body (:body function)})))

(defn- byte-at-plan
  "`(= (bytes-at value I) N)` -> `[:input-byte-at-eq I N]`, else nil.

  Returning nil means \"some other body shape\", which the caller reports
  generically. Two well-shaped bodies are rejected here by name instead,
  because a generic message would hide what is actually wrong with them:

  - a negative index is not an index;
  - `bytes-at` yields an unsigned byte, so comparing against anything outside
    0..255 is constantly false. Lowering it would turn a source mistake into a
    validator that quietly always answers no.

  The index must be a literal. That is this profile's restriction, not the
  language's -- `bytes-at` types an arbitrary i64 index -- and it is what keeps
  the emitted bounds check decidable at compile time."
  [body name]
  (let [[op read expected] (when (and (seq? body) (= 3 (count body))) body)]
    (when (and (= '= op) (seq? read) (= 3 (count read))
               (= 'bytes-at (first read)) (= 'value (second read))
               (integer? (nth read 2)) (integer? expected))
      (let [index (nth read 2)]
        (when-not (<= 0 index Integer/MAX_VALUE)
          (reject! "IPLD ADL byte index must be a non-negative int32"
                   {:operation name :profile :pure-closed-v1 :index index}))
        (when-not (<= 0 expected 255)
          (reject! "IPLD ADL byte comparison must be an unsigned byte"
                   {:operation name :profile :pure-closed-v1 :expected expected}))
        [:input-byte-at-eq index expected]))))

(defn- validator-plan [function name]
  (when-not (exact-function-shape? function :bool)
    (reject! "unsupported IPLD ADL operation signature"
             {:operation name :profile :pure-closed-v1}))
  (let [body (:body function)]
    (cond
      (= true body) :true
      (= false body) :false
      (and (seq? body) (= '= (first body)) (= 3 (count body))
           (= '(bytes-count value) (second body))
           (integer? (nth body 2)) (<= 0 (nth body 2) Integer/MAX_VALUE))
      [:input-byte-count-eq (nth body 2)]
      :else
      (or (byte-at-plan body name)
          (reject! "unsupported IPLD ADL operation body"
                   {:operation name :profile :pure-closed-v1 :body body})))))

(defn compile-source
  "Compile the closed pure bytes ADL Kotoba profile to ipld-adl-wasm-v1.

  Validators accept literal true/false, `(= (bytes-count value) N)`, or
  `(= (bytes-at value I) N)` for a literal index and an unsigned byte. Decode
  and encode accept the input value or `(bytes)`, which lowers to canonical
  DAG-CBOR empty bytes (0x40).
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
     (let [plan {:validate-representation
                 (validator-plan (get by-name 'validate-representation)
                                 'validate-representation)
                 :decode (operation-plan (get by-name 'decode) 'decode :bytes
                                         {'value :identity '(bytes-empty) :empty-bytes})
                 :encode (operation-plan (get by-name 'encode) 'encode :bytes
                                         {'value :identity '(bytes-empty) :empty-bytes})
                 :validate-logical
                 (validator-plan (get by-name 'validate-logical)
                                 'validate-logical)}
           profile (cond
                     (= {:validate-representation :true :decode :identity
                         :encode :identity :validate-logical :true} plan)
                     :pure-identity-v1
                     (some vector? (vals plan)) :input-bytes-v1
                     :else :pure-closed-v1)
           kir {:format :kotoba.ipld-adl-kir/v1
                :profile profile :operations required-exports :plan plan}
           compatible (assoc
                       (compatibility/descriptor
                        {:hir-format (:format hir) :kir-format (:format kir)
                         :target target :target-profile target-profile
                         :value-abi :ipld.canonical-dag-cbor/bytes-v1})
                       :tender-contract :ipld-adl-wasm-v1)]
       {:format :wasm/v1 :target target :target-profile target-profile
      :hir hir :kir kir :compatibility compatible
      :bytes (closed-module memory-pages plan profile)
      :adl {:abi "ipld-adl-wasm-v1" :profile profile :plan plan
            :operations #{:validate-representation :decode :encode :validate-logical}}
      :limits {:memory-pages memory-pages :ambient-authority false
               :imports 0 :max-input-bytes (- (* memory-pages 65536) 1024)}}))))

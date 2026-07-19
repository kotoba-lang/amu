(ns kotoba.compiler.backend.wasm
  ;; See `kotoba.compiler.ir`'s ns form for why the whole `:require` clause
  ;; (not just an item inside it) is behind the reader-conditional.
  (:require [kotoba.compiler.value :as value]
            #?@(:cljs [[kotoba.compiler.cljs-i64 :as i64]])))

;; `uleb` only ever encodes small, non-negative, interpreter-internal counts
;; and indices in this file (section/payload lengths, function/type/import
;; indices) -- never an arbitrary `.kotoba` i64 VALUE -- so it stays plain
;; JS-number-based on both runtimes (`(long n)` was already a no-op cast on
;; :clj for values in this range; dropped for :cljs since cljs has no
;; `long`).
(defn- uleb [n]
  (loop [n #?(:clj (long n) :cljs n) out []]
    (let [b (bit-and n 0x7f) n' (unsigned-bit-shift-right n 7)]
      (if (zero? n') (conj out b) (recur n' (conj out (bit-or b 0x80)))))))

;; `sleb` DOES encode arbitrary `.kotoba` i64 literals (`emit-expr`'s
;; `i64.const` case, below) across the FULL signed 64-bit range, so this is
;; the highest-risk port in this file: cljs's own `bit-shift-right` throws
;; on bigint input ("Cannot mix BigInt and other types" -- confirmed live),
;; and even if it didn't, cljs bitwise ops are JS int32-coerced and would
;; silently truncate any constant outside +-2^31 -- a byte-level corruption
;; of the compiled artifact, not just a value-range check failing loudly
;; like `frontend`'s admission check does. The `:cljs` branch works over
;; bigint throughout via `cljs-i64`, using `i64/ashr` (see its own
;; docstring) in place of `bit-shift-right`.
(defn- sleb [n]
  #?(:clj
     (loop [n (long n) out []]
       (let [b (bit-and n 0x7f) n' (bit-shift-right n 7)
             done (or (and (= n' 0) (zero? (bit-and b 0x40)))
                      (and (= n' -1) (not (zero? (bit-and b 0x40)))))]
         (if done (conj out b) (recur n' (conj out (bit-or b 0x80))))))
     :cljs
     (loop [n (i64/->bigint n) out []]
       (let [b (js/Number (bit-and n (js/BigInt 0x7f))) n' (i64/ashr n 7)
             done (or (and (= n' i64/zero) (zero? (bit-and b 0x40)))
                      (and (= n' (js/BigInt -1)) (not (zero? (bit-and b 0x40)))))]
         (if done (conj out b) (recur n' (conj out (bit-or b 0x80))))))))

(defn- section [id payload] (into [id] (concat (uleb (count payload)) payload)))
(defn- utf8 [s]
  #?(:clj (mapv #(bit-and (int %) 0xff) (.getBytes ^String s "UTF-8"))
     :cljs (vec (js/Array.from (.encode (js/TextEncoder.) s)))))
(defn- name-bytes [s] (let [bs (utf8 s)] (into (uleb (count bs)) bs)))

(defn- f64-bytes [n]
  #?(:clj
     (let [bits (Double/doubleToRawLongBits ^double n)]
       (mapv #(bit-and 0xff (unsigned-bit-shift-right bits (* 8 %))) (range 8)))
     :cljs
     (let [buffer (js/ArrayBuffer. 8)
           view (js/DataView. buffer)]
       (.setFloat64 view 0 n true)
       (mapv #(.getUint8 view %) (range 8)))))

(defn- wasm-type [type]
  (case type :i64 0x7e :f64 0x7c
        (throw (ex-info "unsupported Wasm value type" {:phase :backend :type type}))))

(declare expression-type)

(defn- expression-type [form type-env function-types]
  (cond
    #?(:clj (integer? form) :cljs (or (i64/bigint-value? form) (integer? form))) :i64
    (value/f64-value? form) :f64
    (symbol? form) (get type-env form)
    (seq? form)
    (let [[op & args] form]
      (cond
        (= op 'let) (let [[bindings body] args]
                       (loop [pairs (partition 2 bindings) env type-env]
                         (if-let [[name binding] (first pairs)]
                           (recur (next pairs) (assoc env name (expression-type binding env function-types)))
                           (expression-type body env function-types))))
        (= op 'if) (expression-type (second args) type-env function-types)
        (= op 'f64-to-bits) :i64
        (= op 'f64-from-bits) :f64
        (contains? function-types op) (:result (get function-types op))
        :else :i64))
    :else nil))

(defn- local-count [form]
  (if-not (seq? form)
    0
    (let [[op & args] form]
      (if (= op 'let)
        (let [[bindings body] args]
          (+ (quot (count bindings) 2)
             (reduce + (map local-count (take-nth 2 (rest bindings))))
             (local-count body)))
        (reduce + (map local-count args))))))

(declare emit-expr)

(defn- emit-many [forms env ctx]
  (mapcat #(emit-expr % env ctx) forms))

(defn emit-expr [form env {:keys [function-indices intrinsic-indices next-local type-env function-types] :as ctx}]
  (cond
    ;; A literal here may be a bigint (from a `.kotoba` source literal, or
    ;; from `kotoba.compiler.ir`'s coercion once it passes through there)
    ;; or a plain number (synthesized directly by `kotoba.compiler.frontend`
    ;; -- e.g. `when`'s trailing `0`); `sleb` above accepts either.
    #?(:clj (integer? form) :cljs (or (i64/bigint-value? form) (integer? form)))
    (into [0x42] (sleb form))                                    ; i64.const
    (value/f64-value? form) (into [0x44] (f64-bytes form))       ; f64.const
    (symbol? form) [0x20 (get env form)]                         ; local.get
    :else
    (let [[op & args] form]
      (cond
        (= op 'let)
        (let [[bindings body] args]
          (loop [pairs (partition 2 bindings) env env types type-env out [] cursor next-local]
            (if-let [[name value] (first pairs)]
              (let [value-code (emit-expr value env (assoc ctx :next-local cursor :type-env types))
                    value-type (expression-type value types function-types)]
                (recur (next pairs) (assoc env name cursor) (assoc types name value-type)
                       (into out (concat value-code [0x21 cursor])) (inc cursor))) ; local.set
              (into out (emit-expr body env (assoc ctx :next-local cursor :type-env types))))))

        (= op 'if)
        (let [[test then else] args]
          (concat (emit-expr test env ctx)
                  [0x50 0x45 0x04 (wasm-type (expression-type then type-env function-types))]
                  (emit-expr then env ctx) [0x05]
                  (emit-expr else env ctx) [0x0b]))

        (= op 'f64-to-bits)
        (concat (emit-expr (first args) env ctx) [0xbd])         ; i64.reinterpret_f64

        (= op 'f64-from-bits)
        (concat (emit-expr (first args) env ctx) [0xbf])         ; f64.reinterpret_i64

        (= op 'cap-call)
        (let [[cap-id value] args]
          (concat [0x42] (sleb cap-id) (emit-expr value env ctx)
                  [0x10 (get intrinsic-indices 'cap-call)]))

        (contains? '#{pair pair-first pair-second} op)
        (concat (emit-many args env ctx) [0x10 (get intrinsic-indices op)])

        (contains? '#{+ - * quot} op)
        (let [opcode ({'+ 0x7c '- 0x7d '* 0x7e 'quot 0x7f} op)]
          (if (and (= op '-) (= 1 (count args)))
            (concat [0x42 0] (emit-expr (first args) env ctx) [0x7d])
            (concat (emit-expr (first args) env ctx)
                    (mapcat #(concat (emit-expr % env ctx) [opcode]) (rest args)))))

        (contains? '#{bit-and bit-xor} op)
        (let [opcode ({'bit-and 0x83 'bit-xor 0x85} op)]
          (concat (emit-expr (first args) env ctx)
                  (mapcat #(concat (emit-expr % env ctx) [opcode]) (rest args))))

        (contains? '#{= < > <= >=} op)
        (concat (emit-many args env ctx)
                [({'= 0x51 '< 0x53 '> 0x55 '<= 0x57 '>= 0x59} op)
                 0xad])                                          ; extend i32 result to i64

        :else
        (concat (emit-many args env ctx) [0x10 (get function-indices op)]))))) ; call

(defn- function-type [{:keys [params param-types result]}]
  (let [types (or param-types (vec (repeat (count params) :i64)))]
    (concat [0x60] (uleb (count params)) (map wasm-type types)
            [1 (wasm-type (or result :i64))])))

(defn- function-body [function function-indices intrinsic-indices function-types]
  (let [param-env (zipmap (:params function) (range))
        type-env (zipmap (:params function)
                         (or (:param-types function)
                             (repeat (count (:params function)) :i64)))
        locals (local-count (:body function))
        _ (when (and (pos? locals)
                     (some #{:f64} (cons (:result function) (:param-types function))))
            (throw (ex-info "f64 Wasm phase 1 forbids local bindings"
                            {:phase :backend :function (:name function)})))
        declarations (if (zero? locals) [0] (concat [1] (uleb locals) [0x7e]))
        ;; Every call consumes one unit from a module-private monotonic fuel
        ;; global. It is never exported and cannot be replenished by guest code.
        charge [0x23 0 0x50 0x04 0x40 0x00 0x0b ; global.get;eqz;if;unreachable;end
                0x23 0 0x42 1 0x7d 0x24 0]       ; global.get;const 1;sub;global.set
        instructions (concat charge (emit-expr (:body function) param-env
                                {:function-indices function-indices
                                 :intrinsic-indices intrinsic-indices
                                 :type-env type-env
                                 :function-types function-types
                                 :next-local (count (:params function))}))
        body (concat declarations instructions [0x0b])]
    (concat (uleb (count body)) body)))

(defn emit [kir target]
  (let [functions (:functions kir)
        has-cap? (contains? (set (map first (:effects kir))) :cap/call)
        heap-ops (let [found (volatile! #{})]
                   (letfn [(walk [form]
                             (cond
                               (seq? form)
                               (do
                                 (when (contains? '#{pair pair-first pair-second} (first form))
                                   (vswap! found conj (first form)))
                                 (doseq [arg (rest form)] (walk arg)))
                               (coll? form) (doseq [item form] (walk item))))]
                     (doseq [function functions] (walk (:body function)))
                     @found))
        imports (vec (concat
                      (when has-cap? [['cap-call "kotoba:cap" "call"
                                       [0x60 2 0x7e 0x7e 1 0x7e]]])
                      (when (seq heap-ops)
                        [['pair "kotoba:heap" "pair" [0x60 2 0x7e 0x7e 1 0x7e]]
                         ['pair-first "kotoba:heap" "pair-first" [0x60 1 0x7e 1 0x7e]]
                         ['pair-second "kotoba:heap" "pair-second" [0x60 1 0x7e 1 0x7e]]])))
        shift (count imports)
        intrinsic-indices (into {} (map-indexed (fn [index [op]] [op index]) imports))
        indices (into {} (map-indexed (fn [i f] [(:name f) (+ i shift)]) functions))
        function-types (into {} (map (fn [f] [(:name f) {:result (or (:result f) :i64)
                                                         :param-types (or (:param-types f)
                                                                          (vec (repeat (count (:params f)) :i64)))}])
                                     functions))
        types (concat (uleb (+ (count functions) shift))
                      (mapcat #(nth % 3) imports) (mapcat function-type functions))
        import-sec (when (seq imports)
                     (concat (uleb shift)
                             (mapcat (fn [[_ module field _] index]
                                       (concat (name-bytes module) (name-bytes field)
                                               [0] (uleb index)))
                                     imports (range))))
        function-sec (concat (uleb (count functions))
                             (mapcat uleb (range shift (+ shift (count functions)))))
        ;; (global (mut i64) (i64.const 256)); low enough to trap before the
        ;; host call stack becomes the limiting resource.
        global-sec [1 0x7e 1 0x42 0x80 0x02 0x0b]
        ;; Pure functions are exported with their source names. This makes
        ;; runtime parameters observable and testable without host authority.
        export-sec (concat (uleb (count functions))
                           (mapcat (fn [[index function]]
                                     (concat (name-bytes (name (:name function))) [0]
                                             (uleb (+ index shift))))
                                   (map-indexed vector functions)))
        code-sec (concat (uleb (count functions))
                         (mapcat #(function-body % indices intrinsic-indices function-types) functions))
        target-sec (concat (name-bytes "kotoba.target")
                           (utf8 (name target)))]
    (let [bytes (concat [0 0x61 0x73 0x6d 1 0 0 0] (section 0 target-sec)
                        (section 1 types) (when (seq imports) (section 2 import-sec))
                        (section 3 function-sec) (section 6 global-sec)
                        (section 7 export-sec) (section 10 code-sec))]
      #?(:clj (byte-array (map unchecked-byte bytes))
         :cljs (js/Uint8Array.from (clj->js (map #(bit-and % 0xff) bytes)))))))

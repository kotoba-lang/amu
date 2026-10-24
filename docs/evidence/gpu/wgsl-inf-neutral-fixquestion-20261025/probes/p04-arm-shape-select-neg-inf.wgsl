// probe p04 -- THE ARM'S OWN SHAPE, line-for-line: the :max row's
// `var v:f32=select(bitcast<f32>(0xFF800000u),x[i],i<n.value);` with the
// runtime values i and n.value read from storage instead of gid.x / the
// uniform. This is the exact spelling Chrome 155 refused at error@9:33 in
// every :max/:min file of the admitted row.
// Expected per spec 15.7 Finite Math Assumption: shader-creation error.
@group(0) @binding(0) var<storage,read> x: array<f32>;
@group(0) @binding(1) var<storage,read_write> out: array<f32>;
@compute @workgroup_size(1) fn main() {
  let i = u32(x[1]);
  let n_value = u32(x[2]);
  var v:f32=select(bitcast<f32>(0xFF800000u),x[i],i<n_value);
  out[0] = v;
}

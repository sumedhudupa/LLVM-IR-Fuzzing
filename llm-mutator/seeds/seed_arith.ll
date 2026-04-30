; seed_arith.ll - Integer arithmetic, no branches
; Valid LLVM IR that passes llvm-as + opt -passes=verify

define i32 @main() {
entry:
  %a = add i32 10, 20
  %b = sub i32 %a, 5
  %c = mul i32 %b, 2
  %d = sdiv i32 %c, 3
  %e = add i32 %d, 100
  ret i32 %e
}

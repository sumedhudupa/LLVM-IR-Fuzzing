; ModuleID = 'seed_arith.ll'
; Test Case 1: Basic Arithmetic Operations
; Expected exit code: 50  ((10+20-5)*2 = 50)
; Tests: arithmetic substitution, constant mutation

define i32 @main() {
entry:
  %a = add i32 10, 20
  %b = sub i32 %a, 5
  %c = mul i32 %b, 2
  ret i32 %c
}

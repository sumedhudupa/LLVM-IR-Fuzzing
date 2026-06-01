; ModuleID = 'seed_multifunction.ll'
; Test Case 4: Multiple Functions with Call
; Expected exit code: 42  (10 + 32 = 42)
; Tests: cross-function mutation, call preservation

define i32 @add_numbers(i32 %a, i32 %b) {
entry:
  %result = add i32 %a, %b
  ret i32 %result
}

define i32 @main() {
entry:
  %r = call i32 @add_numbers(i32 10, i32 32)
  ret i32 %r
}

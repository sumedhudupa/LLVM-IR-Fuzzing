; seeds/01_basic_add.ll
; Simple function that adds two i32 arguments and returns the result.
; No loops, no PHI, no pointers; easy to mutate and validate.

define i32 @add(i32 %a, i32 %b) {
entry:
  %sum = add i32 %a, %b
  ret i32 %sum
}

; Entry‑point wrapper for differential testing.
; Compilers can optimize this trivially, but even small mutants may expose bugs.

define i32 @main() {
entry:
  %v1 = call i32 @add(i32 3, i32 5)
  ret i32 %v1
}
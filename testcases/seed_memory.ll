; ModuleID = 'seed_memory.ll'
; Test Case 6: Memory Operations (Alloca + Load/Store)
; Expected exit code: 50  (42 + 8 = 50)
; Tests: memory operation types, pointer semantics preservation

define i32 @main() {
entry:
  %ptr = alloca i32
  store i32 42, i32* %ptr
  %val = load i32, i32* %ptr
  %result = add i32 %val, 8
  ret i32 %result
}

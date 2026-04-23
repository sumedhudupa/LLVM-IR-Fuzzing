; ModuleID = 'seed_memory.ll'
; Source: Stack memory operations (alloca, store, load) for LLVM IR fuzzing
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

; Function: swap values using stack allocation
define i64 @swap_and_add(i64 %a, i64 %b) {
entry:
  %ptr_a = alloca i64, align 8
  %ptr_b = alloca i64, align 8
  %ptr_temp = alloca i64, align 8

  store i64 %a, i64* %ptr_a, align 8
  store i64 %b, i64* %ptr_b, align 8

  ; temp = a
  %val_a = load i64, i64* %ptr_a, align 8
  store i64 %val_a, i64* %ptr_temp, align 8

  ; a = b
  %val_b = load i64, i64* %ptr_b, align 8
  store i64 %val_b, i64* %ptr_a, align 8

  ; b = temp
  %val_temp = load i64, i64* %ptr_temp, align 8
  store i64 %val_temp, i64* %ptr_b, align 8

  ; return new_a + new_b (which is b + a)
  %new_a = load i64, i64* %ptr_a, align 8
  %new_b = load i64, i64* %ptr_b, align 8
  %result = add i64 %new_a, %new_b
  ret i64 %result
}

; Function: accumulate values on stack
define i64 @accumulate(i64 %n) {
entry:
  %sum_ptr = alloca i64, align 8
  store i64 0, i64* %sum_ptr, align 8

  %i_ptr = alloca i64, align 8
  store i64 1, i64* %i_ptr, align 8
  br label %loop

loop:
  %i_val = load i64, i64* %i_ptr, align 8
  %done = icmp sgt i64 %i_val, %n
  br i1 %done, label %exit, label %body

body:
  %sum_val = load i64, i64* %sum_ptr, align 8
  %new_sum = add i64 %sum_val, %i_val
  store i64 %new_sum, i64* %sum_ptr, align 8

  %i_next = add i64 %i_val, 1
  store i64 %i_next, i64* %i_ptr, align 8
  br label %loop

exit:
  %final = load i64, i64* %sum_ptr, align 8
  ret i64 %final
}

; Main entry point
define i32 @main() {
entry:
  %v1 = call i64 @swap_and_add(i64 10, i64 20)
  %v2 = call i64 @accumulate(i64 5)
  %total = add i64 %v1, %v2
  %result = trunc i64 %total to i32
  ret i32 %result
}

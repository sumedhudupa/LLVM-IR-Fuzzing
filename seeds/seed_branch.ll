; ModuleID = 'seed_branch.ll'
; Source: Simple conditional branch test for LLVM IR fuzzing
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

; Function: absolute value using conditional branches
define i64 @abs_val(i64 %x) {
entry:
  %cmp = icmp slt i64 %x, 0
  br i1 %cmp, label %negate, label %done

negate:
  %neg = sub i64 0, %x
  br label %done

done:
  %result = phi i64 [ %neg, %negate ], [ %x, %entry ]
  ret i64 %result
}

; Function: max of two values with nested compare
define i64 @max_val(i64 %a, i64 %b) {
entry:
  %cmp = icmp sgt i64 %a, %b
  br i1 %cmp, label %a_is_max, label %b_is_max

a_is_max:
  ret i64 %a

b_is_max:
  ret i64 %b
}

; Main entry point
define i32 @main() {
entry:
  %v1 = call i64 @abs_val(i64 -42)
  %v2 = call i64 @max_val(i64 %v1, i64 100)
  %result = trunc i64 %v2 to i32
  ret i32 %result
}

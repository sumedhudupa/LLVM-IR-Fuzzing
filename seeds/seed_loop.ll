; ModuleID = 'seed_loop.ll'
; Source: Simple loop with PHI node for LLVM IR fuzzing
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

; Function: factorial calculation using loop
define i64 @factorial(i64 %n) {
entry:
  %cmp = icmp slt i64 %n, 0
  br i1 %cmp, label %negative, label %init

negative:
  ret i64 0

init:
  br label %loop

loop:
  %i = phi i64 [ 1, %init ], [ %i_next, %loop ]
  %acc = phi i64 [ 1, %init ], [ %acc_next, %loop ]
  %acc_next = mul i64 %acc, %i
  %i_next = add i64 %i, 1
  %done = icmp sgt i64 %i_next, %n
  br i1 %done, label %exit, label %loop

exit:
  ret i64 %acc
}

; Function: sum of squares
define i64 @sum_squares(i64 %n) {
entry:
  br label %loop

loop:
  %i = phi i64 [ 1, %entry ], [ %i_next, %loop ]
  %sum = phi i64 [ 0, %entry ], [ %sum_next, %loop ]
  %sq = mul i64 %i, %i
  %sum_next = add i64 %sum, %sq
  %i_next = add i64 %i, 1
  %done = icmp sgt i64 %i_next, %n
  br i1 %done, label %exit, label %loop

exit:
  ret i64 %sum
}

; Main entry point
define i32 @main() {
entry:
  %fact5 = call i64 @factorial(i64 5)
  %sum3 = call i64 @sum_squares(i64 3)
  %total = add i64 %fact5, %sum3
  %result = trunc i64 %total to i32
  ret i32 %result
}

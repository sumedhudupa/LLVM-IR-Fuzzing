; ModuleID = 'seed_arith.ll'
; Source: hand-crafted minimal LLVM IR for fuzzing tests
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

; Function: add two integers
define i64 @add(i64 %a, i64 %b) {
entry:
  %result = add i64 %a, %b
  ret i64 %result
}

; Function: compare and branch
define i64 @max(i64 %x, i64 %y) {
entry:
  %cmp = icmp slt i64 %x, %y
  br i1 %cmp, label %then, label %else

then:
  ret i64 %y

else:
  ret i64 %x
}

; Function: simple loop counter
define i64 @loop_sum(i64 %n) {
entry:
  br label %loop

loop:
  %i    = phi i64 [ 0, %entry ], [ %i_next, %loop ]
  %acc  = phi i64 [ 0, %entry ], [ %acc_next, %loop ]
  %acc_next = add i64 %acc, %i
  %i_next   = add i64 %i, 1
  %done = icmp eq i64 %i_next, %n
  br i1 %done, label %exit, label %loop

exit:
  ret i64 %acc_next
}

; --- Main Entry Point for Differential Testing ---
@.str = private unnamed_addr constant [13 x i8] c"Result: %ld\0A\00", align 1
declare i32 @printf(i8*, ...)

define i32 @main() {
entry:
  %add_res = call i64 @add(i64 5, i64 10)
  %call1 = call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([13 x i8], [13 x i8]* @.str, i32 0, i32 0), i64 %add_res)
  
  %max_res = call i64 @max(i64 100, i64 50)
  %call2 = call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([13 x i8], [13 x i8]* @.str, i32 0, i32 0), i64 %max_res)
  
  %loop_res = call i64 @loop_sum(i64 10)
  %call3 = call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([13 x i8], [13 x i8]* @.str, i32 0, i32 0), i64 %loop_res)
  
  ret i32 0
}

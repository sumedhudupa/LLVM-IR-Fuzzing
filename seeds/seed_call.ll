; ModuleID = 'seed_call.ll'
; Source: Function calls with arguments and returns for LLVM IR fuzzing
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

; Function: add two integers
define i64 @add(i64 %a, i64 %b) {
entry:
  %result = add i64 %a, %b
  ret i64 %result
}

; Function: multiply two integers
define i64 @multiply(i64 %a, i64 %b) {
entry:
  %result = mul i64 %a, %b
  ret i64 %result
}

; Function: chained arithmetic - (a + b) * c
define i64 @chained(i64 %a, i64 %b, i64 %c) {
entry:
  %sum = call i64 @add(i64 %a, i64 %b)
  %result = call i64 @multiply(i64 %sum, i64 %c)
  ret i64 %result
}

; Function: identity function
define i64 @identity(i64 %x) {
entry:
  ret i64 %x
}

; Main entry point
define i32 @main() {
entry:
  %v1 = call i64 @add(i64 10, i64 20)
  %v2 = call i64 @multiply(i64 %v1, i64 2)
  %v3 = call i64 @chained(i64 1, i64 2, i64 3)
  %v4 = call i64 @identity(i64 42)
  %sum1 = add i64 %v2, %v3
  %total = add i64 %sum1, %v4
  %result = trunc i64 %total to i32
  ret i32 %result
}

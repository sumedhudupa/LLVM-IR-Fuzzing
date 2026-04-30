; seed_call.ll - Function call + return value
; Valid LLVM IR that passes llvm-as + opt -passes=verify

define i32 @helper(i32 %x) {
entry:
  %result = mul i32 %x, 2
  ret i32 %result
}

define i32 @main() {
entry:
  %a = call i32 @helper(i32 10)
  %b = call i32 @helper(i32 20)
  %sum = add i32 %a, %b
  ret i32 %sum
}

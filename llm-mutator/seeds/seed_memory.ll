; seed_memory.ll - Alloca + store + load
; Valid LLVM IR that passes llvm-as + opt -passes=verify

define i32 @main() {
entry:
  %x = alloca i32, align 4
  %y = alloca i32, align 4
  %z = alloca i32, align 4
  store i32 10, i32* %x, align 4
  store i32 20, i32* %y, align 4
  %x_val = load i32, i32* %x, align 4
  %y_val = load i32, i32* %y, align 4
  %sum = add i32 %x_val, %y_val
  store i32 %sum, i32* %z, align 4
  %result = load i32, i32* %z, align 4
  ret i32 %result
}

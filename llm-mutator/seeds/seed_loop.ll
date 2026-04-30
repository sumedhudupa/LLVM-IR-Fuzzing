; seed_loop.ll - Loop with PHI node
; Valid LLVM IR that passes llvm-as + opt -passes=verify

define i32 @main() {
entry:
  %i = alloca i32, align 4
  %sum = alloca i32, align 4
  store i32 0, i32* %i, align 4
  store i32 0, i32* %sum, align 4
  br label %loop

loop:
  %i_val = load i32, i32* %i, align 4
  %sum_val = load i32, i32* %sum, align 4
  %new_sum = add i32 %sum_val, %i_val
  store i32 %new_sum, i32* %sum, align 4
  %new_i = add i32 %i_val, 1
  store i32 %new_i, i32* %i, align 4
  %cmp = icmp slt i32 %new_i, 10
  br i1 %cmp, label %loop, label %exit

exit:
  %final_sum = load i32, i32* %sum, align 4
  ret i32 %final_sum
}

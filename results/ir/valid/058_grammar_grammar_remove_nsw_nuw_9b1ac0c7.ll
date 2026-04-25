define i32 @loop_simple(i32 %n) {
entry:
  br label %loop

loop:
  %i = phi i32 [0, %entry], [%next_i, %loop]
  %sum = phi i32 [0, %entry], [%next_sum, %loop]
  %next_sum = add i32 %sum, %i
  %next_i = add i32 %i, 1
  %cmp = icmp slt i32 %next_i, %n
  br i1 %cmp, label %loop, label %exit

exit:
  ret i32 %next_sum
}

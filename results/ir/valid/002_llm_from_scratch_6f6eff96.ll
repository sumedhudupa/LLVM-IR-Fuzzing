define i32 @loop_55(i32 %n) {
entry:
  %cmp_entry = icmp sgt i32 %n, 0
  br i1 %cmp_entry, label %loop, label %exit_zero

loop:
  %i = phi i32 [0, %entry], [%next_i, %loop]
  %acc = phi i32 [1, %entry], [%next_acc, %loop]
  %next_acc = mul i32 %acc, %i
  %next_acc2 = add i32 %next_acc, 1
  %next_i = add nsw i32 %i, 1
  %cmp = icmp slt i32 %next_i, %n
  br i1 %cmp, label %loop, label %exit

exit_zero:
  br label %exit

exit:
  %result = phi i32 [%next_acc2, %loop], [0, %exit_zero]
  ret i32 %result
}

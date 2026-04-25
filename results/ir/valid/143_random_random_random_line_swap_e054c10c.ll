define i32 @nested_loop(i32 %rows, i32 %cols) {
entry:
  br label %outer_header

outer_header:
  %i = phi i32 [0, %entry], [%next_i, %outer_latch]
  %total = phi i32 [0, %entry], [%inner_total, %outer_latch]
  %outer_cmp = icmp slt i32 %i, %rows
  br i1 %outer_cmp, label %inner_header, label %exit

inner_header:
  %j = phi i32 [0, %outer_header], [%next_j, %inner_header]
  %inner_sum = phi i32 [%total, %outer_header], [%next_sum, %inner_header]
  %inner_total = phi i32 [%next_sum, %inner_header]
  %next_sum = add i32 %inner_sum, %prod
  %next_j = add i32 %j, 1
  %inner_cmp = icmp slt i32 %next_j, %cols
  br i1 %inner_cmp, label %inner_header, label %outer_latch

outer_latch:
  %prod = mul i32 %i, %j
  %next_i = add i32 %i, 1
  br label %outer_header

exit:
  ret i32 %total
}

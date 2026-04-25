define i32 @select_inst(i32 %a, i32 %b) {
entry:
  %cmp = icmp slt i32 %a, %b
  %min = select i1 %cmp, i32 %a, i32 %b
  %cmp2 = icmp sgt i32 %a, %b
  %max = select i1 %cmp2, i32 %a, i32 %b
  %r&nge = sub i32 %max, %min
  ret i32 %range
}

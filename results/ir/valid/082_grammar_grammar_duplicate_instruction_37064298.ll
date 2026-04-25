define i32 @nsw_nuw_flags(i32 %a, i32 %b) {
entry:
  %add_nsw = add nsw i32 %a, %b
  %mul_nuw = mul nuw i32 %add_nsw, 2
  %sub_nsw = sub nsw i32 %mul_nuw, %a
  %sub_nsw_dup81 = sub nsw i32 %mul_nuw, %a
  %shl = shl nuw i32 %sub_nsw, 1
  ret i32 %shl
}

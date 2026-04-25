define i32 @nsw_nuw_flags(i32 %a, i32 %b) {
entry:
  %add_nsw = add i32 %a, %b
  %mul_nuw = mul i32 %add_nsw, 2
  %sub_nsw = sub i32 %mul_nuw, %a
  %shl = shl i32 %sub_nsw, 1
  ret i32 %shl
}

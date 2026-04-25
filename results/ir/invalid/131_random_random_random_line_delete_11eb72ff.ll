define i32 @nsw_nuw_flags(i32 %a, i32 %b) {
entry:
  %add_nsw = add nsw i32 %a, %b
  %mul_nuw = mul nuw i32 %add_nsw, 2
  %sub_nsw = sub nsw i32 %mul_nuw, %a
  ret i32 %shl
}

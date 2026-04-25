define i32 @simple_add(i32 %a, i32 %b) {
entry:
  %result = add i32 %b, %a
  ret i32 %result
}

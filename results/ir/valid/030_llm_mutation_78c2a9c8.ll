define i32 @branch_489(i32 %x, i32 %y) {
entry:
  %cmp1 = icmp sgt i32 %x, %y
  br i1 %cmp1, label %then1, label %else1

then1:
  %a = add i32 %x, %y
  %cmp2 = icmp eq i32 %a, 0
  br i1 %cmp2, label %inner_then, label %merge

else1:
  %b = sub i32 %y, %x
  br label %merge

inner_then:
  %c = mul i32 %x, 2
  br label %merge

merge:
  %res = phi i32 [%a, %then1], [%b, %else1], [%c, %inner_then]
  ret i32 %res
}

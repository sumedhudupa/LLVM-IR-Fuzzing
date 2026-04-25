define i32 @branch_simple(i32 %x) {
entry:
  %cmp = icmp sgt i32 %x, 0
  br i1 %cmp, label %positive, label %negative

positive:
  %add = add i32 %x, 1
  br label %merge

negative:
  %sub = sub nsw i32 0, %x
  br label %merge

merge:
  %result = phi i32 [%add, %positive], [%sub, %negative]
  ret i32 %result
}

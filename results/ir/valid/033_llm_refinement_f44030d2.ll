define i32 @arith_53(i32 %a, i32 %b) {
entry:
  %sum = add nsw i32 %a, %b
  %prod = mul nsw i32 %sum, %a
  %diff = sub i32 %prod, %b
  %cmp = icmp sgt i32 %diff, 0
  br i1 %cmp, label %pos, label %neg

pos:
  %r1 = add i32 %diff, 1
  br label %done

neg:
  %r2 = sub i32 0, %diff
  br label %done

done:
  %result = phi i32 [%r1, %pos], [%r2, %neg]
  ret i32 %result
}
